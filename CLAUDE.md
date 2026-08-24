# pordata map

Making Portuguese public statistics consumable. PORDATA holds 2,196 curated indicator pages behind a
UI with no API; this project built the machine-readable layer on top: a self-maintaining
catalogue of that curation (**metadata only — no PORDATA data values, ever**) with a public
search site. Where it is heading: pull the actual series from INE, Eurostat and BPstat under
*their* terms, archive them, and build the interface PORDATA lacks — aiming to end up more
complete than PORDATA, with its curation as the map rather than the cargo.

**Status:** shipped and live. The search site — fuzzy, PT/EN UI (four more prepared), PT/EN indicator
names — is at [caasols.github.io/pordata](https://caasols.github.io/pordata/), rebuilt
automatically by the harvest pipeline. Public repo, MIT (code) / CC BY 4.0 (metadata).

## Read this first

- [context.md](context.md) - the whole project: what has been built and how it runs, measured
  facts about PORDATA, the central insight, the four-stage problem framing, ecosystem,
  decisions and why, and the roadmap. Start here every session. Nothing else in this repo
  carries state.
- [README.md](README.md) - human front door. Brief overview; carries no state.

## Current focus

**Harvest complete: 2,195/2,195 reachable pages.** The 2,196th (id 1221) is dead upstream —
verified in a normal browser, not bot-blocking — so it lives in `data/catalogue/abandoned.txt`,
skipped and tombstoned rather than retried for ever.

The pipeline is event-driven (detector→worker: the sitemap watcher dispatches the harvester
only when there is pending work, plus a nightly safety net) and **gated at three layers**:
`fetch_sitemap.py` refuses a snapshot that loses >5% of indicator targets, `parse()` drops
field values that fail a shape assertion (and marks the record), and `qa_catalogue.py
--strict` blocks the publish — reverting `docs/`, opening an issue and failing the job — when
any threshold breaks. A `/mega-audit` on 2026-08-23 (57 verified findings, report in
`data/audits/`) drove all of that, plus a high-precision rewrite of the featured matcher, the
site's accessibility and SEO layer, and a sweep of doc corrections.

Shipped since: **roadmap 6a** (parse-time shape assertions), **roadmap 12** (the
Resumo/Summary filter pill and badge — the quadro-resumo is PORDATA's per-location overview,
the same 37/56 indicators on every município's and country's page; pill and badge share one
i18n key, with the PORDATA attribution in the badge tooltip) and
**roadmap 10** (the card design pass).

The card is now a **routing decision**, not a summary. PORDATA's description is gone (96.3% of
them are exactly its SEO template); a `Badge` means *a facet you can filter on* and nothing
else; sources and freshness are labelled micro-columns; the chart slot is reserved but inert
until item 14. The coverage line was already in the catalogue, welded to the title with a
colon: `split_breakdown` demotes that tail on 54.5% of rows and **refuses** when the tail is
the indicator itself, and `extract_unit` recovers a unit on 51.8% from `marker_windows` —
78.4% of rows carry a coverage line, and the card renders fine without one. Also repaired an
upstream defect: PORDATA serves a literal `?` where an en dash belongs in 37 names (ours
decodes clean; their own slug drops the character), now the second concrete bug for the FFMS
follow-up.

**The INE catalogue landed 2026-08-24 and unblocked the roadmap's biggest lever.** The fetch
succeeded from an Actions runner on the *fourth* attempt, so the recorded conclusion that INE
"blocks cloud IP ranges persistently" was wrong — it is intermittent, and the owner's `raw.xml`
upload is no longer needed. `data/ine/indicators.csv` now holds **13,084 indicators** across 25
themes, each with a per-indicator **`json` API URL** (the concrete route to values, i.e. the
starting point for roadmap 14) and **`geo_lastlevel`** (the geographic granularity PORDATA's
markup does not expose).

Next up per the roadmap in `context.md` (execution order in its header): the PORDATA→upstream
**crosswalk** (roadmap 2, now unblocked), with the **rename** (17) alongside it; then the
label-filter design (roadmap 8); Phase D (MCP server) gated on owner go. FFMS was emailed
2026-08-21, reply pending; ledger attempts remain the owner's evidence-gathering task.

**Direction set 2026-08-23 (owner):** the project does not stop at a catalogue of pointers. Go
to the sources, pull and archive the series, and build the UI PORDATA does not have — charts
people can work with — and aim to end up **more complete than PORDATA**. This stays inside
decision 1: what gets redistributed is INE's, Eurostat's and BPstat's data under *their*
terms, never PORDATA's rendering of it; PORDATA's contribution remains the curation. Roadmap
items **13** (read and record the three upstream licences — owner, laptop, gates 14), **14**
(the series archive, gated on the crosswalk), **15** (per-indicator detail pages with charts),
**16** (the coverage gap against INE and Eurostat — a *selection*, never an enumeration:
completeness without curation is a regression) and **17** (rename — "pordata map" describes
the thing the project is outgrowing, and it borrows FFMS's mark; do it before Phase D
publishes a package name).

**Open threads from the card pass** — *most closed 2026-08-23 while the owner slept.*
**18** (unit vocabulary) shipped: `site/src/lib/unit-terms.json` is the single source of truth
for both the site and the QA gate, EN complete, unknown terms falling back to Portuguese
rather than blank. **19's spike** ran (`data/spikes/a3-coverage-fields.md`) and settled the
unit half outright — the chart caption is in **7 of 7** sampled pages including portugal, so
its 0% was a missing *marker*, not a missing template. `"ampliado"` added to `MARKER_WORDS`
fixes it at **zero extra requests**: units accrue as pages go stale. A forced ~12 h re-harvest
would finish it in one pass — owner's call, not a prerequisite. **20** follows automatically:
471 of the 475 uncovered rows are portugal, so coverage should reach ~99.8% — *re-measure
before believing it*; `unit_ratio[portugal]` sits at a gate floor of 0.0 recording the gap.
**21** (one full re-harvest) is last on the board on purpose: raw HTML is not stored, so every
field the parser learns about after a harvest needs the pages fetched again — fire it once the
detail pages (15) have stopped teaching it new things, not the moment it is possible.

Two things worth carrying forward. A catalogue-wide QA threshold passed the 100/100/0 unit
split without complaint, so **coverage thresholds for fields parsed out of page markup are now
per-area** — the areas are separate templates and a mean cannot say "each still works". And a
hypothesis of mine died usefully: `A carregar conteúdo…` led me to guess the data table was
client-rendered; it appears **0 times** across all seven pages, which are server-rendered with
12–18 tables. The period is in a `<table>` on portugal and europa, and spike A4 found the
municipios case is a **`<select>` year picker** (17–18 `<option value="YYYY">` per page) — so
extraction is fully specified for all three areas. But it needs *raw* HTML: `marker_windows`
runs on stripped text, so the structure is gone before a window is cut. That makes the period
a harvest-time parse plus a fetch — i.e. **item 21**, and the second field found after the
harvest that could have been captured during it.

## How it runs

Seven workflows on `main`, the first two a detector→worker pair:

| workflow | when | what |
|---|---|---|
| `sitemap.yml` | 09:07 UTC daily + 18:23 UTC weekdays | fetches the sitemap, diffs it, opens an issue on add/remove, dispatches the harvest when work is pending |
| `harvest.yml` | dispatch + 01:45 UTC safety net | fetch-missing + re-fetch-stale + retry-errors, rebuild, **QA gate**, commit |
| `tests.yml` | push to scripts/tests | unittest + coverage gate + mutmut |
| `site.yml` | push to site/ | typecheck, build, vitest + coverage gate, StrykerJS (break 85) |
| `featured-sets.yml`, `ine-catalogue.yml`, `spikes.yml` | manual | quadro names, INE catalogue, one-off probes |

Data-writing workflows check out the branch head at run time — never the trigger-time sha. A
QA-gate breach reverts `docs/`, opens an issue and fails the job, so a degraded harvest never
publishes. This sandbox cannot reach pordata.pt or ine.pt; anything needing their network runs
via Actions.

## Sibling project

[../raycast-assembleia-da-republica/context.md](../raycast-assembleia-da-republica/context.md) -
a Raycast extension over Portuguese parliamentary data via the openAR API. Separate repo,
separate domain, but the same underlying interest in making public data reachable. openAR is the
working template throughout: one volunteer, an OpenAPI spec, ETags, incremental sync, an MCP.

## Deep navigation

A graphify graph exists under `graphify-out/` (derived, gitignored; rebuild with
`graphify update .`). Read `graphify-out/GRAPH_REPORT.md` or query with `graphify path` /
`explain`.

## Health checks

```bash
python3 -m unittest discover -s tests
python3 scripts/build_catalogue.py
cd site && npm ci && npm run build   # UI: typecheck + build into docs/
python3 ~/.claude/skills/cartographer/scripts/audit.py . --style-lint
```

At milestones, run `/mega-audit` — the cross-consistency sweep that checks plans and doc
claims against measured state (decision 7 in `context.md`). Roadmap items always state
their preconditions; feature-gating metrics belong in QA thresholds, not prose.

The site is a React + Vite + Tailwind app in `site/` (shadcn-style components, TypeScript);
`npm run build` writes the deployable bundle into `docs/` (committed — Pages serves it).
Never hand-edit `docs/index.html` or `docs/assets/`; edit `site/src/` and rebuild.
