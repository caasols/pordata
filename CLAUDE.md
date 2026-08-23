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
only when there is pending work, plus a nightly safety net) and now **gated**: `qa_catalogue.py
--strict` blocks the publish when data quality regresses, and `fetch_sitemap.py` refuses a
snapshot that loses >5% of targets. A `/mega-audit` on 2026-08-23 (57 verified findings, report
in `data/audits/`) drove that work plus a high-precision rewrite of the featured matcher, the
site's accessibility and SEO layer, and these doc corrections.

Next up per the roadmap in `context.md` (execution order in its header): the featured filter
pill + rename (roadmap 12), the card design pass with Claude Design (roadmap 10), then the
PORDATA→upstream **crosswalk** (gated on the INE cache — owner unblock) and the rest of the
label-filter design (roadmap 8); Phase D (MCP server) gated on owner go. FFMS was emailed
2026-08-21, reply pending; ledger attempts remain the owner's evidence-gathering task.

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
