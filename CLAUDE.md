# pordata map

Making Portuguese public statistics consumable. PORDATA holds 2,268 curated indicators behind a
UI with no API; this project built the machine-readable layer on top: a self-maintaining
catalogue of that curation (metadata only, never data values) with a public search site.

**Status:** shipped and live. The search site — fuzzy, six UI languages, PT/EN indicator
names — is at [caasols.github.io/pordata](https://caasols.github.io/pordata/), rebuilt
automatically by the harvest pipeline. Public repo, MIT (code) / CC BY 4.0 (metadata).

## Read this first

- [context.md](context.md) - the whole project: what has been built and how it runs, measured
  facts about PORDATA, the central insight, the four-stage problem framing, ecosystem,
  decisions and why, and the roadmap. Start here every session. Nothing else in this repo
  carries state.
- [README.md](README.md) - human front door. Brief overview; carries no state.

## Current focus

Harvest complete at 2,195/2,196 (2026-08-23): one page (id 1221) 500s on PORDATA's side and is
auto-retried each cron run; the cron is now pure maintenance. The 3d QA repair ran (512 stored
fontes trimmed) alongside a live-bug fix: page ids repeat across areas, so EN names and
featured flags are keyed by `(area, id)`. Next up per the roadmap in `context.md`: the INE
catalogue cache and the PORDATA→upstream **crosswalk** (the gateway to serving values and to
Phase D, an MCP server — both gated on owner go). FFMS was emailed 2026-08-21, reply pending;
ledger attempts remain the owner's evidence-gathering task.

## How it runs

Everything is GitHub Actions on `main`: `sitemap.yml` (daily watcher, opens issues on
add/remove), `harvest.yml` (3×/day; fetch-missing + re-fetch-stale + retry-errors, then
rebuilds `docs/`), `tests.yml` (unit + coverage gate + mutation on every scripts/tests push),
`featured-sets.yml` and `ine-catalogue.yml` (manual). Data-writing workflows check out the
branch head at run time — never the trigger-time sha. This sandbox cannot reach pordata.pt or
ine.pt; anything needing their network runs via Actions.

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
python3 ~/.claude/skills/cartographer/scripts/audit.py . --style-lint
```
