"""Shared helpers for the pordata scripts.

The functions here define the corpus (which sitemap URLs count as
indicator pages) and how the harvested JSONL is read. Harvest, QA and
build all import from here so the definition cannot drift.
"""

import json
import pathlib
import re

URLS_FILE = pathlib.Path("data/sitemap-urls.txt")
LASTMOD_FILE = pathlib.Path("data/sitemap-lastmod.tsv")
PAGES_FILE = pathlib.Path("data/catalogue/pages.jsonl")

AREA_PREFIXES = ("portugal", "municipios", "europa")

# UI text that marks the end of the real Fontes/Entidades value on a page.
FONTES_BOUNDARY = (r"Carregue|ver tabela|ver o gráfico|Última|Ultima"
                   r"|Consulte|©|Fontes?\s*/\s*Entidades")


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


def load_records(pages_file: pathlib.Path = PAGES_FILE) -> dict[str, dict]:
    """url -> record, keeping the LAST occurrence of each url so that
    re-harvested (stale) pages override their older lines."""
    records: dict[str, dict] = {}
    if not pages_file.exists():
        return records
    for line in pages_file.read_text(encoding="utf-8").splitlines():
        try:
            rec = json.loads(line)
            records[rec["url"]] = rec
        except (ValueError, KeyError):
            continue
    return records


def write_records(records: dict[str, dict],
                  pages_file: pathlib.Path = PAGES_FILE) -> None:
    """Rewrite the JSONL deduplicated, in stable url order."""
    with pages_file.open("w", encoding="utf-8") as fh:
        for url in sorted(records):
            fh.write(json.dumps(records[url], ensure_ascii=False) + "\n")
