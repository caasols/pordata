# INE crosswalk — measured

Rebuilt by `scripts/build_crosswalk.py`. Every figure here is counted from the run that wrote it (decision 7).

- PORDATA rows in scope (INE-sourced, portugal/municipios): **839**
- matched to a candidate family: **206** (24.6%)
- refused (`null` — no candidate survived the filters): **633** (75.4%)

## Confidence

- `exact` — an INE title normalises to the indicator's own phrase: **113**
- `family` — containment plus head, derivation and negation parity: **93**

## Family size

One-to-many is the relation's real shape (spike A5), so size is reported, never used to refuse.

- median **8**, max **590**
- families of exactly one series: **14**
- families larger than the 25 stored ids: **56** (`truncated: true`; `n_candidates` keeps the true size)

## Not in scope

`europa` rows are Eurostat's and BPstat has not been measured. Spike A5's shape must not be assumed to carry over — measure each the same way before specifying it.
