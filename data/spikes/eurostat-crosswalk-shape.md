# The shape of the PORDATA–Eurostat relation (roadmap 2)

The mirror of spike A5, run because the roadmap says to measure Eurostat rather than assume INE's shape carries over. Offline and reproducible: `python3 scripts/analyse_eurostat_crosswalk.py`.

## Inputs

- PORDATA `europa` rows citing Eurostat, with an English name: **616**
- Eurostat datasets: **7572** (7493 distinct normalised titles)

**Matched EN↔EN.** Every `europa` row carries an English name and every Eurostat title is English, so this comparison does not cross a translation gap — which the INE crosswalk did, and which is why that matcher had to be so strict.

## Exact title match

- an exact normalised title exists for **25** rows (4.1%)

## Token containment (all of PORDATA's words inside a title)

- fully contained by at least one dataset: **113** (18.3%)
- no shared token with any dataset: **3**

Best containment achieved, distribution:

- 0.00–0.25: 2
- 0.25–0.50: 144
- 0.50–0.75: 262
- 0.75–1.00: 92
- 1.00–1.01: 113

## How many datasets does a contained row tie?

- median **1**, mean **16.6**, max **505**
- resolves to exactly one: **57** of 113

**This is the number that decides the schema.** INE tied a median of 9 pre-sliced series, which is why its crosswalk stores a candidate set and defers the choice to fetch time. A median near 1 here would mean a PORDATA row maps to one dataset plus a dimension filter, and the entry should say so rather than pretend to a family it does not have.

## Does the theme tree constrain it?

- ties landing in a single Eurostat theme: **42** of 113 (37%)

INE's themes turned out not to constrain usefully — purity there *rejected* exact matches, because INE files one series under two themes. Whether Eurostat's tree behaves the same way is the question, and it is the cheapest precision available if it does not.

## Which operator, and which ones were rejected

Containment over the raw titles reaches 18.3% and the reason is structural, not incidental. Diagnosing the near-misses named the blocking words: `percentage` on 35 rows, `euro` on 23, then `type`, `category`, `sex`, `sector`. **PORDATA's name is a concept plus a slicing instruction plus a unit; Eurostat's title is a cube name whose unit and dimensions are not in it.** Asking a cube's name to contain the words for its own dimensions is asking the wrong question.

So the operator splits both sides at the `by` that opens the breakdown and matches the **heads**, exactly:

- an exact head match exists for **136** rows (22.1%)

### The tail is a veto, not a ranking

Ranking the tied candidates by how well PORDATA's breakdown matches Eurostat's picked a single winner on only 10 of 83 tied rows, and one of the first eight sampled was *Employment by professional status — **ENP-South countries***, a non-EU geography. As a discriminator it manufactures confidence.

As a **veto** the same signal is sound: if both sides name a breakdown and the two share no word, they are not the same slice. Silence on either side is not a contradiction, so the veto needs two tails to fire.

- head matches surviving the veto: **118** (of 136; **18** refused outright)
- surviving candidate sets resolving to exactly one dataset: **60**

Every outright refusal that was read by hand was correct:

- `Fatal accidents at work total and by sex` ≠ *Fatal Accidents at work by NACE Rev. 2 activity*
- `General government expenditure by category (euro)` ≠ *General government expenditure by function (COFOG)*
- `General government expenditure by category (percentage)` ≠ *General government expenditure by function (COFOG)*
- `Agricultural holdings total and by dimension` ≠ *Agricultural holdings by legal form of the management*
- `Exports total and by type of energy product` ≠ *Exports by industry (FIGARO application)*
- `Imports total and by type of energy product` ≠ *Imports by industry (FIGARO application)*

### Rejected: a content-token floor on the head

The obvious guard against a generic head — *Exports* matching *Exports by industry (FIGARO application)* — is to require the head to carry two content words. It would drop **38** head matches, and among them *Obesity rate by body mass index*, which matches its Eurostat title **exactly**, and *Total fertility rate*, whose only content word survives the stopword list. The floor measures length where the failure is contradiction; the veto catches the same two cases without the collateral. Recorded because it was the first idea and the numbers are what refuted it.

### What the entry cannot claim

The catalogue carries titles, not dimension names. When PORDATA asks for *total and by sex* and the candidate cube's title says nothing about sex, the cube may still have that dimension — there is no way to tell without fetching each dataset's structure, which is 7,572 requests and item 14's problem. So the breakdown is stored as an **unresolved filter**, never as a satisfied one.
