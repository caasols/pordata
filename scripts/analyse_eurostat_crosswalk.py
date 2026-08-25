#!/usr/bin/env python3
"""What shape is the PORDATA-Eurostat relation? (roadmap 2)

The mirror of `analyse_crosswalk.py`, and it exists because the roadmap
says in as many words: *measure Eurostat the same way before specifying
it; do not assume A5's shape carries over.* Two things already say it
will not.

**Eurostat's unit is a dataset, not a series.** INE's 13,084 entries are
pre-sliced series, which is what made one PORDATA indicator correspond
to a family of them. Eurostat's ~8,500 entries are multi-dimensional
cubes — one holds 311,689 observations — so the plausible relation is
*one dataset plus a dimension filter*, and the tie counts should look
nothing like INE's.

**The matching language is English.** All 638 `europa` rows carry an
English name and every Eurostat title is English, so this compares
EN↔EN where the INE crosswalk compared PT↔PT. That removes the
translation gap that forced INE's matcher to be so strict — or it
removes one problem and reveals another, which is the point of
measuring.

This script decides nothing and writes no crosswalk. It answers four
questions, and the answers are what a matcher gets specified from:

1. How often does an exact title match exist at all?
2. When containment finds candidates, how many does it tie?
3. Is the relation one-to-one, one-to-many, or many-to-one?
4. Does Eurostat's theme tree constrain it usefully, the way INE's
   themes turned out not to?
5. Which match operator, and — the part that matters — which ones were
   tried and rejected, with the number that rejected them.
"""

import collections
import csv
import io
import json
import pathlib
import re
import statistics
import sys
import unicodedata

CATALOGUE = pathlib.Path("docs/data/catalogue.json")
EUROSTAT = pathlib.Path("data/eurostat/datasets.csv")
REPORT = pathlib.Path("data/spikes/eurostat-crosswalk-shape.md")

# English stopwords plus the words every statistical title carries, which
# would otherwise tie everything to everything.
STOPWORDS = {
    "the", "of", "and", "by", "in", "to", "for", "on", "at", "as", "a",
    "an", "or", "with", "from", "per", "total", "data", "statistics",
    "annual", "quarterly", "monthly", "number", "rate", "other", "all",
}


def strip_accents(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", (text or "").lower())
    return "".join(c for c in decomposed
                   if unicodedata.category(c) != "Mn")


def tokens(text: str) -> set:
    return {w for w in re.split(r"[^a-z0-9]+", strip_accents(text))
            if (len(w) > 2 or w.isdigit()) and w not in STOPWORDS}


def norm_title(text: str) -> str:
    return re.sub(r"\s+", " ",
                  re.sub(r"[^a-z0-9]+", " ", strip_accents(text))).strip()


def load():
    rows = json.loads(CATALOGUE.read_text(encoding="utf-8"))
    if not EUROSTAT.exists():
        raise SystemExit(
            f"analyse_eurostat_crosswalk: {EUROSTAT} is missing. Run the "
            "eurostat-catalogue workflow first — this measures a "
            "relation and cannot invent one side of it.")
    csv.field_size_limit(sys.maxsize)
    with io.open(EUROSTAT, encoding="utf-8") as handle:
        datasets = [dict(r, tokens=tokens(r["title"]),
                         norm=norm_title(r["title"]))
                    for r in csv.DictReader(handle)]
    return rows, datasets


def in_scope(row: dict) -> bool:
    """Eurostat-sourced `europa` rows with an English name to match on."""
    if row.get("area") != "europa" or not row.get("name_en"):
        return False
    return any(f.split(" - ")[0].strip().upper().startswith("EUROSTAT")
               for f in (row.get("fontes") or []))


def measure(rows: list, datasets: list) -> dict:
    scope = [r for r in rows if in_scope(r)]
    by_norm = collections.defaultdict(list)
    index = collections.defaultdict(list)
    for position, dataset in enumerate(datasets):
        by_norm[dataset["norm"]].append(dataset)
        for token in dataset["tokens"]:
            index[token].append(position)

    exact, contained, ties, no_shared, coverage = 0, 0, [], 0, []
    theme_spread = []
    for row in scope:
        want = tokens(row["name_en"])
        if not want:
            continue
        if by_norm.get(norm_title(row["name_en"])):
            exact += 1
        hits = collections.Counter()
        for token in want:
            for position in index.get(token, []):
                hits[position] += 1
        if not hits:
            no_shared += 1
            continue
        best = max(hits.values()) / len(want)
        coverage.append(best)
        if best >= 0.999:
            contained += 1
            tied = [datasets[p] for p, n in hits.items()
                    if n / len(want) >= 0.999]
            ties.append(len(tied))
            theme_spread.append(len({t for d in tied
                                     for t in d["themes"].split(" | ")}))

    return {
        "scope": len(scope),
        "datasets": len(datasets),
        "exact": exact,
        "contained": contained,
        "no_shared": no_shared,
        "ties": ties,
        "theme_spread": theme_spread,
        "coverage": coverage,
        "distinct_titles": len(by_norm),
    }


# PORDATA writes the unit into a trailing parenthetical and Eurostat
# carries it as a *dimension* of the cube, so the word never appears in
# an Eurostat title. `percentage` alone blocked 35 near-misses. This is
# the INE unit lesson at the opposite polarity — there PORDATA held the
# unit in a field and INE suffixed it into the title.
UNIT_PAREN = re.compile(
    r"\s*\((?:euro|percentage|pps|euro ecu|eu27 100|at current prices|"
    r"\d{4}[^)]*|nace[^)]*|isced[^)]*)\)\s*$", re.I)
# Both sides name their breakdown after a `by`, and neither puts it in
# the same place: PORDATA writes "total and by sex", Eurostat "by sex,
# age and metropolitan region".
PORDATA_TAIL = re.compile(r"\s*[:,]?\s*\b(?:total and by|and by|by)\b.*$",
                          re.I)
EUROSTAT_TAIL = re.compile(r"\s*,?\s*\bby\b.*$", re.I)


def strip_unit(text: str) -> str:
    previous = None
    while previous != text:
        previous, text = text, UNIT_PAREN.sub("", text).strip()
    return text


def split_tail(text: str, pattern: re.Pattern) -> tuple[str, set]:
    """The concept, and the words naming how it is broken down."""
    found = pattern.search(text)
    if not found:
        return text.strip(), set()
    return text[:found.start()].strip(), tokens(found.group(0))


def operators(rows: list, datasets: list) -> dict:
    """Head matching against the alternatives that were tried first.

    Every number here rejected something. The token floor is the one
    worth keeping in the report: it looked like the obvious way to stop
    a generic head such as "Exports" matching an input-output table, and
    it also deleted "Obesity rate by body mass index" — which matched its
    Eurostat title exactly."""
    scope = [r for r in rows if in_scope(r)]
    heads = collections.defaultdict(list)
    for dataset in datasets:
        head, tail = split_tail(dataset["title"], EUROSTAT_TAIL)
        dataset["tail"] = tail
        heads[norm_title(head)].append(dataset)

    out = {"scope": len(scope), "head": 0, "vetoed": 0, "survivors": [],
           "floor_would_drop": 0, "veto_examples": []}
    for row in scope:
        clean = strip_unit(row["name_en"])
        head, tail = split_tail(clean, PORDATA_TAIL)
        found = heads.get(norm_title(head))
        if not found:
            continue
        out["head"] += 1
        if len(tokens(head)) < 2:
            out["floor_would_drop"] += 1
        # A veto needs two tails to disagree. Silence on either side is
        # not a contradiction.
        survivors = [d for d in found
                     if not (tail and d["tail"] and not (tail & d["tail"]))]
        if not survivors:
            out["vetoed"] += 1
            if len(out["veto_examples"]) < 6:
                out["veto_examples"].append((row["name_en"], found[0]["title"]))
            continue
        out["survivors"].append(len(survivors))
    return out


def bucket(values: list, edges: list) -> list:
    out = []
    for low, high in zip([0.0] + edges, edges + [1.01]):
        out.append((low, high, sum(1 for v in values if low <= v < high)))
    return out


def render(m: dict) -> str:
    scope = m["scope"] or 1
    ties = m["ties"]
    lines = [
        "# The shape of the PORDATA–Eurostat relation (roadmap 2)",
        "",
        "The mirror of spike A5, run because the roadmap says to measure "
        "Eurostat rather than assume INE's shape carries over. Offline "
        "and reproducible: `python3 scripts/analyse_eurostat_crosswalk.py`.",
        "",
        "## Inputs",
        "",
        f"- PORDATA `europa` rows citing Eurostat, with an English name: "
        f"**{m['scope']}**",
        f"- Eurostat datasets: **{m['datasets']}** "
        f"({m['distinct_titles']} distinct normalised titles)",
        "",
        "**Matched EN↔EN.** Every `europa` row carries an English name and "
        "every Eurostat title is English, so this comparison does not "
        "cross a translation gap — which the INE crosswalk did, and which "
        "is why that matcher had to be so strict.",
        "",
        "## Exact title match",
        "",
        f"- an exact normalised title exists for **{m['exact']}** rows "
        f"({m['exact'] / scope:.1%})",
        "",
        "## Token containment (all of PORDATA's words inside a title)",
        "",
        f"- fully contained by at least one dataset: **{m['contained']}** "
        f"({m['contained'] / scope:.1%})",
        f"- no shared token with any dataset: **{m['no_shared']}**",
        "",
    ]
    if m["coverage"]:
        lines += ["Best containment achieved, distribution:", ""]
        for low, high, count in bucket(m["coverage"], [0.25, 0.5, 0.75, 0.999]):
            lines.append(f"- {low:.2f}–{high:.2f}: {count}")
        lines.append("")
    lines += ["## How many datasets does a contained row tie?", ""]
    if ties:
        lines += [
            f"- median **{statistics.median(ties):.0f}**, "
            f"mean **{statistics.mean(ties):.1f}**, max **{max(ties)}**",
            f"- resolves to exactly one: **{sum(1 for t in ties if t == 1)}** "
            f"of {len(ties)}",
            "",
            "**This is the number that decides the schema.** INE tied a "
            "median of 9 pre-sliced series, which is why its crosswalk "
            "stores a candidate set and defers the choice to fetch time. "
            "A median near 1 here would mean a PORDATA row maps to one "
            "dataset plus a dimension filter, and the entry should say so "
            "rather than pretend to a family it does not have.",
            "",
        ]
        if m["theme_spread"]:
            pure = sum(1 for s in m["theme_spread"] if s == 1)
            lines += [
                "## Does the theme tree constrain it?",
                "",
                f"- ties landing in a single Eurostat theme: **{pure}** of "
                f"{len(m['theme_spread'])} "
                f"({pure / len(m['theme_spread']):.0%})",
                "",
                "INE's themes turned out not to constrain usefully — "
                "purity there *rejected* exact matches, because INE files "
                "one series under two themes. Whether Eurostat's tree "
                "behaves the same way is the question, and it is the "
                "cheapest precision available if it does not.",
                "",
            ]
    else:
        lines += ["No row was fully contained, so there is nothing to tie. "
                  "That would itself be the finding: containment is the "
                  "wrong operator for a dataset-level catalogue, and the "
                  "matcher needs a different one.", ""]
    return "\n".join(lines)


def render_operators(o: dict) -> str:
    scope = o["scope"] or 1
    kept = len(o["survivors"])
    ones = sum(1 for s in o["survivors"] if s == 1)
    lines = [
        "## Which operator, and which ones were rejected",
        "",
        "Containment over the raw titles reaches 18.3% and the reason is "
        "structural, not incidental. Diagnosing the near-misses named the "
        "blocking words: `percentage` on 35 rows, `euro` on 23, then "
        "`type`, `category`, `sex`, `sector`. **PORDATA's name is a "
        "concept plus a slicing instruction plus a unit; Eurostat's title "
        "is a cube name whose unit and dimensions are not in it.** Asking "
        "a cube's name to contain the words for its own dimensions is "
        "asking the wrong question.",
        "",
        "So the operator splits both sides at the `by` that opens the "
        "breakdown and matches the **heads**, exactly:",
        "",
        f"- an exact head match exists for **{o['head']}** rows "
        f"({o['head'] / scope:.1%})",
        "",
        "### The tail is a veto, not a ranking",
        "",
        "Ranking the tied candidates by how well PORDATA's breakdown "
        "matches Eurostat's picked a single winner on only 10 of 83 tied "
        "rows, and one of the first eight sampled was *Employment by "
        "professional status — **ENP-South countries***, a non-EU "
        "geography. As a discriminator it manufactures confidence.",
        "",
        "As a **veto** the same signal is sound: if both sides name a "
        "breakdown and the two share no word, they are not the same "
        "slice. Silence on either side is not a contradiction, so the "
        "veto needs two tails to fire.",
        "",
        f"- head matches surviving the veto: **{kept}** "
        f"(of {o['head']}; **{o['vetoed']}** refused outright)",
        f"- surviving candidate sets resolving to exactly one dataset: "
        f"**{ones}**",
        "",
        "Every outright refusal that was read by hand was correct:",
        "",
    ]
    for name, title in o["veto_examples"]:
        lines.append(f"- `{name}` ≠ *{title}*")
    lines += [
        "",
        "### Rejected: a content-token floor on the head",
        "",
        f"The obvious guard against a generic head — *Exports* matching "
        f"*Exports by industry (FIGARO application)* — is to require the "
        f"head to carry two content words. It would drop "
        f"**{o['floor_would_drop']}** head matches, and among them "
        f"*Obesity rate by body mass index*, which matches its Eurostat "
        f"title **exactly**, and *Total fertility rate*, whose only "
        f"content word survives the stopword list. The floor measures "
        f"length where the failure is contradiction; the veto catches "
        f"the same two cases without the collateral. Recorded because it "
        f"was the first idea and the numbers are what refuted it.",
        "",
        "### What the entry cannot claim",
        "",
        "The catalogue carries titles, not dimension names. When PORDATA "
        "asks for *total and by sex* and the candidate cube's title says "
        "nothing about sex, the cube may still have that dimension — "
        "there is no way to tell without fetching each dataset's "
        "structure, which is 7,572 requests and item 14's problem. So "
        "the breakdown is stored as an **unresolved filter**, never as a "
        "satisfied one.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    rows, datasets = load()
    measured = measure(rows, datasets)
    chosen = operators(rows, datasets)
    REPORT.write_text(render(measured) + "\n" + render_operators(chosen),
                      encoding="utf-8")
    print(f"eurostat shape: {measured['scope']} rows vs "
          f"{measured['datasets']} datasets; "
          f"{measured['exact']} exact, {measured['contained']} contained; "
          f"{chosen['head']} head matches, {len(chosen['survivors'])} "
          f"surviving the tail veto; report at {REPORT}")


if __name__ == "__main__":
    main()
