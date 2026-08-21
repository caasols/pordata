# pordata map

Making Portuguese public statistics consumable. PORDATA holds 2,268 curated indicators behind a
UI with no API; this project is working out what intervention would actually help.

**Status:** research and problem definition. No solution chosen, deliberately. Nothing built.
Version 0.1.0.

## Read this first

- [context.md](context.md) - the whole project: measured facts about PORDATA, the central
  insight, the four-stage problem framing, ecosystem, decisions and why, and the open backlog.
  Start here every session. Nothing else in this repo carries state.
- [README.md](README.md) - human front door. Brief overview; carries no state.

## Current focus

Problem definition, not building. FFMS was emailed on 2026-08-21 (awaiting reply; see
`context.md` backlog item 1). The next action is writing the Question Ledger. An explicit decision recorded there is **not** to jump to an MCP
or a scraper before the catalogue question is settled.

## Sibling project

[../raycast-assembleia-da-republica/context.md](../raycast-assembleia-da-republica/context.md) -
a Raycast extension over Portuguese parliamentary data via the openAR API. Separate repo,
separate domain, but the same underlying interest in making public data reachable. openAR is the
working template for what PORDATA lacks: one volunteer, an OpenAPI spec, ETags, incremental sync.

## Deep navigation

A graphify graph exists under `graphify-out/` (derived, gitignored; rebuild with
`graphify update .`). Be aware it currently indexes only the markdown headings of these docs,
since the repo holds no code, so its god-nodes reflect this file's structure rather than any
architecture. It becomes useful once there is code. Read `graphify-out/GRAPH_REPORT.md` or query
with `graphify path` / `explain`.

## Health checks

```bash
python3 ~/.claude/skills/cartographer/scripts/audit.py . --style-lint
```
