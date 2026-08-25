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

## What has been built (2026-08-21 → 2026-08-25)

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
  testing on every push, gated at a 58% kill-rate floor by `scripts/mutation_gate.py`. The
  CI configuration is itself under test (`tests/test_workflows.py`). Network fetchers are
  validated by their live runs instead. Rates and counts are measured by the suites, never
  quoted here — the previous "~65%" here was asserted, and measured at 55.9% when someone
  finally checked (decision 7).
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
  no values exist until roadmap 14 and PORDATA's are never redistributed. **Since item 15 the
  click opens this project's own page**, not pordata.pt; the click-out moved to the detail
  page, beside the chart slot it will eventually replace.
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
- **Three more fields found and captured** (spikes A3–A6 and roadmap 19/23/24, 2026-08-24).
  The **unit** was never missing from portugal's template, only from our markers: `"ampliado"`
  now anchors the chart caption, at zero extra requests. The **question** PORDATA writes under
  every title — present in `<h2>` on 15/15 sampled pages, and phrased per area (`portugal`
  "Quantas…", `municipios` "Onde há mais e menos…", `europa` "Que países…") — is captured at
  harvest time, as is the **period**, whose mechanism differs by area (portugal names the first
  and last year in their own elements; municipios uses a `<select>` picker; europa does
  neither and stays honestly empty). The **revision note** needed no fetch at all: it was
  already sitting in the `revis` marker windows, and 203 rows now carry decision 5's caveat.
  Two false-positive classes had to be excluded, both real Portuguese: "imp**revis**ta"
  contains the stem, and "**revistas**" means magazines.
- **How the probing itself was corrected.** A6 first sampled one page per area and called it an
  inventory; the owner pointed out that PORDATA's pages are not all alike. The variant count
  was measurable offline from records already stored — **9 structural fingerprints**, and
  municipios pages spanning 174 KB to 2.2 MB — so the frame became one page per fingerprint
  plus each area's size extremes. It paid immediately: the period elements are `portugal`-only,
  and the old frame would have generalised them from its single portugal page to the whole
  catalogue. Three of my own false negatives were caught the same day (a literal string search
  against entity-encoded HTML, void elements unwinding a skip counter, and inline markup
  splitting a text node) — each looked like a finding about PORDATA and was a bug in a filter.
- **Test strength, and two bugs it surfaced** (roadmap 6c/6d/6e, 2026-08-24). The Python
  mutation kill rate was measured at **55.9%** — below the ~65% the roadmap claimed — and
  ungated. Boundary tests pinning every threshold constant from both sides, plus content
  (not prose) assertions on the report writers, took it to **62.5%**, and
  `scripts/mutation_gate.py` now enforces a floor the way StrykerJS does on the site.
  Coverage went 80% → 86%. The floor is 58%, not 62%: two runs of the same tree scored 64.1%
  and 62.5%, and a gate that flakes gets disabled. Writing those tests found a **live
  crash** — `extract_names` raised `IndexError` on any quadro page whose last two lines are a
  repeated name, because a length guard sat after an index access Python evaluates first.
  **Not every survivor is worth killing**, and the gate says so: `parse()`'s ~54 are
  equivalent mutants, and ~80% of the rest are markdown labels where asserting exact prose
  buys brittleness rather than correctness.
- **The freshness loop stopped losing same-day updates** (roadmap 6c). Staleness compared
  `lastmod > harvested_at`, both date-only, so an update published the day a page was
  harvested never re-fetched — and never would, since every later run compares the same two
  equal dates. `>=` was not the fix (it re-fetches those pages for ever); the harvester now
  stores the lastmod it saw and re-fetches when the value *changes*, exactly once. Records
  predating the field keep the old comparison deliberately, so the fix could not fire a full
  re-harvest by accident.
- **One definition of "indicator page"** (roadmap 6e). `diff_sitemap` used a looser copy — a
  numeric id and nothing else — so **3,661** URLs counted as indicator updates that the
  harvester never treats as indicators (2,944 `/en`, 337 quadro+resumo, 380 other), and the
  CHANGELOG over-reported roughly threefold. Now `lib.is_indicator_url`, shared.
- **A page per indicator** (roadmap 15, metadata half, 2026-08-24). Every card used to bounce
  to pordata.pt; now it opens a page this project owns, at a real URL —
  `/indicador/<area>/<id>/`, **2,195 of them pre-rendered**, each with its own `Dataset`
  JSON-LD and listed in `docs/sitemap-indicadores.xml`. Hash routing was the cheap option and
  the wrong one: a catalogue whose whole claim is machine discoverability cannot have 2,195
  indicators with no addresses. **No JavaScript bundle** — a metadata page is a document, not
  an app, so these are plain HTML against one shared stylesheet, ~4 KB and 2 KB gzipped
  against the SPA's 110 KB of bundle. The only script is nine lines restoring the reader's
  stored theme and language from the same `localStorage` keys the SPA writes.
  **What the page has that PORDATA's does not**: the revision note rendered *with* the
  indicator rather than in a footer (decision 5 — a caveat that does not travel with the
  series is a caveat nobody reads), and the crosswalk as **provenance** — the INE operation,
  its granularity and periodicity, and the candidate series each linked to both INE's page and
  its **JSON endpoint**, because an id you cannot fetch from is a footnote. A refusal renders
  as a first-class state that says the matcher looked and declined, never as an empty section.
  The chart stays inert and says why, with the click-out to PORDATA beside it.
  **Three things that make it maintainable.** Pages are written only when their bytes change,
  so a harvest touching five indicators commits five files instead of 2,195 — the whole set
  packs to 4.45 MiB in git. The colour tokens are read out of `site/src/index.css` at build
  time and the build **fails** if that block moves, rather than serving stale colours that
  look fine. And `--strict` asserts every published row has a page on disk, because every card
  now links here and a missing one is a 404 a visitor meets. Writing the tests found a real
  defect: the visible HTML was escaped and the **JSON-LD block was not**, so an indicator name
  containing `</script>` would have closed the element early and put the rest into the
  document as live markup.

  **It shipped looking like a different site, and the fix is the durable part** (owner caught
  it on a phone, 2026-08-24). The stylesheet had been hand-written from memory of the card
  rather than derived from the components the card uses, and it showed: the area badge was a
  primary-orange pill where the card's is a grey `secondary` Badge; the meta value rendered at
  the 16 px body size against an 11 px label where the card pairs 9.5 px with 12 px; the CTA
  was a **filled primary button on a site whose `button.tsx` has no filled variant at all**;
  the shadow, the radii and the theme-boot condition were each a guess a few points off. The
  worst of them was invisible in the CSS: **`"Public Sans"` was named in the font stack and
  never loaded**, because the SPA pulls it from Google Fonts in its own `<head>` — so the
  pages rendered in the system sans, and no amount of colour-matching would have closed the
  gap. Every value now comes from the component it mirrors, `theme_tokens()` lifts the radius
  scale and `--font-sans` alongside the colours, and seven `DesignSystemTest` cases assert
  against `badge.tsx`, `button.tsx`, `card.tsx`, `App.tsx` and the compiled bundle so a
  component variant changing fails the build. **The lesson generalises past CSS**: writing
  what looks right instead of reading what the component does produced the orange pill, and
  then produced the orange button one element along after the first fix.
- **PORDATA's category prefix, demoted** (roadmap 2, 2026-08-25). `REVIEW.md` earned its
  keep: a colon prefix turned out to be **6× over-represented among refusals** — 15.5% of the
  633, against 2.4% of matches — because PORDATA writes a category in front ("Cinema: nº de
  ecrãs", "SNS: hospitais gerais") where INE names the indicator alone, and full containment
  cannot forgive a word the title never had. **The trap is that a colon is not always a
  category**: "Densidade populacional: estatísticas por município" has the indicator in front
  and boilerplate behind. The two separate on a measured property rather than a guess — *a
  category repeats and an indicator does not*. 36 heads are shared by two or more rows (sns
  20, cinema 14, administrações públicas 13) and every one reads as a category; 45 appear once
  (abortos, dívida pública, óbitos infantis) and every one is the indicator itself. Same shape
  as `split_breakdown`, mirrored. The first version lost two rows it should have kept, both
  ending in `: total` — a tail with no content words is a breakdown, not an indicator, and
  `total` is already a stopword, so the phrase reduced to nothing to match on. With that
  guard: **206 → 212 matched, 6 gained, 0 lost**, and the category is stored as evidence.
- **Source organisations, normalised** (roadmap 8b, 2026-08-25). **159 source strings → 127
  organisations** on two mechanical rules: a trailing parenthetical carrying a year is a period
  qualifier ("INE (a partir de 2001)"), and a slash separates the body from its ministry — so
  "DGEEC/MECI" and "DGEEC/MEd" are one source under two cabinets, as are "GEP/MTSSS" and
  "GEP/MSESS". Only slashes *outside* parentheses count: three sources carry an acronym in
  brackets ("… (ETC/BD)", "… (ITF / OCDE)") and splitting those cuts the name in half, which
  the first version did. PORDATA is excluded — it cites itself on all 2,195 rows, so as a
  filter facet it separates nothing. Gated on coverage (99.4%) **and** on the distinct count
  (127, ceiling 140), the second because the collapsing rules failing silently would leave 159
  near-singleton facets. Payload 148.1 → 151.7 KB gzipped against a 250 ceiling.
  **Recency (8c) deliberately gets the opposite treatment** and `site/src/lib/recency.ts` says
  why: a bucket is relative to *now*, so one baked in at build time is wrong when the calendar
  turns, and the harvest only rebuilds rows whose records changed. Derived in the client, where
  it cannot rot; a missing date is a third state rather than a synonym for stale.
- **Where PORDATA is thin against INE** (roadmap 16, 2026-08-24). `data/coverage/INE-GAP.md`
  is a shortlist of **302 concepts** INE publishes and PORDATA never names once, ranked and
  grouped by theme with three distinct examples each, for the owner to accept or reject —
  which is what produces the curation rule. **The series-level complement is not computed, and
  saying so is the point.** The crosswalk names 1,062 of 13,084 INE ids (8.1%) because it
  refuses rather than guesses; subtracting that would present ~12,000 series as "missing from
  PORDATA" when most are indicators PORDATA covers under a name the matcher declines to claim
  — a number that would be enormous, precise and wrong. The unit is therefore the **concept**:
  a content word INE uses that none of PORDATA's 2,195 names uses. That question survives a
  matcher with a quarter of the recall, because it asks whether PORDATA has *any* indicator
  touching a subject. **Two measurements changed the design.** Ranking by *series* put "TDT"
  near the top — 54 series, one indicator republished across geographies — so the rank is
  distinct titles, which is INE's investment in the subject rather than how widely one title
  was cut. And single-token vocabulary overlap "reached" 90% of INE's catalogue, which is the
  saturated mirror of the 0-occurrence trap: PORDATA's 2,687 words are ordinary Portuguese
  statistical language, so *any* overlap proves nothing. Bookkeeping INE writes into its
  titles (vintages, `CAE Rev.3`, seasonal adjustment, survey reference periods) is filtered by
  an explicit list, and the report **prints that list and its cost** rather than presenting a
  cleaner result than the data supports — a filter nobody can see is a filter nobody can
  contest. Recomputed by `harvest.yml` and `ine-catalogue.yml` after the crosswalk.
- **A payload budget, gated** (roadmap 6f, 2026-08-24). A first visit downloads **261 KB
  gzipped** before it can search — 1.3 KB of page, 111.8 KB of bundle and 148.1 KB of
  catalogue — because the client holds everything and there is no search API. That is fine, and
  it is gated anyway at **400 KB first load / 250 KB catalogue** in `qa_catalogue.py --strict`,
  because *the thing that breaks a payload budget is never a mistake — it is a good idea*.
  Every field the crosswalk or the label system wants to add is defensible on its own, and none
  of them is weighed against the download until something weighs them. The measurement is
  transfer size, not disk: 1,430 KB of catalogue is 148 KB on the wire, so budgeting raw bytes
  would budget a number nobody downloads. An absent bundle reports *nothing* rather than a
  small number — a missing build must not read as a payload win. **The levers, measured, for
  when a ceiling breaks**: `url` is **25%** of the gzipped catalogue and is derivable from
  `area` + slug; `description` is another **12%** for a field the UI never renders — it exists
  only in the search haystack, and 96.3% of descriptions are PORDATA's SEO template, so it adds
  almost nothing there either. Neither is worth doing today; both are worth having already
  counted.
- **The INE crosswalk** (roadmap 2, 2026-08-24). `data/crosswalk/ine.json` routes
  **206 of the 839** in-scope PORDATA rows (INE-sourced, portugal/municipios) to a candidate
  family of INE series — 113 with an exact title inside the family, 93 by containment — and
  writes `null` for the other 633. **Coverage is not the goal.** The relation is one-to-many
  (spike A5), so each entry stores the candidate set, its true size, the INE operation and
  theme it sits in, the geographic levels and periodicities available, and the evidence that
  selected it; picking a series is deferred to fetch time (item 14). Median family 8;
  25 ids are stored and `n_candidates` keeps the true count. **Family size is never a reason to
  refuse** — "Agregados domésticos privados" ties 62 entries because INE publishes 62 of them,
  and refusing on size throws away the correct answer for being correct about a broad
  indicator. Four filters, each added after a specific wrong match: full containment (rare
  tokens alone let "Dimensão média das **empresas**" match "…das **famílias** clássicas"),
  the INE title's head must be a word PORDATA used ("População residente…" matched "**Tempo
  de acesso** a pé da população residente…"), derivation parity (a count is not a rate:
  "Água distribuída" matched "Água distribuída **por habitante**"), and negation parity
  ("alojamentos familiares **não** clássicos"). Two more the tests caught: the unit belongs to
  a *different* comparison from the derivation words — INE suffixes it into the title
  ("Taxa de desemprego (Série 2021 - %)") and PORDATA carries it in a field, so reading `%`
  out of the raw title refused "Taxa de desemprego" against itself; and numbers are content,
  because the two-character floor that filters prose noise also swallowed age brackets and let
  "…com **16 a 64** anos" match "…com menos de **15** anos". **Two things that looked like good ideas and
  were not:** PORDATA's `fontes` is bare "INE" with at most a period qualifier — it never
  names the survey, so INE's 366 operation strings offer no join; and INE theme *purity* as a
  refusal rule rejects exact matches, because INE files one series under two themes
  ("Corpos de bombeiros", "Poder de compra per capita"). Purity is reported, not enforced.
  Rebuilt by `harvest.yml` after the QA gate passes and by `ine-catalogue.yml` after a
  snapshot, gated at `--strict` with a floor of 170 matches. Refusals sampled for a human in
  `data/crosswalk/REVIEW.md`; reading it surfaced the unit defect above and a next lead —
  PORDATA's colon prefix ("Farmácias: número de estabelecimentos", "SNS: hospitais gerais"),
  which is a category label the way the breakdown clause was, and is untried.
  *(The colon prefix landed 2026-08-25: `category_heads` derives the repeating heads from the
  catalogue itself and `split_category` demotes them, 206 → 212 matched, 6 gained, 0 lost. A
  head only counts as a category when it repeats, and a tail with no content word is a
  breakdown rather than an indicator — the guard that stopped "População residente: total"
  becoming "total".)*
- **The Eurostat crosswalk** (roadmap 2, Eurostat half, 2026-08-25). `data/eurostat/
  datasets.csv` caches **7,572** datasets, `data/crosswalk/eurostat.json` routes **118 of 616**
  in-scope `europa` rows (35 exact, 37 single, 46 family), and the 118 now carry provenance on
  their detail pages. **The point of measuring first was that the shape is not INE's.** Eurostat
  publishes multi-dimensional *cubes*, not pre-sliced series, so a PORDATA row wants one dataset
  **plus a filter over its dimensions** — and INE's "family size is never a reason to refuse"
  reverses: these candidates are *rivals* of which one is right, so a large set is an open
  question, and the QA report says the opposite of INE's on purpose.

  The operator (`data/spikes/eurostat-crosswalk-shape.md`): strip PORDATA's unit parenthetical,
  split both sides at the `by` that opens the breakdown, require identical heads. Plain
  containment reaches 18.3% because it asks a cube's name to contain the words for its own
  dimensions — `percentage` blocked 35 rows and `euro` 23, which is the INE unit lesson at the
  opposite polarity (there PORDATA held the unit in a field and INE suffixed it into the title).

  **The breakdown is a veto, never a ranking.** Ranking on it picked a single winner on 10 of 83
  tied rows and one of the first eight sampled was *Employment by professional status —
  ENP-South countries*, a non-EU geography. As a veto it refuses 18 head matches and every
  hand-read one is correct: *Exports total and by type of energy product* is not *Exports by
  industry (FIGARO application)*; *expenditure by category* is not *by function (COFOG)*.
  A content-token floor on the head was the first idea and is recorded as **rejected with the
  number that rejected it** — it drops 38 matches including *Obesity rate by body mass index*,
  whose Eurostat title is identical. It measures length where the failure is contradiction.

  **`filter_resolved` is `false` on every entry**, and the detail page shows the wanted
  breakdown as unverified rather than omitting it. The catalogue has titles, not dimension
  names; item 14 resolves the filter against the real structure at fetch time or refuses.
  URLs are stored as codes against a template measured across all 7,572 rows and asserted on
  every build — 184 KB → 106 KB, and a build failure rather than dead links the day the
  pattern changes.

  **The bug worth not re-learning: the TOC is a tree, and a dataset hangs off up to eight
  branches of it.** The first parse emitted a row per appearance — 10,313 rows for 7,572
  datasets — and every candidate count derived from it was multiplied by how many themes the
  dataset happened to sit under. Fixing it moved the measured median candidate count from 3 to
  **1** and resolves-to-one from 36 to 57, i.e. it was hiding the one thing the analysis
  existed to see. This is INE's theme lesson from the other direction: there, theme *purity*
  rejected correct matches; here, theme *multiplicity* inflated the counts. An upstream theme
  tree is a set of views, not a partition.
- **The 2026-08-25 audit, applied** (`data/audits/2026-08-25-mega-audit.md`). Twelve
  dimensions, 114 findings, each checked by an independent verifier that saw the claims and
  not the reasoning; 1 dropped as not reproduced. The measured layer came back honest — every
  headline number recomputed exactly — and the failures were all in *claims about
  enforcement*.

  **Critical: decision 1 was unenforced and untrue.** `LICENSE-DATA` asserts "No PORDATA data
  values are contained in or redistributed by this repository" over the directory it grants
  CC BY 4.0 on; **15,946** were in `data/catalogue/pages.jsonl`. `marker_windows` slices 60
  characters ahead of each marker and the last row of the data table sits directly above
  `Fontes/Entidades:`, so record 2858's window opened
  `4 3,2 1,9 10,4 10,7 8,7 4,0 3,9 3,8 3,7 5,9 1,6 1,8 2,0 2,4`. Redacted at the cut so no
  window is ever held unredacted, and backfilled through the same function. Matched by form,
  and the two forms are disjoint from everything a parser reads — grouped thousands need a
  space or stop between three-digit groups, Portuguese decimals need a comma, and the
  lookarounds exclude slashes, so `2026-01-06` survives for `recoverable_from_windows` and
  `Euro (a partir de 1/1/1999) / ECU (até 31/12/1998) - Média` survives whole. Verified the
  strongest way available: **the catalogue rebuilds byte-identical from the redacted corpus**.
  `jsonl_value_leak_max: 0` now reads every window of every record, sharing the redactor's
  pattern object rather than a copy — the copy that drifts is always the checker. *Note the
  fix does not reach git history; that is a separate decision, and the audit did not scan it.*

  **Four gates that could not fail.** The harvest QA step wrote `status` on two of three exit
  paths and the runner uses `bash -e`, so an exception in the builder aborted before any
  `echo` — leaving the output unset, falsy for all seven `if:` conditions, and
  `continue-on-error` keeping the job green. `Commit progress` staged `docs/` under `always()`
  whether or not the four derived builders had run. `build_crosswalk.py` wrote three files
  *before* checking its floor and only under `--strict`, so a collapsed crosswalk landed on
  disk and was pushed. `featured-sets.yml` — a full 2,195-row rebuild — ran `qa_catalogue.py`
  without `--strict`, which prints a breach and exits 0, then pushed. And
  `eurostat-catalogue.yml` refreshed the crosswalk's input without rebuilding it, the exact
  rule `ine-catalogue.yml` states in a comment. All five are fixed, and stated as properties
  over every workflow rather than one at a time; two of the three new assertions failed on
  first run and caught the bugs above.

  **`DesignSystemTest` had never run.** `tests.yml`'s push paths omitted `site/**` while
  `setup.cfg`'s `also_copy` listed four paths that were not triggers — so the guard credited
  with keeping one design across the SPA and the 2,195 detail pages was itself unguarded, on
  four real commits. The two lists are now asserted against each other.

  **Three things published that the catalogue could not support.** 38 INE panels printed an
  operation under half their own family agreed with (portugal/3018, a resident-population
  series, named a health survey at 0.447); the card and the page it opens showed different
  units on 1,111 rows because the pages rendered `unit` raw while the SPA routes through
  `unit-terms.json`; and `name_en` — derived from one regex over a URL shape that has already
  broken once — was gated by nothing, so rewriting `/en/` to `/en-gb/` gave 0 of 2,195 names
  with the gate still green.

  **Three WCAG failures, all the same shape**: an alpha modifier on a token that passes at
  full opacity. The focus ring computed to **1.29:1** against 1.4.11's 3:1 with `outline-none`
  beside it — worse than shipping no focus style at all — and the token was only 2.59:1 before
  the modifier; the micro-column labels were **2.99:1** at 9.5px; `n/a` was **1.97:1**,
  functionally invisible, on the 1,057 rows with no unit. `site/src/lib/contrast.ts` now does
  oklch → linear sRGB → luminance with alpha compositing and the test walks a table of real
  pairs read out of the shipped stylesheet, anchored on white-on-black at exactly 21 rather
  than on thresholds. Also: all 2,195 `Dataset` blocks lacked `description` (Google's
  eligibility requirement) and `license`, and told crawlers the measured variable was
  "Indivíduo" or "%" on 1,138 of them.
- **Failures nobody hears** (roadmap 6b, 2026-08-24). Five places where something broke and
  the pipeline stayed green. *(i)* The harvest commit step had no `if`, so a crash or timeout
  skipped it and threw away every 25-page checkpoint the harvester writes precisely so a dead
  run is not a total loss; it now commits with `always()` and marks the commit partial.
  Nothing degraded can publish that way: when the fetch dies, build and QA never run, so
  `docs/data` is untouched. *(ii)* `sitemap.yml` committed its snapshot before opening the
  issue, and the diff is computed against the *committed* snapshot — so a failed
  `gh issue create` lost the add/remove notification permanently, because the next run
  compared against the advanced snapshot and saw nothing. Notifying first makes it
  self-healing. *(iii)* Nothing checked that the committed `docs/` bundle matches `site/`
  source; the build is byte-deterministic, so `site.yml` now rebuilds and fails on a diff.
  *(iv)* `sitemap.yml` and `spikes.yml` had no `timeout-minutes`, so a stalled fetch inherits
  GitHub's six-hour default and holds its serial concurrency group all day — for the detector,
  that is the whole pipeline. *(v)* Pages deploys `docs/` out of band, so the last hop to the
  public had no gate on either side; `pages-health.yml` fetches the live site daily and
  compares its `built_at` with the committed one, and checks that the assets the *served*
  `index.html` names resolve — a partial deploy answers 200 on `/` and renders a white page,
  which a check of `/` alone would call healthy.
- **The workflows are now tested** (roadmap 6b). Eight workflows were the only thing running
  this project and the one part of it with no tests. The failures they hide are quiet by
  construction: Actions does not error on a mistyped `steps.<id>`, it renders the empty string
  and takes the other branch; an output renamed in `diff_sitemap.py` leaves
  `steps.diff.outputs.notify == 'true'` simply never true, and the run stays green with no
  issue opened. `tests/test_workflows.py` asserts invariants rather than a schema — every job
  bounded, every pusher serialised, every writer checked out at the branch head, no dangling
  step ids, notify-before-commit, `always()` on the salvage paths, the QA revert before the
  commit, the `docs/` gate after the build — and two cross-file contracts run the real script
  and compare the keys it emits against the ones the workflow reads. Each mechanical invariant
  was verified by breaking it in the real files and confirming a red suite. **535 tests, 88%
  coverage, kill rate 65.3%** (current; re-measured after the UI consistency sweep). Two
  things the exercise taught: `tests.yml` only triggered on
  its own workflow file, so tests *about* the other seven would not have run when they changed
  (now `.github/workflows/**`); and mutmut runs from a copied tree, so `.github/` had to join
  `also_copy` — caught by the suite's own "no workflows found" guard rather than by an empty
  glob passing silently.
- **The card logic moved into `site/src/lib/card.ts`** so it is mutation-tested. Adding
  `App.tsx` to Stryker's scope was tried first and rejected: it scored 59% and pulled the
  overall under the break threshold, because most of what it mutates is JSX. Moving the pure
  functions in put them inside the gate instead of weakening it — 92.13% overall, and 52
  mutants that were never exercised are now killed.
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

**Execution order (2026-08-24, end of day — after the crosswalk, the coverage gap, the CI
hardening and the detail pages).** Ids are stable and never reused. Fully shipped: **6**
(a–f), **10**, **11**, **12**, **18**, **19**, **23**, **24**. Half shipped, with the open half
named in the item: **2** (INE done, Eurostat/BPstat open), **15** (metadata done, charts open),
**16** (computed, owner pass open), **13** (Eurostat answered, INE/BPstat open).

**Owner's queue first.** Four things are blocked on a human and nothing else, so they head the
list; together they are about ninety minutes, and each unblocks work that is otherwise ready
to run.

1. **25 — curate the INE gap shortlist** (~45 min). The accept/reject record *is* the curation
   rule, and it is the only way to acquire one. Closes 16.
2. **13 — INE and BPstat's reuse terms** (~10 min now; Eurostat is answered as CC BY 4.0).
   Both 403 from a cloud IP, so this needs a real browser. The only thing gating 14.
3. **17 — name the project.** Cheap now, more expensive once Phase D publishes a package name
   or FFMS replies.
4. **The residual checks in item 1** — the ~20-record spot-check and
   `data/catalogue/FEATURED-UNMATCHED.md`.

**Then, in order:**

5. **14 — the series archive.** Where the project stops being a catalogue. Unblocked the
   moment 13 is recorded, and the pilot it asks for (size, vintages, "no series" as a
   first-class state) is measurable the same day, since nobody has yet fetched a single INE
   series and the response shape is unmeasured.
6. **15's charts**, on the archive. The layer is chosen and measured (`@tanstack/charts`,
   pre-rendered SVG plus interactive-on-demand); the slot is already shaped for it.
7. **2 — the crosswalk's remaining half.** BPstat (measure it before specifying it; neither
   INE's shape nor Eurostat's is safe to assume), and the refusals: 480 Eurostat rows where no
   head matched, in `data/crosswalk/EUROSTAT-REVIEW.md`, and the INE ones in
   `data/crosswalk/REVIEW.md`.
8. **20 — watch the new fields accrue** and answer europa's period. Low effort, and it closes
   out the whole field-capture thread.
9. **8b/c, then 9** — labels from sources and recency, then blended relevance.
10. Background, in any order: **7** (name/i18n review), **3** (the ledger), and **4** (the FFMS
   follow-up, due ~2026-09-04).
11. **21 — the full re-harvest** stays last on purpose: its value grows with everything the
   parser learns from 15, so firing it early means doing it twice. **22** runs itself daily
   until it retires.

1. **Harvest closed — residual owner checks.** 2,195/2,195 reachable pages; id 1221 is dead
   upstream and retired via `data/catalogue/abandoned.txt` (owner-verified in a browser, and
   cited in a 2022 Gulbenkian publication, so it is a genuine PORDATA bug worth including in
   the FFMS follow-up, item 4). Remaining: spot-check ~20 records against live pages (owner,
   browser), and curate `data/catalogue/FEATURED-UNMATCHED.md` — 50 quadro names the matcher
   deliberately refuses to guess, each listed with candidates and a paste-ready `overrides`
   snippet. Several have no counterpart at all (derived aggregates PORDATA publishes only
   inside the quadro; a few quadro rows share one catalogue page), so a perfect score is not
   the goal and the QA floor is set accordingly.
2. **The crosswalk** *(INE half **done 2026-08-24**, Eurostat half **done 2026-08-25** — see
   "What has been built"; BPstat still open, and 2a below)*.
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
   no credible family exists.

   *"Constrain with INE's `theme`/`subtheme` before any name comparison — the cheapest
   precision available" was the plan here, and it was **tried and measured wrong**
   (2026-08-24). Theme purity rejects exact matches, because INE files the same series under
   two themes: "Corpos de bombeiros" and "Poder de compra per capita" are literal title
   matches that a purity rule refuses. Theme and operation are reported as evidence instead.
   `keywords` is INE's own field and mostly repeats the title's words plus the theme name;
   nothing there is a constraint the title does not already give.*

   **Eurostat: done 2026-08-25, and the measurement was worth taking.** `data/eurostat/
   datasets.csv` caches **7,572** datasets; `data/crosswalk/eurostat.json` routes **118 of
   616** in-scope rows, `null` for the rest, gated at a floor of 100. The shape is *not* INE's,
   which is why the roadmap said to measure rather than assume: Eurostat publishes
   multi-dimensional **cubes**, not pre-sliced series, so a PORDATA row wants one dataset
   **plus a filter over its dimensions**. The consequence is a rule reversal — INE's "family
   size is never a reason to refuse" does not carry over, because Eurostat's candidates are
   *rivals* of which one is right, so a large set is an open question rather than a fact about
   the upstream, and the QA report says the opposite of INE's.

   The operator, measured in `data/spikes/eurostat-crosswalk-shape.md`: strip PORDATA's unit
   parenthetical (Eurostat carries the unit as a *dimension*, so `percentage` alone blocked 35
   rows — the INE unit lesson at the opposite polarity), split both sides at the `by` that
   opens the breakdown, require the heads to be **identical**. Plain containment reaches only
   18.3% because it asks a cube's name to contain the words for its own dimensions.

   **The breakdown is a veto, never a ranking.** Ranking candidates by it picked a single
   winner on 10 of 83 tied rows and one of the first eight sampled was *Employment by
   professional status — ENP-South countries*, a non-EU geography. As a veto — two breakdowns
   sharing no word are not the same slice, and silence on either side is not a contradiction —
   it refuses 18 head matches and every hand-read one is correct.

   **What the entry may not claim**: the catalogue carries titles, not dimension names, so
   `filter_resolved` is `false` on every entry. Item 14 must resolve the breakdown against the
   real structure at fetch time, or refuse to archive.

   **Still open: BPstat.** Measure it the same way; neither INE's shape nor Eurostat's is
   safe to assume. The 2,195-to-13,084 ratio is also item 16's raw material.

   **Also open on the INE half**: 627 in-scope rows refused, sampled in
   `data/crosswalk/REVIEW.md`. Two categories are visible there and are worth separate work —
   PORDATA rewording an indicator INE publishes under another name, and PORDATA computing a
   ratio INE publishes only as its parts ("Acidentes de viação com vítimas **por mil
   habitantes**" has no INE counterpart, but its numerator does). The second is a
   `derived_from` tier the schema has room for and v1 does not attempt.

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
5. **Phase D: MCP server over the catalogue** *(gated on owner go; the crosswalk precondition
   is met for INE as of 2026-08-24 — "which INE series answers this?" is now answerable for 206
   indicators, which is the query that makes an MCP worth having)*. Discovery
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
6. **Hardening backlog — closed 2026-08-24** *(absorbed the old item 11; sourced from the
   2026-08-23 `/mega-audit`, full report in `data/audits/`)*. All six strands shipped: (a)
   silent data corruption, (b) failures nobody hears, (c) freshness, (d) test strength, (e)
   code hygiene, (f) payload budget. Each is described in "What has been built"; the id stays
   because code and docs reference `6b`/`6d`/`6f`.

   **Still open, and only this:** harvesting the `/en` tree (~2,196 pages) if EN descriptions
   ever become worth having. Deferred, not scheduled — the EN *names* already come from the
   sitemap, and 96.3% of PT descriptions are an SEO template, so there is no reason to expect
   the EN ones to carry more.
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
13. **Upstream reuse terms — read and record** *(owner, laptop, **~10 min now**; gates item 14;
   `spikes.yml` probe `licences`, report in `data/spikes/licences.md`)*.

   **Eurostat is answered, in its own words** (fetched 2026-08-24): the Commission legal notice
   at <https://commission.europa.eu/legal-notice_en> says "content owned by the EU on this
   website is licensed under the **Creative Commons Attribution 4.0 International (CC BY 4.0)**
   licence" and "reuse is allowed, **provided appropriate credit is given and changes are
   indicated**", implementing the Commission Decision of 12 December 2011 on the reuse of
   Commission documents. That covers redistribution of derived series, which is what item 14
   needs. *Confirm the quote against the page before recording it as this project's basis —
   the spike quotes, it does not decide.*

   **INE and BPstat still need a browser, and it has to be yours.** All three INE candidates
   returned **403**, including its front page: the same bot protection item 22 is measuring,
   and a result about the runner's IP rather than about INE's terms. BPstat served but is a
   JavaScript app, so its 104 KB front page carries no terms text, and
   `bportugal.pt/pagina/termos-e-condicoes` 403'd too. Both are a two-minute look from a real
   browser.

   **What to record here, per source**, before a single upstream value is archived: the licence
   name, its URL, the exact attribution string it requires, and whether it permits
   redistribution of derived/reformatted series — not merely display. Expected outcome is three
   source-citation regimes rather than three blockers, but "expected" is not "recorded", and
   decision 7 exists because an upstream was once asserted from memory. **Prevention**: item
   14's archive job refuses to write a series whose source has no entry here.

14. **Series archive — pull the numbers from the sources** *(**13 is the only thing still
   gating this**; item 2's INE half landed 2026-08-24, so 212 indicators already carry a fetch
   route and `europa` simply has none yet)*.

   **The pilot ran 2026-08-25** (`data/spikes/ine-series.md`, 8 series). It answers all three
   of the questions below with measurements rather than guesses, and one of the answers is a
   surprise worth acting on:

   - **INE's JSON API is not blocked.** All 8 returned **200**, on the same runner where
     `www.ine.pt` returns 403 to every request. `pindica.jsp` is a different subsystem from the
     `xportal` pages, so **the archive can run from Actions after all** — which had been the
     main unexamined risk in this item.
   - **Size: it does not fit in git.** Median 291 KB, mean 1,497 KB, max **10.2 MB** for a
     single series, and the largest response alone is 87% of the sample's bytes. Extrapolated
     over the crosswalk's 1,062 named ids that is 0.29 GB by the median and 1.52 GB by the
     mean — five times apart, so *neither is a size estimate at n=8*. What they jointly settle
     is that this cannot live beside `catalogue.json`, and that the next measurement should be
     the **distribution**, not another average.
   - **Vintages are exposed.** Each response carries `DataExtracao` and
     `DataUltimoAtualizacao`, so revision history is available per fetch rather than only by
     diffing snapshots — which is what decision 5 wanted and what neither PORDATA nor INE shows
     anyone today.

   **The schema, measured**, so the long-format target maps rather than being invented:
   `[].Dados.<ano>[]` holds one record per observation with `geocod` / `geodsg` (geography),
   `dim_3` / `dim_3_t` (the breakdown dimension and its label), `valor` (the value) and
   `ind_string`; the period is the **key** of `Dados`, and `IndicadorCod` / `IndicadorDsg`
   identify the series. So (indicator, geography, period, value, unit, flag) maps to
   (`IndicadorCod`, `geocod`, the `Dados` key, `valor`, …) with the unit and flag still to be
   located — `MetaInfUrl` is the obvious place to look next. The turn from a
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

15. **Per-indicator detail pages with charts** *(**metadata half done 2026-08-24** — see
   "What has been built"; the charts remain, gated on 14)*.

   **Chart layer chosen and measured: `@tanstack/charts`** (owner ask 2026-08-24; spike in
   `data/spikes/charts-tanstack.md`, reproducible). Marginal cost **≈27 KB gzipped** over
   React, from 113 granular per-mark exports and `sideEffects: false`. The finding that
   decides the architecture: **it renders to SVG in plain Node with no DOM** —
   `createChartScene()` compiles a renderer-neutral scene and `renderChartSvg()` is a pure
   string function. So the chart does not have to cost 88 KB of JavaScript:

   - **pre-render the SVG at build time** (~3.4 KB gzipped for a 195-point three-series line),
     which keeps the detail pages at the zero-JS weight they were built for, works with
     JavaScript off, and is crawlable;
   - **load the interactive chart only when someone reaches for it** — picking geographies,
     changing the window, comparing. That is when 88 KB is worth spending.

   CSS custom properties survive into the emitted SVG and axes use `currentColor`, so **one**
   pre-rendered file serves light and dark. `ariaLabel` is a required prop and the root
   carries `role="img"`; the React adapter exposes `tabIndex` and focus callbacks.

   **The risk, recorded: 0.14.0, six releases in six days.** Pre-1.0 and moving fast, so a
   breaking change before item 14 lands is likely rather than unlikely. Survivable because of
   how it is used — the static path is two calls behind one build script and the interactive
   path is one component on one page. Re-check the release timeline before adopting, and
   treat the project going quiet, or `defineChart` churning across 0.x, as the signal to
   reconsider. **Not added to `site/package.json` yet**: nothing to chart until 14 archives
   values, and a dependency nothing renders is a dependency nobody maintains. Replace the click-out to pordata.pt with a page this project owns: the
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
   2026-08-23; **INE half done 2026-08-24** — `data/coverage/INE-GAP.md`, 302 concepts
   awaiting owner accept/reject, which is step (d); Eurostat still needs its TOC, which
   needs network)*. The goal stated plainly: **be more complete than PORDATA**.
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

20. **Let the new fields accrue, then raise the floors** *(follows 24; low effort, high
   signal)*. Roadmap 24 widened the parse for question, period and revision note, and the
   freshness loop now collects them as pages go stale. Three things remain:

   - **Watch the per-area coverage.** `question_ratio` and `period_ratio` are gated per area
     with floors at 0, because nothing harvested before 2026-08-24 carries them. Raising each
     floor as coverage climbs is how 24 is known to be working — and a selector that fails on
     one template surfaces as a named breach in the area it broke rather than as silence.
   - ~~**Answer europa's period.**~~ **Answered 2026-08-25, and the premise was wrong.**
     "Neither mechanism appears there" was inferred from spikes A3 and A4, which sampled the
     *other two* areas. Probed directly (`data/spikes/europa-period.md`), all three sampled
     europa pages carry **both**: four `YearCurrentText`/`YearOtherText` elements and 26–30
     `<option value="YYYY">`. `extract_period` already returns the range on that shape — so
     `period_ratio[europa]` sits at 0 purely because **no europa page has been re-fetched since
     the parser learned the field** (0 of 638 records carry one). It is harvest lag, not a
     missing extractor, and there is nothing to write. Pinned by a regression test so the
     premise cannot return.
   - **Then re-measure the coverage line.** It stood at 78.4% with 475 rows carrying neither
     breakdown nor unit, **471 of them portugal**. If portugal's units accrue as expected that
     falls to roughly 4 rows — a projection from a 7-page sample, so treat it as a hypothesis
     until the gate says otherwise. `unit_ratio[portugal]` sitting at a floor of 0.0 is the
     marker for this whole thread being finished.
21. **One full re-harvest, deliberately** *(owner ask 2026-08-23; last item on the board on
   purpose)*. Nothing is blocked on this — the caption marker means units accrue for free as
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
   is settled and item 20 has answered europa's period. Firing early
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

25. **Curate the INE gap shortlist — accept or reject, one by one** *(owner, laptop, ~45 min;
   the blocking half of item 16)*. Read `data/coverage/INE-GAP.md`. It proposes **302 concepts**
   INE publishes that PORDATA never names once, the 40 largest laid out by theme with three
   distinct example indicators each.

   **This is the step that cannot be automated, and not because it is fiddly.** The central
   insight of this project is that the scarce asset is the curation, not the numbers — so a
   shortlist accepted wholesale would give the catalogue INE's coverage *and* INE's usability,
   which is the problem this project exists to fix. The accept/reject record **is** the curation
   rule; there is no way to acquire one except by making the calls. Item 16(d) says this in the
   roadmap's own words and it is worth restating: *completeness without curation is a
   regression.*

   **What a decision looks like.** For each concept, one of three:
   - **accept** — worth adding, with a human-meaningful Portuguese name for the indicator (not
     INE's title) and the theme it belongs under. Those two fields are what makes an entry
     usable, and nothing downstream can invent them.
   - **reject** — PORDATA leaves it out on purpose, or it is an INE construct rather than a
     public-facing indicator ("saldo de respostas extremas" is a survey instrument, not a
     question anyone asks).
   - **annotation** — not a subject at all, and the filter missed it. Say so and it moves to
     `ANNOTATION` in `scripts/coverage_gap.py`, where the report already prints its own
     filtering for exactly this purpose.

   **The one that stands out on a first read** *(a starting point, not a recommendation —
   the call is the owner's)*: **mortality by cause**. INE publishes 54 indicators on tumores
   malignos, 54 on doenças do aparelho circulatório/digestivo/respiratório, and "anos potenciais
   de vida perdidos" throughout — down to município — and PORDATA names none of it. Also large:
   `horas trabalhadas` (130 indicators), `inovação` (50), `encomendas` (80), and the
   confidence/expectations family (`apreciação`, `perspetivas`).

   **Not a to-do list of 302.** Working through the 40 in the report is the deliverable; the
   rest are in `data/coverage/ine-gap.json` if the shortlist runs dry. Record the decisions
   wherever is easiest — a scratch list is fine — and the next session turns them into the rule.

   *Preconditions: none. Item 16's INE half shipped 2026-08-24; this is its step (d).*


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
