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


SUP_DIGITS = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")
SUB_DIGITS = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")


def strip_markup(s: str) -> str:
    """PORDATA titles carry inline HTML (<em>per capita</em>,
    CO<sub>2</sub>, km<sup>2</sup>). Digits in sub/sup become their
    Unicode forms; every other tag is dropped."""
    s = re.sub(r"<sup>(\d+)</sup>", lambda m: m.group(1).translate(SUP_DIGITS), s)
    s = re.sub(r"<sub>(\d+)</sub>", lambda m: m.group(1).translate(SUB_DIGITS), s)
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
        row = {
            "id": rec["id"],
            "area": rec["area"],
            "name": strip_markup(rec.get("name", ""))
                or name_from_slug(rec.get("slug", "")),
            "name_en": en_names.get((rec["area"], rec["id"]), ""),
            "description": strip_markup(rec.get("description", "")),
            "fontes": split_fontes(rec.get("fontes", "")),
            "ultima_atualizacao": rec.get("ultima_atualizacao", ""),
            "url": rec["url"],
            "harvested_at": rec.get("harvested_at", ""),
        }
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
