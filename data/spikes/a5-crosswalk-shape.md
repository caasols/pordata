# Spike A5 - the shape of the PORDATA-INE crosswalk

Roadmap 2 was written as "match each catalogue entry to its upstream **series**", which presumes a 1:1 relation. Measured against the INE cache, that presumption does not hold. Offline and reproducible: `python3 scripts/analyse_crosswalk.py`.

## Inputs

- PORDATA rows: **2,195**
- INE indicators: **13,084** (5,197 distinct normalised titles)
- PORDATA rows citing INE, in portugal/municipios: **839**

## Exact title match, scoped to the expected geography

- no title match: **710** (84.6%)
- still ambiguous: **102** (12.2%)
- title matched, wrong geo level: **20** (2.4%)
- resolved to exactly 1: **7** (0.8%)

**Exact matching is a dead end.** PORDATA rewrites names for readability, so most never match a literal INE title, and scoping by geography rescues almost nothing.

## Token containment (how much of PORDATA's phrase INE covers)

- full containment: **231** (27.5%)
- 0.75-0.99: **73** (8.7%)
- 0.50-0.74: **318** (37.9%)
- below 0.50: **211** (25.1%)
- no shared token: **6** (0.7%)

Containment finds a match far more often, but it does not find *one*: of the 231 fully-contained rows only **14** hit a single INE entry, the median row ties **9** entries and the worst ties **1341**.

## What that means

**INE's catalogue is series-level; PORDATA's is indicator-level.** One PORDATA indicator - "Alojamentos familiares clássicos" - corresponds to a *family* of INE series split by geography, periodicity, census-vs-estimate and breakdown. The tie counts are not matcher noise; they are the relation's real shape.

So a crosswalk storing one `ine_id` per row would be **choosing arbitrarily and recording the choice as fact** - the exact failure mode the featured matcher was rewritten to avoid. The honest model is one-to-many:

- store the **candidate set** plus the evidence that selected it,
- defer picking a series to fetch time (item 14), where geography and period are known from what the user asked for,
- and keep `crosswalk: null` for rows with no credible family.

This also raises the value of INE's `keywords` and `theme` fields, unused here: they constrain the family before any name comparison, which is the cheapest precision available.
