---
updated: 2026-08-23
---

# pordata: context

## What this is

A project to make Portuguese public statistics actually consumable. PORDATA is the country's main
free statistics database and is genuinely good at one thing: presenting a single indicator,
attractively, to someone who already knows what they are looking for. Everything here is about
what happens when that condition does not hold.

**Current phase: the Discovery stage is shipped and live** — a public, multilingual, fuzzy
search over PORDATA's full indicator catalogue at
**[caasols.github.io/pordata](https://caasols.github.io/pordata/)**, self-maintaining via
GitHub Actions. Next frontiers: the upstream crosswalk (Extraction) and, gated on it, an MCP
server (Phase D). See Roadmap.

## Architecture and inventory

| Path | What it is |
|---|---|
| `CLAUDE.md` | The map. Ranked pointers, current focus |
| `context.md` | This file. All project state: findings, decisions, roadmap |
| `README.md` | Human front door: overview, site link, licensing. Carries no state |
| `LICENSE` / `LICENSE-DATA` | MIT for the code; CC BY 4.0 for the catalogue metadata, with PORDATA/FFMS attribution |
| `scripts/` | Python package: sitemap watcher, harvester, catalogue build, QA, featured sets, spikes |
| `tests/` | 74 unittest cases, coverage-gated; mutation-tested via mutmut (`setup.cfg`). Site tests live in `site/src/**/*.test.*` (48 vitest) |
| `.github/workflows/` | Seven: sitemap watch (detector), catalogue harvest (worker, QA-gated), tests.yml and site.yml (per push), featured-sets / ine-catalogue / spikes (manual). Table in `CLAUDE.md` |
| `data/` | Committed pipeline state: sitemap snapshots, `catalogue/pages.jsonl`, CHANGELOG, QA (gated), `catalogue/abandoned.txt`, spike reports, `audits/` |
| `site/` | The search UI source: React + Vite + Tailwind + shadcn-style components (TypeScript). `npm run build` → `docs/` |
| `docs/` | The GitHub Pages site: built UI bundle (from `site/`, committed) + `data/` (catalogue.json/csv/stats — the static "API") |
| `ledger/` | Question Ledger: 100 demand-side questions plus protocol |
| `outreach/` | Record of external contacts. Holds the FFMS email as sent |
| `graphify-out/` | Derived code graph, gitignored |
| `.claude/commands/` | `/mega-audit`: the cross-consistency deep-audit prompt (decision 7) |

## What has been built (2026-08-21 → 2026-08-23)

The pipeline, end to end, all live on `main`:

- **Sitemap watcher** (`sitemap.yml`, daily 09:07 UTC + weekdays 18:23 UTC — bracketing the
  Lisbon working day per the measured publication cadence): fetches PORDATA's sitemap, diffs
  URLs and `<lastmod>` against the committed snapshot, writes `data/CHANGELOG.md`, opens a
  GitHub issue when indicator pages are added or removed, and dispatches the harvester when
  the fresh snapshot leaves pending work (main only — the push trigger also runs on feature
  branches). Landing-page lastmod churn is filtered out.
- **Initial harvest complete** (2026-08-23): **2,195 / 2,195 reachable** target pages. The
  2,196th (`portugal/…despesas…ambiente…-1221`) returns HTTP 500 on every attempt and is dead
  in a normal browser too (owner-verified), so it is listed in `data/catalogue/abandoned.txt`:
  skipped by the harvest plan and tombstoned at build time instead of retried for ever. Its
  series is discontinued (1995-2013) and still cited in the wild (Gulbenkian, "Governar a
  Próxima Geração", 2022 — owner find). Finding where its data lives now is roadmap 2a. Same day: the fontes repair pass (512 stored `fontes` trimmed of pre-fix UI text) and a
  live-bug fix — **page ids repeat across areas**, so EN names and featured flags are keyed by
  `(area, id)` (205 wrong `name_en` and 14 phantom featured flags corrected).
- **Catalogue harvester** (`harvest.yml`): 2,196 indicator pages (quadro+resumo excluded),
  one request per 20 s, resumable 4.5 h chunks, metadata only — name, description,
  Fontes/Entidades, última atualização, JSON-LD, marker excerpts for offline re-parsing.
  **Freshness is built in**: each run fetches only pages new to the sitemap, pages whose
  lastmod moved past `harvested_at`, and stored errors; removed pages are tombstoned at build
  time, never deleted. Since 2026-08-23 it is the worker in a **detector→worker pair** (owner
  ask): the sitemap watcher dispatches it whenever the fresh snapshot leaves pending work, so
  changes are harvested minutes after detection; the harvester keeps one nightly cron
  (01:45 UTC) purely as a safety net for missed dispatches, and a run that changes no records
  skips the rebuild so no-op retries commit nothing. During the initial harvest the cron ran
  3×/day launching back-to-back chunks.
- **Published catalogue + search site** (Phase C, live): `build_catalogue.py` renders
  `pages.jsonl` into `docs/data/catalogue.json` / `.csv` / `stats.json`. The UI is a
  **React + Vite + Tailwind app in `site/`** (migrated from the original single-file page
  2026-08-23, owner call — real shadcn-style components on Radix primitives, TypeScript;
  `npm run build` in `site/` writes the static bundle into `docs/`, committed, ~106 KB
  gzipped; `site.yml` build-checks every push touching `site/`; never hand-edit
  `docs/index.html`/`docs/assets/`). Features: ranked fuzzy matching (substring > prefix >
  bounded edit distance), key-based i18n with strings prepared in six languages
  (PT/EN selectable per decision — content exists in PT/EN only; roadmap 7), all 24 EU
  languages listed greyed, `name_en` on every row derived free from the `/en` sitemap
  slugs, opt-in area filter pills in one swipeable row, a sort pill (newest/oldest/A→Z/Z→A,
  newest default), infinite scroll in device-sized chunks, featured and
  "descontinuado" badges, light/dark theme, PORDATA credited prominently, every hit linking
  to its PORDATA page. Data redeploys automatically after every harvest chunk (the app
  fetches `docs/data/*.json` at runtime, so data changes need no rebuild). Repo made public
  and Pages enabled 2026-08-22. A UI-consistency pass and a high-effort code audit
  (2026-08-23) normalised typography to a 4-step scale and fixed seven findings — singular
  result counts in all six languages, locale-aware number formatting, duplicate-name alt
  dedupe, `aria-pressed` on filter pills, a "0 indicators" loading flash, sort-comparator
  perf (precomputed keys + one collator) — and the build now strips PORDATA's inline HTML
  from published names (`<em>`, with `<sub>`/`<sup>` digits converted to Unicode: CO₂, km²).
- **Featured sets**: quadro-resumo rows are OutSystems postbacks with no ids, but names are
  server-rendered; `fetch_featured_sets.py` extracts them (subtitle-aware) and the build maps
  them to catalogue entries. Confirmed: the municipal quadro set is exactly 37 indicators,
  identical across concelhos; Europa's is 56. Retratos pages are e-book publications with no
  indicator list — no signal there. The 2026-08-23 audit proved the original token-containment
  matcher **flagged the wrong indicator** under a curated badge (negations inverted, absolute
  vs %-of-total, one id claimed by five names). It is now **injective and high-precision** —
  overrides, then exact match on the name or its dash-split head, then containment 1.0 with at
  most two extra tokens and a CONTRAST vocabulary blocking meaning-flipping extras. 43 rows
  carry the badge, all high-confidence, where 52 included ~10 wrong. Mapping a human curation
  needs a human for the tail: `data/catalogue/FEATURED-UNMATCHED.md` is regenerated each build
  with candidates and paste-ready `overrides` snippets.
- **Quality — Python**: 74 unit tests (line coverage gated at 80%) plus full mutation testing
  on every push (mutmut; kill rate ~65%, roadmap 6). Network fetchers are validated by their
  live runs instead. Exact counts are measured by the suites, not quoted here (decision 7).
- **Quality — data**: since the 2026-08-23 audit the pipeline is **gated, not just reported**:
  `qa_catalogue.py --strict` checks nine thresholds (record ratio, per-field coverage, ISO
  dates, duplicate `(area, id)`, corrupt JSONL lines, featured collisions and row floor) and
  fails the harvest before `docs/` is published, reverting the build and opening an issue;
  `fetch_sitemap.py` refuses a snapshot that loses more than 5% of indicator targets.
- **Quality — site** (2026-08-23): 48 vitest tests (search/i18n logic + app behavior via
  Testing Library with mocked data; 93% line coverage, 80% gate) plus StrykerJS mutation
  testing over `site/src/lib` (vitest runner; copy/language tables marked no-mutate —
  content, not logic). Survivor hunt same day took the kill rate 69%→91% (killed a dead
  word-prefix scoring tier found by a surviving mutant) and set **break: 85 as a hard CI
  gate**. Both run in `site.yml` on every push touching `site/`.
- **Question Ledger**: 100 questions drafted blind, stratification-audited against the real
  slug list (every theme backed; the control question correctly unanswerable).
- **Spikes** (Phase A, both decisive): PORDATA indicator metadata is server-rendered (plain
  HTTP suffices); INE's full catalogue is enumerable (`xml_indic.jsp?opc=2`, ~21 MB XML with
  themes; per-indicator metadata and data via JSON, no auth) — but INE's bot protection
  blocks Actions runners persistently (403, timeout ×2 over two days), so the offline
  `data/ine/raw.xml` upload path exists and the fetch is deferred (roadmap 2).
- **Audit and hardening** (2026-08-23, `/mega-audit` — report in `data/audits/`): 24 agents
  across eleven dimensions, adversarially verified; **57 findings survived** (7 high) plus 9
  gaps the completeness critic found. All seven high-severity findings and the
  accessibility/SEO/licensing gaps were fixed the same day, in five batches:
  **①** the four silent-failure paths — a failed re-fetch used to overwrite a good record and
  silently delete a live indicator; corrupt JSONL lines vanished; a `<sitemapindex>` switch
  was *verified* to tombstone all 2,195 rows automatically; and QA was a report, not a gate.
  **②** the featured matcher, which was flagging the wrong indicator under a curated badge.
  **③** the site's accessibility (the search box had no accessible name at all) and its
  machine discoverability (a project about discoverability was invisible to machines).
  **④** every disputed doc claim, including "2,268 indicators" — really 2,196 — which had
  already reached FFMS; plus `abandoned.txt`, giving roadmap 1's tombstone plan the code path
  it never had. **⑤** the audit command itself, whose scope was the root of every blind spot.
  The lesson is recorded as decision 7: the quality machinery verified code, and nothing
  verified plans or claims against measured state.
- **FFMS emailed** 2026-08-21 (text in `outreach/`), disclosing exactly this plan and asking:
  API planned? catalogue shareable / polite harvest acceptable? open to a conversation?

Operational lessons recorded the hard way: GitHub schedules only fire from the default
branch, and are delayed or skipped at the top of the hour (use odd minutes); a queued run in
a concurrency group is replaced by the next queued run; checkouts default to the trigger-time
sha, so data-writing workflows must check out the branch ref at run time (fixed 2026-08-22
after one duplicated chunk); a paths-filtered push trigger fires on every branch, so steps
that dispatch workflows or commit data must be gated to main (fixed 2026-08-23 after a
feature-branch harvest diverged the branch); an unconditional rebuild step turns no-op runs
into daily timestamp-only commits (build is now gated on records changing).

## What PORDATA is

Run by the Fundação Francisco Manuel dos Santos, a private non-partisan foundation. It republishes
official statistics across demographics, economy, employment, health, education, housing,
environment, justice and digital, with series often reaching back to 1960.

Products: statistics at three levels (Portugal, the 308 municipalities, Europe), Retratos
(interactive profiles with 30+ indicators for one country or municipality), summary tables,
simulators including an inflation calculator covering 1960 to 2025, and publications.

## Measured facts

Measured live on 2026-08-18, not read off documentation. Re-measure before relying on them.

Re-measured 2026-08-21 from the first committed sitemap snapshot (`data/sitemap-urls.txt` and
`data/sitemap-lastmod.tsv`, fetched by the Actions workflow): 5,906 unique URLs. The sitemap
**carries `<lastmod>`** on 4,423 of them, with real, varied per-page dates (2023 through
2026-08), so update tracking is high-signal, not churn. The 1,483 blank-lastmod pages are the
whole `/en` tree in the sample plus structural pages: 308 `municipios/quadro+resumo/<concelho>`
summary tables (one per municipality — these, not new indicators, explain the apparent +308
municipal jump against 2026-08-18), 260 subtema and 48 tema taxonomy pages, and 29 retratos.
The per-municipality quadros resumo are further evidence for the central insight: hand-built
joins, one per concelho.

Corrected 2026-08-23 (mega-audit): an earlier version of this paragraph counted quadro+resumo
summary tables as indicator pages and so inflated the per-area figures. Measured from the
current snapshot, the indicator corpus is **2,196** — Portugal 1,054, Europa 638, municípios
504 — out of 2,536 PT pages under those three areas, the difference being 337 quadro+resumo
tables (308 municipal, 28 europa, 1 portugal).

**Publication cadence** (measured 2026-08-23 over 12 months of indicator lastmods): PORDATA
publishes on **weekdays only** — zero Saturday lastmods, ~19 Sunday ones (noise) against
300–470 per weekday — in batches of 2–70 pages, most weekdays having some activity. lastmod is
date-only (no time of day). This sized the watcher schedule: daily morning run plus a weekday
late-afternoon run (`30 16 * * 1-5`, ~17:30 Lisbon) to catch same-day publishes; more frequent
polling cannot help while the granularity is a day.

| Fact | Value | How established |
|---|---|---|
| Public API | None | No developer or API route in the sitemap; not listed as having an API in either community aggregator |
| Total URLs in sitemap | 5,907 | `PordataSitemap.aspx`, 846 KB |
| Portuguese-language URLs | 2,940 | Excluding the `/en` tree |
| Indicator pages (PT) | **2,196** | 1,054 Portugal, 638 Europe, 504 municipal — the pipeline's corpus. An earlier 2,268 figure added 29 Retratos, 17 ODS, 15 comunicação and 11 publicações, which are publications, not indicators; it reached the FFMS email before being corrected (2026-08-23 audit) |
| English duplicates | 2,967 URLs | Under `/en`; EN pages share numeric ids with their PT originals |
| Platform | OutSystems | `OSFillParent` and `OSInline` classes in the markup; quadro-resumo rows are `__doPostBack` calls |
| Query tool | Server-side postbacks | `/db/ambiente+de+consulta/nova+consulta` holds no JSON, XHR or REST endpoint. Only jQuery and DataTables |
| Machine-readable path | Blocked | `robots.txt` disallows `/*Export*.aspx`, `/*Popup.aspx`, `/*PDF_*.aspx` |
| Source attribution | On every indicator page | Server-rendered `Fontes/Entidades:` line; confirmed harvestable at 100% coverage |
| Freshness metadata | Present | `Última atualização` per page, plus revision notes; confirmed harvestable at 100% coverage |
| Legal terms | Restrictive | Prohibit reproduction, commercialisation, transmission and public distribution of content without express authorisation. Silent on APIs, scraping and automated access. No stated attribution requirement |

Indicator pages have stable URLs, for example
`/portugal/populacao+residente++estimativas+a+31+de+dezembro+total+e+por+sexo-5`. The *query
tool* does not: because it runs on postbacks, a filtered view cannot be linked, bookmarked or
shared. You cannot send anyone a URL for "population of Bragança, 1960 to 2025".

## The central insight

**The scarce asset is not the numbers. It is the curation.**

Every indicator page names its upstream source, and those sources publish openly with real APIs:
INE, Eurostat, Banco de Portugal, various ministries. The numbers are already free and already
machine-readable elsewhere.

What only PORDATA has is the map: 2,196 human-meaningful indicator definitions, organised by
theme, harmonised across 65 years and 308 municipalities, each attributed to its source. That
curation is what makes a question answerable, and no upstream API provides it.

Supporting evidence that this is the real gap: PORDATA hand-builds Retratos and quadros resumo,
which are pre-assembled joins across indicators. Products built as workarounds are strong evidence
of a need users cannot meet themselves.

## The problem, stated properly

Four failure modes, all four live simultaneously:

1. **Discovery.** With 2,196 indicators under a statistical taxonomy, you cannot tell whether what
   you want exists. You must already know the thing is called "Índice de envelhecimento" to ask
   "is my town getting older?". *Addressed by the live catalogue + search site.*
2. **Extraction.** Once found, getting numbers out is manual and per-indicator, one spreadsheet at
   a time, laid out for eyes rather than machines, with no API and exports disallowed by
   `robots.txt`. *Partially addressed: the catalogue points to sources; the crosswalk (roadmap 2)
   is what makes values programmatically reachable.*
3. **Combination.** Nothing joins. Two indicators, or two geographies, or an indicator against a
   time window means downloading separately and aligning by hand. *Open.*
4. **Interpretation.** Even holding the numbers, a person cannot tell what is normal, notable or
   fairly comparable. A figure without a baseline, a peer group, or a caveat about a revision or
   definition change is close to useless and can mislead. *Open; the catalogue carries source,
   vintage and revision markers as the floor.*

These are not four problems. They are four stages of one pipeline: find the indicator, get its
numbers out, combine it with something, know what it means. If any stage is broken the whole path
from question to answer is broken. **Fixing one stage deeply produces nothing usable; a thin slice
through all four beats a deep fix to any one.**

## Ecosystem

| Source | What it offers | API |
|---|---|---|
| INE (Statistics Portugal) | The primary source behind most PORDATA tables | Yes, JSON, no auth; catalogue enumerable via `xml_indic.jsp?opc=2`; bot-protective toward cloud IPs |
| Eurostat | The European comparisons PORDATA republishes | Yes, REST dissemination API |
| Banco de Portugal (BPstat) | Monetary, financial, macro series | Yes, with an OpenAPI spec |
| dados.gov.pt | National open-data portal, CKAN-style | Yes, API key for writes only |
| api.ptdata.org | Community aggregator: geography, weather, public contracts, civil protection, transport, health, aviation, fiscal, plus a few macro indicators | Yes, `/v1/*` |
| api.openar.pt | Parliamentary data. Different domain, but the best available model of the shape PORDATA lacks. MIT, no auth, OpenAPI spec, ETags, incremental sync | Yes |
| PORDATA | 2,196 curated indicator pages | **No** (this project's catalogue is the machine-readable index of it) |

`api.ptdata.org` is broad but its economic coverage is a handful of macro series; it carries
neither INE's statistical database nor PORDATA's indicator catalogue. Nobody has built the layer
that takes a plain-language question about Portugal and returns the right series with its source.
That is the hole this project is filling, stage by stage.

## Decisions and why

Recorded so they are not re-litigated. Each carries what it costs if it turns out wrong.

1. **Do not redistribute PORDATA's data values. Harvest catalogue metadata only; serve values from
   upstream.** Why: the legal terms forbid redistribution, and INE and Eurostat make it
   unnecessary. A catalogue of facts *about* PORDATA's holdings is a different legal object from a
   copy of its content. Cost if wrong: if FFMS objects even to metadata harvesting, the catalogue
   plan needs their cooperation instead, which is why they were emailed first.
2. **Problem first, solution later.** Why: the owner's explicit call at the start; produced the
   framing above before any code. Superseded in practice by decision 6, with the ledger kept as
   the evidence base and acceptance tests.
3. **Do not go straight to an MCP server, however tempting.** Why: without the crosswalk a model
   guesses at series identity, and it will guess confidently and wrongly. For public statistics
   that is the worst available failure mode, because a plausible wrong number gets repeated. An
   MCP that returns catalogue *pointers* (not values) is exempt from this objection; values
   require the crosswalk. Cost if wrong: a slower path to a demo.
4. **Treat openAR as the template.** Why: one volunteer wrapped a government data programme in a
   clean API with an OpenAPI spec, weak ETags, `updated_since` incremental sync and a 100 rpm
   limit, then shipped a web frontend and an MCP server on top. It proves the scope is achievable
   solo. Cost if wrong: little; it is a reference, not a dependency.
5. **Any answer must carry its source, its vintage, and any revision caveat.** Why: revision
   notes like INE's 2021–2024 restatement must never be silently dropped. Cost if wrong: none,
   this is a floor not a bet.
6. **Proceed without waiting for FFMS (owner decision, 2026-08-22).** The email disclosed
   exactly this plan, the reply can still redirect later, and the harvest stays on the recorded
   legal line (metadata only). Executed as phases A (spikes) → B (harvest) → C (site), all
   shipped 2026-08-22; D (MCP) remains gated on the owner and the crosswalk. Harvest pacing set
   by owner at one request per 20 seconds. Cost if wrong: if FFMS replies with objections,
   harvested metadata may need renegotiating or discarding.
7. **Plans and claims must be verifiable against measured state (2026-08-23).** Prompted by a
   near-miss: the fast-tracked featured pill silently depended on a 29/56 Europa match rate
   recorded only in `stats.json` — the quality machinery verified code, but nothing verified
   plans against reality. Three practices follow: **(a)** roadmap items state their
   preconditions explicitly where the plan is written; **(b)** any metric a feature depends on
   becomes a machine-checked threshold in the QA report, never prose someone must remember;
   **(c)** `/mega-audit` (`.claude/commands/mega-audit.md`) runs periodically — an
   eight-dimension cross-consistency sweep (roadmap preconditions vs measured state, doc
   claims vs primary sources, data-quality gates, drift, silent failure paths, assumption
   inventory, dead code, executed edge probes) where every finding must carry an automated
   prevention. Widened after its first run to eleven dimensions — the completeness critic
   showed the command's own scope was the blind spot, so it now also names accessibility and
   machine discoverability of the deliverable, licensing/provenance/supply chain, the
   directories no other dimension opens (`ledger/`, `outreach/`, `.claude/`), and finally
   itself. Cost if wrong: audit overhead on a one-person project; mitigated by running it
   at milestones, not on a schedule.

## Constraints

- Do not redistribute PORDATA's data values.
- Catalogue metadata is the defensible line. Indicator pages are permitted by `robots.txt`; only
  Export, Popup and PDF paths are disallowed. Any harvest should be politely rate-limited and
  should credit PORDATA prominently.
- INE tolerates sparse requests only from cloud IPs: cache its catalogue, retry later not harder.
- Interpretation errors are the real danger, not missing features.
- **Nothing publishes past a failing gate.** `qa_catalogue.py --strict` and the sitemap
  corpus floor exist because a green Actions run used to be compatible with a silently
  degraded catalogue. Lowering a threshold to make a run pass is a decision to record, not a
  fix to apply quietly.
- **A curated badge must be right or absent.** The featured matcher is deliberately
  high-precision: showing the wrong indicator under PORDATA's curation is worse than showing
  none, because faithfully mirroring that curation is the whole claim.

## Roadmap

Only open work. History lives in "What has been built" and git. Item numbers are stable ids
(referenced from code and docs), **not** priority order.

**Execution order (2026-08-23, after the audit).** Ids are stable and never reused — a
retired id stays retired (11), and a promoted one keeps its own (12). Priority:

1. **12 — featured pill + rename.** Small, ready, and the only visible feature whose
   precondition is now proven rather than assumed.
2. **10 — card design pass** with Claude Design. Runs after 12 so the design sees every badge
   it must lay out, and it owns badge presentation for item 8's labels too.
3. **6a — silent data corruption.** Three parse-time assertions. Cheap, and they protect the
   artefact everything else depends on; the gate catches degradation but not a wrong value
   that looks well-formed.
4. **2 + 2a — INE cache and the crosswalk** the moment the upload lands. Strategically the
   largest item on the board and the gateway to Phase D; blocked only on a laptop.
5. **8b/c, then 9** — labels from sources and recency, then blended relevance.
6. Background, in any order: **6b–6f**, **7**, and **3** as evidence accumulates.

Items 4 (calendar) and 5 (gated on 2 + owner go) unchanged.

**Waiting on the owner:** the INE `raw.xml` upload (5 min at a laptop; unblocks item 2, the
crosswalk — the roadmap's biggest strategic lever), the item 12 name call
("Destaques"/"Highlights" proposed), the ~20-record spot-check, curating
`data/catalogue/FEATURED-UNMATCHED.md` (item 1), and ledger attempts (3). *Done: the id-1221
browser check — dead for humans too, so it is retired rather than retried.*

1. **Harvest closed — residual owner checks.** 2,195/2,195 reachable pages; id 1221 is dead
   upstream and retired via `data/catalogue/abandoned.txt` (owner-verified in a browser, and
   cited in a 2022 Gulbenkian publication, so it is a genuine PORDATA bug worth including in
   the FFMS follow-up, item 4). Remaining: spot-check ~20 records against live pages (owner,
   browser), and curate `data/catalogue/FEATURED-UNMATCHED.md` — 50 quadro names the matcher
   deliberately refuses to guess, each listed with candidates and a paste-ready `overrides`
   snippet. Several have no counterpart at all (derived aggregates PORDATA publishes only
   inside the quadro; a few quadro rows share one catalogue page), so a perfect score is not
   the goal and the QA floor is set accordingly.
2. **INE catalogue snapshot, then the crosswalk** — the gateway to Extraction and Phase D.
   Three fetch attempts failed from Actions runners (403, timeout ×2, 2026-08-22/23): INE
   likely blocks cloud IP ranges persistently, not temporarily. Fallback shipped: the owner
   downloads `xml_indic.jsp?opc=2` from their own connection and commits it as
   `data/ine/raw.xml`; `fetch_ine_catalogue.py` then processes the committed file offline
   (and deletes it — the gzip is the cache). Then cache `data/ine/indicators.csv`. Then
   match each catalogue entry to its upstream series: name-match against INE's catalogue for
   INE-sourced indicators, Eurostat dataset codes for `europa`, BPstat for monetary. Store
   match + confidence; unmatched entries stay honest with `crosswalk: null`.

   **2a. Pilot: find the upstream of the dead page (id 1221).** "Despesas das administrações
   públicas em ambiente em % do total das despesas (1995-2013)" is the ideal first case —
   PORDATA's page is gone, so a successful crosswalk demonstrates the whole value
   proposition: *the curation layer still routes you to living data*. It also strengthens the
   FFMS follow-up (item 4) from "your page is broken" to "your page is broken, here is where
   the series lives, and here is a user still citing it in 2022".
   **Hypothesis, unverified** (asserted from memory 2026-08-23; this sandbox cannot reach
   Eurostat or INE, so it has *not* been checked against a primary source — decision 7): this
   looks like COFOG data, environmental protection = division GF05, which Eurostat publishes
   in `gov_10a_exp` (general government expenditure by function) and INE mirrors in national
   accounts under "Despesas das Administrações Públicas por funções"; the 2013 cut-off is
   consistent with the ESA 95 → ESA 2010 changeover. **Verify before recording it anywhere as
   fact** — dataset code, the exact "% of total expenditure" measure, and whether the series
   is Portugal-only or EU-wide. Do it when the INE cache lands, or sooner from any machine
   with open internet.
3. **Attempt the ledger questions** (owner, browser, spare moments): 100 questions in
   `ledger/questions.csv` per `ledger/README.md`. The evidence base for what to build next and
   the acceptance tests for everything built so far.
4. **FFMS follow-up** if no reply by ~2026-09-04 (email sent 2026-08-21; see `outreach/`). Any
   reply may redirect items 2 and 5.
5. **Phase D: MCP server over the catalogue** *(gated on owner go + crosswalk)*. Discovery
   tools first — search the catalogue, return metadata + PORDATA link + upstream source:
   pointers, not numbers, so nothing can be hallucinated. Values from upstream only where the
   crosswalk is confident, each answer carrying source/vintage/caveats per decision 5.
   `@openar/mcp` is the shape precedent.
   **Semantic search design (decided 2026-08-23):** embeddings, no vector database — at
   ~2,200 entries brute-force cosine is ~1 ms anywhere. Pipeline step embeds each
   indicator's PT+EN names (+description) with a small **multilingual** model
   (multilingual-E5-small class, quantized) and ships the vectors as a static file next to
   `catalogue.json` (~2,200 × 384 dims int8 < 1 MB), refreshed by the harvest loop.
   Multilingual embeddings mean queries in any EU language match the PT/EN catalogue —
   search works in the selector's greyed languages before their UIs are translated.
   Consumers:
   - **MCP server**: embeds queries locally, hybrid keyword+vector ranking. Embeddings only
     *find* entries, so decision 3's no-hallucination line holds.
   - **Site, as progressive enhancement** (owner's call over the initial MCP-only lean):
     fuzzy search remains the instant baseline; the query-embedding model (~25–30 MB
     quantized) lazy-loads in the background via transformers.js, is cached by the browser
     per device (one-time download, ~50–200 ms local inference thereafter), and silently
     upgrades results to hybrid ranking when ready. Two caveats weighed and accepted by
     the owner (2026-08-23) with their mitigations: metered-data cost → respect the
     `Save-Data` signal (skip auto-load) and keep the model optional, the page fully
     useful without it; low-end phone memory during inference → that is why the model
     must stay in the small-quantized class, not a larger one.
6. **Hardening backlog** *(absorbs the old item 11; sources: the 2026-08-23 `/mega-audit`,
   full report in `data/audits/`)*. Ordered by what breaks if ignored, not by effort.

   **(a) Silent data corruption** — the pipeline can still publish wrong values without
   tripping the gate: the fontes boundary vocabulary is circular, so new PORDATA UI text
   passes harvest, QA and build straight into published sources; the `ultima_atualizacao`
   fallback regex can publish arbitrary page text if PORDATA drops its on-page ISO dates, and
   the site's default sort trusts that field; indicator-name extraction assumes today's
   `<title>` template. Each needs a shape assertion at parse time, not a report afterwards.

   **(b) Failures nobody hears** — the harvest commit step is skipped on crash/timeout, so
   in-run checkpoints protect nothing in Actions; `sitemap.yml` commits its snapshot before
   opening the issue, so a failed `gh issue create` loses the add/remove notification for
   good; nothing verifies the committed `docs/` bundle matches `site/` source, and the Pages
   deployment itself is unmonitored; `tests.yml` swallows mutation failures with `|| true`.

   **(c) Correctness of the freshness loop** — staleness uses a strict `>` on a date-only
   lastmod, so a same-day PORDATA update is missed for ever.

   **(d) Test strength** — Python mutation kill rate is ~65% (mutmut) and ungated; the site's
   is 91% behind a hard `break: 85`. Bring Python up and gate it the same way.

   **(e) Code hygiene** — `diff_sitemap.py` re-implements `pordata_lib`'s parsing instead of
   importing it (the lib exists to prevent exactly that drift); `build_catalogue.AREA_LABELS`
   duplicates a vocabulary it never uses; records missing required keys still crash with a
   raw `KeyError`.

   **(f) Payload budget** — every visitor downloads the whole catalogue (1.27 MB raw / 137 KB
   gzipped) before the first search. Benign today, unbounded once the crosswalk widens each
   row: set a budget before that lands, then split or stream if it breaks.

   *Done 2026-08-23:* `spikes.yml` made dispatch-only — a push trigger was re-running finished
   research probes on any edit to their scripts.
   *Deferred:* harvesting the `/en` tree (~2,196 pages) if EN descriptions become worth having.
7. **Name/i18n coverage review** *(owner ask 2026-08-23)*. `docs/data/names-map.csv`
   (rebuilt on every harvest) maps each indicator's PT name to its EN name and flags gaps:
   `missing_pt` (harvest found no name — the 3 known empties), `missing_en` (no `/en`
   sitemap slug for the id), counts in `stats.json` under `names`. After the harvest
   completes: review flagged rows and repair. Separately, the site's language selector now
   lists all 24 EU official languages with only PT/EN selectable; enable others
   progressively by translating the `STRINGS` block (ES/FR/DE/IT UI strings already exist
   in the file, greyed pending the content-language decision) and adding the code to
   `AVAILABLE`.
8. **Label system for filtering** *(owner ask 2026-08-23; design first)*. Richer filters
   beyond the three area pills, as clickable labels on cards plus a filter row. Candidate
   label sources, by value:
   - **(a) PORDATA's own theme taxonomy** — the strongest, it *is* the curation — via the 260
     `subtema` pages in the sitemap. A one-off ~1.7 h harvest at the polite pace would map
     indicators to temas/subtemas; check first whether subtema pages are server-rendered
     lists, as the quadros turned out to be.
   - **(b) source entity** from `fontes`, already harvested: 165 distinct source strings
     (measured 2026-08-23) to normalise to ~30 organisations (INE, Eurostat, OCDE, DGEEC…).
   - **(c) recency** buckets from `ultima_atualizacao` (updated this year / stale >5y).
   - **(d) status** — featured and descontinuado. Split out as **item 12**, which ships first.

   Order: 12, then (b)+(c) — both zero new requests — then design (a)'s harvest, then the
   full label UI. Design it with item 10, not twice: labels add chips to the same card.

9. **Relevance / recommended sorting** *(owner ask 2026-08-23)*. The fuzzy-score
   "relevance" option was **removed from the sort pill** the same day (owner call: not
   producing a useful order); the pill now offers newest/oldest/A→Z/Z→A with
   **newest-first as the default**, and match scores only gate which rows count as hits.
   Bringing relevance back means a real blended ranking: match score plus featured status,
   update recency, breadth (a headline indicator over a narrow breakdown), and eventually
   the Phase D embeddings for semantic closeness. The `sortRelevance` i18n strings remain
   in `site/src/lib/i18n.ts` for its return. Design after the label system, since labels
   and ranking share the same signal inventory.
10. **Card design review — information hierarchy** *(owner ask 2026-08-23)*. The result
   card is currently a stain of undifferentiated text: title, EN alt, area badge,
   featured/status badges, sources, update date and description all compete, and the eye
   has nowhere to land. Run a proper design pass **with Claude Design** (the canvas
   editor): establish a reading order — what a scanner needs first (title), second
   (freshness? area?), what can collapse or truncate (long fontes lists, description),
   what earns color vs. muted — and mock 2–3 card variants side by side on real data
   (long municipal names, tag-heavy featured rows, tombstoned rows) before touching
   `App.tsx`. Owner picks the winner on the canvas; then implement with the existing
   shadcn tokens. Coordinates with item 8 (labels add more chips to the same card —
   design them together, not twice).

12. **Featured pill + rename** *(promoted out of item 8d, 2026-08-23 — it is next up and was
   unreadable inside that item)*. Two halves, both small:
   - **Rename.** Cards badge the raw internal value `★ quadro_resumo`, which no visitor can
     decode. Proposed: PT **"Destaques"** / EN **"Highlights"** — these are the indicators
     PORDATA itself curates into its summary tables — with ES "Destacados", FR "Essentiels",
     DE "Highlights", IT "In evidenza" prepared. Badge and pill say the same thing in the UI
     language. *Owner confirms the wording; it is a one-line change either way, so it does
     not block the build.*
   - **Pill.** A fourth filter chip in the existing swipeable row, opt-in like the areas.
   **Precondition met and machine-checked:** the matcher was rebuilt high-precision and
   injective after the audit proved it was flagging wrong indicators, and the QA gate enforces
   `featured_collisions = 0` and `featured_rows >= 40`, so the pill cannot ship over a broken
   mapping. 43 rows carry the badge today; the tail is owner curation (item 1), and the honest
   framing is that the badge marks *confidently matched* quadro indicators, not the full
   quadro.

## Verification

```bash
# pipeline
python3 -m unittest discover -s tests            # Python suite
python3 -m mutmut run                            # mutation suite (~1 min)
python3 scripts/build_catalogue.py               # rebuild docs/data from pages.jsonl
python3 scripts/qa_catalogue.py --strict         # the data gate; non-zero = do not publish
python3 scripts/repair_pages.py                  # idempotent fontes repair

# site (never hand-edit docs/index.html or docs/assets)
cd site && npm ci && npm run build               # typecheck + build into docs/
npm run test:coverage                            # vitest, 80% line gate
npm run mutation                                 # StrykerJS, break at 85

# live
curl -s https://caasols.github.io/pordata/data/stats.json
curl -s https://www.pordata.pt/robots.txt
python3 ~/.claude/skills/cartographer/scripts/audit.py . --style-lint
```

Counts are deliberately not quoted here: the suites report them, and prose drifts
(decision 7). At milestones run `/mega-audit`; its reports land in `data/audits/`.
