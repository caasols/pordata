#!/usr/bin/env python3
"""Route PORDATA indicators to the INE series that could answer them
(roadmap 2).

**The relation is one-to-many, and that is not matcher noise.** Spike A5
measured it: INE's catalogue is series-level where PORDATA's is
indicator-level, so one PORDATA indicator corresponds to a *family* of
INE series split by geography, periodicity, census-versus-estimate and
breakdown. Exact title matching leaves 84.6% unmatched; token
containment ties a median of 9 entries. A crosswalk storing one
`ine_id` per row would be choosing arbitrarily and recording the choice
as fact — the failure the featured matcher was rewritten to avoid.

So this stores the **candidate set and the evidence that selected it**,
and picking a series is deferred to fetch time (item 14), where the
geography and period follow from what was asked.

**Four filters, each earning its place against a measured failure.** In
the order they were added, because each one was a wrong match first:

1. **Full containment.** Every content word of PORDATA's phrase must
   appear in the INE title. Requiring only the *rare* words let
   "Dimensão média das empresas" match "Dimensão média das famílias
   clássicas" — `empresas` was common enough to go unchecked.
2. **The INE title's head must be a word PORDATA used.** Without it
   "População residente com idade entre 16 e 89 anos" matched "**Tempo
   de acesso** a pé da população residente…", and "Mercadorias
   transportadas" matched "**Sobrevivências** de…". Only this direction
   is checkable: full containment already puts PORDATA's own head in
   every surviving title, so testing that half was dead code — mutation
   testing found it by mutating it away with nothing failing.
3. **Derivation parity.** A count and a rate are different indicators.
   "Água distribuída" matched "Água distribuída **por habitante**" until
   the normalisation markers had to agree on both sides.
4. **Negation parity.** "Alojamentos familiares clássicos" matched
   "…alojamentos familiares **não** clássicos".

Plus geography: a `municipios` indicator needs a series INE publishes at
municipal level or finer. `portugal` gets no geographic filter, because
`geo_lastlevel` is the *finest* level published and a municipal series
still answers a national question.

**What is deliberately not filtered: family size.** "Agregados
domésticos privados" ties 62 entries because INE genuinely publishes 62
of them. Refusing on size would throw away the correct answer for being
correct about a broad indicator. The size is reported instead, and
candidates are ordered by how little they add to PORDATA's phrase, so
the closest series is first.

**Coverage is not the goal; being right is.** Rows with no surviving
candidate get `null`, and `data/crosswalk/REVIEW.md` lists the near
misses for a human — the same shape as `FEATURED-UNMATCHED.md`.
"""

import collections
import csv
import io
import json
import pathlib
import re
import sys

if __package__:
    from . import pordata_lib as lib  # noqa: F401  (kept for parity)
else:
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

CATALOGUE = pathlib.Path("docs/data/catalogue.json")
INE_CSV = pathlib.Path("data/ine/indicators.csv")
OUT_JSON = pathlib.Path("data/crosswalk/ine.json")
OUT_QA = pathlib.Path("data/crosswalk/QA.md")
OUT_REVIEW = pathlib.Path("data/crosswalk/REVIEW.md")

# Kept out of docs/data/catalogue.json on purpose: every visitor already
# downloads 1.27 MB before the first search (roadmap 6f), and nothing in
# the UI reads the crosswalk yet. Item 14 consumes this file in CI.

MAX_STORED = 25
REVIEW_SAMPLE = 40

# A floor, not a target. Measured 2026-08-24: 192 of 839 in-scope rows
# match. Coverage is low by design — the filters refuse rather than
# guess — but a *drop* means something broke upstream rather than the
# crosswalk becoming more careful. The catalogue's `title` field is the
# obvious fragility: a parser change that stops splitting the breakdown
# clause would feed whole titles in and quietly halve this. Margin is
# for the catalogue growing and rewording, the way the QA floors work.
MIN_MATCHED = 170
# A plurality is not a finding. `operation` and `theme` are the most
# common values across the candidate family, and the detail page prints
# them unhedged as "Operação estatística do INE" — so on 38 of 212
# entries the page asserted an attribution that under half the family
# agreed with, one of them naming a health survey for a resident
# population series (portugal/3018, share 0.447). Below this the field
# is null and the page omits the row: the same rule the rest of the
# matcher follows, one level down. Measured share distribution: median
# 1.0, 38 entries under 0.5, minimum 0.231.
MIN_SHARE = 0.5

# The finest level INE publishes at. A municipal question needs a series
# that reaches municipalities; a national one can be served by any level,
# since a finer series aggregates upward.
# A closed vocabulary matched by exact string equality against INE's
# `geo_lastlevel`, a field that already shows drift ('NUTS II' beside
# 'NUTS 2', 'Região agrária' beside 'região agrária'). Simulated: rename
# the 1,457 'Freguesia' rows and the build still exits 0 at 199/839 —
# above the 170 floor — while 13 entries vanish, 15 shrink, and the
# total candidate count falls 14.9%. A match count cannot see that,
# which is why the floor below counts candidates too.
MUNICIPAL_LEVELS = {"Município", "Freguesia", "Lugar", "Freguesia/Agregação"}
# Measured 8,452 today. A vocabulary member that stops matching takes
# thousands of candidates with it while leaving the match count healthy.
MIN_CANDIDATES = 7500

STOPWORDS = {
    "de", "da", "do", "das", "dos", "e", "em", "no", "na", "nos", "nas",
    "por", "a", "o", "as", "os", "com", "para", "total", "ao", "aos",
    "um", "uma", "que",
}

# Words that change *what* is measured rather than how it is sliced: a
# count and a rate over the same subject are two indicators, not one
# family. Parity is required in both directions — PORDATA writes rates
# too ("Acidentes de viação com vítimas por mil habitantes").
DERIVATION = {
    "proporcao", "percentagem", "taxa", "indice", "racio", "media",
    "mediana", "densidade", "variacao", "capita", "peso", "quota",
    "medio", "mediano", "percentual",
}
PER_UNIT = re.compile(r"\bpor\s+(mil|cem|100|1000|habitante)")
NEGATION = re.compile(r"\b(nao|sem|exceto|excepto|excluindo|fora)\b")

# INE suffixes the unit in parentheses — "(N.º)", "(GT)", "(kg/ ha)" —
# which PORDATA never does.
# Two readings of the same suffix, on purpose.
#
# TRAILING_UNIT is what `normalised_title` strips before asking whether
# two titles are the *same indicator*, and it stays short deliberately:
# "Casamentos (Entre pessoas de sexo oposto - N.º)" is a breakdown, and
# stripping it would let a slice masquerade as an exact match.
#
# TRAILING_PAREN is what `unit_markers` reads to find `%` or `‰`, and
# takes any length, because INE writes vintages into the same
# parenthesis: "(Série 2021 - %)" is a percentage and a 12-character cap
# cannot see it.
TRAILING_UNIT = re.compile(r"\s*\([^)]{1,12}\)\s*$")

# PORDATA writes a category ahead of a colon — "Cinema: nº de ecrãs",
# "SNS: hospitais gerais e especializados". INE names the indicator
# alone, so the category is a word the title can never contain and full
# containment refuses the row. Colon prefixes are **6x over-represented
# among refusals** (15.5% of 633, against 2.4% of matches), which is
# what made this worth chasing.
#
# The trap is that a colon does not always mean a category: "Densidade
# populacional: estatísticas por município" has the indicator in *front*
# and boilerplate behind, so taking the tail would throw the indicator
# away. The two are separable by a measured property rather than a
# guess — **a category repeats and an indicator does not**. Measured
# across the catalogue: 36 heads are shared by two or more rows (sns 20,
# cinema 14, administrações públicas 13, teatro 4) and every one reads
# as a category; 45 appear once (abortos, dívida pública, óbitos
# infantis) and every one reads as the indicator itself.
#
# Same shape as `split_breakdown`, mirrored: demote the tail there, the
# head here, and refuse in the case where the part being demoted is the
# indicator.
CATEGORY_COLON = re.compile(r"^([^:]{2,40}):\s*(.+)$")
MIN_CATEGORY_ROWS = 2
TRAILING_PAREN = re.compile(r"\(([^)]*)\)\s*$")


def trailing_unit(title: str) -> str:
    """The final parenthesised group of a title, or "" when there is
    none. Used for the unit symbol, not for title equality."""
    match = TRAILING_PAREN.search(title or "")
    return match.group(1) if match else ""


def strip_accents(text: str) -> str:
    import unicodedata
    decomposed = unicodedata.normalize("NFD", (text or "").lower())
    return "".join(c for c in decomposed if unicodedata.category(c) != "Mn")


def ordered_tokens(text: str) -> list[str]:
    """Content words in order of first appearance. Order matters for one
    thing only — the head — so duplicates are dropped rather than kept."""
    out: list[str] = []
    for word in re.split(r"[^a-z0-9]+", strip_accents(text)):
        # numbers of any length: the two-character floor that filters
        # noise out of prose also swallowed age brackets, and
        # "População residente com **16 a 64** anos e **65 a 89** anos"
        # then matched a 336-entry family headed by "com menos de 15
        # anos". Three rows stopped matching when this changed and all
        # three were that mistake.
        if ((len(word) > 2 or word.isdigit())
                and word not in STOPWORDS and word not in out):
            out.append(word)
    return out


def content_tokens(text: str) -> set:
    return set(ordered_tokens(text))


def head(text: str) -> str | None:
    words = ordered_tokens(text)
    return words[0] if words else None


def derivation_markers(text: str) -> set:
    """Normalisation this phrase applies, from its **words only**.

    Symbols are deliberately excluded and handled by `unit_markers`,
    because the two sides do not write units in the same place. INE
    suffixes the title — "Taxa de desemprego (Série 2021 - %)" — and
    PORDATA never does; it carries the unit in a separate field. Reading
    `%` out of the raw title made every INE rate carry a marker its
    PORDATA counterpart could not, and "Taxa de desemprego" was refused
    against "Taxa de desemprego". The unit is still compared, but only
    where PORDATA has one to compare with."""
    markers = {t for t in content_tokens(text) if t in DERIVATION}
    if PER_UNIT.search(strip_accents(text)):
        markers.add("per")
    return markers


def unit_markers(text: str) -> set:
    """The rate symbols in a unit string, from either side.

    PORDATA writes "Taxa - %" in its own `unit` field; INE writes "(%)"
    at the end of the title. Same information, two places."""
    markers = set()
    if "%" in (text or ""):
        markers.add("pct")
    if "‰" in (text or ""):
        markers.add("permil")
    return markers


def negations(text: str) -> set:
    return set(NEGATION.findall(strip_accents(text)))


def geo_ok(area: str, geo_lastlevel: str) -> bool:
    if area == "municipios":
        return geo_lastlevel in MUNICIPAL_LEVELS
    return True


def category_heads(rows: list) -> set:
    """Colon heads that behave like categories, from the catalogue.

    Derived, not listed: a hand-written vocabulary would be one more
    thing to maintain and would miss whatever PORDATA adds next."""
    counts: collections.Counter = collections.Counter()
    for row in rows:
        match = CATEGORY_COLON.match(row.get("title") or row.get("name") or "")
        if match:
            counts[strip_accents(match.group(1)).strip()] += 1
    return {head for head, n in counts.items() if n >= MIN_CATEGORY_ROWS}


def split_category(phrase: str, categories: set) -> tuple[str, str]:
    """(indicator, category) — the category is "" when there is none.

    Refuses in the direction that matters: an unrepeated head is the
    indicator, so the phrase passes through whole rather than being
    reduced to a qualifier like "estatísticas por município"."""
    match = CATEGORY_COLON.match(phrase)
    if not match:
        return phrase, ""
    head = strip_accents(match.group(1)).strip()
    if head not in categories:
        return phrase, ""
    tail = match.group(2).strip()
    # A tail with no content words is a breakdown, not an indicator.
    # "População residente: total" and "Pessoal ao serviço nas empresas:
    # total" both have heads that repeat often enough to look like
    # categories, and both lost their match to this rule before the
    # guard existed — because `total` is a stopword and reducing the
    # phrase to it leaves nothing to match on at all.
    if not content_tokens(tail):
        return phrase, ""
    return tail, match.group(1).strip()


def phrase_of(row: dict, categories: set | None = None) -> str:
    """The indicator without its breakdown clause where `split_breakdown`
    found one: "Casamentos – total e por sexo" is asking about
    casamentos, and the tail is a slicing instruction INE expresses as
    separate series. And without its category prefix where one repeats
    across the catalogue, since INE names the indicator alone."""
    phrase = row.get("title") or row.get("name") or ""
    if categories:
        phrase, _category = split_category(phrase, categories)
    return phrase


def ine_entities(row: dict) -> list[str]:
    return [f.split(" - ")[0].strip() for f in (row.get("fontes") or [])]


def in_scope(row: dict) -> bool:
    """INE-sourced, and in an area INE publishes for. `europa` rows are
    Eurostat's and are measured separately before being specified —
    the A5 shape must not be assumed to carry over."""
    return (row.get("area") in ("portugal", "municipios")
            and any(e.upper().startswith("INE") for e in ine_entities(row)))


def load_ine(path: pathlib.Path | None = None) -> list[dict]:
    # resolved at call time, not bound as a default: a default argument
    # captures the constant when the function is defined, so the module
    # attribute stops being the single source of truth the moment
    # anything overrides it
    path = INE_CSV if path is None else path
    csv.field_size_limit(sys.maxsize)
    with io.open(path, encoding="utf-8") as handle:
        entries = []
        for raw in csv.DictReader(handle):
            title = raw["title"]
            entries.append({
                "id": raw["id"],
                "title": title,
                "tokens": content_tokens(title),
                "head": head(title),
                # the title without its unit suffix for words, and the
                # suffix alone for symbols — the two are compared
                # against different things
                "derivation": derivation_markers(TRAILING_UNIT.sub("", title)),
                "unit": unit_markers(trailing_unit(title)),
                "negations": negations(title),
                "geo": raw["geo_lastlevel"],
                "periodicity": raw["periodicity"],
                "source": raw["source"],
                "theme": raw["theme"],
                "subtheme": raw["subtheme"],
            })
    return entries


def build_index(entries: list[dict]) -> dict:
    index = collections.defaultdict(list)
    for position, entry in enumerate(entries):
        for token in entry["tokens"]:
            index[token].append(position)
    return index


def normalised_title(title: str) -> str:
    return re.sub(r"\s+", " ",
                  re.sub(r"[^a-z0-9]+", " ",
                         TRAILING_UNIT.sub("", strip_accents(title)))).strip()


def candidates(row: dict, entries: list[dict], index: dict,
               categories: set | None = None) -> list[dict]:
    """The family, closest first. Empty means refuse."""
    phrase = phrase_of(row, categories)
    wanted = content_tokens(phrase)
    if not wanted:
        return []
    want_derivation = derivation_markers(phrase)
    want_negations = negations(phrase)
    want_unit = unit_markers(row["unit"]) if row.get("unit") else None

    # containment is an AND over the query's tokens, so the smallest
    # posting list bounds the work rather than the largest
    postings = sorted((index.get(t, []) for t in wanted), key=len)
    if not postings[0]:
        return []
    shared = set(postings[0]).intersection(*(set(p) for p in postings[1:]))

    matched = []
    for position in shared:
        entry = entries[position]
        if not geo_ok(row["area"], entry["geo"]):
            continue
        if entry["derivation"] != want_derivation:
            continue
        # only when PORDATA has a unit to speak with: it is present on
        # 270 of 839 in-scope rows, so requiring parity unconditionally
        # would refuse every row that simply has no unit recorded
        if want_unit is not None and entry["unit"] != want_unit:
            continue
        if entry["negations"] != want_negations:
            continue
        # only one direction is checkable here: full containment already
        # guarantees PORDATA's head is in the INE title, so the test that
        # earns its place is the reverse — the INE title's own subject
        # must be a word PORDATA used
        if entry["head"] and entry["head"] not in wanted:
            continue
        matched.append((entry, len(entry["tokens"] - wanted)))
    # exact titles first, then fewest additions: the closest series leads
    # the family, so truncating the stored list can never drop a better
    # candidate than one it keeps. The title breaks ties so the order is
    # stable across runs.
    target = normalised_title(phrase)
    matched.sort(key=lambda item: (
        normalised_title(item[0]["title"]) != target, item[1],
        item[0]["title"]))
    return [entry for entry, _extra in matched]


def entry_summary(row: dict, family: list[dict],
                  categories: set | None = None) -> dict:
    """What was matched, how, and how confident to be about it."""
    themes = collections.Counter(e["theme"] for e in family)
    sources = collections.Counter(e["source"] for e in family)
    theme, theme_n = themes.most_common(1)[0]
    source, source_n = sources.most_common(1)[0]
    theme_share = theme_n / len(family)
    source_share = source_n / len(family)
    # kept as evidence either way; nulled as a *claim* when the family
    # does not support it
    if source_share < MIN_SHARE:
        source = None
    if theme_share < MIN_SHARE:
        theme = None
    target = normalised_title(phrase_of(row, categories))
    exact = [e["id"] for e in family if normalised_title(e["title"]) == target]
    stored = family[:MAX_STORED]
    stored_ids = {e["id"] for e in stored}
    return {
        "source": "INE",
        "candidates": [e["id"] for e in stored],
        "n_candidates": len(family),
        "truncated": len(family) > MAX_STORED,
        # a subset of `candidates` by construction, so a reader never
        # meets an id in one list and not the other; `n_exact` keeps the
        # true count when the family is truncated
        "exact_title": [i for i in exact if i in stored_ids],
        "n_exact": len(exact),
        "operation": source,
        "operation_share": round(source_share, 3),
        "theme": theme,
        "theme_share": round(theme_share, 3),
        "subthemes": sorted({e["subtheme"] for e in family})[:10],
        "geo_levels": sorted({e["geo"] for e in family}),
        "periodicities": sorted({e["periodicity"] for e in family}),
        # an exact title inside the family is the strongest evidence
        # available offline; without one this is a family by containment
        "confidence": "exact" if exact else "family",
    }


def build(rows: list[dict], entries: list[dict]) -> tuple[dict, dict]:
    index = build_index(entries)
    # derived from the whole catalogue, so a head only counts as a
    # category when it actually repeats across it
    categories = category_heads(rows)
    crosswalk: dict = {}
    stats = {"in_scope": 0, "matched": 0, "refused": 0, "exact": 0,
             "family": 0, "sizes": [], "refusals": [],
             "categories": len(categories), "decategorised": 0}
    for row in rows:
        if not in_scope(row):
            continue
        stats["in_scope"] += 1
        key = f"{row['area']}/{row['id']}"
        _phrase, category = split_category(
            row.get("title") or row.get("name") or "", categories)
        family = candidates(row, entries, index, categories)
        if not family:
            crosswalk[key] = None
            stats["refused"] += 1
            stats["refusals"].append((phrase_of(row, categories), row["area"]))
            continue
        summary = entry_summary(row, family, categories)
        if category:
            # recorded as evidence: the reader should be able to see that
            # "Cinema" was set aside before the title was compared
            summary["category"] = category
            stats["decategorised"] += 1
        crosswalk[key] = summary
        stats["matched"] += 1
        stats[summary["confidence"]] += 1
        stats["sizes"].append(summary["n_candidates"])
    return crosswalk, stats


def median(values: list) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return float(ordered[mid])
    return (ordered[mid - 1] + ordered[mid]) / 2


def qa_report(stats: dict) -> str:
    sizes = stats["sizes"]
    scope = stats["in_scope"] or 1
    lines = [
        "# INE crosswalk — measured",
        "",
        "Rebuilt by `scripts/build_crosswalk.py`. Every figure here is "
        "counted from the run that wrote it (decision 7).",
        "",
        f"- PORDATA rows in scope (INE-sourced, portugal/municipios): "
        f"**{stats['in_scope']}**",
        f"- matched to a candidate family: **{stats['matched']}** "
        f"({stats['matched'] / scope:.1%})",
        f"- refused (`null` — no candidate survived the filters): "
        f"**{stats['refused']}** ({stats['refused'] / scope:.1%})",
        "",
        "## Confidence",
        "",
        f"- `exact` — an INE title normalises to the indicator's own "
        f"phrase: **{stats['exact']}**",
        f"- `family` — containment plus head, derivation and negation "
        f"parity: **{stats['family']}**",
        "",
        "## Family size",
        "",
        "One-to-many is the relation's real shape (spike A5), so size is "
        "reported, never used to refuse.",
        "",
        f"- median **{median(sizes):.0f}**, max **{max(sizes) if sizes else 0}**",
        f"- families of exactly one series: "
        f"**{sum(1 for s in sizes if s == 1)}**",
        f"- families larger than the {MAX_STORED} stored ids: "
        f"**{sum(1 for s in sizes if s > MAX_STORED)}** (`truncated: true`; "
        "`n_candidates` keeps the true size)",
        "",
        "## Not in scope",
        "",
        "`europa` rows are Eurostat's and BPstat has not been measured. "
        "Spike A5's shape must not be assumed to carry over — measure "
        "each the same way before specifying it.",
        "",
    ]
    return "\n".join(lines)


def review_report(stats: dict) -> str:
    refusals = stats["refusals"]
    lines = [
        "# INE crosswalk — refusals worth a human eye",
        "",
        f"{len(refusals)} rows in scope found no candidate that survived "
        "full containment plus head, derivation and negation parity. "
        "Refusing beats guessing, but a refusal is not evidence that no "
        "upstream series exists — most of these are PORDATA rewording "
        "the indicator, or computing a ratio INE publishes only as its "
        "parts.",
        "",
        f"A sample of {min(REVIEW_SAMPLE, len(refusals))}, spread across "
        "the list rather than taken from the front, so it is not all one "
        "letter of the alphabet:",
        "",
    ]
    step = max(1, len(refusals) // REVIEW_SAMPLE) if refusals else 1
    for phrase, area in refusals[::step][:REVIEW_SAMPLE]:
        lines.append(f"- `{area}` — {phrase}")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    rows = json.loads(CATALOGUE.read_text(encoding="utf-8"))
    entries = load_ine()
    crosswalk, stats = build(rows, entries)

    # Checked before the writes, and unconditionally — both were wrong.
    # The floor used to sit after three `write_text` calls and only under
    # `--strict`, so a collapsed build landed on disk and the harvest's
    # `always()` commit pushed it; the only issue-opening step is keyed on
    # the QA status, which is `pass` in that case, so nothing said so.
    # The Eurostat sibling has always refused before writing. Same rule
    # here now: a degraded crosswalk never reaches the working tree, so
    # there is nothing to revert.
    total_candidates = sum(stats["sizes"])
    if total_candidates < MIN_CANDIDATES:
        raise SystemExit(
            f"build_crosswalk: {stats['matched']} rows matched but only "
            f"{total_candidates} candidates in total, under the floor of "
            f"{MIN_CANDIDATES}. Families have shrunk without the match "
            "count moving — check MUNICIPAL_LEVELS against the "
            "`geo_lastlevel` values in the INE snapshot before lowering "
            "this.")
    if stats["matched"] < MIN_MATCHED:
        raise SystemExit(
            f"build_crosswalk: only {stats['matched']} rows matched, "
            f"under the floor of {MIN_MATCHED}. Refusing to overwrite the "
            "crosswalk with a degraded build — something upstream changed "
            "shape; check the catalogue's `title` field and the INE "
            "snapshot before lowering this.")

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(
        json.dumps(crosswalk, ensure_ascii=False, indent=1, sort_keys=True),
        encoding="utf-8")
    OUT_QA.write_text(qa_report(stats), encoding="utf-8")
    OUT_REVIEW.write_text(review_report(stats), encoding="utf-8")
    print(f"crosswalk: {stats['matched']}/{stats['in_scope']} matched "
          f"({stats['exact']} exact, {stats['family']} family), "
          f"{stats['refused']} refused; median family "
          f"{median(stats['sizes']):.0f}")


if __name__ == "__main__":
    main()
