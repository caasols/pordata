#!/usr/bin/env python3
"""Where PORDATA is thin against INE's own tree (roadmap 16).

The goal stated plainly is to be *more complete than PORDATA*. The trap,
stated just as plainly in the roadmap: the scarce asset is the curation,
not the numbers, so dumping the complement into the catalogue produces
something with INE's coverage and INE's usability — the problem, not the
fix. **Completeness without curation is a regression.** So this emits a
shortlist for a human to accept or reject, and the accept/reject record
is what becomes the curation rule.

**The series-level complement is not computable, and pretending
otherwise would be the worst version of this report.** The crosswalk
names 1,062 of 13,084 INE ids — 8.1% — because it refuses rather than
guesses. Subtracting that from INE's catalogue would present ~12,000
series as "missing from PORDATA" when most of them are indicators
PORDATA covers under a name the matcher would not claim. The number
would be enormous, precise, and wrong.

So the unit here is the **concept**, not the series: content words INE
uses and PORDATA's 2,195 indicator names never use, once. That question
survives a matcher with 25% recall, because it asks whether PORDATA has
*any* indicator touching a subject rather than which series maps to
which. It answers the roadmap's own ranking signal — "themes where
PORDATA is visibly thin against INE's own tree" — and it ranks by how
many series INE itself publishes on the concept, which is the closest
thing to evidence of demand available without the ledger (item 3).

**The annotation list is a curation choice, and the report shows its
working.** INE writes bookkeeping into its titles — vintages ("Série
2012"), classification versions ("CAE Rev.3"), seasonal adjustment
("ajustado de efeitos de calendário"). Those are the highest-frequency
"absent" words by a wide margin and none of them is a subject. Filtering
them is a judgement, so the report lists what was removed and why,
rather than quietly presenting a cleaner list than the data supports.
"""

import collections
import json
import pathlib
import sys

if __package__:
    from . import build_crosswalk as xw
else:
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
    import build_crosswalk as xw

CATALOGUE = pathlib.Path("docs/data/catalogue.json")
CROSSWALK = pathlib.Path("data/crosswalk/ine.json")
OUT_JSON = pathlib.Path("data/coverage/ine-gap.json")
OUT_REPORT = pathlib.Path("data/coverage/INE-GAP.md")

# Below this, INE's own investment in the concept is too small to read as
# evidence of demand — and the tail is long: 458 absent tokens at 8, and
# most of what is under it is a single oddly-worded series.
MIN_SERIES = 8

# How many concepts the report proposes. This is a shortlist for a human
# to work through, not an inventory; a hundred rows is an inventory.
SHORTLIST = 40
EXAMPLES = 3

# INE's bookkeeping, written into the title. None of these is a subject,
# all of them rank near the top of the raw "absent" list, and every one
# is here because it was read in context first:
#
#   serie/antiga/base/metodologia — vintage markers, "(Série 2012 - €)"
#   cae/rev                       — classification version, "(CAE Rev.3)"
#   ajustado/efeitos/calendario/sazonalidade/uteis/homologa
#                                 — seasonal and calendar adjustment
#   hab                           — the unit abbreviation in "N.º/ hab."
#   anteriores/entrevista/primeiros
#                                 — survey reference periods, "nos 12
#                                   meses anteriores à entrevista"
#   trimestral/trimestrais/deflacionado
#                                 — how a series is expressed, not what
#                                   it measures
#
# Removing these is a judgement about what counts as a subject, so the
# report prints the list and its cost rather than applying it silently.
ANNOTATION = {
    "serie", "antiga", "base", "metodologia", "cae", "rev",
    "ajustado", "efeitos", "calendario", "sazonalidade", "uteis",
    "homologa", "hab", "anteriores", "entrevista", "primeiros",
    "trimestral", "trimestrais", "deflacionado",
}

# Two tokens whose series are this much the same are one concept written
# twice — "tumor"/"maligno", "respostas"/"extremas". Keeping both spends
# a shortlist slot on a synonym rather than on the next gap.
SAME_CONCEPT = 0.9


def pordata_vocabulary(rows: list) -> set:
    """Every content word PORDATA's indicator names use, PT and EN.

    Descriptions are deliberately excluded: 96.3% of them are the SEO
    template with the name substituted in, so they widen the vocabulary
    with nothing the name did not already say."""
    vocab = set()
    for row in rows:
        vocab |= xw.content_tokens(xw.phrase_of(row))
        vocab |= xw.content_tokens(row.get("name") or "")
        vocab |= xw.content_tokens(row.get("name_en") or "")
        vocab |= xw.content_tokens(row.get("breakdown") or "")
    return vocab


def absent_concepts(entries: list, vocab: set,
                    min_series: int = MIN_SERIES) -> list:
    """INE words PORDATA never uses, with what INE publishes about them.

    **Ranked by distinct titles, not by series count.** INE republishes
    one indicator across geographies and vintages, so a series count
    measures how widely a single title was cut, not how much INE has to
    say. "TDT" carries 54 series and is one indicator — "Televisores
    ligados à Televisão Digital Terrestre" — repeated; ranking by series
    put it near the top of the shortlist and ranking by title drops it
    out entirely, which is the correct answer for a list about where
    PORDATA is thin."""
    carriers = collections.defaultdict(list)
    for entry in entries:
        for token in entry["tokens"]:
            carriers[token].append(entry)

    concepts = []
    for token, holders in carriers.items():
        if token in vocab or token.isdigit() or len(holders) < min_series:
            continue
        titles = {normalise(e["title"]) for e in holders}
        themes = collections.Counter(
            f'{e["theme"]} / {e["subtheme"]}' for e in holders)
        theme, theme_n = themes.most_common(1)[0]
        concepts.append({
            "token": token,
            "titles": len(titles),
            "series": len(holders),
            "_titles": titles,
            "theme": theme,
            "theme_share": round(theme_n / len(holders), 3),
            "annotation": token in ANNOTATION,
            # distinct titles, shortest first: INE republishes one title
            # across geographies, so the naive slice showed the same
            # sentence three times and taught a reader nothing
            "examples": distinct_examples(holders),
            "geo_levels": sorted({e["geo"] for e in holders})[:6],
        })
    concepts.sort(key=lambda c: (-c["titles"], -c["series"], c["token"]))
    return collapse_synonyms(concepts)


def distinct_examples(holders: list, limit: int = EXAMPLES) -> list:
    seen, out = set(), []
    for entry in sorted(holders, key=lambda e: (len(e["title"]), e["title"])):
        key = normalise(entry["title"])
        if key in seen:
            continue
        seen.add(key)
        out.append(entry["title"])
        if len(out) == limit:
            break
    return out


def normalise(title: str) -> str:
    return xw.normalised_title(title)


def collapse_synonyms(concepts: list, overlap: float = SAME_CONCEPT) -> list:
    """Drop a concept whose titles are already covered by a stronger one.

    "tumor" and "maligno" carry the same 54 titles; both are the concept
    "tumores malignos". The shortlist is a human's working list, so a
    slot spent on the second word of a phrase is a slot not spent on the
    next gap."""
    kept: list = []
    for concept in concepts:
        titles = concept["_titles"]
        host = next((other for other in kept
                     if len(titles & other["_titles"])
                     >= overlap * len(titles)), None)
        if host is not None:
            # the surviving token is arbitrary among exact synonyms — all
            # their counts are identical by definition — so record what
            # collapsed into it. "aparelho (also: circulatorio)" is the
            # phrase; either word alone is half of one.
            host.setdefault("also", []).append(concept["token"])
            continue
        kept.append(concept)
    for concept in concepts:
        concept.pop("_titles", None)
    return kept


def crosswalk_reach(crosswalk: dict, total_series: int) -> dict:
    named = set()
    for entry in crosswalk.values():
        if entry:
            named.update(entry["candidates"])
    return {"named_ids": len(named), "total_series": total_series,
            "share": round(len(named) / total_series, 4) if total_series else 0.0}


def report(concepts: list, reach: dict, vocab_size: int, rows: int) -> str:
    subjects = [c for c in concepts if not c["annotation"]]
    filtered = [c for c in concepts if c["annotation"]]
    by_theme = collections.defaultdict(list)
    for concept in subjects[:SHORTLIST]:
        by_theme[concept["theme"]].append(concept)

    lines = [
        "# Where PORDATA is thin against INE — a shortlist to accept or reject",
        "",
        "Rebuilt by `scripts/coverage_gap.py`. **This is a selection, not an "
        "inventory.** The goal is to be more complete than PORDATA, and the "
        "way to fail at it is to add coverage without curation: every entry "
        "that lands needs a human-meaningful Portuguese name, a theme and a "
        "stated reason for being there. Accepting or rejecting the rows below "
        "one by one is what produces the curation rule — there is no honest "
        "shortcut to one.",
        "",
        "## What this does not claim",
        "",
        f"The **series-level** complement is not computable and is not "
        f"attempted. The crosswalk names {reach['named_ids']} of "
        f"{reach['total_series']} INE ids ({reach['share']:.1%}) because it "
        "refuses rather than guesses, so subtracting it from INE's catalogue "
        "would present some twelve thousand series as \"missing\" when most "
        "are indicators PORDATA covers under a name the matcher declines to "
        "claim. That number would be enormous, precise and wrong.",
        "",
        f"The unit here is the **concept**: a content word INE uses that none "
        f"of PORDATA's {rows} indicator names uses once "
        f"({vocab_size} distinct words, PT and EN). That question survives a "
        "matcher with a quarter of the recall, because it asks whether "
        "PORDATA has *any* indicator touching a subject.",
        "",
        f"Ranked by how many **distinct** INE indicators use the word, not "
        f"by series count: INE republishes one title across geographies and "
        f"vintages, so a series count measures how widely a title was cut "
        f"rather than how much INE has to say. Distinct titles are its own "
        f"investment in the subject, the closest thing to demand available "
        f"before the ledger (item 3) exists. Floor of {MIN_SERIES} series; "
        f"{len(subjects)} concepts clear it, and the {SHORTLIST} largest are "
        "below.",
        "",
    ]

    for theme in sorted(by_theme, key=lambda t: -sum(
            c["series"] for c in by_theme[t])):
        lines += [f"### {theme}", ""]
        for concept in by_theme[theme]:
            also = concept.get("also")
            with_also = (f" (with `{'`, `'.join(also[:4])}`)" if also else "")
            lines.append(f"- **`{concept['token']}`**{with_also} — "
                         f"{concept['titles']} distinct INE indicators "
                         f"({concept['series']} series), "
                         f"{concept['theme_share']:.0%} in this subtheme; "
                         f"published down to "
                         f"{', '.join(concept['geo_levels'][:3])}")
            for example in concept["examples"]:
                lines.append(f"  - {example}")
        lines.append("")

    lines += [
        "## What was filtered out, and why",
        "",
        "INE writes bookkeeping into its titles — vintages, classification "
        "versions, seasonal adjustment, survey reference periods. Those words "
        "are absent from PORDATA because they are not subjects, and they "
        "dominate the raw list. Removing them is a judgement, so here it is "
        "in the open:",
        "",
    ]
    for concept in filtered[:12]:
        lines.append(f"- `{concept['token']}` — {concept['titles']} "
                     f"indicators / {concept['series']} series "
                     f"— e.g. {concept['examples'][0]}")
    lines += ["",
              "If any of these is a subject rather than an annotation, take "
              "it out of `ANNOTATION` in `scripts/coverage_gap.py` and it "
              "rejoins the shortlist.",
              ""]
    return "\n".join(lines)


def main() -> None:
    rows = json.loads(CATALOGUE.read_text(encoding="utf-8"))
    entries = xw.load_ine()
    crosswalk = json.loads(CROSSWALK.read_text(encoding="utf-8"))

    vocab = pordata_vocabulary(rows)
    concepts = absent_concepts(entries, vocab)
    reach = crosswalk_reach(crosswalk, len(entries))

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(
        json.dumps({"crosswalk_reach": reach,
                    "pordata_vocabulary": len(vocab),
                    "min_series": MIN_SERIES,
                    "concepts": concepts},
                   ensure_ascii=False, indent=1),
        encoding="utf-8")
    OUT_REPORT.write_text(
        report(concepts, reach, len(vocab), len(rows)), encoding="utf-8")

    subjects = sum(1 for c in concepts if not c["annotation"])
    print(f"coverage gap: {subjects} concepts INE publishes and PORDATA "
          f"never names (>= {MIN_SERIES} series each), "
          f"{len(concepts) - subjects} filtered as INE bookkeeping")


if __name__ == "__main__":
    main()
