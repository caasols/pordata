---
updated: 2026-08-21
---

# pordata: context

## What this is

A project to make Portuguese public statistics actually consumable. PORDATA is the country's main
free statistics database and is genuinely good at one thing: presenting a single indicator,
attractively, to someone who already knows what they are looking for. Everything here is about
what happens when that condition does not hold.

**Current phase: problem definition.** No solution has been chosen and that is deliberate. See
Decisions.

## Architecture and inventory

There is no code yet. The repo holds research only.

| Path | What it is |
|---|---|
| `CLAUDE.md` | The map. Ranked pointers, current focus |
| `context.md` | This file. All project state: findings, decisions, backlog |
| `README.md` | Human front door. Brief overview, cross-links here for all state |
| `.gitignore` | Standard Python, Node and OS patterns plus `graphify-out/` |
| `outreach/` | Record of external contacts. Holds the FFMS email as sent |
| `ledger/` | Question Ledger: 100 demand-side questions plus protocol. See backlog item 2 |
| `scripts/` | `fetch_sitemap.py`, one polite request, writes `data/sitemap-urls.txt` for diffing |
| `data/` | Fetched artifacts, committed for git-diff change tracking. Holds the sitemap snapshot |
| `.github/workflows/` | `sitemap.yml`: Actions runner fetches the sitemap and commits the snapshot |
| `graphify-out/` | Derived code graph, gitignored. Currently indexes only these docs' headings |

When code arrives, the shape implied by the decisions below is: a harvester producing an indicator
**catalogue** (metadata only), and a resolver that maps a catalogue entry to an upstream open API
series. Neither exists.

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
| English duplicates | 2,967 URLs | Under `/en` |
| Platform | OutSystems | `OSFillParent` and `OSInline` classes in the markup |
| Query tool | Server-side postbacks | `/db/ambiente+de+consulta/nova+consulta` holds no JSON, XHR or REST endpoint. Only jQuery and DataTables |
| Machine-readable path | Blocked | `robots.txt` disallows `/*Export*.aspx`, `/*Popup.aspx`, `/*PDF_*.aspx` |
| Source attribution | On every indicator page | Sampled page states `Fontes/Entidades: INE, PORDATA` |
| Freshness metadata | Present | Same page: `Última actualização: 2026-06-22`, plus a note that 2021 to 2024 values were revised by INE |
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
   "is my town getting older?".
2. **Extraction.** Once found, getting numbers out is manual and per-indicator, one spreadsheet at
   a time, laid out for eyes rather than machines, with no API and exports disallowed by
   `robots.txt`.
3. **Combination.** Nothing joins. Two indicators, or two geographies, or an indicator against a
   time window means downloading separately and aligning by hand. Every genuine question, such as
   whether wages track housing prices per municipality, is blocked.
4. **Interpretation.** Even holding the numbers, a person cannot tell what is normal, notable or
   fairly comparable. A figure without a baseline, a peer group, or a caveat about a revision or
   definition change is close to useless and can mislead.

These are not four problems. They are four stages of one pipeline: find the indicator, get its
numbers out, combine it with something, know what it means. If any stage is broken the whole path
from question to answer is broken. **Fixing one stage deeply produces nothing usable; a thin slice
through all four beats a deep fix to any one.**

## Ecosystem

| Source | What it offers | API |
|---|---|---|
| INE (Statistics Portugal) | The primary source behind most PORDATA tables | Yes, JSON, no auth |
| Eurostat | The European comparisons PORDATA republishes | Yes, REST dissemination API |
| Banco de Portugal (BPstat) | Monetary, financial, macro series | Yes, with an OpenAPI spec |
| dados.gov.pt | National open-data portal, CKAN-style | Yes, API key for writes only |
| api.ptdata.org | Community aggregator: geography, weather, public contracts, civil protection, transport, health, aviation, fiscal, plus a few macro indicators | Yes, `/v1/*` |
| api.openar.pt | Parliamentary data. Different domain, but the best available model of the shape PORDATA lacks. MIT, no auth, OpenAPI spec, ETags, incremental sync | Yes |
| PORDATA | 2,268 curated indicators | **No** |

`api.ptdata.org` is broad but its economic coverage is a handful of macro series; it carries
neither INE's statistical database nor PORDATA's indicator catalogue. Nobody has built the layer
that takes a plain-language question about Portugal and returns the right series with its source.
That is the hole.

## Decisions and why

Recorded so they are not re-litigated. Each carries what it costs if it turns out wrong.

1. **Do not redistribute PORDATA's data values. Harvest catalogue metadata only; serve values from
   upstream.** Why: the legal terms forbid redistribution, and INE and Eurostat make it
   unnecessary. A catalogue of facts *about* PORDATA's holdings is a different legal object from a
   copy of its content. Cost if wrong: if FFMS objects even to metadata harvesting, the catalogue
   plan needs their cooperation instead, which is why the email is backlog item 1.
2. **Problem first, solution later.** Why: the owner's explicit call, and all four pipeline stages
   are broken, so committing early risks fixing one stage and shipping something unusable. Cost if
   wrong: a week spent diagnosing rather than building, leaving no artifact.
3. **Do not go straight to an MCP server, however tempting.** Why: without the crosswalk a model
   guesses at series identity, and it will guess confidently and wrongly. For public statistics
   that is the worst available failure mode, because a plausible wrong number gets repeated. It
   also leaves Interpretation entirely unaddressed. Cost if wrong: a slower path to a demo.
4. **Treat openAR as the template.** Why: one volunteer wrapped a government data programme in a
   clean API with an OpenAPI spec, weak ETags, `updated_since` incremental sync and a 100 rpm
   limit, then shipped a web frontend and an MCP server on top. It proves the scope is achievable
   solo. Cost if wrong: little; it is a reference, not a dependency.
5. **Any answer must carry its source, its vintage, and any revision caveat.** Why: the sampled
   page's note about INE revising 2021 to 2024 is exactly the kind of thing that must not be
   silently dropped. Cost if wrong: none, this is a floor not a bet.
6. **Proceed without waiting for FFMS (owner decision, 2026-08-22).** The email disclosed
   exactly this plan, the reply can still redirect later, and the harvest stays on the
   recorded legal line (metadata only). Phased: **A** spikes (is PORDATA metadata
   server-rendered; is INE's catalogue enumerable) → **B** catalogue harvest → **C** static
   catalogue + search on GitHub Pages → **D** MCP server over the catalogue,
   discovery/pointers first, values from upstream only where the crosswalk is solid. Phases B
   onward start only on explicit owner go. Harvest pacing set by owner at one request per 20
   seconds; at 2,533 pages that is ~14 hours, over the 6-hour Actions job cap, so the
   harvester must be resumable and chunked across runs. Cost if wrong: if FFMS replies with
   objections, harvested metadata may need renegotiating or discarding.

## Constraints

- Do not redistribute PORDATA's data values.
- Catalogue metadata is the defensible line. Indicator pages are permitted by `robots.txt`; only
  Export, Popup and PDF paths are disallowed. Any harvest should be politely rate-limited and
  should credit PORDATA prominently.
- Interpretation errors are the real danger, not missing features.

## Backlog

Open items only. Verify against reality before acting; strike items when they land.

1. ~~**Email FFMS.**~~ **Sent 2026-08-21** (text in `outreach/2026-08-21-ffms-email.md`). Asked
   the three questions: is an API or open catalogue planned; would FFMS share the catalogue
   metadata or accept a polite automated harvest of the public indicator pages; openness to a
   conversation. **Awaiting reply.** If nothing by ~2026-09-04, send a short follow-up or try the
   press/communication contact instead. A reply to any of the three questions redirects backlog
   items 3 and 4 before they are acted on.
2. **Write the Question Ledger.** *Questions drafted 2026-08-21*: 100 of them (expanded from
   30-50 by owner decision), written blind with no sitemap or catalogue consulted, in
   `ledger/questions.csv` with the protocol in `ledger/README.md`. Stratification audited
   2026-08-21 against the sitemap slugs: every theme has real indicator backing (52 to 323
   matching slugs per theme); the deliberately-unanswerable control question (Q098, pets) has
   none, as intended. Still open: attempt each question with today's tools, recording which of
   the four stages broke and how long it took. Converts an opinion into evidence and tells you
   what deserves building.
2a. ~~**Run the sitemap fetch.**~~ **Done 2026-08-21 and upgraded to a full watcher the same
   day**, via GitHub Actions (`.github/workflows/sitemap.yml`) because neither the remote
   sandbox nor a phone could reach pordata.pt. Each run fetches the sitemap (one request),
   diffs URLs and `<lastmod>` against the last committed snapshot
   (`scripts/diff_sitemap.py`), commits the snapshot plus a `data/CHANGELOG.md` entry, and
   opens a GitHub issue when pages are added or removed. Merged to main 2026-08-22, so the
   daily cron (06:17 UTC) is armed. First production run caught 7 lastmod updates; they were
   daily churn on section landing pages, so update reporting is now limited to
   indicator-style URLs (slug ending in an id). Adds and removes are still tracked for every
   page.
3. ~~**Spike: is INE's catalogue queryable?**~~ **Done 2026-08-22, answer: yes.** Phase A
   spikes ran via `.github/workflows/spikes.yml`, reports in `data/spikes/`:
   - **A1 (PORDATA pages): metadata is server-rendered.** All three sampled areas return
     full HTML over plain HTTP with Fontes/Entidades, atualização dates and the data tables
     present; no screenservices calls. The Phase B harvester needs no headless browser.
   - **A2 (INE): the catalogue is enumerable.** `xml_indic.jsp?opc=2&lang=PT` returns the
     full indicator catalogue as one ~21 MB XML with per-indicator theme and subtheme;
     `pindicaMeta.jsp?varcd=` gives per-indicator metadata (periodicity, first/last period)
     and `pindica.jsp?op=2&varcd=` the data, both JSON, no auth. The xportal docs page 403s
     non-browser clients, but the API endpoints themselves are open. Much of the
     PORDATA→INE crosswalk can therefore be built against a real INE catalogue instead of
     guessed. **Caveat:** a second run 15 minutes later got 403 on every ine.pt endpoint —
     bot protection reacting to the 21 MB pull from a cloud IP. So: fetch the INE catalogue
     rarely, cache it in the repo, keep requests sparse, retry later not harder.
3b. **Phase B: catalogue harvest.** *Started 2026-08-22 on owner go.*
   `scripts/harvest_catalogue.py` via `.github/workflows/harvest.yml`: 2,196 target
   indicator pages (quadro+resumo excluded), one request per 20 s, resumable 4.5 h chunks,
   cron every 8 h until complete (~3 runs), then disable the cron. Output
   `data/catalogue/pages.jsonl` (metadata + marker excerpts, never data values) and a
   coverage REPORT.md. `scripts/fetch_ine_catalogue.py` via `ine-catalogue.yml`
   (dispatch-only) caches the INE catalogue as `data/ine/catalogue.xml.gz` +
   `indicators.csv` for the crosswalk.
3c. **Extract featured-indicator sets.** *Scaffolded 2026-08-22*: `scripts/fetch_featured_sets.py`
   via `.github/workflows/featured-sets.yml` (dispatch-only, 4 requests) fetches two
   quadro+resumo pages + two Retratos, records the indicator ids each references in
   `data/catalogue/featured.json`, and `build_catalogue.py` merges them as `featured` flags.
   Captures PORDATA's editorial "what summarizes a place" curation without harvesting 308
   near-identical pages or any data values.
3d. **Harvest QA pass.** *Tooling built 2026-08-22*: `scripts/qa_catalogue.py` runs after every
   harvest chunk and writes `data/catalogue/QA.md` (coverage per area, over-capture detection,
   error records, what is recoverable offline from `marker_windows`). Still open after
   completion: repair the ~10 pre-parser-fix records' `fontes` in pages.jsonl offline (the
   published catalogue already re-trims them defensively at build time), fix 2 empty names,
   and spot-check ~20 records against live pages.
3e. **Build the PORDATA→upstream crosswalk.** Needs 3d and the INE catalogue cache
   (`data/ine/indicators.csv`, fetch pending INE unblocking). Match each catalogue entry to its
   upstream series: exact/fuzzy name match against INE's catalogue for INE-sourced indicators;
   Eurostat dataset codes for `europa` entries (fontes says Eurostat); Banco de Portugal via
   BPstat for monetary series. Store match + confidence in the catalogue; unmatched entries
   stay honest with `crosswalk: null`. This is the artifact that makes Phase D (values via MCP)
   safe.
3f. ~~**Keep the catalogue fresh: one signal chain, three change types.**~~ **Implemented
   2026-08-22.** The pipeline watcher → committed snapshot → harvest cron handles all three
   without a new job: **new** indicators land in `sitemap-urls.txt` and the next harvest run
   fetches them (keep the harvest cron enabled after completion); **updated** pages are
   detected in `harvest_catalogue.py` (`<lastmod>` newer than the record's `harvested_at` →
   re-fetch replaces the record; error records are retried the same way); **removed** pages
   are tombstoned at build time (`build_catalogue.py` sets `removed: true` for records no
   longer in the target list, shown as "descontinuado" on the site; records are never
   deleted).
3g. **Phase C scaffolded (2026-08-22): static catalogue + search site.**
   `scripts/build_catalogue.py` turns pages.jsonl into `docs/data/catalogue.json` + `.csv` +
   `stats.json` (the static "API"); `docs/index.html` is a zero-dependency PT search page
   (accent-insensitive, area filters, featured/discontinued badges, PORDATA credited
   prominently, links every hit back to its PORDATA page). Both rebuild automatically in every
   harvest-chunk run. **Open: enable GitHub Pages** (repo Settings → Pages → Deploy from a
   branch → `main`, folder `/docs`) — an owner action, one time; the site then lives at
   `https://caasols.github.io/pordata/`.
4. **Then decide direction.** Candidates, recorded so they are not re-derived: the **catalogue**
   (harvest indicator metadata, publish as open JSON and CSV with search; fixes Discovery, measures
   the rest, and is the crosswalk any real tool needs); an **MCP server or skill** over INE and
   Eurostat grounded in the catalogue (note `@openar/mcp` exists as a precedent for shape and
   scope); a **consumer site** (type a question, get a chart plus its source: broadest reach, most
   work, hardest from a phone); **data stories** (most immediately satisfying, leaves no reusable
   tool behind).
5. ~~**Replace `.gitignore`.**~~ **Done 2026-08-21.** AL / Dynamics template block removed;
   now standard Python, Node and OS patterns plus `graphify-out/`. Python assumed as the likely
   implementation language; revisit if that changes.
6. ~~**Write README.md.**~~ **Done 2026-08-21.** Overview plus status, cross-linking here for
   all state.

## Verification

```bash
curl -s https://www.pordata.pt/robots.txt
curl -s https://www.pordata.pt/PordataSitemap.aspx | grep -c '<loc>'
curl -s "https://www.ine.pt/xportal/xmain?xpid=INE&xpgid=ine_api"
curl -s https://api.ptdata.org/v1/economy/exchange-rates | head -c 300
python3 ~/.claude/skills/cartographer/scripts/audit.py . --style-lint
```
