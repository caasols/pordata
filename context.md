---
updated: 2026-08-24
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
GitHub Actions.

**Where it is going (owner, 2026-08-23).** Not a catalogue of pointers, and not a mirror of
PORDATA. Go to the sources, pull the series, archive them, and build the interface PORDATA
does not have — charts people can actually work with — with the explicit goal of ending up
**more complete than PORDATA**. This stays inside decision 1: values come from INE, Eurostat
and BPstat under *their* terms, never from PORDATA's rendering of them, and PORDATA's
contribution stays the curation. The crosswalk (Extraction) is therefore not one roadmap item
among many but the **spine**: the archive, the detail pages, the coverage gap and Phase D all
hang off it. See Roadmap; execution order is in its header.

## Architecture and inventory

| Path | What it is |
|---|---|
| `CLAUDE.md` | The map. Ranked pointers, current focus |
| `context.md` | This file. All project state: findings, decisions, roadmap |
| `README.md` | Human front door: overview, site link, licensing. Carries no state |
| `LICENSE` / `LICENSE-DATA` | MIT for the code; CC BY 4.0 for the catalogue metadata, with PORDATA/FFMS attribution |
| `scripts/` | Python package: sitemap watcher, harvester, catalogue build, QA, featured sets, spikes |
| `tests/` | Python unittest suite, coverage-gated, mutation-tested via mutmut (`setup.cfg`). Site tests live in `site/src/**/*.test.*` (vitest + StrykerJS) |
| `.github/workflows/` | Eight: sitemap watch (detector), catalogue harvest (worker, QA-gated), tests.yml and site.yml (per push), ine-availability (daily probe, self-retiring), featured-sets / ine-catalogue / spikes (manual). Table in `CLAUDE.md` |
| `data/` | Committed pipeline state: sitemap snapshots, `catalogue/pages.jsonl`, CHANGELOG, QA (gated), `catalogue/abandoned.txt`, spike reports, `audits/` |
| `site/` | The search UI source: React + Vite + Tailwind + shadcn-style components (TypeScript). `npm run build` → `docs/` |
| `docs/` | The GitHub Pages site: built UI bundle (from `site/`, committed) + `data/` (catalogue.json/csv/stats — the static "API") |
| `ledger/` | Question Ledger: 100 demand-side questions plus protocol |
| `outreach/` | Record of external contacts. Holds the FFMS email as sent |
| `graphify-out/` | Derived code graph, gitignored |
| `.claude/commands/` | `/mega-audit`: the cross-consistency deep-audit prompt (decision 7) |

## What has been built (2026-08-21 → 2026-08-24)

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
  slugs, opt-in area filter pills in one swipeable row plus a **Resumo/Summary** pill on its
  own axis (PORDATA's per-location overview set; ANDs with the areas), a sort pill
  (newest/oldest/A→Z/Z→A, newest default), infinite scroll in device-sized chunks, an
  "Resumo" badge (attribution in its tooltip) and a "descontinuado" badge, light/dark theme, PORDATA credited prominently, every hit linking
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
- **Quality — Python**: unittest suite with line coverage gated at 80%, plus full mutation
  testing on every push (mutmut; kill rate ~65%, roadmap 6d). Network fetchers are validated
  by their live runs instead. Counts are measured by the suites, never quoted here — they
  drifted three times in two days before this rule (decision 7).
- **Quality — data**: since the 2026-08-23 audit the pipeline is **gated, not just reported**:
  `qa_catalogue.py --strict` checks nine thresholds (record ratio, per-field coverage, ISO
  dates, duplicate `(area, id)`, corrupt JSONL lines, featured collisions and row floor) and
  fails the harvest before `docs/` is published, reverting the build and opening an issue;
  `fetch_sitemap.py` refuses a snapshot that loses more than 5% of indicator targets.
- **Quality — site** (2026-08-23): vitest suite (search/i18n logic + app behavior via
  Testing Library with mocked data; ~93% line coverage against an 80% gate) plus StrykerJS mutation
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
  Follow-through the same evening: **6a** added parse-time shape assertions for date, fontes
  and title — the gate catches a field going empty, never a field filled with something
  well-formed but wrong, so a value failing its shape is now dropped and the record carries
  `parse_warnings` for the gate to trip on (verified against all 2,195 records, zero false
  positives). **12** then shipped the Resumo/Summary pill and retired the raw
  `quadro_resumo` badge, which the matcher rewrite had finally made safe to surface.
- **The card became a routing decision** (roadmap 10, 2026-08-23). It answers *is this the
  row I meant?*, not *what is this indicator?* PORDATA's description is gone from it — 96.3%
  of descriptions are exactly the SEO template, 0.5% are definitional — and the English alt
  name left the card while staying in search and sort. A `Badge` now means *a facet you can
  filter on* and nothing else, which is what stops the card becoming a wall of pills when item
  8's labels land; sources and freshness are labelled micro-columns; freshness is month
  precision; the whole card is one tap target. The chart slot is reserved, muted and inert —
  no values exist until roadmap 14 and PORDATA's are never redistributed — and the click still
  leaves for pordata.pt until the detail pages (15) land.
  **The coverage line came out of the title.** The descriptive half was already in the
  catalogue, welded on with a colon at equal weight, which *was* the hierarchy problem:
  `split_breakdown` demotes that tail on 1,196 rows (54.5%) and refuses when the tail is the
  indicator itself. `extract_unit` recovers a unit from the chart caption already sitting in
  `marker_windows` on 1,138 rows (51.8%) — 78.4% of rows carry a coverage line, and the card
  renders correctly without one. Marker windows are searched slice by slice, never joined:
  joining spliced two truncated fragments into a plausible-but-corrupt unit. Four derived
  metrics became QA thresholds, because a derived field degrades silently.
  **A second upstream defect for the FFMS follow-up:** PORDATA serves a literal `?` where an
  en dash belongs in 37 names; our decoding is clean and their own slug drops the character,
  so it is theirs. Repaired at build time, anchored mid-string so "Onde existem mais Vilas?"
  (a real question) survives.
- **Unit vocabulary translated** (roadmap 18, 2026-08-23). The unit rendered in Portuguese
  whatever the UI language. It was cheap because PORDATA writes units compositionally: the 148
  distinct strings are **108 measures × 14 scales**, so translating the parts covers the whole
  vocabulary and any future combination. `site/src/lib/unit-terms.json` is the single source of
  truth — the site renders from it and the QA gate measures coverage against the same file, so
  the two cannot drift. Unknown terms fall back to Portuguese, never to a blank. EN complete;
  ES/FR/DE/IT deliberately left to item 7, when those UIs are actually selectable. The `pt`
  table holds *repairs*: the caption loses superscripts, so `m 3` was wrong in Portuguese too.
- **The INE catalogue landed** (2026-08-24), unblocking the crosswalk. The fetch succeeded from
  an Actions runner on the **fourth** attempt, retiring the recorded belief that INE "blocks
  cloud IP ranges persistently" — the log shows two successful Saturday pulls and failures only
  after a third and fourth 21 MB request inside 45 minutes. We throttled ourselves.
  `data/ine/indicators.csv` holds **13,084 indicators** across 25 themes, each carrying a
  per-indicator **`json` API URL** (the concrete route to values for item 14) and
  **`geo_lastlevel`** (the geographic granularity PORDATA's markup never exposed). The owner's
  `raw.xml` upload is no longer needed.
- **The crosswalk turned out to be one-to-many** (spike A5, `data/spikes/`). Item 2 had been
  written as "match each entry to its upstream **series**", presuming 1:1. Measured: exact title
  matching leaves 84.6% unmatched and geography scoping resolves 7 rows; token containment
  matches 27.5% but with a median tie of **9** INE entries and a worst of **1,341**. INE's
  catalogue is series-level where PORDATA's is indicator-level, so one indicator maps to a
  *family* split by geography, periodicity and census-vs-estimate. Storing one `ine_id` per row
  would have recorded an arbitrary choice as fact — the failure the featured matcher was
  rewritten to avoid. Spec revised to store candidate sets and defer selection to fetch time.
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
   **Widened 2026-08-23 (owner).** "Serve values from upstream" means *fetch and archive from
   upstream*, not merely link out to it. Reusing an INE, Eurostat or BPstat series under that
   body's own terms is a different legal object from copying PORDATA's rendering of it;
   PORDATA's contribution stays what the central insight says it is — the curation. The binding
   constraint therefore moves from PORDATA's terms to each upstream's, which is why item 13
   (read and record those three licences) gates item 14 (the archive). The goal is not to
   mirror PORDATA but to replace what it does with the numbers: its UI cannot show a series
   properly, and stages 3 and 4 of the framing above are unreachable without holding values.
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

**Execution order (2026-08-24).** Ids are stable and never reused — a retired id stays
retired (10, 11, 12, 18 have shipped; 11 was absorbed into 6). Priority:

1. **2 — the crosswalk.** The INE cache landed 2026-08-24, so the biggest lever is live and
   nothing gates it. **17 — name the project** runs alongside: cheap, and more expensive once
   Phase D publishes a package name or FFMS replies.
2. **13, then 14 → 15** — read the three upstream licences (owner, ~30 min), then the series
   archive, then per-indicator detail pages. 13 is now the only thing gating 14.
3. **16 — the coverage gap**, once the crosswalk makes the complement computable. This is what
   turns the project from a mirror of PORDATA into something more complete than it.
4. **8b/c, then 9** — labels from sources and recency, then blended relevance.
5. **24 — widen the harvest parse** (question, revision note, period) so every future fetch
   captures what A6 found. No new requests, and it is 21's precondition.
6. Background, in any order: **6b–6f**, **7**, **3** as evidence accumulates, and **20** once
   19's units have accrued. **21** is deliberately last: its value grows with everything the
   parser learns from 15 and 24, so firing it early means doing it twice. **22** runs itself
   daily until it retires.

*Shipped 2026-08-23/24: **6a**, **10**, **12**, **18**, and **19's spikes A3/A4** — see
"What has been built".*

1. **Harvest closed — residual owner checks.** 2,195/2,195 reachable pages; id 1221 is dead
   upstream and retired via `data/catalogue/abandoned.txt` (owner-verified in a browser, and
   cited in a 2022 Gulbenkian publication, so it is a genuine PORDATA bug worth including in
   the FFMS follow-up, item 4). Remaining: spot-check ~20 records against live pages (owner,
   browser), and curate `data/catalogue/FEATURED-UNMATCHED.md` — 50 quadro names the matcher
   deliberately refuses to guess, each listed with candidates and a paste-ready `overrides`
   snippet. Several have no counterpart at all (derived aggregates PORDATA publishes only
   inside the quadro; a few quadro rows share one catalogue page), so a perfect score is not
   the goal and the QA floor is set accordingly.
2. **The crosswalk** *(INE cache landed 2026-08-24; nothing gates this)*.
   `data/ine/indicators.csv` holds 13,084 INE indicators across 25 themes, each with a
   per-indicator `json` API URL and `geo_lastlevel`. Match PORDATA's rows to upstream: INE for
   INE-sourced indicators, Eurostat dataset codes for `europa`, BPstat for monetary.

   **It is one-to-many — measured, not assumed** (`data/spikes/a5-crosswalk-shape.md`,
   reproducible via `scripts/analyse_crosswalk.py`). INE's catalogue is series-level and
   PORDATA's is indicator-level, so one indicator maps to a *family* split by geography,
   periodicity and census-vs-estimate: exact title matching leaves 84.6% unmatched, and token
   containment ties a median of 9 entries and a worst of 1,341. **Store the candidate set and
   the evidence that selected it, never a single winner**; defer picking a series to fetch time
   (item 14), where geography and period follow from the request; keep `crosswalk: null` where
   no credible family exists. Constrain with INE's `theme`/`subtheme`/`keywords` before any
   name comparison — unused so far and the cheapest precision available.

   Measure Eurostat and BPstat the same way before specifying them; do not assume they share
   this shape. The 2,195-to-13,084 ratio is also item 16's raw material.

   **2a. Pilot: the dead page (id 1221).** "Despesas das administrações públicas em ambiente em
   % do total das despesas (1995-2013)". PORDATA's page is gone, so a successful crosswalk
   demonstrates the whole proposition: *the curation still routes you to living data*. It also
   strengthens the FFMS follow-up (item 4). **Hypothesis, unverified** (asserted from memory
   2026-08-23, never checked against a primary source — decision 7): COFOG environmental
   protection = GF05, which Eurostat publishes in `gov_10a_exp`. **Verify before recording it
   as fact** — dataset code, the exact "% of total expenditure" measure, and whether the series
   is Portugal-only or EU-wide.
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

   *(a) Silent data corruption — **done**; see "What has been built".)*

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
   - **(d) status** — featured and descontinuado. *Shipped 2026-08-23 as the Resumo pill and
     the descontinuado badge; see "What has been built".*

   Order: (b)+(c) first — both zero new requests — then design (a)'s harvest, then the full
   label UI. **The card design pass has already shipped**, so labels must fit the design that
   exists rather than prompt a second one: a `Badge` means *a facet you can filter on* and
   nothing else, and the chip row needs an overflow rule before it gains more chips.

9. **Relevance / recommended sorting** *(owner ask 2026-08-23)*. The fuzzy-score
   "relevance" option was **removed from the sort pill** the same day (owner call: not
   producing a useful order); the pill now offers newest/oldest/A→Z/Z→A with
   **newest-first as the default**, and match scores only gate which rows count as hits.
   Bringing relevance back means a real blended ranking: match score plus featured status,
   update recency, breadth (a headline indicator over a narrow breakdown), and eventually
   the Phase D embeddings for semantic closeness. The `sortRelevance` i18n strings remain
   in `site/src/lib/i18n.ts` for its return. Design after the label system, since labels
   and ranking share the same signal inventory.
13. **Upstream reuse terms — read and record** *(owner, laptop, ~30 min; gates item 14)*. Before
   a single upstream value is archived, read and record the actual reuse licence of each source
   the archive would draw on: **Eurostat** (Commission reuse policy), **INE** (Statistics
   Portugal's terms of use) and **BPstat** (Banco de Portugal). For each, record in this file:
   the licence name, its URL, the exact attribution string it requires, and whether it permits
   redistribution of derived/reformatted series (not just display). *Not yet checked from this
   sandbox — it has no route to any of the three, and decision 7 exists because an upstream was
   once asserted from memory.* Expected outcome is three source-citation regimes rather than
   three blockers, but "expected" is not "recorded". Prevention: the archive job should refuse
   to write a series whose source has no recorded licence entry.

14. **Series archive — pull the numbers from the sources** *(gated on 2 + 13)*. The turn from a
   catalogue of pointers into a data layer. For each crosswalked indicator, fetch the series
   from its upstream API, normalise to one long-format schema (indicator, geography, period,
   value, unit, flag), and archive it on the same git-scraping cadence the harvest already
   runs. Three things to settle before building, each answerable from a pilot rather than in
   the abstract:
   - **Size.** A municipal indicator is ~308 geographies x ~65 years x breakdowns; across
     ~2,200 indicators that plausibly spans tens of MB to several GB. Measure it on ~10 real
     series across the three sources *first* — the answer decides whether this lives next to
     `catalogue.json` in git or needs different storage entirely.
   - **Vintages, not just latest.** Archiving on a schedule yields revision history for free,
     and INE's 2021-2024 restatement is exactly the case decision 5 was written for. Neither
     PORDATA nor INE lets anyone see what changed between releases; keeping vintages is the
     cheapest genuinely new thing on this roadmap.
   - **Honesty about coverage.** Uncrosswalked indicators keep `crosswalk: null` and simply
     have no series. The site must render that state as a first-class case, never as an error.
   Preconditions in QA thresholds, not prose: a per-source fetch-success floor, a schema
   conformance check, and a size budget that trips before the repo does.

15. **Per-indicator detail pages with charts** *(owner direction 2026-08-23; gated on 14 for
   the charts)*. Replace the click-out to pordata.pt with a page this project owns: the
   indicator's full metadata, its upstream attribution per decision 5 (source, vintage,
   revision caveat rendered *with* the series, not in a footer), and a chart the user can
   actually work with — pick geographies, pick a window, compare. This is stages 3
   (Combination) and 4 (Interpretation) of the framing, which no amount of catalogue work
   reaches. Two decisions to take when it starts:
   - **Routing on GitHub Pages.** Hash routing is cheap but unshareable and invisible to
     crawlers; pre-rendering ~2,200 static pages at build time costs build minutes and buys a
     real canonical URL plus per-indicator JSON-LD. Lean pre-render — discoverability is the
     project's stated purpose.
   - **A metadata-only version can ship before 14.** A detail page with no chart still beats
     bouncing to a page from the year 2000, and it de-risks the routing decision early.
   The card already assumes this: it was rebuilt as a routing decision with a reserved, inert
   chart slot, so the detail page inherits a card that expects it. A sparkline is the one
   element that would later earn a place on the card — gated on 14, and the slot is waiting.

16. **Coverage gap: what INE and Eurostat have that PORDATA does not** *(owner ask
   2026-08-23; gated on 2)*. The goal stated plainly: **be more complete than PORDATA**.
   PORDATA curates ~2,196 indicators out of upstream catalogues that hold far more, and the
   crosswalk (item 2) is what makes the comparison computable — once each PORDATA indicator
   is matched to its upstream series, the *complement* is the gap.

   **The trap this item must not fall into.** The central insight of this project is that the
   scarce asset is the curation, not the numbers. Eurostat alone publishes thousands of
   datasets; dumping the complement into the catalogue would produce something with INE's
   coverage and INE's usability, which is the problem, not the fix. So the deliverable is
   **not** an enumeration — it is a *selection*, and every addition must arrive with what
   makes PORDATA's entries usable: a human-meaningful name in Portuguese, a theme, and a
   stated reason for being there. Completeness without curation is a regression.

   Method, in order: (a) hold INE's catalogue (item 2) and fetch Eurostat's table of contents;
   (b) subtract what the crosswalk already matched; (c) rank what is left by evidence of
   demand, not by volume. Ranking signals available without inventing any: the ledger's 100
   real questions (item 3) and which of them nothing in the catalogue answers; themes where
   PORDATA is visibly thin against INE's own tree; and series the quadro-resumo implies people
   want per-location but PORDATA only publishes nationally. (d) Propose a shortlist for the
   owner to accept or reject one by one — the accept/reject record then *becomes* the curation
   rule, which is the only honest way to acquire one.

   Preconditions: item 2 (INE cache and crosswalk) — without it the complement cannot be
   computed at all, only guessed. Eurostat's TOC needs network, so it runs via Actions.

17. **Name the project properly** *(owner ask 2026-08-23: "pordata map is a shitty name")*.
   Three reasons it is worth real effort, beyond taste:
   - **It will soon be wrong.** Items 14–16 take the project from *a map of PORDATA* to *a
     data layer that holds upstream series and deliberately exceeds PORDATA's coverage*. A
     name that describes the thing it is outgrowing misdescribes it within one milestone.
   - **It borrows someone else's mark.** PORDATA is FFMS's brand. *Verify, do not assume*
     (decision 7): check whether it is a registered trademark in PT/EU before deciding how
     much distance the new name needs. Either way, a name built on theirs implies an
     endorsement that does not exist, and the outreach in `outreach/` is still unanswered.
   - **It gets harder to change, fast.** Phase D publishes an MCP package; a published package
     name is close to permanent, and the FFMS reply may arrive at any time. Do this **before**
     either.

   Deliverable: a shortlist with availability actually checked (GitHub org/repo, npm/PyPI if
   Phase D ships, domain, and a plain search for collisions in the PT data space), owner
   picks. Then a rename plan that **enumerates what breaks** rather than discovering it later:
   the Pages URL is `caasols.github.io/pordata`, so renaming the repo moves the live site —
   GitHub redirects repository URLs but the published site path changes, which invalidates
   every link already shared, the canonical tag, the JSON-LD `url`, the OG/Twitter meta and
   the sitemap. Decide up front whether a custom domain absorbs that once and for all.
   Constraint on candidates: the name must survive the scope change — it should describe
   *Portuguese public statistics made reachable*, not *a wrapper around PORDATA*.

19. **Recover the period, and the units portugal is missing** *(spikes A3 and A4 run
   2026-08-23/24; reports in `data/spikes/`)*.

   **The unit half is solved and already shipped.** The chart caption is present in 7 of 7
   sampled pages including portugal, so its 0% was a missing marker, not a missing template.
   `"ampliado"` added to `MARKER_WORDS` fixes it at **zero extra requests** — units accrue as
   pages go stale. A forced re-harvest would complete it in one pass; that is item 21.

   **The period needs three extractors, one per area** (A4 + A6, both 2026-08-24). `portugal`
   carries `div.YearCurrentText` / `div.YearOtherText` (first and last, as named elements — the
   cleanest of the three); `municipios` uses a `<select>` year picker, 17–18
   `<option value="YYYY">` per page; `europa` has neither, and is the one still unspecified.
   The catch: `marker_windows` runs on *stripped* text, so the tags carrying that structure are
   gone before a window is cut. The period therefore needs a parse against unstripped HTML at
   harvest time plus a fetch to populate — **it belongs to item 21**, and it is the second field
   found after the harvest that could have been captured during it.

   **Geography is not in PORDATA's markup** (2 selects, 19 options — not the ~308 a município
   list needs) and does not need to be: INE's `geo_lastlevel` states it directly, so it comes
   with item 14.

   *Corrected 2026-08-24:* A3 reported `A carregar conteúdo…` appearing **0 times** and I
   recorded the client-rendering hypothesis as killed. Spike A6 found it — `div.Text_Note`.
   A3 searched for the literal string in entity-encoded HTML while A6 decodes entities, so
   A3's zero was a false negative, not evidence. The conclusion still holds for the **main
   table** (42 `td.ValueCell` and 16 `td.YearCell` are server-rendered on the sampled page),
   but there *is* a lazily-loaded section, and the binary framing was wrong.
20. **Raise the coverage line past 78.4%** *(owner ask 2026-08-23; unblocked by 19)*. 475 rows
   (21.6%) carry neither a breakdown nor a unit, and **471 of the 475 are `portugal`** — 3 are
   europa, 1 is municipios. Spike A3 established the cause and the fix landed the same evening
   (item 19): the caption marker is in place, so the gap closes as pages are re-fetched.
   Expected end state once every portugal page has been fetched again: uncovered falls from
   475 to roughly **4 rows**, and the coverage line goes from 78.4% to ~99.8%.

   **Do not treat that as done until re-measured.** The projection assumes portugal behaves
   like europa and municipios, which the 7-page sample supports but does not prove across
   1,053 pages. `breakdown_ratio` and `unit_ratio` are already gated per area, and
   `unit_ratio[portugal]` sits at a floor of **0.0 recording this known gap** — raising it is
   the signal that 20 is genuinely done, and a test asserts the 0.0 is deliberate so raising
   it must be a decision rather than a drift.

   What remains after that is real tail, with two further levers in order of value: (a) the
   **period** from item 19, which turns the line into
   `1960–2024 · 308 municípios · total e por sexo` and applies to rows with no breakdown at
   all; (b) the 158 rows whose colon tail the splitter deliberately refused — not a defect,
   since refusing is correct where the tail is the indicator, but some could carry a second
   line derived differently.


21. **One full re-harvest, deliberately** *(owner ask 2026-08-23; last item on the board on
   purpose)*. Nothing is blocked on this — item 19's marker fix means units accrue for free as
   pages go stale. It is here because **the harvester now captures things it did not capture
   when those 2,195 pages were fetched**, and the stored records are frozen at whatever the
   parser understood in August 2026. Raw HTML is not kept (`bytes` is recorded, the body is
   not), so every field added after the fact needs the pages fetched again.

   **The known-missing list, as of 2026-08-24** — this is what 21 exists to collect, and the
   parser must be widened to capture it *before* 21 runs, not after:

   | field | where it lives | coverage |
   |---|---|---|
   | unit | chart caption, `ampliado` marker | shipped; accrues as pages go stale |
   | **question** | `<h2>` | **15/15 sampled pages, every fingerprint** |
   | **revision note** | `revis` marker window | 215 pages |
   | period (portugal) | `div.YearCurrentText` / `div.YearOtherText` | 5/5 portugal pages |
   | period (municipios) | `<select>` year picker, `<option value>` | A4, 3/3 pages |
   | period (europa) | **unknown** | neither mechanism present |

   Known already-missed, and the reason to expect more: `"ampliado"` was added to
   `MARKER_WORDS` after the harvest, so 1,053 portugal records carry no unit. Whatever items
   14 and 15 need from the page — the period, geographic granularity, a chart caption, a
   footnote, a definition — will be discovered the same way, *after* the last harvest that
   could have captured it.

   So the sequencing matters more than the run: **do not fire this the moment it is possible.**
   Its value is proportional to how much the parser has learned since the last pass, and the
   detail pages (15) are what will teach it the most. Fire it when the answer to "what else
   should we be pulling off these pages?" has stopped changing — most likely once 15's design
   is settled and item 19's municipios probe has said where the period lives. Firing early
   means doing it twice.

   Cost and shape when it does run: 2,195 pages at the polite 20 s pace is ~12 h, which the
   harvester already handles in resumable 4.5 h chunks, so it is three dispatches rather than
   one long job. Force it by clearing the freshness check rather than by deleting records — a
   failed re-fetch must keep the good record it already has, which is the data-loss bug the
   2026-08-23 audit found and fixed. Re-measure `breakdown_ratio` and `unit_ratio` per area
   afterwards and raise the floors, `unit_ratio[portugal]` first: that floor sitting at 0.0 is
   the marker for this whole thread being finished.

22. **Characterise INE's availability window** *(armed 2026-08-24; gates nothing, but item 14
   is guesswork without it)*. The owner asked whether INE lowers capacity at weekends. The
   attempt log says no: the catalogue was served **twice on a Saturday morning** and only began
   failing after a third and fourth 21 MB pull inside 45 minutes. But a simple cooldown does not
   fit either — a 22.6 h gap failed while an 11.3 h gap succeeded — and with n=7, every attempt
   confounded by the ones before it, the honest position is **we do not know**.

   Running: `ine-availability.yml`, cron `45 9 * * *` = 09:45 UTC = **10:45 Lisbon** on WEST.
   One `HEAD` a day (2 KB `Range` fallback), appended to `data/ine/availability.csv`, which is
   seeded with the seven attempts above as `full-pull` rows so analysis starts from real
   history. Deliberately not a catalogue pull — re-pulling 21 MB to test availability is what
   caused the block.

   Guards, since this is scheduled against someone else's infrastructure: `START_DATE`
   2026-08-25 (a probe hours behind the 24th's full pull would inherit the same confound), one
   sample per day, and `MAX_SAMPLES` 21 after which it **retires itself** — then record the
   finding here and delete the workflow. **No back-off on failure**, reversing this item's first
   draft: at one request a day, a block is exactly when the measurement matters, and skipping it
   would hide the recovery being observed.

   Read it with `python3 scripts/probe_ine_availability.py --summary`. Caveat to apply at the
   end: 21 days is only ~3 of each weekday — enough for a strong weekend effect, not a subtle
   one. If it is ambiguous at day 21, say so rather than extending on autopilot; Lisbon leaves
   WEST in late October, which would silently shift the sampled hour.

23. **Sample by page template, not by area** *(owner correction 2026-08-24)*. Spike A6 was
   dispatched as a "full inventory" of one page per area. That was the wrong sampling frame,
   and the owner named it: *PORDATA's detail pages are not all the same, and we do not know how
   many variants exist.* Three pages is a sample; calling it an inventory hid the assumption
   rather than testing it.

   **The variant count is measurable offline, from records we already hold.** Every harvested
   record carries which marker keys matched and how big the page was — a structural fingerprint
   never used. Measured 2026-08-24, at zero request cost:

   - **9 distinct `(area, marker-key-set)` fingerprints**, not 3.
   - `Unidade` matched on **494** pages and not on ~1,700 — and it is a **false positive**,
     matching "Nomenclatura das **Unidade**s Territoriais" (NUTS), never a unit label. So the
     earlier note that "'Unidade' never appears in the page text" was wrong: it appears, and
     never means what the marker assumed.
   - `revis` matched on **215** pages (140 portugal, 71 municipios, 3 europa, 1 more) and holds
     a **revision note** — "Os valores foram revistos pela entidade oficial. (01/02/2024)".
     That is decision 5's revision caveat, which the project requires rendered *with* the
     series, and we capture none of it.
   - **municipios pages span 174 KB to 2.2 MB** — a 12× range within one area. A6 sampled a
     359 KB page and would never have seen whatever the 2.2 MB one is.

   Two fields were also found *in windows we already stored*, needing no fetch at all: a year
   run (127 records, e.g. 2005–2025) and **the question itself** on 14 records — "Onde há mais
   e menos empregadores a contribuir para a Segurança Social?", "Quantos empregadores ou
   trabalhadores domésticos descontam para a Segurança Social?". Only 14 because the windows
   are narrow slices around `Fontes`; the question usually falls outside them.

   **Done 2026-08-24.** `build_frame()` in `spike_page_inventory.py` derives the frame from
   `pages.jsonl`: the median page of each of the 9 fingerprints plus the smallest and largest
   of each area — 15 pages, deterministic, so re-runs stay comparable. A6 then ran against it
   (`data/spikes/a6-page-inventory.md`) and the frame paid for itself immediately:

   - **The question is universal**: present in `<h2>` on **15 of 15** pages, every fingerprint.
     It is the field to harvest.
   - **Its phrasing is area-specific**, which the old frame could never have shown:
     `portugal` asks *"Quantas / Quanto / Qual…"*, `municipios` asks *"Onde há mais e menos…"*,
     `europa` asks *"Que países…"*. The question encodes the geographic comparison mode, which
     makes it a better search and embedding input than the name — and hints that PORDATA's own
     curation is organised around a question form per area.
   - **The period elements are `portugal`-only**: `div.YearCurrentText`, `div.YearOtherText`
     and `td.YearCell` appear on **5 of 5** portugal pages and **0 of 10** europa and
     municipios pages. A frame of one page per area would have found them on its single
     portugal page and generalised them to the whole catalogue. With A4 (municipios uses a
     `<select>` year picker) that makes **three** distinct period mechanisms, one per area.

   The general rule this earns: **a probe's sampling frame must be derived from measured
   variation, never from a dimension that seems obvious** — area seemed obvious and was wrong.

24. **Widen the harvest parse before re-harvesting** *(precondition for 21; no new requests)*.
   A6 named three fields and their selectors. Capturing them is not another probe — it is a
   change to `harvest_catalogue.py` that makes **every future fetch pay for itself**, because
   the freshness loop already re-fetches pages as their sitemap `lastmod` moves.

   Add to `parse()`: the **question** from `<h2>`, the **revision note** from the `revis`
   window, and the **period** via the per-area mechanism (portugal's named year elements,
   municipios' `<option value>` picker; europa pending). Each needs a roadmap-6a shape
   assertion so a template change drops the value and raises `parse_warnings` rather than
   publishing junk, and a **per-area** QA floor (roadmap 23's lesson: a catalogue-wide mean
   hid a 100/100/0 split).

   **Why this beats sampling more pages.** A wider sample tells you about the pages you
   sampled; the parser plus the QA gate tells you about all 2,195, continuously, for free.
   Coverage climbing toward its expected ceiling *is* the validation, and a selector that
   fails on some template surfaces as a named `parse_warnings` breach in the area it broke —
   which is stronger evidence than any hand-picked frame can give.

   Sequence: widen the parse → let the freshness loop accrue and watch the per-area coverage →
   answer europa's period (one small probe, not a frame) → then fire 21 with a parser that is
   actually complete.

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
