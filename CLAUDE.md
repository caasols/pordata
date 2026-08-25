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
Since item 15 the whole card opens *this project's* page, not pordata.pt — the click-out moved
to the detail page, beside the chart slot it will replace.
The coverage line was hiding in the title, welded on with a colon: `split_breakdown` demotes
that tail on 54.5% of rows and **refuses** when the tail is the indicator itself, and
`extract_unit` recovers a unit on 51.8%.

**The INE crosswalk landed 2026-08-24.** `data/crosswalk/ine.json` routes **212 of 839**
in-scope rows (INE-sourced, portugal/municipios) to a candidate *family* of INE series — 113
with an exact title inside it — and `null` for the other 627. The relation is one-to-many
(spike A5), so each entry stores the set, its true size, the INE operation/theme, and the
evidence; series selection is deferred to fetch time — never a single `ine_id`. **Family size
is never a reason to refuse**: 62 candidates means INE publishes 62 of them. Six filters,
each added after a specific wrong match — full containment, the INE head must be a word
PORDATA used, derivation parity (a count is not a rate), negation parity — plus two the tests
caught: the unit is a *separate* comparison (INE suffixes it into the title, PORDATA carries it
in a field, so reading `%` out of the raw title refused "Taxa de desemprego" against itself),
and numbers are content (the two-character floor swallowed age brackets). Gated at
`--strict` with a 170-match floor. Since 2026-08-25 the colon prefix is demoted too
(`category_heads` derives the repeating heads from the catalogue itself): **212 matched**,
6 gained, 0 lost.

**The Eurostat crosswalk landed 2026-08-25, and the shape is not INE's.**
`data/eurostat/datasets.csv` caches **7,572** datasets; `data/crosswalk/eurostat.json` routes
**118 of 616** in-scope `europa` rows (35 exact, 37 single, 46 family) and `null` for the rest,
floored at 100. Eurostat publishes multi-dimensional **cubes**, not pre-sliced series, so a
PORDATA row wants one dataset **plus a filter over its dimensions** — and INE's rule reverses:
these candidates are *rivals* of which one is right, so **a large set is an open question, not
a fact about the upstream**. The operator strips PORDATA's unit parenthetical (Eurostat carries
the unit as a dimension, so `percentage` alone blocked 35 rows), splits both sides at the `by`
that opens the breakdown, and requires **identical heads** — plain containment reaches 18.3%
because it asks a cube's name to contain the words for its own dimensions. **The breakdown is a
veto, never a ranking**: ranking on it picked a winner on 10 of 83 ties and one of the first
eight sampled was a non-EU geography; as a veto it refuses 18 head matches, every hand-read one
correctly. A content-token floor on the head is recorded as **rejected with the number that
rejected it** — it drops 38 matches including one whose Eurostat title is identical.
`filter_resolved` is **false on every entry** and the detail page shows the wanted breakdown as
unverified: the catalogue has titles, not dimension names. **BPstat** is the remaining half —
measure it; neither INE's shape nor Eurostat's is safe to assume.

**Every indicator now has a page** (item 15, metadata half). `/indicador/<area>/<id>/` —
**2,195 pre-rendered**, each with `Dataset` JSON-LD, listed in `docs/sitemap-indicadores.xml`,
and carrying the two things PORDATA's page does not: the revision note **with** the indicator
(decision 5) and the crosswalk as provenance — **330 pages, 212 INE and 118 Eurostat** —
candidates linked to the upstream page *and* its machine-readable endpoint. The panel
dispatches on the entry's `source`, not the row's area, because the two crosswalks answer
differently shaped questions and a single panel would misreport both. No JS bundle — ~4 KB of HTML against one shared stylesheet. Pages are written
only when their bytes change (the whole set packs to 4.45 MiB); theme tokens are read from
`site/src/index.css` and the build **fails** if that block moves; `--strict` asserts every row
has a page, because every card links here now. The chart slot stays inert until item 14.
**One design, asserted**: the page's chip, card, meta, button, shadow, radii, focus ring, font
stack and theme boot all come from the components the SPA uses, and `DesignSystemTest` reads
those files so a variant change fails the build rather than leaving two designs on one site.

**The chart layer is chosen and measured, and deliberately not installed yet**
(`@tanstack/charts`, spike in `data/spikes/charts-tanstack.md`). Marginal cost **≈27 KB
gzipped** over React. The finding that decides the architecture: **it renders to SVG in plain
Node with no DOM** — `createChartScene()` compiles a renderer-neutral scene and
`renderChartSvg()` is a pure string function. So pre-render the SVG at build time (~3.4 KB gz
for 195 points, crawlable, works with JS off, keeps the detail pages at their zero-JS weight)
and load the interactive chart only when someone reaches for it. CSS custom properties survive
into the output and axes use `currentColor`, so **one** file serves light and dark. Risk
recorded: **0.14.0, six releases in six days** — re-check the release timeline before adopting.
Not in `site/package.json`: nothing to chart until 14 archives values.

**The gap it makes computable is a shortlist, not an inventory** (item 16).
`data/coverage/INE-GAP.md` names **302 concepts** INE publishes and PORDATA never mentions,
for owner accept/reject. The *series*-level complement is deliberately not computed: the
crosswalk names 8.1% of INE ids, so subtracting it would call ~12,000 series "missing" when
most are covered under a name the matcher declines to claim.

**Three fields we do not capture, with selectors** (spike A6, 2026-08-24, sampled across all
9 structural fingerprints): the plain-language **question** under each title, in `<h2>`, on
**15/15** pages — phrased per area (`portugal` "Quantas…", `municipios` "Onde há mais e
menos…", `europa` "Que países…"), which makes it a better search and embedding input than the
name; a **revision note** in the `revis` window on 215 pages, which is decision 5's caveat; and
the **period**, whose mechanism differs by area — portugal has named year elements, municipios
a `<select>` picker, and europa turns out to carry both. The parser captures all three — the
revision note needed no fetch at all (203 rows carry it today, from windows already stored) —
so future fetches pay for themselves; item **21** is the re-harvest that backfills the rest.

**Next: the owner's queue, then BPstat and the refusals.** Four things are blocked on
a human and nothing else, and all four unblock work that is otherwise ready — **25** (curate
`data/coverage/INE-GAP.md`, ~45 min: the accept/reject record *is* the curation rule, and it
closes 16), **13** (upstream licences — now ~10 min: Eurostat is answered as CC BY 4.0 in
`data/spikes/licences.md`, INE and BPstat need a browser that is not a cloud IP; the only
thing gating **14**), **17** (the rename), and item **1**'s residual checks (a ~20-record spot-check, plus curating
`data/catalogue/FEATURED-UNMATCHED.md`). Then **BPstat** (measure first — neither INE's shape
nor Eurostat's is safe to assume) and the refusals: 480 Eurostat rows where no head matched
(`data/crosswalk/EUROSTAT-REVIEW.md`) and the INE ones in `data/crosswalk/REVIEW.md`. Full
detail and execution order in `context.md`.

**The 2026-08-25 audit's findings are applied** (`data/audits/2026-08-25-mega-audit.md`,
114 findings across 12 dimensions, each verified by an independent skeptic). The critical one:
`LICENSE-DATA` said "No PORDATA data values are contained in or redistributed by this
repository" while **15,946** sat in `data/catalogue/pages.jsonl` — `marker_windows` slices 60
characters ahead of each marker and the last row of the data table sits above
`Fontes/Entidades:`. Redacted at the cut and backfilled; `jsonl_value_leak_max: 0` reads every
window of every record. Proof the redaction is surgical: the catalogue rebuilds byte-identical
from the redacted corpus. Also closed: the harvest QA step could not report its own death
(`bash -e` aborted before `echo status=`, leaving all seven `if:` conditions falsy and the job
green); `docs/` was staged under `always()` regardless of whether the derived builders ran;
the INE builder wrote before checking its floor; `featured-sets.yml` published with `--strict`
omitted; `eurostat-catalogue.yml` refreshed an input without rebuilding its consumer;
`DesignSystemTest` had never run on a site-only push; 38 pages printed an INE operation under
half their family agreed with; the card and the page it opened showed different units on
1,111 rows; `name_en` was ungated; and the focus ring computed to **1.29:1** against a 3:1
requirement.

**The medium and low findings are applied too** (2026-08-25). The ones worth carrying:
the **tombstone path had never run** — `if "error" in rec: continue` came before the
`removed` branch and the abandoned record carries no `id`, so the catalogue shrank 2,196 →
2,195 with no machine-readable trace; it publishes as `removed: true` now and the new
`detail_pages_missing` gate caught the missing page within the minute. **The mutation gate
scored 100% on a run that tested nothing** (killed/killable with killable at zero), which is
the exact state a missing `also_copy` entry produces. `is_indicator_url` checked that a URL
*mentioned* pordata.pt rather than came from it. **256 detail pages carried duplicate link
names**, up to twelve reading "JSON", because a one-to-many family makes that the normal case.
And the **English half had no address**: `og:locale:alternate en_GB` was advertised with
`grep -r hreflang docs/` returning nothing, so language was a localStorage state rather than a
URL. Now `?lang=`, `hreflang` on every page, alternates in the sitemap, and a two-link switch
that needs no JavaScript.

**Ten things worth not re-learning:**
- **Coverage thresholds for markup-parsed fields are per-area.** A catalogue-wide mean passed a
  100/100/0 unit split without complaint. The areas are separate PORDATA templates; a mean
  cannot say "each still works".
- **Raw HTML is not stored**, so any field the parser learns about after a harvest needs the
  pages fetched again. Two such fields already exist (the unit marker, the period). That is why
  item 21 is last on the board — fire it once 15 has stopped teaching the parser new things.
- **A sampling frame must come from measured variation, not an obvious-looking dimension.**
  Spike A6 sampled one page per area and called it an inventory; the stored records actually
  hold **9 distinct structural fingerprints**, and municipios pages span 174 KB to 2.2 MB.
  `scripts/spike_page_inventory.py` derives the frame from those fingerprints instead.
  Its mirror image is just as dangerous: a *saturated* result. Single-token vocabulary overlap
  "reached" 90% of INE's catalogue when item 16 was built, and proved nothing — PORDATA's words
  are ordinary Portuguese statistical language. Only total absence carried signal.
- **Check a "0 occurrences" result before believing it.** A3 reported `A carregar conteúdo…`
  0 times and it went into the docs as a killed hypothesis; A6 found it — A3 matched a literal
  string against entity-encoded HTML. The INE "persistent block" reading died the same way:
  it served twice on a Saturday and we throttled ourselves with four 21 MB pulls in 45 minutes.
- **An upstream theme tree is a set of views, not a partition** — and it misleads in *both*
  directions. INE files one series under two themes, so theme *purity* rejected exact matches.
  Eurostat files one dataset under up to eight, so emitting a row per appearance gave 10,313
  rows for 7,572 datasets and multiplied every candidate count derived from the file. Fixing it
  moved the measured median from 3 to 1: the inflation was hiding the one thing the analysis
  existed to see. Count the *entity*, and store the themes as the set they are.
- **Refusing beats guessing** — and the first guard you reach for is usually measuring the
  wrong thing. The featured matcher, `split_breakdown` and both crosswalks converged on
  "be right or be absent". But a *content-token floor* on the Eurostat head, the obvious way to
  stop a generic name like "Exports" matching an input-output table, also deleted "Obesity rate
  by body mass index" — whose Eurostat title is identical. The failure was contradiction, not
  length; a tail *veto* caught both cases with no collateral. Audit a filter against what it
  removes, not against the case that suggested it.
- **Derive from the component; do not write what looks right.** The detail pages' stylesheet
  was hand-written from memory of the card and shipped as a visibly different design — an
  orange pill where the card has a grey `secondary` Badge, a 16 px meta value against an 11 px
  label. Fixing the pill by hand then produced an orange **button** one element along, on a
  site whose `button.tsx` has no filled variant at all. The values now come from
  `badge.tsx` / `button.tsx` / `card.tsx` / `App.tsx`, and `DesignSystemTest` asserts against
  those files so a variant change fails the build. Naming a font is not loading it: the SPA
  pulls Public Sans from Google Fonts in its own `<head>`, and the pages that only listed it
  in a stack rendered in the system sans.
- **Anything a test reads off disk must be in mutmut's `also_copy` *and* in `tests.yml`'s push
  paths.** It runs the suite from a copied tree, so `.github/workflows/`, `site/src/`,
  `docs/assets/` and `data/crosswalk/` are listed; without them the cross-file tests die on a
  `FileNotFoundError` that reads like a bug in the code under test. The second half cost more:
  four of the six were not triggers, so `DesignSystemTest` never ran on a site-only push and
  the guard against two designs on one site was itself unguarded. `test_workflows.py` now
  asserts one list against the other, so the coupling maintains itself.
- **A guarantee no code can falsify is not a guarantee.** Decision 1 was stated in
  `LICENSE-DATA`, in the README, in the FFMS email — and checked only against the published
  `unit` field, so 15,946 values sat in the committed corpus through months of green CI. The
  same shape produced every other high finding: a gate whose failure path emitted nothing, a
  floor that ran after its writes, a report naming an enforcer that did not contain the check,
  a focus-ring test asserting the *string* was present rather than that it could be seen.
  Write the invariant over the bytes you ship, and check it where it can fail.
- **Not every mutation survivor is worth killing.** `parse()`'s ~54 are equivalent mutants
  (`decode("utf-8")` vs `decode()`, `[-1]` vs `[+1]` on a two-element list), and ~80% of the
  rest are markdown labels in report writers. Test the *figures and sections* a reader
  depends on, not the prose. And put logic in `src/lib` — that is where StrykerJS mutates, so
  a helper living in `App.tsx` is unit-tested but never mutation-tested.

## How it runs

Ten workflows on `main`, the first two a detector→worker pair:

| workflow | when | what |
|---|---|---|
| `sitemap.yml` | 09:07 UTC daily + 18:23 UTC weekdays | fetches the sitemap, diffs it, opens an issue on add/remove, dispatches the harvest when work is pending |
| `harvest.yml` | dispatch + 01:45 UTC safety net | fetch-missing + re-fetch-stale + retry-errors, rebuild, **QA gate**, both crosswalks, coverage gap, detail pages, commit |
| `tests.yml` | push to scripts/tests/workflows/site-src/docs-assets/crosswalk | unittest + coverage gate (floor 80%, at 90%) + **mutmut gate** (floor 58%, at 65.4%) + `qa_catalogue.py --strict` |
| `site.yml` | push to site/ | typecheck, build, **committed `docs/` matches source**, vitest + coverage gate, StrykerJS (break 85) |
| `pages-health.yml` | 11:11 UTC daily | fetches the live site, compares its `built_at` with the committed one and checks the served bundle's assets resolve; opens/closes one issue |
| `ine-availability.yml` | 09:45 UTC daily | one HEAD to INE, logs serving-vs-blocked (roadmap 22; **self-retires after 21 samples — then delete it**) |
| `featured-sets.yml`, `ine-catalogue.yml`, `eurostat-catalogue.yml`, `spikes.yml` | manual | quadro names, INE catalogue + crosswalk, Eurostat catalogue, one-off probes (`spikes.yml` takes a probe input: a1–a4, a6, `licences`, `eurostat-toc`, `ine-series`, `europa-period`) |

Data-writing workflows check out the branch head at run time — never the trigger-time sha. A
QA-gate breach reverts `docs/`, opens an issue and fails the job, so a degraded harvest never
publishes; the harvest commits its checkpoints even when the run dies, and `tests/test_workflows.py`
asserts these invariants offline (ordering, `always()` guards, bounded jobs, no dangling
step ids). This sandbox cannot reach pordata.pt, ine.pt or the live Pages site; anything
needing their network runs via Actions.

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
