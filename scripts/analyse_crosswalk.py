#!/usr/bin/env python3
"""Measure the shape of the PORDATA-INE crosswalk before building it.

Roadmap 2 was specified as "match each catalogue entry to its upstream
series ... store match + confidence". That presumes a 1:1 relation. This
script tests the presumption against the INE cache that landed
2026-08-24, and writes data/spikes/a5-crosswalk-shape.md.

Offline and reproducible: reads docs/data/catalogue.json and
data/ine/indicators.csv, fetches nothing. Re-run it after any change to
the matcher's normalisation to see the numbers move.
"""

import collections
import csv
import io
import json
import pathlib
import re
import sys
import unicodedata

CATALOGUE = pathlib.Path("docs/data/catalogue.json")
INE_CSV = pathlib.Path("data/ine/indicators.csv")
REPORT = pathlib.Path("data/spikes/a5-crosswalk-shape.md")

# PORDATA's area implies the geographic level INE would publish at.
AREA_GEO = {
    "municipios": {"Município", "Freguesia"},
    "portugal": {"Portugal", "Continente", "NUTS I", "NUTS II",
                 "NUTS III", "NUTS 3", "Região autónoma"},
}
STOPWORDS = {
    "de", "da", "do", "das", "dos", "e", "em", "no", "na", "nos", "nas",
    "por", "a", "o", "as", "os", "com", "para", "total", "ao", "aos",
    "um", "uma", "que",
}


def strip_accents(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", (text or "").lower())
    return "".join(c for c in decomposed
                   if unicodedata.category(c) != "Mn")


def norm_title(text: str) -> str:
    """INE suffixes the unit in parentheses — "(N.º)", "(GT)", "(t)" —
    which PORDATA never does, so it is stripped before comparing."""
    text = re.sub(r"\s*\([^)]{1,12}\)\s*$", "", strip_accents(text))
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", text)).strip()


def tokens(text: str) -> set:
    return {w for w in re.split(r"[^a-z0-9]+", strip_accents(text))
            if len(w) > 2 and w not in STOPWORDS}


def load():
    rows = json.loads(CATALOGUE.read_text(encoding="utf-8"))
    csv.field_size_limit(sys.maxsize)
    with io.open(INE_CSV, encoding="utf-8") as fh:
        ine = [{"id": r["id"], "title": r["title"],
                "geo": r["geo_lastlevel"], "periodicity": r["periodicity"],
                "tokens": tokens(r["title"])}
               for r in csv.DictReader(fh)]
    return rows, ine


def ine_sourced(rows: list) -> list:
    def entities(row):
        return [f.split(" - ")[0].strip() for f in (row.get("fontes") or [])]
    return [r for r in rows
            if any(e.upper().startswith("INE") for e in entities(r))
            and r["area"] in AREA_GEO]


def measure(rows: list, ine: list) -> dict:
    by_title = collections.defaultdict(list)
    for entry in ine:
        by_title[norm_title(entry["title"])].append(entry)

    inverted = collections.defaultdict(list)
    for i, entry in enumerate(ine):
        for word in entry["tokens"]:
            inverted[word].append(i)

    candidates = ine_sourced(rows)
    exact = collections.Counter()
    contain = collections.Counter()
    tie_sizes = []

    for row in candidates:
        name = row.get("title") or row["name"]
        allowed = AREA_GEO[row["area"]]

        hits = by_title.get(norm_title(name), [])
        scoped = [h for h in hits if h["geo"] in allowed]
        if not hits:
            exact["no title match"] += 1
        elif len(scoped) == 1:
            exact["resolved to exactly 1"] += 1
        elif not scoped:
            exact["title matched, wrong geo level"] += 1
        else:
            exact["still ambiguous"] += 1

        query = tokens(name)
        if not query:
            continue
        overlap = collections.Counter()
        for word in query:
            for i in inverted.get(word, ()):
                overlap[i] += 1
        best, best_score = [], 0.0
        for i, shared in overlap.items():
            if ine[i]["geo"] not in allowed:
                continue
            score = shared / len(query)
            if score > best_score:
                best, best_score = [i], score
            elif score == best_score:
                best.append(i)
        if best_score >= 0.99:
            contain["full containment"] += 1
            tie_sizes.append(len(best))
        elif best_score >= 0.75:
            contain["0.75-0.99"] += 1
        elif best_score >= 0.50:
            contain["0.50-0.74"] += 1
        elif best_score > 0:
            contain["below 0.50"] += 1
        else:
            contain["no shared token"] += 1

    tie_sizes.sort()
    return {
        "pordata_rows": len(rows),
        "ine_entries": len(ine),
        "ine_distinct_titles": len(by_title),
        "candidates": len(candidates),
        "exact": exact,
        "containment": contain,
        "ties": {
            "n": len(tie_sizes),
            "median": tie_sizes[len(tie_sizes) // 2] if tie_sizes else 0,
            "max": tie_sizes[-1] if tie_sizes else 0,
            "one_to_one": sum(1 for t in tie_sizes if t == 1),
        },
    }


def render(m: dict) -> str:
    total = m["candidates"] or 1
    pct = lambda n: f"{n / total * 100:.1f}%"                # noqa: E731
    lines = [
        "# Spike A5 - the shape of the PORDATA-INE crosswalk",
        "",
        "Roadmap 2 was written as \"match each catalogue entry to its "
        "upstream **series**\", which presumes a 1:1 relation. Measured "
        "against the INE cache, that presumption does not hold. Offline "
        "and reproducible: `python3 scripts/analyse_crosswalk.py`.",
        "",
        "## Inputs",
        "",
        f"- PORDATA rows: **{m['pordata_rows']:,}**",
        f"- INE indicators: **{m['ine_entries']:,}** "
        f"({m['ine_distinct_titles']:,} distinct normalised titles)",
        f"- PORDATA rows citing INE, in portugal/municipios: "
        f"**{m['candidates']:,}**",
        "",
        "## Exact title match, scoped to the expected geography",
        "",
    ]
    for key in ("no title match", "still ambiguous",
                "title matched, wrong geo level", "resolved to exactly 1"):
        lines.append(f"- {key}: **{m['exact'][key]:,}** ({pct(m['exact'][key])})")
    lines += [
        "",
        "**Exact matching is a dead end.** PORDATA rewrites names for "
        "readability, so most never match a literal INE title, and "
        "scoping by geography rescues almost nothing.",
        "",
        "## Token containment (how much of PORDATA's phrase INE covers)",
        "",
    ]
    for key in ("full containment", "0.75-0.99", "0.50-0.74",
                "below 0.50", "no shared token"):
        lines.append(f"- {key}: **{m['containment'][key]:,}** "
                     f"({pct(m['containment'][key])})")
    ties = m["ties"]
    lines += [
        "",
        f"Containment finds a match far more often, but it does not find "
        f"*one*: of the {ties['n']:,} fully-contained rows only "
        f"**{ties['one_to_one']}** hit a single INE entry, the median row "
        f"ties **{ties['median']}** entries and the worst ties "
        f"**{ties['max']}**.",
        "",
        "## What that means",
        "",
        "**INE's catalogue is series-level; PORDATA's is "
        "indicator-level.** One PORDATA indicator - \"Alojamentos "
        "familiares clássicos\" - corresponds to a *family* of INE series "
        "split by geography, periodicity, census-vs-estimate and "
        "breakdown. The tie counts are not matcher noise; they are the "
        "relation's real shape.",
        "",
        "So a crosswalk storing one `ine_id` per row would be **choosing "
        "arbitrarily and recording the choice as fact** - the exact "
        "failure mode the featured matcher was rewritten to avoid. The "
        "honest model is one-to-many:",
        "",
        "- store the **candidate set** plus the evidence that selected it,",
        "- defer picking a series to fetch time (item 14), where geography "
        "and period are known from what the user asked for,",
        "- and keep `crosswalk: null` for rows with no credible family.",
        "",
        "This also raises the value of INE's `keywords` and `theme` "
        "fields, unused here: they constrain the family before any name "
        "comparison, which is the cheapest precision available.",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    rows, ine = load()
    metrics = measure(rows, ine)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(render(metrics), encoding="utf-8")
    print(f"candidates {metrics['candidates']}, "
          f"exact-resolved {metrics['exact']['resolved to exactly 1']}, "
          f"contained {metrics['containment']['full containment']} "
          f"(median tie {metrics['ties']['median']}, "
          f"max {metrics['ties']['max']})")
    print(f"report written: {REPORT}")


if __name__ == "__main__":
    main()
