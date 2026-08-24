# Spike: the period on europa pages (roadmap 20)

`extract_period` handles portugal's named year elements and the municipios `<select>` picker. Neither appears on europa, so `period_ratio[europa]` is gated at a floor of 0 — a recorded gap, not an acceptable state. A4 answered this for municipios by naming the innermost element around every year in the page; this is the same question pointed at the third template.

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
