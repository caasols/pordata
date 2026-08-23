# pordata map

Making Portuguese public statistics consumable. PORDATA holds 2,268 curated indicators behind a
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

Harvest complete at 2,195/2,196 (2026-08-23); the one hold-out (id 1221) 500s on PORDATA's
side and is auto-retried. The pipeline is now event-driven: the sitemap watcher dispatches the
harvester only when there is pending work (detector→worker, plus a nightly safety-net cron).
Same day: 3d QA repair (512 fontes), the `(area, id)` keying fix (ids repeat across areas),
and site UX — opt-in area filters, infinite scroll in device-sized chunks. INE catalogue fetch
is blocked from cloud IPs and deferred (offline `data/ine/raw.xml` upload path ready). Next up
per the roadmap in `context.md`: the PORDATA→upstream **crosswalk** (gated on the INE cache)
and the label-filter design (roadmap 8); Phase D (MCP server) gated on owner go. FFMS was
emailed 2026-08-21, reply pending; ledger attempts remain the owner's evidence-gathering task.

## How it runs

Everything is GitHub Actions on `main`, as a detector→worker pair: `sitemap.yml` (daily 09:07
UTC + weekdays 18:23 UTC, bracketing the Lisbon working day; opens issues on add/remove and
dispatches the harvest when the fresh snapshot leaves pending work), `harvest.yml` (the
worker; fetch-missing + re-fetch-stale + retry-errors, then rebuilds `docs/` only when
records changed; nightly 01:45 UTC cron as a safety net), `tests.yml` (unit + coverage gate +
mutation on every scripts/tests push), `featured-sets.yml` and `ine-catalogue.yml` (manual). Data-writing workflows check out the
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
cd site && npm ci && npm run build   # UI: typecheck + build into docs/
python3 ~/.claude/skills/cartographer/scripts/audit.py . --style-lint
```

The site is a React + Vite + Tailwind app in `site/` (shadcn-style components, TypeScript);
`npm run build` writes the deployable bundle into `docs/` (committed — Pages serves it).
Never hand-edit `docs/index.html` or `docs/assets/`; edit `site/src/` and rebuild.
