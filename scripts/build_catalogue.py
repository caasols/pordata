#!/usr/bin/env python3
"""Phase C: build the publishable catalogue from the harvested JSONL.

Reads data/catalogue/pages.jsonl (+ data/catalogue/featured.json if the
featured-sets job has run) and writes the static "API" the site and any
programmatic consumer use:

    docs/data/catalogue.json   one object per indicator (see fields below)
    docs/data/catalogue.csv    same rows, flat, for spreadsheet users
    docs/data/stats.json       counts + build date for the site header

Tombstones: a record whose url is no longer in the sitemap target list is
kept with removed=true, never deleted (deprecated indicators still matter
historically).

Offline; run after every harvest chunk. Error records are excluded from
the published catalogue until their retry succeeds.
"""

import collections
import csv
import json
import os
import pathlib
import re
import sys
import time
import unicodedata
from urllib.parse import unquote

if __package__:
    from . import pordata_lib as lib
else:  # executed directly, e.g. python3 scripts/build_catalogue.py
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import pordata_lib as lib

FEATURED_FILE = pathlib.Path("data/catalogue/featured.json")
UNMATCHED_FILE = pathlib.Path("data/catalogue/FEATURED-UNMATCHED.md")
OUT_DIR = pathlib.Path("docs/data")

AREA_LABELS = {"portugal": "Portugal", "municipios": "Municípios",
               "europa": "Europa"}


# featured.json groups -> which catalogue area their names live in
GROUP_AREAS = {"quadro_resumo_municipios": "municipios",
               "quadro_resumo_europa": "europa"}

# /en tree area segment -> PT catalogue area. Page ids are only unique
# within an area (id 6 is cinema+recintos in municipios and a population
# series in portugal), so every id-keyed lookup must carry the area.
EN_AREAS = {"portugal": "portugal", "municipalities": "municipios",
            "europe": "europa"}


NAME_STOPWORDS = {"de", "da", "do", "das", "dos", "e", "em", "no", "na",
                  "nos", "nas", "por", "para", "a", "o", "os", "as", "com",
                  "que", "total", "%", "€"}


def norm_name(s: str) -> str:
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower().replace("-", "")  # auto-estradas == autoestradas
    s = re.sub(r"[^\w\s%€]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def content_tokens(s: str) -> set[str]:
    """Meaning-bearing tokens: stopwords out, crude plural strip so that
    limites==limite across the quadro and catalogue spellings."""
    tokens = set()
    for t in norm_name(s).split():
        if t in NAME_STOPWORDS or len(t) < 2:
            continue
        if len(t) > 3 and t.endswith("s"):
            t = t[:-1]
        tokens.add(t)
    return tokens


# Quadro names that carry an inline definition after a dash, and the
# negation words that must agree between a quadro name and its match
# ("Alunos do ensino NÃO superior" must never match "ensino superior").
DEFINITION_DASH = re.compile(r"\s+[—–-]\s+")
NEGATIONS = {"nao", "sem"}

# Tokens that flip an indicator's meaning. A candidate carrying one the
# quadro name does not is a different indicator, however well its other
# tokens overlap: each of these was an observed mis-match before the
# 2026-08-23 audit ("antes"->"após transferências sociais", "feminina"
# ->"Homens", plain "Taxa de desemprego"->"de longa duração",
# "Casamentos"->"Casamentos dissolvidos por morte").
CONTRAST = {"ante", "apo", "homen", "mulhere", "feminina", "masculina",
            "longa", "densidade", "concentracao", "dissolvido", "morte",
            "dependencia", "credito", "desigualdade"}

# Beyond an exact name match we accept a candidate only when it contains
# EVERY quadro token (containment 1.0) and adds at most this many of its
# own. Matching a human curation is a curation problem: precision here,
# `overrides` in featured.json for the rest. Loosening this re-introduces
# the wrong-indicator-under-a-curated-badge failure.
MAX_EXTRA_TOKENS = 2


def split_definition(name: str) -> str:
    """Quadro-resumo names often append a definition after a dash
    ('Índice de envelhecimento — número de idosos…'); the catalogue
    carries only the head."""
    return DEFINITION_DASH.split(name, maxsplit=1)[0].strip()


def resolve_featured(records: dict) -> tuple[dict[tuple, list[str]], dict]:
    """Match quadro-resumo indicator names to catalogue (area, id) keys
    (the quadro pages carry names but no ids).

    Three passes per group, each **injective** — a catalogue entry can
    satisfy at most one quadro name, so near-identical names (the five
    school levels, 'antes'/'após transferências sociais') can no longer
    collapse onto one id and mis-flag four of them:
      1. owner overrides from featured.json (`overrides`), for names the
         matcher cannot reach;
      2. exact normalized match, on the full name then the dash-split head;
      3. token containment >= FUZZY_FLOOR, assigned globally best-first,
         with negation words required to agree and the candidate carrying
         the fewest extra tokens preferred.
    """
    if not FEATURED_FILE.exists():
        return {}, {}
    data = json.loads(FEATURED_FILE.read_text(encoding="utf-8"))
    overrides = data.get("overrides", {})
    flags: dict[tuple, list[str]] = {}
    stats: dict = {}
    for group, area in GROUP_AREAS.items():
        names = data.get(group, {}).get("indicator_names", [])
        if not names:
            continue
        pool = [(norm_name(r["name"]), content_tokens(r["name"]), r["id"])
                for r in records.values()
                if "error" not in r and r["area"] == area and r.get("name")]
        exact: dict[str, int] = {}
        for n, _, rid in pool:
            exact.setdefault(n, rid)

        assigned: dict[str, int] = {}
        taken: set[int] = set()

        for name, rid in overrides.get(group, {}).items():
            if name in names and rid not in taken:
                assigned[name], _ = rid, taken.add(rid)

        for name in names:
            if name in assigned:
                continue
            for form in (norm_name(name), norm_name(split_definition(name))):
                rid = exact.get(form)
                if rid is not None and rid not in taken:
                    assigned[name], _ = rid, taken.add(rid)
                    break

        scored = []
        for name in names:
            if name in assigned:
                continue
            tokens = content_tokens(split_definition(name))
            if not tokens:
                continue
            for _, cand_tokens, pid in pool:
                if not tokens <= cand_tokens:      # containment must be 1.0
                    continue
                extra = cand_tokens - tokens
                if len(extra) > MAX_EXTRA_TOKENS or extra & CONTRAST:
                    continue
                if (cand_tokens & NEGATIONS) != (tokens & NEGATIONS):
                    continue
                scored.append((-len(extra), name, pid))
        # fewest extra tokens first, then a stable name order, so the
        # assignment is deterministic and each id is claimed once
        for _, name, pid in sorted(scored, key=lambda c: (c[0], c[1]),
                                   reverse=True):
            if name in assigned or pid in taken:
                continue
            assigned[name], _ = pid, taken.add(pid)

        for name in names:
            rid = assigned.get(name)
            if rid is None:
                continue
            key = (area, rid)
            flags.setdefault(key, [])
            if "quadro_resumo" not in flags[key]:
                flags[key].append("quadro_resumo")
        stats[group] = {
            "names": len(names),
            "matched": len(assigned),
            # distinct rows is what the site actually shows; it equalled
            # matched only by accident before injectivity was enforced
            "distinct_rows": len(taken),
            "unmatched": [n for n in names if n not in assigned],
        }
    return flags, stats


def write_unmatched_worksheet(records: dict, stats: dict) -> None:
    """Quadro names the matcher deliberately would not guess at, each
    with its nearest catalogue candidates and a paste-ready snippet for
    featured.json's `overrides`. Matching a human curation needs a human
    for the tail; this makes that a copy-paste job, not research."""
    if not stats:
        return
    lines = ["# Featured (quadro-resumo) names still unmatched", "",
             "The matcher only accepts exact names and containment "
             "matches with at most "
             f"{MAX_EXTRA_TOKENS} extra tokens (audit ②: looser rules "
             "flagged the wrong indicator under a curated badge). The "
             "rest are listed here with candidates.", "",
             "Some have no counterpart at all — several quadro rows are "
             "derived aggregates PORDATA publishes only inside the "
             "quadro, and a few share one catalogue page. Those stay "
             "unmatched by design; leave them.", "",
             "To pin one, add it to `data/catalogue/featured.json`:", "",
             "```json", '"overrides": {"<group>": {"<quadro name>": <id>}}',
             "```", ""]
    for group, area in GROUP_AREAS.items():
        st = stats.get(group)
        if not st or not st["unmatched"]:
            continue
        pool = [(content_tokens(r["name"]), r["id"], r["name"])
                for r in records.values()
                if "error" not in r and r["area"] == area and r.get("name")]
        lines += [f"## {group} — {len(st['unmatched'])} of {st['names']} "
                  f"unmatched", ""]
        for name in st["unmatched"]:
            tokens = content_tokens(split_definition(name))
            ranked = sorted(
                ((len(tokens & ct) / len(tokens) if tokens else 0,
                  -len(ct - tokens), rid, nm) for ct, rid, nm in pool),
                key=lambda c: (c[0], c[1]), reverse=True)[:3]
            lines.append(f"- **{name}**")
            for score, neg_extra, rid, nm in ranked:
                lines.append(f"  - `{rid}` {score:.0%} (+{-neg_extra}) {nm}")
        lines.append("")
    UNMATCHED_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_en_names(sitemap_text: str) -> dict[tuple, str]:
    """(area, id) -> English name, derived from the /en tree's slugs in
    the same sitemap snapshot (EN pages share page ids with their PT
    originals, so this costs zero requests). Keyed by area as well as id
    because ids repeat across areas. Slugs are lowercase ASCII; we
    titlecase the first letter only."""
    en_names: dict[tuple, str] = {}
    for url in sitemap_text.split():
        m = re.match(
            r"https://www\.pordata\.pt/en/"
            r"(portugal|municipalities|europe)/([^/]+)-(\d+)$", url)
        if not m or "summary+table" in url:
            continue
        name = re.sub(r"\s+", " ",
                      unquote(m.group(2)).replace("+", " ")).strip()
        if name:
            en_names[(EN_AREAS[m.group(1)], int(m.group(3)))] = \
                name[:1].upper() + name[1:]
    return en_names


def strip_markup(s: str) -> str:
    """PORDATA titles carry inline HTML (<em>per capita</em>,
    CO<sub>2</sub>, km<sup>2</sup>). Digits in sub/sup become their
    Unicode forms (shared with the harvester via `lib`); every other tag
    is dropped."""
    s = lib.scripts_to_unicode(s)
    s = re.sub(r"<[^>]+>", "", s)
    return re.sub(r"\s+", " ", s).strip()


def name_from_slug(slug: str) -> str:
    """Readable fallback name for records whose <title> parse came up
    empty: the PT slug minus the id, pluses as spaces."""
    text = unquote(re.sub(r"-\d+$", "", slug.split("/")[-1])).replace("+", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text[:1].upper() + text[1:]


def split_fontes(fontes: str) -> list[str]:
    # defensive re-trim: records harvested before the parser fix may still
    # carry trailing UI text; repair_pages.py cleans the stored JSONL
    parts = re.split(r"[|,;]", lib.clean_fontes(fontes))
    seen, out = set(), []
    for p in (p.strip() for p in parts):
        if p and p not in seen:
            seen.add(p)
            out.append(p)
    return out


# --- coverage fields -------------------------------------------------
# What an indicator covers is not in the description field (96.3% of
# those are PORDATA's SEO template). It is in two places we already
# hold: welded onto the title after a colon, and in the chart caption
# captured by the harvester's marker windows.

# PORDATA serves a literal '?' where an en dash belongs, in 37 names
# ("... a tempo completo e parcial ? Homens"). Their own slug drops the
# character entirely (…parcial+++homens-1604), so this is upstream, not
# a decoding fault on our side. Anchored between two non-spaces so a
# genuine trailing question ("Onde existem mais Vilas?") is untouched.
SEPARATOR_DEFECT = re.compile(r"(?<=\S) \? (?=\S)")


def fix_separator(name: str) -> str:
    return SEPARATOR_DEFECT.sub(" – ", name)


# A colon tail is demoted to the coverage line only when it reads as a
# dimension list. Deliberately narrow: "Administrações Públicas: dívida
# bruta em % do PIB" must keep its colon, because there the tail *is*
# the indicator and demoting it would misname the row. Same rule as the
# featured matcher — right or absent.
BREAKDOWN = re.compile(
    r"^(total\s+e\s+por\b|total,\s|total\s+e\s+|"
    r"por\s+(?!cem|mil|100|habitante)\w|homens\s+e\s+mulheres\b|"
    r"\w+\s+e\s+\w+\s+por\b)", re.I)


def split_breakdown(name: str) -> tuple[str, str]:
    """(title, breakdown). breakdown is "" when the split is refused."""
    if name.count(":") != 1:
        return name, ""
    head, tail = (part.strip() for part in name.split(":", 1))
    if not head or not BREAKDOWN.match(tail):
        return name, ""
    return head, tail


# The unit sits in the chart caption, between two PORDATA UI strings.
UNIT_WINDOW = re.compile(r"ampliado\s+(.{1,100}?)\s+ver tabela completa")
# The marker windows are stitched slices, so a window can be cut
# mid-phrase ("ver tabela comple") and the capture then runs on into the
# next slice. Cutting the capture back at our own anchor text recovers
# the unit; this is trimming at a known marker, not guessing at content.
UNIT_RUNON = re.compile(r"\s+(?:ver tabela|Carregue|\|\|)")
MAX_UNIT_LEN = 90
# 12, not 8: a real unit can be verbose — "Euro (a partir de 1/1/1999) /
# ECU (até 31/12/1998) - Média" is 11 words and entirely legitimate.
MAX_UNIT_WORDS = 12
MAX_UNIT_DIGIT_RATIO = 0.35


def plausible_unit(value: str) -> bool:
    """Shape assertion, not a vocabulary check — the same reasoning as
    the roadmap 6a validators. A unit is short, mostly letters and has
    few words; a data value or a slab of UI text fails on shape whatever
    words it happens to contain."""
    if not value or len(value) > MAX_UNIT_LEN:
        return False
    if len(value.split()) > MAX_UNIT_WORDS:
        return False
    # ASCII digits only: str.isdigit() is True for '²', which would
    # reject the perfectly good unit "Km²".
    digits = sum(c in "0123456789" for c in value)
    if digits / len(value) > MAX_UNIT_DIGIT_RATIO:
        return False
    return not any(c in value for c in "|:\n")


# --- revision note (roadmap 24) --------------------------------------
# Decision 5 requires a revision caveat to travel *with* the series. The
# harvester has been storing one since day one without anyone reading it:
# 215 pages carry a `revis` marker window holding sentences like "Os
# valores apresentados entre 2021 e 2024 foram revistos pelo INE…".
# Extracted at build time, so it needs no re-fetch.
#
# Matching the bare word is not enough, twice over. Without \b, "despesa
# imprevista" matches because "previs" contains "revis". And **"revistas"
# means magazines** in Portuguese, so pages about jornais e revistas
# matched too and served their own question as a revision note. So the
# pattern requires a revision *event* — the noun "revisão/revisões", or a
# participle with its auxiliary — not merely the stem.
REVISION_WORD = re.compile(
    r"\brevis(?:ão|ões)|(?:foram|foi|são|ser|sido)\s+revist|"
    r"\brevist[oa]s?\s+(?:pel|em|entre|a partir)", re.I)
# UI furniture that shares the window and must never be served as a note
REVISION_BOUNDARY = re.compile(
    r"Mais opções|Aprofunde|Carregue|ver tabela|Relacionados|"
    r"Fontes/Entidades|A carregar", re.I)
# a window is a slice, so it can open mid-sentence or just after a label
REVISION_LEAD = re.compile(r"^.*?(?:\d{4}-\d{2}-\d{2}|actualiza[^:]*:)\s*",
                           re.S)
MIN_REVISION_LEN = 25
MAX_REVISION_LEN = 240


def extract_revision(rec: dict) -> str:
    """The revision sentence from the stored `revis` window, or ""."""
    window = (rec.get("marker_windows") or {}).get("revis")
    if not window:
        return ""
    text = window if isinstance(window, str) else " ".join(map(str, window))
    text = re.sub(r"\s+", " ", text)
    for part in re.split(r"(?<=[.!?])\s+", text):
        part = part.strip()
        match = REVISION_WORD.search(part)
        # a question is never a revision note, whatever words it shares
        if not match or part.endswith("?"):
            continue
        # trim the label the window sliced into *before* testing for UI
        # furniture: a window that opens on "Fontes/Entidades: … Última
        # actualização: <date> Os valores foram revistos…" is a good note
        # preceded by chrome, not chrome
        head = REVISION_LEAD.sub("", part[:match.start()])
        candidate = re.sub(r"^[^A-Za-zÀ-Úà-ú]+", "",
                           head + part[match.start():]).strip()
        if REVISION_BOUNDARY.search(candidate):
            continue
        if MIN_REVISION_LEN <= len(candidate) <= MAX_REVISION_LEN:
            return candidate
    return ""


def unit_slices(rec: dict):
    """Each marker window is a list of disjoint excerpts. They are
    searched one at a time and never concatenated: joining them lets a
    match run across a boundary and splice two fragments into a
    plausible-looking but corrupt unit ("Euro (a partir de 1/1 tir de
    1/1/1999)"). Per-slice search makes that class impossible."""
    for value in (rec.get("marker_windows") or {}).values():
        if isinstance(value, str):
            yield value
        else:
            for part in value:
                yield str(part)


def extract_unit(rec: dict) -> str:
    found = collections.Counter()
    for excerpt in unit_slices(rec):
        for match in UNIT_WINDOW.finditer(excerpt):
            unit = re.sub(r"\s+", " ", match.group(1)).strip()
            unit = UNIT_RUNON.split(unit, 1)[0].strip()
            if plausible_unit(unit):
                found[unit] += 1
    return found.most_common(1)[0][0] if found else ""


def main() -> None:
    records = lib.load_records()
    current = set(lib.targets()) - lib.abandoned()
    featured_flags, featured_stats = resolve_featured(records)
    write_unmatched_worksheet(records, featured_stats)
    en_names = build_en_names(lib.URLS_FILE.read_text(encoding="utf-8"))

    rows = []
    for url in sorted(records):
        rec = records[url]
        if "error" in rec:
            continue
        name = fix_separator(strip_markup(rec.get("name", ""))
                             or name_from_slug(rec.get("slug", "")))
        title, breakdown = split_breakdown(name)
        row = {
            "id": rec["id"],
            "area": rec["area"],
            # `name` stays the full string so search and sort are
            # unchanged; `title` and `breakdown` are what the card
            # renders. Derived fields are omitted when they carry
            # nothing - `title` when it just repeats `name`, the others
            # when empty - because every key ships to every visitor
            # (roadmap 6f, payload budget).
            "name": name,
            "name_en": en_names.get((rec["area"], rec["id"]), ""),
            "description": strip_markup(rec.get("description", "")),
            "fontes": split_fontes(rec.get("fontes", "")),
            "ultima_atualizacao": rec.get("ultima_atualizacao", ""),
            "url": rec["url"],
            "harvested_at": rec.get("harvested_at", ""),
        }
        if title != name:
            row["title"] = title
        if breakdown:
            row["breakdown"] = breakdown
        unit = extract_unit(rec)
        if unit:
            row["unit"] = unit
        revision = extract_revision(rec)
        if revision:
            row["revision"] = revision
        # captured at harvest time from 2026-08-24 (roadmap 24); existing
        # records predate it and simply have none until re-fetched
        question = strip_markup(rec.get("question", ""))
        if question:
            row["question"] = question
        if rec.get("period_start") and rec.get("period_end"):
            row["period"] = f"{rec['period_start']}-{rec['period_end']}"
        if url not in current:
            row["removed"] = True
        if (rec["area"], rec["id"]) in featured_flags:
            row["featured"] = featured_flags[(rec["area"], rec["id"])]
        rows.append(row)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "catalogue.json").write_text(
        json.dumps(rows, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8")

    with (OUT_DIR / "catalogue.csv").open("w", encoding="utf-8",
                                          newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["id", "area", "name", "name_en", "fontes",
                         "ultima_atualizacao", "url", "removed", "featured"])
        for r in rows:
            writer.writerow([r["id"], r["area"], r["name"], r["name_en"],
                             " | ".join(r["fontes"]), r["ultima_atualizacao"],
                             r["url"], "yes" if r.get("removed") else "",
                             ",".join(r.get("featured", []))])

    # PT<->EN names map with coverage flags: which indicators still lack a
    # harvested PT name or an EN name from the /en sitemap slugs
    name_status_counts: dict[str, int] = {}
    with (OUT_DIR / "names-map.csv").open("w", encoding="utf-8",
                                          newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["id", "area", "name_pt", "name_en", "status"])
        for url in sorted(records):
            rec = records[url]
            if "error" in rec:
                continue
            raw_pt = strip_markup(rec.get("name", ""))
            name_en = en_names.get((rec["area"], rec["id"]), "")
            status = ("ok" if raw_pt and name_en
                      else "missing_en" if raw_pt
                      else "missing_pt" if name_en
                      else "missing_both")
            name_status_counts[status] = name_status_counts.get(status, 0) + 1
            writer.writerow([
                rec["id"], rec["area"],
                raw_pt or name_from_slug(rec.get("slug", "")),
                name_en, status])

    by_area = {}
    for r in rows:
        by_area[r["area"]] = by_area.get(r["area"], 0) + 1
    live = sum(1 for r in rows if not r.get("removed"))
    stats = {
        "indicators": len(rows),
        "by_area": by_area,
        "targets": len(current),
        "complete": live >= len(current),
        "built_at": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()),
    }
    stats["names"] = name_status_counts
    flagged = sum(n for k, n in name_status_counts.items() if k != "ok")
    if flagged:
        print(f"names-map: {flagged} indicators flagged "
              f"({ {k: v for k, v in name_status_counts.items() if k != 'ok'} })")
    if featured_stats:
        stats["featured"] = {
            g: {"names": s["names"], "matched": s["matched"],
                # distinct_rows is what the site shows; before injectivity
                # it silently exceeded the flagged-row count (audit ②)
                "distinct_rows": s["distinct_rows"],
                "collisions": s["matched"] - s["distinct_rows"],
                "unmatched": len(s["unmatched"])}
            for g, s in featured_stats.items()}
        for g, s in featured_stats.items():
            if s["unmatched"]:
                print(f"featured {g}: {s['matched']}/{s['names']} matched; "
                      f"unmatched: {s['unmatched'][:5]}")
    (OUT_DIR / "stats.json").write_text(
        json.dumps(stats, ensure_ascii=False), encoding="utf-8")
    print(f"built catalogue: {len(rows)} indicators "
          f"({', '.join(f'{a}: {n}' for a, n in sorted(by_area.items()))})")


if __name__ == "__main__":
    main()
