#!/usr/bin/env python3
"""Text operators shared by a matcher and the analysis that justifies it.

`analyse_eurostat_crosswalk.py` carried byte-identical copies of
`STOPWORDS`, `UNIT_PAREN`, `PORDATA_TAIL`, `EUROSTAT_TAIL`, `norm_title`
and `strip_accents`, plus near-copies of `tokens` and `strip_unit`. That
matters more than ordinary duplication: the analyser's output is this
project's *cited evidence* — "plain containment reaches 18.3%", "ranking
picked a winner on 10 of 83 ties", "a token floor drops 38 matches" —
while the matcher is rebuilt nightly. A change to `strip_unit` in one
file would silently invalidate every one of those figures with nothing
to notice, because no test imported both modules and no workflow runs
the analysers at all.

One definition, imported by both. `pordata_lib.py` is the precedent for
this; it stays separate from it because these are matching operators and
that module is the harvest's.
"""

import re
import unicodedata

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
# "Obesity rate by body mass index" opens its breakdown that way.
PORDATA_TAIL = re.compile(r"\s*[:,]?\s*\b(?:total and by|and by|by)\b.*$",
                          re.I)
EUROSTAT_TAIL = re.compile(r"\s*,?\s*\bby\b.*$", re.I)


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
