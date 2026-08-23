"""Shared helpers for the pordata scripts.

The functions here define the corpus (which sitemap URLs count as
indicator pages) and how the harvested JSONL is read. Harvest, QA and
build all import from here so the definition cannot drift.
"""

import datetime
import json
import os
import pathlib
import re

URLS_FILE = pathlib.Path("data/sitemap-urls.txt")
LASTMOD_FILE = pathlib.Path("data/sitemap-lastmod.tsv")
PAGES_FILE = pathlib.Path("data/catalogue/pages.jsonl")
ABANDONED_FILE = pathlib.Path("data/catalogue/abandoned.txt")

AREA_PREFIXES = ("portugal", "municipios", "europa")

# UI text that marks the end of the real Fontes/Entidades value on a page.
# Europa pages append "Carregue aqui para ver o gráfico…", municipal pages
# append the toolbar "Operações Opções Ver Gráfico Ranking".
FONTES_BOUNDARY = (r"Carregue|ver tabela|ver o gráfico|Última|Ultima"
                   r"|Consulte|©|Fontes?\s*/\s*Entidades"
                   r"|Operações|Opções|Ver Gráfico|Ranking|Simbologia"
                   r"|Exportar")


# ---- parse-time shape assertions (roadmap 6a) ------------------------
# The QA gate catches a field going *empty*; it cannot catch a field
# filled with something well-formed but wrong. These validators run at
# parse time: a value that fails its shape is dropped rather than
# published, and the record carries a warning so the gate sees the
# coverage fall instead of the site quietly serving junk.

MAX_FONTES_LEN = 200
MAX_FONTE_PART_LEN = 90
MAX_FONTE_PART_WORDS = 14
EARLIEST_PLAUSIBLE_DATE = "1990-01-01"


def valid_date(value: str, today: str | None = None) -> bool:
    """ISO YYYY-MM-DD, a real calendar date, and inside the window a
    PORDATA update could plausibly carry. The site's default sort is
    'newest first', so a garbage date does not just display wrong - it
    takes over the top of the results."""
    if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value or ""):
        return False
    try:
        datetime.date.fromisoformat(value)
    except ValueError:            # 2026-02-31 and friends
        return False
    today = today or datetime.datetime.now(datetime.UTC).date().isoformat()
    # +2 days of slack for timezones and for PORDATA post-dating a release
    limit = (datetime.date.fromisoformat(today)
             + datetime.timedelta(days=2)).isoformat()
    return EARLIEST_PLAUSIBLE_DATE <= value <= limit


def plausible_fontes(value: str) -> bool:
    """A Fontes/Entidades value is a short list of organisation names.
    The boundary vocabulary that trims it is a fixed list, so any new UI
    string PORDATA introduces flows straight through: this checks the
    *shape* instead of enumerating what to strip."""
    if not value:
        return False
    if len(value) > MAX_FONTES_LEN:
        return False
    for part in re.split(r"[|,;]", value):
        part = part.strip()
        if not part:
            continue
        if len(part) > MAX_FONTE_PART_LEN:
            return False
        if len(part.split()) > MAX_FONTE_PART_WORDS:
            return False
    return True


def name_from_title(title: str) -> str:
    """PORDATA titles are '<Area>: <Name> | Pordata'. If that template
    ever changes, deriving a name from it yields junk - so require the
    suffix and return '' when it is absent, letting the build fall back
    to the slug and the gate see name coverage drop."""
    if not re.search(r"\|\s*Pordata\s*$", title or ""):
        return ""
    name = re.sub(r"\s*\|\s*Pordata\s*$", "", title)
    name = re.sub(r"^(Portugal|Municípios|Europa):\s*", "", name)
    return name.strip()


def clean_fontes(raw: str) -> str:
    """Trim a captured Fontes/Entidades string at the first UI boundary."""
    return re.split(FONTES_BOUNDARY, raw)[0].strip(" ,;|-")


def targets(urls_file: pathlib.Path = URLS_FILE) -> list[str]:
    """Indicator pages: the three statistical areas, PT tree, slug ending
    in a numeric id, quadro+resumo summary tables excluded."""
    urls = urls_file.read_text(encoding="utf-8").split()
    picked = []
    for u in urls:
        path = u.split("pordata.pt/", 1)[-1]
        area = path.split("/", 1)[0]
        if area in AREA_PREFIXES and "/en/" not in u \
                and "quadro+resumo" not in u and re.search(r"-\d+$", u):
            picked.append(u)
    return picked


def abandoned(file: pathlib.Path = ABANDONED_FILE) -> set[str]:
    """URLs PORDATA still lists but no longer serves. Retrying them for
    ever is dishonest bookkeeping: they are skipped by the harvest plan
    and tombstoned at build time, exactly like a page that left the
    sitemap. One URL per line; '#' comments carry the evidence."""
    if not file.exists():
        return set()
    return {ln.strip() for ln in file.read_text(encoding="utf-8").splitlines()
            if ln.strip() and not ln.startswith("#")}


def lastmods(tsv_file: pathlib.Path = LASTMOD_FILE) -> dict[str, str]:
    """url -> lastmod (may be empty string) from the watcher's snapshot."""
    if not tsv_file.exists():
        return {}
    entries = {}
    for line in tsv_file.read_text(encoding="utf-8").splitlines():
        url, _, mod = line.partition("\t")
        if url:
            entries[url] = mod
    return entries


# Set by load_records: lines that could not be parsed into a record.
# Non-zero means the JSONL is corrupt and the catalogue built from it is
# incomplete — qa_catalogue.py gates on this rather than letting a
# truncated file publish a silently shrunken catalogue.
SKIPPED_LINES = 0


def load_records(pages_file: pathlib.Path = PAGES_FILE) -> dict[str, dict]:
    """url -> record, keeping the LAST occurrence of each url so that
    re-harvested (stale) pages override their older lines. Unparseable
    lines are skipped but counted in SKIPPED_LINES, never silently."""
    global SKIPPED_LINES
    records: dict[str, dict] = {}
    SKIPPED_LINES = 0
    if not pages_file.exists():
        return records
    for line in pages_file.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
            records[rec["url"]] = rec
        except (ValueError, KeyError, TypeError):
            # TypeError: a valid-JSON non-object line (null, 42, "x")
            SKIPPED_LINES += 1
    if SKIPPED_LINES:
        print(f"WARNING: {SKIPPED_LINES} unparseable line(s) in "
              f"{pages_file}; records built from it are incomplete")
    return records


def write_records(records: dict[str, dict],
                  pages_file: pathlib.Path = PAGES_FILE) -> None:
    """Rewrite the JSONL deduplicated, in stable url order. Atomic: a
    crash mid-write leaves the previous file intact rather than a
    truncated one."""
    tmp = pages_file.with_suffix(pages_file.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        for url in sorted(records):
            fh.write(json.dumps(records[url], ensure_ascii=False) + "\n")
    os.replace(tmp, pages_file)
