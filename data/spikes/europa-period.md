# Spike: the period on europa pages (roadmap 20)

> **Correction, 2026-08-25.** The opening sentence read "Neither appears on europa" — directly above the table that counts 4 year elements and 26–30 picker options on all three sampled pages. It was a hardcoded literal in `render()` rather than a reading of `known`, so re-running the probe regenerated it. The sentence is now derived from the counts, and the five documents that repeated it are corrected.

`extract_period` handles portugal's named year elements and the municipios `<select>` picker. Both are already handled, and **municipios year picker and portugal year element and select element at all** appear on europa — so `extract_period` works there today and `period_ratio[europa]` reads 0 because no europa record has been re-fetched since the parser learned the field, not because the template lacks one. A4 answered this for municipios by naming the innermost element around every year in the page; this is the same question pointed at the third template.

## Are the mechanisms we already handle present?

Cheapest possible answer first — if europa uses the picker, there is nothing to write.

| page | portugal year element | municipios year picker | select element at all | time element | data attribute with a year |
|---|---|---|---|---|---|
| `europa/abastecimento+publico+de+agua-1415` | 4 | 30 | 2 | 0 | 0 |
| `europa/fluxos+migratorios+internacionais-1622` | 4 | 26 | 2 | 0 | 0 |
| `europa/populacao+inativa+com+15+e+mais+anos+total+e+por+grupo+etario-1942` | 4 | 30 | 2 | 0 | 0 |

## Where the years actually are

### `europa/abastecimento+publico+de+agua-1415` (165 KB, 75 years found)

| enclosing element | years |
|---|---|
| `<option>` | 30 |
| `<div>` | 3 |
| `<div> class="CountryPT"` | 2 |
| `<div> class="YearCurrentText"` | 2 |
| `<div> class="YearOtherText"` | 2 |

### `europa/fluxos+migratorios+internacionais-1622` (167 KB, 67 years found)

| enclosing element | years |
|---|---|
| `<option>` | 26 |
| `<div>` | 3 |
| `<div> class="CountryPT"` | 2 |
| `<div> class="YearCurrentText"` | 2 |
| `<div> class="YearOtherText"` | 2 |

### `europa/populacao+inativa+com+15+e+mais+anos+total+e+por+grupo+etario-1942` (173 KB, 75 years found)

| enclosing element | years |
|---|---|
| `<option>` | 30 |
| `<div>` | 3 |
| `<div> class="CountryPT"` | 2 |
| `<div> class="YearCurrentText"` | 2 |
| `<div> class="YearOtherText"` | 2 |

## What to do with this

A selector that appears on all three sampled pages is a candidate for `extract_period`; one that appears on a single page is a coincidence. If nothing is shared, say so and leave the floor at 0 — a wrong extractor is worse than a recorded gap, because the gate would then pass while the field was junk.
