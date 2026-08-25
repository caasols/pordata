# Eurostat crosswalk QA

Rebuilt by `scripts/build_eurostat_crosswalk.py` and gated at `qa_catalogue.py --strict` with a floor of 100 matches. Offline and reproducible.

## Coverage

- in scope (`europa`, Eurostat-sourced, English name): **616**
- routed to at least one dataset: **118** (19.2%)
- refused: **498** — of which **18** found a head and rejected every candidate as the wrong slice
- Eurostat datasets searched: **7572**

Entries store dataset **codes**, not URLs. Every download and browser URL in the cached catalogue is exactly the code substituted into `https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/{code}/?format=TSV` and `https://ec.europa.eu/eurostat/databrowser/product/view/{code}` — measured across all of them, and asserted on every build, so a changed pattern stops the build rather than publishing dead links.

## Confidence

- **exact** (a candidate's title is the indicator's): **35** (29.7%)
- **single** (one candidate, title not identical): **37**
- **family** (several rival cubes, choice deferred): **46**

## Candidate set size

- median **1**, max **73**
- resolving to exactly one dataset: **60**

A large set means something different here from the INE crosswalk. There, a family of 62 was 62 pre-sliced series that all belong to the indicator, and size was never a reason to refuse. Here the candidates are **rival cubes** and only one is right, so a large set is an unresolved question rather than a fact about Eurostat.

## What is not checked

- entries carrying an unresolved breakdown filter: **69** of 118

The catalogue carries titles, not dimension names. When PORDATA asks for *total and by sex* and a candidate's title says nothing about sex, the cube may still have that dimension. `filter_resolved` is `false` on every entry and item 14 must resolve the filter against the real structure at fetch time, or refuse to archive the series.
