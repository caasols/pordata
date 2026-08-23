---
updated: 2026-08-22
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
| `LICENSE` | MIT (code). Catalogue metadata is CC BY 4.0 with PORDATA/FFMS attribution, per README |
| `scripts/` | Python package: sitemap watcher, harvester, catalogue build, QA, featured sets, spikes |
| `tests/` | 40 unittest cases, 85% coverage; mutation-tested via mutmut (`setup.cfg`) |
| `.github/workflows/` | sitemap watch (daily), catalogue harvest (3×/day), tests+mutation (per push), featured sets + INE snapshot (dispatch) |
| `data/` | Committed pipeline state: sitemap snapshots, `catalogue/pages.jsonl`, CHANGELOG, QA, spike reports |
| `docs/` | The GitHub Pages site: `index.html` (search UI) + `data/` (catalogue.json/csv/stats — the static "API") |
| `ledger/` | Question Ledger: 100 demand-side questions plus protocol |
| `outreach/` | Record of external contacts. Holds the FFMS email as sent |
| `graphify-out/` | Derived code graph, gitignored |

## What has been built (2026-08-21 → 2026-08-22)

The pipeline, end to end, all live on `main`:

- **Sitemap watcher** (`sitemap.yml`, daily 06:17 UTC): fetches PORDATA's sitemap, diffs URLs
  and `<lastmod>` against the committed snapshot, writes `data/CHANGELOG.md`, opens a GitHub
  issue when indicator pages are added or removed. Landing-page lastmod churn is filtered out.
- **Catalogue harvester** (`harvest.yml`, cron 01:45/09:45/17:45 UTC): 2,196 indicator pages
  (quadro+resumo excluded), one request per 20 s, resumable 4.5 h chunks, metadata only —
  name, description, Fontes/Entidades, última atualização, JSON-LD, marker excerpts for
  offline re-parsing. **Freshness is built in**: each run also fetches pages new to the
  sitemap, re-fetches pages whose lastmod moved past `harvested_at`, and retries errors;
  removed pages are tombstoned at build time, never deleted. The cron therefore stays enabled
  permanently as the maintenance loop.
- **Published catalogue + search site** (Phase C, live): `build_catalogue.py` renders
  `pages.jsonl` into `docs/data/catalogue.json` / `.csv` / `stats.json`; `docs/index.html` is
  a zero-dependency search page — ranked fuzzy matching (substring > prefix > bounded edit
  distance), key-based i18n in six languages (PT/EN/ES/FR/DE/IT), `name_en` on every row
  derived free from the `/en` sitemap slugs (EN pages share ids with PT), featured and
  "descontinuado" badges, PORDATA credited prominently, every hit linking to its PORDATA
  page. Rebuilt and redeployed automatically after every harvest chunk. Repo made public and
  Pages enabled 2026-08-22.
- **Featured sets** (3c): quadro-resumo rows are OutSystems postbacks with no ids, but names
  are server-rendered; `fetch_featured_sets.py` extracts them (subtitle-aware) and the build
  matches them to catalogue entries by token containment. Confirmed: the municipal quadro set
  is exactly 37 indicators, identical across concelhos; Europa's is 56. Retratos pages are
  e-book publications with no indicator list — no signal there.
- **Quality**: 40 unit tests (85% line coverage, `--fail-under=80` CI gate) plus full
  mutation testing on every push (~1,670 mutants in ~1 min; baseline 946 killed / 505
  survived / 217 uncovered). Network fetchers are validated by their live runs instead.
- **Question Ledger**: 100 questions drafted blind, stratification-audited against the real
  slug list (every theme backed; the control question correctly unanswerable).
- **Spikes** (Phase A, both decisive): PORDATA indicator metadata is server-rendered (plain
  HTTP suffices); INE's full catalogue is enumerable (`xml_indic.jsp?opc=2`, ~21 MB XML with
  themes; per-indicator metadata and data via JSON, no auth) — but INE's bot protection 403s
  repeat pulls from cloud IPs, so the catalogue must be fetched rarely and cached.
- **FFMS emailed** 2026-08-21 (text in `outreach/`), disclosing exactly this plan and asking:
  API planned? catalogue shareable / polite harvest acceptable? open to a conversation?

Operational lessons recorded the hard way: GitHub schedules only fire from the default
branch; a queued run in a concurrency group is replaced by the next queued run; checkouts
default to the trigger-time sha, so data-writing workflows must check out the branch ref at
run time (fixed 2026-08-22 after one duplicated chunk).

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
municipal jump against 2026-08-18; municipal indicators with lastmod number 506, matching the
earlier 504), 260 subtema and 48 tema taxonomy pages, and 29 retratos. Portugal 1,055 and Europe
666 indicator pages (was 1,054 / 638). The per-municipality quadros resumo are further evidence
for the central insight: hand-built joins, one per concelho.

| Fact | Value | How established |
|---|---|---|
| Public API | None | No developer or API route in the sitemap; not listed as having an API in either community aggregator |
| Total URLs in sitemap | 5,907 | `PordataSitemap.aspx`, 846 KB |
| Portuguese-language URLs | 2,940 | Excluding the `/en` tree |
| Indicator pages (PT) | 2,268 | 1,054 Portugal, 638 Europe, 504 municipal, plus 29 Retratos, 17 ODS, 15 comunicação, 11 publicações |
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

What only PORDATA has is the map: 2,268 human-meaningful indicator definitions, organised by
theme, harmonised across 65 years and 308 municipalities, each attributed to its source. That
curation is what makes a question answerable, and no upstream API provides it.

Supporting evidence that this is the real gap: PORDATA hand-builds Retratos and quadros resumo,
which are pre-assembled joins across indicators. Products built as workarounds are strong evidence
of a need users cannot meet themselves.

## The problem, stated properly

Four failure modes, all four live simultaneously:

1. **Discovery.** With 2,268 indicators under a statistical taxonomy, you cannot tell whether what
   you want exists. You must already know the thing is called "Índice de envelhecimento" to ask
   "is my town getting older?". *Addressed by the live catalogue + search site.*
2. **Extraction.** Once found, getting numbers out is manual and per-indicator, one spreadsheet at
   a time, laid out for eyes rather than machines, with no API and exports disallowed by
   `robots.txt`. *Partially addressed: the catalogue points to sources; the crosswalk (roadmap 3)
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
| PORDATA | 2,268 curated indicators | **No** (this project's catalogue is the machine-readable index of it) |

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

## Constraints

- Do not redistribute PORDATA's data values.
- Catalogue metadata is the defensible line. Indicator pages are permitted by `robots.txt`; only
  Export, Popup and PDF paths are disallowed. Any harvest should be politely rate-limited and
  should credit PORDATA prominently.
- INE tolerates sparse requests only from cloud IPs: cache its catalogue, retry later not harder.
- Interpretation errors are the real danger, not missing features.

## Roadmap

Only open work. History lives in "What has been built" and git.

1. **Finish the initial harvest** *(self-completing overnight 2026-08-22→23)*: the 17:45 UTC
   chunk lands ~1,500 records; the 01:45 run completes 2,196/2,196. Then the same cron becomes
   pure maintenance (freshness re-fetches, new/removed indicators). Verify at the 10:00 UTC
   check-in.
2. **QA repair pass (3d remainder)**: fix the ~10 pre-parser-fix `fontes` records offline from
   `marker_windows`, fix 2 empty names, spot-check ~20 records against live pages. Re-dispatch
   `featured-sets.yml` once so municipal matching runs against the full pool (was 7/37 on an
   11%-harvested pool; Europa 29/56 — investigate the unmatched names while at it).
3. **INE catalogue snapshot, then the crosswalk (3e)** — the gateway to Extraction and Phase D.
   Re-dispatch `ine-catalogue.yml` after a cool-down; cache `data/ine/indicators.csv`. Then
   match each catalogue entry to its upstream series: name-match against INE's catalogue for
   INE-sourced indicators, Eurostat dataset codes for `europa`, BPstat for monetary. Store
   match + confidence; unmatched entries stay honest with `crosswalk: null`.
4. **Attempt the ledger questions** (owner, browser, spare moments): 100 questions in
   `ledger/questions.csv` per `ledger/README.md`. The evidence base for what to build next and
   the acceptance tests for everything built so far.
5. **FFMS follow-up** if no reply by ~2026-09-04 (email sent 2026-08-21; see `outreach/`). Any
   reply may redirect items 3 and 6.
6. **Phase D: MCP server over the catalogue** *(gated on owner go + crosswalk)*. Discovery
   tools first — search the catalogue, return metadata + PORDATA link + upstream source:
   pointers, not numbers, so nothing can be hallucinated. Values from upstream only where the
   crosswalk is confident, each answer carrying source/vintage/caveats per decision 5.
   `@openar/mcp` is the shape precedent.
   **Semantic search design (decided 2026-08-23):** embeddings, no vector database — at
   2,196 entries brute-force cosine is ~1 ms anywhere. Pipeline step embeds each
   indicator's PT+EN names (+description) with a small **multilingual** model
   (multilingual-E5-small class, quantized) and ships the vectors as a static file next to
   `catalogue.json` (~2,196 × 384 dims int8 < 1 MB), refreshed by the harvest loop.
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
7. **Quality follow-ups**: drive the mutation kill rate up from 65% and turn it into a CI gate;
   deferred — harvesting the `/en` tree (~2,196 pages) if EN descriptions become worth having.
8. **Name/i18n coverage review** *(owner ask 2026-08-23)*. `docs/data/names-map.csv`
   (rebuilt on every harvest) maps each indicator's PT name to its EN name and flags gaps:
   `missing_pt` (harvest found no name — the 2 known empties), `missing_en` (no `/en`
   sitemap slug for the id), counts in `stats.json` under `names`. After the harvest
   completes: review flagged rows and repair. Separately, the site's language selector now
   lists all 24 EU official languages with only PT/EN selectable; enable others
   progressively by translating the `STRINGS` block (ES/FR/DE/IT UI strings already exist
   in the file, greyed pending the content-language decision) and adding the code to
   `AVAILABLE`.

## Verification

```bash
python3 -m unittest discover -s tests            # 40 tests
python3 -m mutmut run                            # mutation suite (~1 min)
python3 scripts/build_catalogue.py               # rebuild docs/data from pages.jsonl
curl -s https://caasols.github.io/pordata/data/stats.json
curl -s https://www.pordata.pt/robots.txt
python3 ~/.claude/skills/cartographer/scripts/audit.py . --style-lint
```
