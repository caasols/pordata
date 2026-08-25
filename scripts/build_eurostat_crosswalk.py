#!/usr/bin/env python3
"""Route each PORDATA `europa` row to the Eurostat datasets that could
hold it (roadmap 1).

The mirror of `build_crosswalk.py`, and deliberately not a copy of it.
The roadmap's instruction was to *measure Eurostat the same way before
specifying it, and not assume A5's shape carries over*. It does not, in
two ways that change the schema:

**Eurostat's unit is a dataset, not a series.** INE publishes 13,084
pre-sliced series, so one PORDATA indicator legitimately corresponds to
a *family* of them and the crosswalk stores the family. Eurostat
publishes 7,572 multi-dimensional cubes, and a PORDATA row wants one
cube plus a filter over its dimensions. So a large candidate set means
something different here: for INE, "62 candidates means INE publishes 62
of them" and size was never a reason to refuse; here the candidates are
*rivals* and only one is right. The set is still stored — the choice is
still deferred — but the count is a warning rather than a fact about the
upstream.

**The comparison is EN↔EN.** Every in-scope row carries an English name
and every Eurostat title is English, so this does not cross the
translation gap that forced the INE matcher to be so strict.

The operator, and why it is this one, is measured in
`data/spikes/eurostat-crosswalk-shape.md`:

- **the unit is stripped, never matched.** PORDATA writes it into a
  trailing parenthetical; Eurostat carries it as a dimension of the
  cube, so the word is not in the title. `percentage` alone blocked 35
  rows. This is the INE unit lesson at the opposite polarity.
- **both sides are split at the `by` that opens the breakdown, and the
  heads must match exactly.** Containment reaches 18.3% because it asks
  a cube's name to contain the words for its own dimensions.
- **the breakdown is a veto, not a ranking.** Ranking by it picked a
  single winner on 10 of 83 tied rows and one of the first sampled was a
  non-EU geography. As a veto — two tails that share no word are not the
  same slice — it refuses 18 head matches, every hand-read one correctly.
- **a content-token floor on the head was tried and rejected.** It drops
  38 matches including one that matched its Eurostat title exactly. It
  measures length where the failure is contradiction.

What an entry may not claim: the catalogue carries titles, not dimension
names, so when PORDATA asks for *total and by sex* there is no offline
way to know whether the candidate cube has a sex dimension. The
breakdown is stored as an **unresolved filter**. Item 14 resolves it
against the real structure at fetch time, or refuses.

No observation values are read or written. This is metadata about where
data lives — decision 1.
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
EUROSTAT_CSV = pathlib.Path("data/eurostat/datasets.csv")
OUT_JSON = pathlib.Path("data/crosswalk/eurostat.json")
OUT_QA = pathlib.Path("data/crosswalk/EUROSTAT-QA.md")
OUT_REVIEW = pathlib.Path("data/crosswalk/EUROSTAT-REVIEW.md")

# Stored per entry. The set is a shortlist for a human or for item 14,
# not an inventory, and a hundred codes in a JSON file is neither.
MAX_STORED = 25
REVIEW_SAMPLE = 40
# The measured run routes 118 rows. Set under it, as the INE floor is:
# the gate exists to catch a *collapse* — a changed Eurostat format, a
# regression in the splitter — not to freeze today's number.
MIN_MATCHED = 100

# Ordinary English plus the words every statistical title carries, which
# would otherwise make unrelated titles look related.
STOPWORDS = {
    "the", "of", "and", "by", "in", "to", "for", "on", "at", "as", "a",
    "an", "or", "with", "from", "per", "total", "data", "statistics",
    "annual", "quarterly", "monthly", "number", "rate", "other", "all",
}

# PORDATA's trailing parenthetical is a unit or a period, never part of
# the concept. Listed rather than matched as "any parenthetical",
# because `(BMI)`, `(COFOG)` and `(LULUCF)` *are* part of the concept.
UNIT_PAREN = re.compile(
    r"\s*\((?:euro|percentage|pps|euro ecu|eu27 100|at current prices|"
    r"\d{4}[^)]*|nace[^)]*|isced[^)]*)\)\s*$", re.I)

# PORDATA writes "total and by sex"; Eurostat writes "by sex, age and
# metropolitan region". A bare `by` has to count on the PORDATA side —
# "Obesity rate by body mass index" opens its breakdown that way — which
# means the split can cut inside a name that merely contains "by"
# ("soil erosion by water"). Requiring the heads to match *exactly*
# absorbs that: a head cut in the wrong place does not match anything.
PORDATA_TAIL = re.compile(r"\s*[:,]?\s*\b(?:total and by|and by|by)\b.*$",
                          re.I)
EUROSTAT_TAIL = re.compile(r"\s*,?\s*\bby\b.*$", re.I)
THEME_SEP = " | "

# Measured across all 7,572 rows of the cached catalogue: every download
# and browser URL is exactly the dataset code substituted into these,
# with no exceptions and none missing. So storing a URL per candidate
# would repeat a template up to 25 times per entry — 184 KB of it — and
# a consumer can build the route from the code instead. Kept as a
# *checked* claim rather than an assumption: `load_eurostat` asserts it
# on every build, so the day Eurostat changes the pattern the build
# stops rather than quietly publishing dead links.
TSV_TEMPLATE = ("https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1"
                "/data/{code}/?format=TSV")
BROWSER_TEMPLATE = ("https://ec.europa.eu/eurostat/databrowser/product"
                    "/view/{code}")


def strip_accents(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", (text or "").lower())
    return "".join(c for c in decomposed
                   if unicodedata.category(c) != "Mn")


def tokens(text: str) -> set:
    """Content words. Digits are kept whatever their length — a year or
    an age bracket is content, which is a lesson the INE matcher paid
    for with a two-character floor that swallowed `65`."""
    return {w for w in re.split(r"[^a-z0-9]+", strip_accents(text))
            if (len(w) > 2 or w.isdigit()) and w not in STOPWORDS}


def norm_title(text: str) -> str:
    return re.sub(r"\s+", " ",
                  re.sub(r"[^a-z0-9]+", " ", strip_accents(text))).strip()


def strip_unit(text: str) -> str:
    """Repeated, because a name can carry both a unit and a period."""
    previous = None
    while previous != text:
        previous, text = text, UNIT_PAREN.sub("", text).strip()
    return text


def split_tail(text: str, pattern: re.Pattern) -> tuple[str, str]:
    """The concept, and the phrase naming how it is broken down."""
    found = pattern.search(text)
    if not found:
        return text.strip(), ""
    return text[:found.start()].strip(), found.group(0).strip()


def in_scope(row: dict) -> bool:
    """Eurostat-sourced `europa` rows with an English name to match on.

    `portugal` and `municipios` are INE's and are routed by the INE
    crosswalk; a row with no English name has nothing to compare against
    a catalogue that is entirely English."""
    if row.get("area") != "europa" or not row.get("name_en"):
        return False
    return any(f.split(" - ")[0].strip().upper().startswith("EUROSTAT")
               for f in (row.get("fontes") or []))


def load_eurostat(path: pathlib.Path | None = None) -> list[dict]:
    # resolved at call time so the module attribute stays the single
    # source of truth when a test overrides it
    path = EUROSTAT_CSV if path is None else path
    csv.field_size_limit(sys.maxsize)
    with io.open(path, encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise SystemExit(
            f"build_eurostat_crosswalk: {path} is empty. Run the "
            "eurostat-catalogue workflow — this routes to a catalogue "
            "and cannot invent one.")
    deviating = []
    for row in rows:
        head, tail = split_tail(row["title"], EUROSTAT_TAIL)
        row["head"] = norm_title(head)
        row["tail_tokens"] = tokens(tail)
        code = row["code"]
        if (row["browser_url"] != BROWSER_TEMPLATE.format(code=code)
                or row["tsv_url"] != TSV_TEMPLATE.format(code=code)):
            deviating.append(code)
    if deviating:
        raise SystemExit(
            f"build_eurostat_crosswalk: {len(deviating)} datasets no "
            f"longer follow the URL templates ({deviating[:5]}). The "
            "crosswalk stores codes and builds routes from them, so a "
            "changed pattern would turn every stored candidate into a "
            "dead link. Look before publishing it.")
    return rows


def build_index(datasets: list[dict]) -> dict:
    index: dict = {}
    for dataset in datasets:
        index.setdefault(dataset["head"], []).append(dataset)
    return index


def candidates(row: dict, index: dict) -> tuple[list[dict], str, bool]:
    """The datasets whose head is PORDATA's, minus those whose breakdown
    contradicts it.

    Returns the survivors, the breakdown phrase that was set aside, and
    whether a veto actually fired — a refusal *because* every candidate
    disagreed is a different fact from never having found a head, and
    the review file should be able to tell them apart."""
    clean = strip_unit(row["name_en"])
    head, tail = split_tail(clean, PORDATA_TAIL)
    found = index.get(norm_title(head))
    if not found:
        return [], tail, False
    wanted = tokens(tail)
    # A veto needs two breakdowns to disagree. Silence on either side is
    # not a contradiction: a cube whose title names no dimension may
    # still carry the one PORDATA wants, and there is no offline way to
    # know. Refusing on silence would refuse the exact matches.
    survivors = [d for d in found
                 if not (wanted and d["tail_tokens"]
                         and not (wanted & d["tail_tokens"]))]
    return survivors, tail, not survivors


def entry_summary(row: dict, family: list[dict], filter_hint: str) -> dict:
    """What was matched, how, and — as much as it matters — what was not
    checked."""
    target = norm_title(strip_unit(row["name_en"]))
    exact = [d["code"] for d in family if norm_title(d["title"]) == target]
    stored = family[:MAX_STORED]
    stored_codes = {d["code"] for d in stored}
    themes = collections.Counter(
        t for d in family for t in d["themes"].split(THEME_SEP) if t)
    theme, theme_n = themes.most_common(1)[0] if themes else ("", 0)
    return {
        "source": "Eurostat",
        "candidates": [d["code"] for d in stored],
        "n_candidates": len(family),
        "truncated": len(family) > MAX_STORED,
        # a subset of `candidates` by construction, so a reader never
        # meets a code in one list and not the other
        "exact_title": [c for c in exact if c in stored_codes],
        "n_exact": len(exact),
        # titles are stored because a reader judging a candidate set
        # needs them and they are not derivable; the URLs are not,
        # because they are the code in a template (see above)
        "titles": {d["code"]: d["title"] for d in stored},
        "theme": theme,
        "theme_share": round(theme_n / len(family), 3) if family else 0.0,
        # Over the whole family, not the stored slice. Every other
        # whole-family statistic here (`theme`, `theme_share`,
        # `n_candidates`, `n_exact`) already is, and this one silently
        # was not: europa/2970 has 73 candidates and published 2016-2023
        # against a family spanning 2007-2024.
        "period": sorted({f"{d['data_start']}-{d['data_end']}"
                          for d in family if d["data_start"]}),
        # NOT a satisfied filter. The catalogue carries titles, not
        # dimension names, so whether a candidate cube can be sliced this
        # way is unknown offline and item 14 must resolve it or refuse.
        "filter": filter_hint,
        "filter_resolved": False,
        # PORDATA's unit, named as PORDATA's. It sat here as plain
        # `unit` and the detail page rendered it between the
        # Eurostat-derived theme and period, so the panel headed "where
        # the numbers come from" presented our own field as upstream
        # provenance — on the one panel that gets `filter_resolved`
        # right on the adjacent line. Eurostat carries the unit as a
        # dimension, so there is nothing upstream to compare it against
        # until the filter resolves.
        "wanted_unit": row.get("unit", ""),
        # one dataset whose title is exactly the indicator's is the
        # strongest evidence available offline
        "confidence": ("exact" if exact
                       else "single" if len(family) == 1 else "family"),
    }


def build(rows: list[dict], datasets: list[dict]) -> tuple[dict, dict]:
    index = build_index(datasets)
    crosswalk: dict = {}
    stats = {"in_scope": 0, "matched": 0, "refused": 0, "vetoed": 0,
             "exact": 0, "single": 0, "family": 0, "sizes": [],
             "refusals": [], "vetoes": [], "with_filter": 0,
             "datasets": len(datasets)}
    for row in rows:
        if not in_scope(row):
            continue
        stats["in_scope"] += 1
        key = f"{row['area']}/{row['id']}"
        family, filter_hint, vetoed = candidates(row, index)
        if not family:
            crosswalk[key] = None
            stats["refused"] += 1
            if vetoed:
                stats["vetoed"] += 1
                stats["vetoes"].append((row["name_en"], filter_hint))
            else:
                stats["refusals"].append((row["name_en"], filter_hint))
            continue
        summary = entry_summary(row, family, filter_hint)
        crosswalk[key] = summary
        stats["matched"] += 1
        stats[summary["confidence"]] += 1
        stats["sizes"].append(summary["n_candidates"])
        if filter_hint:
            stats["with_filter"] += 1
    return crosswalk, stats


def median(values: list) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return float(ordered[middle])
    return (ordered[middle - 1] + ordered[middle]) / 2


def qa_report(stats: dict) -> str:
    scope = stats["in_scope"] or 1
    matched = stats["matched"] or 1
    sizes = stats["sizes"]
    return "\n".join([
        "# Eurostat crosswalk QA",
        "",
        "Rebuilt by `scripts/build_eurostat_crosswalk.py`, which refuses "
        f"to overwrite this file below {MIN_MATCHED} matches — before "
        "writing, so a collapsed build leaves the previous one in place. "
        "`qa_catalogue.py --strict` re-checks the committed count as "
        "`eurostat_matched_min`, which catches a crosswalk that shrank on "
        "a run that never rebuilt it. Offline and reproducible.",
        "",
        "## Coverage",
        "",
        f"- in scope (`europa`, Eurostat-sourced, English name): "
        f"**{stats['in_scope']}**",
        f"- routed to at least one dataset: **{stats['matched']}** "
        f"({stats['matched'] / scope:.1%})",
        f"- refused: **{stats['refused']}** — of which "
        f"**{stats['vetoed']}** found a head and rejected every candidate "
        "as the wrong slice",
        f"- Eurostat datasets searched: **{stats['datasets']}**",
        "",
        "Entries store dataset **codes**, not URLs. Every download and "
        "browser URL in the cached catalogue is exactly the code "
        f"substituted into `{TSV_TEMPLATE}` and `{BROWSER_TEMPLATE}` — "
        "measured across all of them, and asserted on every build, so a "
        "changed pattern stops the build rather than publishing dead "
        "links.",
        "",
        "## Confidence",
        "",
        f"- **exact** (a candidate's title is the indicator's): "
        f"**{stats['exact']}** ({stats['exact'] / matched:.1%})",
        f"- **single** (one candidate, title not identical): "
        f"**{stats['single']}**",
        f"- **family** (several rival cubes, choice deferred): "
        f"**{stats['family']}**",
        "",
        "## Candidate set size",
        "",
        f"- median **{median(sizes):.0f}**, max **{max(sizes) if sizes else 0}**",
        f"- resolving to exactly one dataset: "
        f"**{sum(1 for s in sizes if s == 1)}**",
        "",
        "A large set means something different here from the INE "
        "crosswalk. There, a family of 62 was 62 pre-sliced series that "
        "all belong to the indicator, and size was never a reason to "
        "refuse. Here the candidates are **rival cubes** and only one is "
        "right, so a large set is an unresolved question rather than a "
        "fact about Eurostat.",
        "",
        "## What is not checked",
        "",
        f"- entries carrying an unresolved breakdown filter: "
        f"**{stats['with_filter']}** of {stats['matched']}",
        "",
        "The catalogue carries titles, not dimension names. When PORDATA "
        "asks for *total and by sex* and a candidate's title says "
        "nothing about sex, the cube may still have that dimension. "
        "`filter_resolved` is `false` on every entry and item 14 must "
        "resolve the filter against the real structure at fetch time, or "
        "refuse to archive the series.",
        "",
    ])


def review_report(stats: dict) -> str:
    lines = [
        "# Eurostat crosswalk: the refusals",
        "",
        "Two kinds, and they are not the same problem.",
        "",
        f"## Rejected as the wrong slice ({stats['vetoed']})",
        "",
        "A head matched and every candidate's breakdown contradicted "
        "PORDATA's. These are the veto working: *Exports total and by "
        "type of energy product* is not *Exports by industry (FIGARO "
        "application)*. Worth reading for a case where the two "
        "vocabularies simply differ.",
        "",
    ]
    for name, tail in stats["vetoes"][:REVIEW_SAMPLE]:
        lines.append(f"- `{name}` — wanted *{tail or '(no breakdown)'}*")
    if len(stats["vetoes"]) > REVIEW_SAMPLE:
        lines.append(f"- …and {len(stats['vetoes']) - REVIEW_SAMPLE} more")
    lines += [
        "",
        f"## No head matched ({len(stats['refusals'])})",
        "",
        "PORDATA's concept, stripped of its unit and breakdown, is not a "
        "Eurostat title's concept. Some are genuinely absent; most are a "
        "vocabulary difference this matcher declines to guess across. "
        "The sample below is the first "
        f"{min(REVIEW_SAMPLE, len(stats['refusals']))}.",
        "",
    ]
    for name, tail in stats["refusals"][:REVIEW_SAMPLE]:
        lines.append(f"- `{name}`")
    if len(stats["refusals"]) > REVIEW_SAMPLE:
        lines.append(f"- …and {len(stats['refusals']) - REVIEW_SAMPLE} more")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    rows = json.loads(CATALOGUE.read_text(encoding="utf-8"))
    datasets = load_eurostat()
    crosswalk, stats = build(rows, datasets)
    if stats["matched"] < MIN_MATCHED:
        raise SystemExit(
            f"build_eurostat_crosswalk: only {stats['matched']} rows "
            f"routed, under the floor of {MIN_MATCHED}. Refusing to "
            "overwrite the crosswalk with a degraded build — either "
            "Eurostat changed its titles or the splitter regressed. "
            "Look before publishing it.")
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(
        json.dumps(crosswalk, ensure_ascii=False, indent=1, sort_keys=True)
        + "\n", encoding="utf-8")
    OUT_QA.write_text(qa_report(stats), encoding="utf-8")
    OUT_REVIEW.write_text(review_report(stats), encoding="utf-8")
    print(f"eurostat crosswalk: {stats['matched']}/{stats['in_scope']} "
          f"routed ({stats['exact']} exact, {stats['single']} single, "
          f"{stats['family']} family), {stats['vetoed']} rejected as the "
          f"wrong slice -> {OUT_JSON}")


if __name__ == "__main__":
    main()
