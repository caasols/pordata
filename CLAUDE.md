# pordata map

Making Portuguese public statistics consumable. PORDATA holds 2,196 curated indicator pages behind a
UI with no API; this project built the machine-readable layer on top: a self-maintaining
catalogue of that curation (metadata only, never data values) with a public search site.

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
Resumo/Summary filter pill and the attributed badge — the quadro-resumo is PORDATA's
per-location overview, the same 37/56 indicators on every município's and country's page) and
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

Next up per the roadmap in `context.md` (execution order in its header): the card design pass
(roadmap 10) — the card just gained the summary badge and item 8's labels will add more chips
to it, so design it once — then the PORDATA→upstream **crosswalk** (gated on the INE cache —
owner unblock) and the rest of the label-filter design (roadmap 8); Phase D (MCP server) gated
on owner go. FFMS was emailed 2026-08-21, reply pending; ledger attempts remain the owner's
evidence-gathering task.

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
