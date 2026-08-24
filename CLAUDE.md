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

**Everything below is measured, not asserted.** Numbers here must reproduce against
`docs/data/catalogue.json`, `data/catalogue/QA.md` or a spike report, or they do not belong
(decision 7).

**Live and stable.** Harvest closed at **2,195/2,195 reachable** pages; the 2,196th (id 1221)
is dead upstream and retired via `data/catalogue/abandoned.txt`. The pipeline is event-driven
(sitemap watcher dispatches the harvester only when work is pending, plus a nightly safety
net) and gated at three layers: a sitemap corpus floor, parse-time shape assertions, and
`qa_catalogue.py --strict`, which reverts `docs/`, opens an issue and fails the job rather than
publishing a degraded catalogue.

**The card is a routing decision, not a summary** (roadmap 10). PORDATA's description is gone —
96.3% of them are exactly its SEO template. A `Badge` means *a facet you can filter on* and
nothing else; sources and freshness are labelled micro-columns in a fixed 3-column grid that
holds its shape when a value is missing; the chart slot is reserved but inert until item 14.
The coverage line was hiding in the title, welded on with a colon: `split_breakdown` demotes
that tail on 54.5% of rows and **refuses** when the tail is the indicator itself, and
`extract_unit` recovers a unit on 51.8%.

**The INE catalogue landed 2026-08-24 and unblocked the crosswalk.** `data/ine/indicators.csv`
holds **13,084 indicators** across 25 themes, each with a per-indicator `json` API URL (the
route to values for item 14) and `geo_lastlevel` (granularity PORDATA never exposed). But
spike A5 measured the relation and it is **one-to-many**: INE is series-level where PORDATA is
indicator-level, so store candidate sets and defer series selection to fetch time — never a
single `ine_id`.

**Next:** item **2** (the crosswalk) with **17** (the rename) alongside; **13** (three upstream
licences, owner, ~30 min) is the only thing gating **14**. Full detail and execution order in
`context.md`.

**Waiting on the owner:** item 13, the item 17 name call, a ~20-record spot-check, curating
`data/catalogue/FEATURED-UNMATCHED.md`, and ledger attempts.

**Four things worth not re-learning:**
- **Coverage thresholds for markup-parsed fields are per-area.** A catalogue-wide mean passed a
  100/100/0 unit split without complaint. The areas are separate PORDATA templates; a mean
  cannot say "each still works".
- **Raw HTML is not stored**, so any field the parser learns about after a harvest needs the
  pages fetched again. Two such fields already exist (the unit marker, the period). That is why
  item 21 is last on the board — fire it once 15 has stopped teaching the parser new things.
- **Killed hypotheses stay killed.** `A carregar conteúdo…` suggested client-rendered tables:
  it appears **0 times** across seven sampled pages. INE "blocks cloud IPs persistently": it
  served twice on a Saturday and we throttled ourselves with four 21 MB pulls in 45 minutes.
- **Refusing beats guessing.** The featured matcher, `split_breakdown` and the crosswalk all
  converged on the same rule: be right or be absent.

## How it runs

Eight workflows on `main`, the first two a detector→worker pair:

| workflow | when | what |
|---|---|---|
| `sitemap.yml` | 09:07 UTC daily + 18:23 UTC weekdays | fetches the sitemap, diffs it, opens an issue on add/remove, dispatches the harvest when work is pending |
| `harvest.yml` | dispatch + 01:45 UTC safety net | fetch-missing + re-fetch-stale + retry-errors, rebuild, **QA gate**, commit |
| `tests.yml` | push to scripts/tests | unittest + coverage gate + mutmut |
| `site.yml` | push to site/ | typecheck, build, vitest + coverage gate, StrykerJS (break 85) |
| `ine-availability.yml` | 09:45 UTC daily | one HEAD to INE, logs serving-vs-blocked (roadmap 22; **self-retires after 21 samples — then delete it**) |
| `featured-sets.yml`, `ine-catalogue.yml`, `spikes.yml` | manual | quadro names, INE catalogue, one-off probes (`spikes.yml` takes a probe input: a1–a4) |

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
