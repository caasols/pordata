<!-- Produced by /mega-audit on 2026-08-25. Twelve dimensions audited in
parallel, each checked by an independent adversarial verifier that saw the
claims and not the reasoning behind them. 114 raw findings; 1 dropped as
not reproduced; 0 dimensions returned an incomplete verdict set.
25 agents, 3.27M tokens, 1,448 tool calls.

Finding 1 was additionally reproduced by hand before this file was written,
because it is a legal claim and the audit's own numbers are pattern-dependent.
Measured directly over `marker_windows` in data/catalogue/pages.jsonl with the
Portuguese-decimal form only (?<![\d,.])-?\d+,\d+(?![\d,.]):

  746 of 2,195 records (34.0%) carry decimal tokens
  7,065 tokens total
  969 windows OPEN with three or more decimals in their first 80 characters,
    which is a data series and cannot be anything else
  split 468 portugal / 278 europa; 0 in municipios

The audit reports 868 records / 9,579 tokens because its pattern also counted
thousands-grouped integers. Both are floors: neither separates grouped integers
from year runs, and neither scans git history. Same defect either way — see
finding 1's mechanism, which is exact.

NOT APPLIED. Per the command, this proposes; the owner chooses.
-->

# pordata map — cross-consistency audit, final report

## Executive summary

**Mostly yes, with two exceptions that matter.** The measured layer is exceptionally honest: every headline number in `CLAUDE.md`/`context.md` that four independent dimensions recomputed reproduced exactly (212/839 INE, 118/616 Eurostat, 302 gap concepts, 2,195 pages, 43 featured rows), and every committed artifact rebuilds byte-identically from a clean checkout. The failures are not in the data — they are in **claims about enforcement** (guarantees the docs state as facts that no gate implements) and in **one absolute claim that is measurably false**.

**The single most important thing to fix:** `LICENSE-DATA` asserts "No PORDATA data values are contained in or redistributed by this repository" while `data/catalogue/pages.jsonl` — a directory that licence file explicitly covers — carries **9,579 observation-value tokens across 868 of 2,195 records**. That is the one promise made to FFMS in writing, and it is enforced by nothing.

Twelve dimensions ran; all twelve returned findings. **1 finding dropped** (meta-command's "dimension 2's file list is enumerated" — verifier marked reproduced=false: dimensions 9 and 10 already cover the files it claimed were out of scope).

---

## Critical

### 1. `LICENSE-DATA` claims no PORDATA values are redistributed; 868 of 2,195 committed records carry them
*(found by licensing-supply-chain and meta-command)*

- **Evidence:** `LICENSE-DATA:6-8` scopes CC BY 4.0 to `data/catalogue/`; `LICENSE-DATA:22-26` asserts "**No PORDATA data values are contained in or redistributed by this repository**". Measured over `data/catalogue/pages.jsonl`: **868 of 2,195 records (39.5%)** contain Portuguese-decimal tokens, **9,579 tokens total, max 33 in one record**. Record id 2858 stores a verbatim series fragment: `4 3,2 1,9 10,4 10,7 8,7 4,0 3,9 3,8 3,7 5,9 1,6 1,8 2,0 2,4`. Cause: `scripts/harvest_catalogue.py:75-86` `marker_windows()` slices `text[m.start()-60 : m.end()+220]`, and those 60 leading characters are the last row of the data table above `Fontes/Entidades:`. Repeated at `outreach/2026-08-21-ffms-email.md:46` ("Não haverá qualquer redistribuição de dados da PORDATA"), `README.md:24`, `context.md:591` (decision 1). Published layer is clean (0 tokens in `docs/data/*`).
- **Impact:** The project's central legal position, stated in the licence file governing the directory that breaks it, and committed to FFMS in writing. A reuser taking `pages.jsonl` under the CC BY grant receives PORDATA values the project cannot license.
- **Fix:** Redact numeric runs at write time in `marker_windows()` and backfill in place (no re-fetch needed). Must be form-specific: strip `(?<![\d,.])-?\d+,\d+(?![\d,.])` and `\d{1,3}([ .]\d{3})+`, while preserving `\d{4}-\d{2}-\d{2}` (needed by `qa_catalogue.recoverable_from_windows:225`) and unit forms like `base=2010` (needed by `extract_unit`).
- **Prevention:** `qa_catalogue.py` threshold `jsonl_value_leak_max: 0`, scanning **every** marker window in `pages.jsonl` for both numeric forms, wired into `--strict`. Every existing decision-1 check (`unit_contamination_max`) inspects only the published `unit` field, which is why 9,579 tokens passed months of green CI. Back it with a `tests/test_harvest.py` fixture containing a value table above `Fontes/Entidades:`, plus a companion test asserting ISO dates and `1/1/1999` survive.

---

## High

### 2. `harvest.yml`'s QA step emits no `status` on a builder crash — the whole publish chain stops with a green job
*(silent-failures)*

- **Evidence:** `.github/workflows/harvest.yml:51-66`. The step is `continue-on-error: true` and writes `status` on only two of three exit paths; `python3 scripts/build_catalogue.py` at `:60` sits between them, and GitHub's default `bash -e {0}` aborts before any `echo status=`. Reproduced: `exit=3`, `GITHUB_OUTPUT` empty. All 7 references read `steps.qa.outputs.status` (`:71,:82,:91,:98,:107,:136,:145`); nothing reads `.outcome`. With `status` unset every one is false — no revert, no crosswalks, no coverage gap, no detail pages, no issue, no `exit 1` — and `continue-on-error` leaves the job **success**. Invisible from outside: `check_pages_live.py:124` compares served vs committed `built_at`, both frozen. Torn-write risk: `build_catalogue.py` writes `catalogue.json` at `:546` and `stats.json` at `:611`, and `Commit progress` (`:116`, `if: always()`) stages `docs/`.
- **Impact:** Any exception in the 620-line builder stops the nightly publish chain with a green tick and no issue, indefinitely.
- **Fix:** `trap 'echo "status=error" >> "$GITHUB_OUTPUT"' ERR` at the top of the run block, and extend the handler conditions to `== 'fail' || == 'error'`. Widen the revert from `docs/data` to `docs/`.
- **Prevention:** The repo already has this exact test one workflow over — `tests/test_workflows.py:273 test_every_referenced_output_is_emitted` runs `diff_sitemap.py` for real and asserts every `steps.diff.outputs.*` the YAML reads is emitted. Extend it to `steps.qa`, plus an assertion that every `continue-on-error: true` step is paired with a later step inspecting its `outcome`.

### 3. A failed post-QA step still publishes the catalogue without its derived pages, and the steady-state path never re-derives them
*(silent-failures; overlaps assumptions)*

- **Evidence:** `harvest.yml:81-108` — the four derived-artifact steps (INE crosswalk, Eurostat crosswalk, coverage gap, detail pages) carry `if: steps.qa.outputs.status == 'pass'` with no `continue-on-error` and no revert counterpart; the only revert (`:70-74`) is keyed on `== 'fail'`. `Commit progress` (`:116-121`) is `if: always()` and stages `docs/`. Each floor is reachable: `build_crosswalk.py:88` MIN_MATCHED=170 (`:552`), `build_eurostat_crosswalk.py:75` MIN_MATCHED=100 (`:416`), `build_detail_pages.py:322-333` SystemExit on a moved theme block. `data/catalogue/REPORT.md:4` reads `pending: 0`, so the ordinary nightly is `status=skipped` and none of the four run. `qa_catalogue.THRESHOLDS` (22 keys) has no crosswalk or detail-page key, so `--strict` cannot catch the mismatch. Current state clean: 2,195 rows / 2,195 pages / 0 orphans.
- **Impact:** New rows reach `docs/data/catalogue.json` with no page under `docs/indicador/` — every card links there, so those are 404s the visitor meets. The state persists indefinitely because the skipped path never re-checks.
- **Fix:** Gate `Commit progress`'s `git add docs/` on the detail-page step's outcome (stage `data/catalogue/` always so checkpoints survive), and add an `if: failure()` issue step covering all four builders.
- **Prevention:** Move the check into `qa_catalogue.py` as `detail_pages_missing_max: 0`, comparing `docs/data/catalogue.json` against `docs/indicador/<area>/<id>/index.html` on disk — a pure filesystem check that runs on **every** path including `skipped`.

### 4. `DesignSystemTest` — the guard CLAUDE.md credits with preventing "two designs on one site" — never runs on a site-only push
*(found by roadmap-deps, cross-file-drift, silent-failures, corners — four dimensions)*

- **Evidence:** `tests/test_detail_pages.py:514-641` reads `site/src/components/ui/badge.tsx`, `button.tsx`, `card.tsx`, `App.tsx`, `site/index.html`. `.github/workflows/tests.yml:4-14` push paths are `scripts/**`, `tests/**`, `setup.cfg`, `conftest.py`, `.github/workflows/**` — **no `site/**`**. `site.yml` runs no Python. `git log --merges --oneline | wc -l` → **0 of 184 commits**, so the `pull_request:` fallback has never fired. Four real instances: `475d9a1`, `909a4ff`, `562eeec`, `15245f8` all touch `site/src/` with `trig=0`. Reproduced in a scratch copy: changing one `--background` token in `site/src/index.css` makes `theme_tokens()` return a different stylesheet, while `npm run build` never touches `docs/indicador` (vite `outDir ../docs`, `emptyOutDir false`), so `site.yml:49-61`'s `git diff --quiet -- docs/` stays green. `setup.cfg:23-30` `also_copy` already enumerates the six paths the suite reads: four are not triggers.
- **Impact:** A badge/button/theme edit ships an SPA with new tokens and 2,195 detail pages serving the old ones. An `index.css` edit is worse: `build_detail_pages.py:319-335` hard-fails, so it surfaces hours later as a red *harvest* job, after the QA gate has passed.
- **Fix:** Add `site/src/**`, `site/index.html`, `docs/assets/**`, `data/crosswalk/**` to `tests.yml`'s push paths (the suite runs in 1.4 s), and run `build_detail_pages.py --strict` as a step in `site.yml`.
- **Prevention:** `tests/test_workflows.py` assertion that `setup.cfg`'s `also_copy` ⊆ `tests.yml`'s `push.paths` as glob prefixes — self-maintaining: a test that reads a new directory must add it to both or fail CI.

### 5. `featured-sets.yml` runs QA without `--strict` and pushes `docs/data/` unconditionally — a second, ungated publish path
*(data-gates)*

- **Evidence:** `.github/workflows/featured-sets.yml:31-34` runs `build_catalogue.py` then `qa_catalogue.py` **without `--strict`**; the Commit step (`:36-47`) has no `if:` guard and does `git add data/catalogue/ docs/data/` then push. `qa_catalogue.py:462-467` confirms a breach without `strict` only prints and exits 0. Contrast `harvest.yml:61-65` (`--strict`, `status=fail`, `exit 1`) and `:71-74` (revert). `grep -n strict tests/test_workflows.py` → nothing; its 23 tests name harvest/site/pages-health only. `build_catalogue.py` has no floor of its own.
- **Impact:** This workflow is a **full catalogue rebuild** — it re-derives name, name_en, title/breakdown, unit, revision, orgs, fontes and featured flags for all 2,195 rows — and pushes straight to the Pages branch with the gate disarmed. `context.md:650` records "Nothing publishes past a failing gate" as a standing decision.
- **Fix:** Add `--strict` at `:34`, mirror harvest's containment (`id: qa` + `continue-on-error`, revert on failure, `exit 1`), and add `build_detail_pages.py --strict` + `docs/indicador/` before the commit.
- **Prevention:** Workflow-agnostic test: for every workflow committing a path under `docs/`, assert some step in the same job runs `qa_catalogue.py --strict` and the commit is guarded on its success.

### 6. All 2,195 `Dataset` JSON-LD blocks omit `description` (Google-required) and `license`
*(a11y-discoverability; overlaps corners)*

- **Evidence:** `scripts/build_detail_pages.py:401-413` builds the dict with name/alternateName/url/isBasedOn/creator/spatialCoverage/dateModified/variableMeasured/isAccessibleForFree. Key frequency across all 2,195 emitted pages: `description 0`, `license 0`, `keywords 0`, `provider 330`, `variableMeasured 1138`, everything else 2195. `docs/index.html`'s DataCatalog block **does** carry both `description` and `license` (CC BY 4.0) — the two blocks on the same site disagree about what a machine needs. `LICENSE-DATA` also does not cover `docs/indicador/`.
- **Impact:** Ineligible for Dataset rich results and Google Dataset Search — the largest machine-discoverability channel, and the stated reason for pre-rendering. Metadata published CC BY 4.0 with no machine-readable rights statement on the pages themselves.
- **Fix:** Synthesise `description` from fields already in hand (name + coverage + spatial + unit + `Fontes:`), add `license` and `keywords`, add `og:description`. Widen `LICENSE-DATA`'s scope to name `docs/indicador/`, `data/crosswalk/`, `data/coverage/`.
- **Prevention:** Required-key assertion in `StructuredDataTest` plus a `--strict` breach in `build_detail_pages.py` scanning written pages for missing required keys. The existing test asserts four properties that *are* present and never enumerates what must be — that shape can never catch an omission.

### 7. Focus indicators are invisible: `ring-ring/30` computes to 1.29:1 light / 1.37:1 dark against a 3:1 requirement, with `outline-none` unconditional
*(a11y-discoverability)*

- **Evidence:** `button.tsx:7`, `input.tsx:10`, `App.tsx:41` all carry `outline-none … focus-visible:ring-[3px] focus-visible:ring-ring/30`. Shipped: `docs/assets/index-DsFAIukP.css` contains `.outline-none{--tw-outline-style:none}` and the `color-mix(… var(--ring) 30% …)` ring. `docs/indicador/style.css:147-148` does the same for links on all 2,195 pages. Computed independently by two parties from `site/src/index.css` tokens (sanity-checked: `oklch(0.147 0.004 49.25)` → `#0c0a09` = stone-950): **1.29 light, 1.37 dark**; even full-opacity `ring-2 ring-ring` on the card link is only 2.59 light. `tests/test_detail_pages.py:609` asserts a ring *string* exists — never its visibility.
- **Impact:** WCAG 1.4.11 fails. Because `outline-none` is unconditional, this is worse than shipping no focus CSS. Bare-ring-only controls (no border swap): language button, theme button, Clear-filters, and every link on 2,195 detail pages.
- **Fix:** Drop `/30`, add `ring-offset-2 ring-offset-background`, and darken light-theme `--ring` (2.59:1 at full opacity is still under 3:1) to ~`oklch(0.55 0.01 56)`.
- **Prevention:** Replace the string assertion with a computed-contrast test: parse `:root`/`.dark` token blocks out of `site/src/index.css`, convert oklch→sRGB, composite declared alpha, fail below 3.0 in either theme. `DesignSystemTest` already reads `site/src` from Python, so the plumbing exists.

### 8. Micro-column labels and every `n/a` fail text contrast: 2.99:1 at 9.5px, 1.97:1 for `n/a`
*(a11y-discoverability)*

- **Evidence:** `App.tsx:61` `text-[9.5px] … text-muted-foreground/75`; `:64` `/50` on missing values; `docs/indicador/style.css:105-106,111` repeats both. Computed (reproduced independently): light — label **2.99:1**, n/a **1.97:1**, chart label 2.31:1; dark — label 4.37:1 on card, n/a **2.66:1**. AA requires 4.5:1 below 18.66px. `n/a` is real text (`i18n.ts:22/39 notAvailable`), rendered on the **1,057 of 2,195 rows** with no unit.
- **Impact:** The labels (UPDATED / UNIT / SOURCES / ÁREA) carry the entire information architecture CLAUDE.md describes and are the least legible text on the page; the `n/a` marker is functionally invisible in light theme, on the common case.
- **Fix:** Drop the alpha modifiers (`text-muted-foreground` alone is 4.81:1 light / 7.63:1 dark), raise 9.5px → 11px, and distinguish `n/a` with italics rather than opacity.
- **Prevention:** Same computed-contrast test, extended to a table of (token, alpha, background, font-size) pairs with a 4.5:1 floor below 18.66px.

### 9. `name_en` coverage is ungated — a per-area `/en` slug change silently ships Portuguese names with a fully green run
*(assumptions; overlaps data-gates)*

- **Evidence:** `build_catalogue.py:247-266` derives `name_en` entirely from one regex over `/en/(portugal|municipalities|europe)/slug-id`; joined at `:512`. `grep -n name_en scripts/qa_catalogue.py` → one hit, `:351`, a printed QA.md line. No `name_en*` key in THRESHOLDS (22 keys) or PER_AREA_THRESHOLDS. **Total-loss experiment:** rewriting `/en/` → `/en-gb/` gives 0/2195 `name_en`, `QA gate: all thresholds pass`, exit 0, QA.md printing `name_en present: 0%`. **Partial experiment (worse):** rewriting only `/en/municipalities/` loses 504 rows' names while `qa_catalogue.py --strict` **and** `build_eurostat_crosswalk.py` both exit 0 — the one accidental detector does not fire.
- **Impact:** `name_en` drives the primary card title in every non-PT language, `displayNames`, a quarter of the search haystack, `nameEn` on 2,195 pages and JSON-LD `alternateName`. The `/en` URL shape has already broken once (205 wrong `name_en`, `context.md:63`).
- **Fix:** Emit `name_en_coverage` and add `name_en_coverage_min: 0.98` **plus** a per-area entry — the project's own lesson ("coverage thresholds for markup-parsed fields are per-area") applies verbatim, and the catalogue-wide mean misses the 504-row case.
- **Prevention:** Rule + test: nothing may appear in QA.md's Published layer as a bare percentage unless it is also a THRESHOLDS key. Enforce by parsing generated QA.md for every `- <field> present: N%` line and asserting a matching `<field>_coverage_min` exists — that closes the class permanently, not this instance.

### 10. `harvest.yml` publishes `docs/` when a floor breach skipped the "every row has a page" assertion — and the INE builder writes its degraded output before checking
*(assumptions + roadmap-deps)*

- **Evidence:** Same skip mechanics as finding 3, with an added asymmetry: `scripts/build_crosswalk.py:542-546` writes `OUT_JSON`/`OUT_QA`/`OUT_REVIEW` **before** the floor check at `:552-557` (and only under `--strict`), while `build_eurostat_crosswalk.py:416-422` raises **before** `write_text` at `:424` and enforces unconditionally. The `always()` commit then stages and pushes the degraded `ine.json`. The only issue-opening step (`:135-136`) is gated on `status == 'fail'`, which is `'pass'` here — so no issue is filed.
- **Impact:** A sub-170 INE build lands on `main` with no notification, silently degrading item 14's input (the archive job is specified to fetch from exactly these candidate ids).
- **Fix:** Move the floor check above the three `write_text` calls and raise unconditionally, matching the Eurostat sibling. Add an `if: failure()` issue step covering the four builders.
- **Prevention:** Mirror the test that already exists for the Eurostat side (`tests/test_eurostat_crosswalk.py:399-414`) in `tests/test_crosswalk.py`: build a fixture yielding fewer than MIN_MATCHED and assert the on-disk crosswalk is byte-identical afterwards.

### 11. Published provenance panels assert a plurality vote as fact — 38 of 212 INE entries name an operation under half their own family agrees with
*(meta-command)*

- **Evidence:** `data/crosswalk/ine.json['portugal/3018']` → operation `"INE, Inquérito nacional de saúde"`, **operation_share 0.447**, for "População residente: total e por grandes grupos etários (%)" — while every stored candidate is a "População residente" series. Rendered unhedged at `docs/indicador/portugal/3018/index.html`: "Operação estatística do INE: **INE, Inquérito nacional de saúde**", two elements above the page's own sentence that storing a single id "would be choosing arbitrarily and recording the choice as fact". Selector is an unfloored plurality: `build_crosswalk.py:393-394` `most_common(1)[0]`, stored `:409-412`. Distribution over 212 entries: `operation_share < 0.5` on **38 (17.9%)**, `< 0.75` on 83, minimum **0.231**; `theme_share < 0.5` on 5. The only gate is MIN_MATCHED=170 — a count. `operation_share` appears in zero `.md` files.
- **Impact:** On a project whose thesis is provenance, 38 public pages print an unsupported upstream attribution as fact, one of them demonstrably absurd. This is decision 3's failure mode ("a plausible wrong number gets repeated") arriving through the metadata.
- **Fix:** `MIN_OPERATION_SHARE = 0.5` — store `operation: null` below it and have `build_detail_pages.py` omit the row rather than print an unhedged one. Alternatively render the share alongside.
- **Prevention:** Golden-file test in `tests/test_crosswalk.py` pinning hand-verified expected operations for ~10 named ids across the share distribution (including `portugal/3018`), so a re-tuned matcher that re-breaks one fails CI.

---

## Medium

### 12. Detail pages ignore `unit-terms.json` — the card shows `m³ - Millions`, the page it opens shows `m 3 - Milhões`
*(dead-code + data-gates)*

- **Evidence:** `build_detail_pages.py:563` renders `field("unit", esc(row.get("unit")))` raw; `:411` emits it as `variableMeasured`; `:517` in the Eurostat panel. The SPA routes through `formatUnit()` (`App.tsx:350` → `lib/units.ts`). Porting `formatUnit` to Python over the catalogue: of **1,138** unit-bearing rows, the page differs from the card on **1,111 for an EN reader** and **12 (verifier: 12 via the full `pt` table) for any reader**. On disk: `docs/indicador/europa/1415/index.html` contains `<span class="v">m 3 - Milhões</span>` with zero `m³` anywhere and only a 1-line theme boot script. `context.md:180-182` claims the file "is the single source of truth … so the two cannot drift"; `build_detail_pages.py:26-30`'s own docstring invokes "the same rule `unit-terms.json` already follows".
- **Impact:** Visible contradiction one click apart, on the shareable canonical URL that gets linked and crawled. `variableMeasured` asserts "m 3" (metres, then three) to machines.
- **Fix:** Port `unitParts`/`formatUnit` to Python, read `site/src/lib/unit-terms.json` at build time (the builder already reads `site/src/index.css` and fails if it moves), and emit through the `both()` idiom so the language switch reaches it.
- **Prevention:** `unit_unrepaired_max: 0` in `qa_catalogue.py` — count published rows whose unit has a part present as a **key** in `unit-terms.json["pt"]`. Fails the moment any surface publishes an unrepaired unit.

### 13. Both `MIN_MATCHED` floors are misattributed: `EUROSTAT-QA.md` names `qa_catalogue.py --strict`, which contains no crosswalk threshold
*(found by claims-vs-reality, cross-file-drift, silent-failures, corners — four dimensions)*

- **Evidence:** `data/crosswalk/EUROSTAT-QA.md:3`, generated at `build_eurostat_crosswalk.py:314-317`: "gated at `qa_catalogue.py --strict` with a floor of 100 matches." `qa_catalogue.THRESHOLDS` has 22 keys, none crosswalk-related; `grep -in eurostat scripts/qa_catalogue.py` → 0. The real floor is at `build_eurostat_crosswalk.py:416-422`, **unconditional** (the script never reads `--strict` at all), and `harvest.yml:92` runs it bare. The sibling `data/crosswalk/QA.md` correctly says only "Rebuilt by `scripts/build_crosswalk.py`" — so the right wording already exists. The same misattribution extends to CLAUDE.md's INE claim ("Gated at `--strict` with a 170-match floor").
- **Impact:** The generated artifact a reader consults points at a module where the check is provably absent; a refactorer could delete the real `SystemExit` believing `qa_catalogue` holds the line. The two gates are not equivalent — a `qa_catalogue --strict` breach reverts `docs/` and opens an issue; a builder breach only aborts its own step.
- **Fix:** Name the real enforcer in the generated sentence, or register `eurostat_matched_min` / `ine_matched_min` in THRESHOLDS so the claim becomes true (and the crosswalks get checked on the skipped path — see finding 3).
- **Prevention:** Test asserting that any module a generated QA report names as its gate actually contains the enforcing check — i.e. if `"qa_catalogue"` appears in the report, a matching THRESHOLDS key must exist.

### 14. `eurostat-catalogue.yml` refreshes the crosswalk's input without rebuilding it — the exact rule `ine-catalogue.yml` states in a comment
*(data-gates + silent-failures)*

- **Evidence:** `ine-catalogue.yml:31-33` carries the rule verbatim ("a refreshed catalogue that did not rebuild it would leave the routing pointing at the previous snapshot's ids with nothing saying so") and implements it at `:34-37` with `build_crosswalk.py --strict` + `coverage_gap.py`, staging `data/crosswalk/` at `:43`. `eurostat-catalogue.yml` has only two steps: fetch (`:33-34`) and `git add data/eurostat/` (`:36-47`). `grep -rn build_eurostat_crosswalk .github/workflows/` → one hit, `harvest.yml:92`, gated on `status == 'pass'`, which is `skipped` whenever `git diff --quiet data/catalogue/`.
- **Impact:** Unbounded stale window on 118 published pages rendering Eurostat codes and **cached** titles as live links to retired datasets.
- **Fix:** Insert `build_eurostat_crosswalk.py` (its floor already refuses to overwrite) + `build_detail_pages.py --strict` between fetch and commit; extend `git add`.
- **Prevention:** Encode the dependency as data in `tests/test_workflows.py`: for each (producer, consumer) pair — `fetch_ine_catalogue`→`build_crosswalk`, `fetch_eurostat_catalogue`→`build_eurostat_crosswalk`, both→`build_detail_pages` — assert any job running the producer also runs the consumer later in the same job.

### 15. Nothing verifies the committed `docs/indicador/` pages against their sources, unlike the equivalent bundle check
*(data-gates)*

- **Evidence:** `site.yml:50-58` rebuilds and diffs — but vite's `emptyOutDir: false` (only `../docs/assets` removed pre-build) means it can only detect bundle staleness. `build_detail_pages.py:645-655 missing_pages()` tests `index.html.exists()` only. The builder runs in one workflow (`harvest.yml:106-108`) gated on `status == 'pass'`, while `ine-catalogue.yml:39-43` commits `data/crosswalk/` with **no** page rebuild. `tests/test_detail_pages.py` has 99 tests and zero references to `OUT_ROOT` or committed bytes. Verified no drift today: rebuilding all 2,195 into a temp root gives 0 differences.
- **Impact:** The repo can hold a crosswalk and a page set that disagree, with the pages being what users and crawlers see, while `--strict` reports "every row has a page."
- **Fix:** CI step (in `tests.yml`) rebuilding into a temp root and `git diff --exit-code -- docs/indicador docs/sitemap-indicadores.xml`.
- **Prevention:** That step is the prevention, plus the producer/consumer table from finding 14 (one table covers both).

### 16. Cross-workflow concurrency is unowned: four workflows write overlapping paths under four different groups, and 7 of 10 notify nobody
*(meta-command; overlaps corners)*

- **Evidence:** `git add` paths: `harvest.yml:121` (`data/catalogue/ data/crosswalk/ data/coverage/ docs/`), `ine-catalogue.yml:43` (`data/ine/ data/crosswalk/ data/coverage/`), `featured-sets.yml:40` (`data/catalogue/ docs/data/`), `sitemap.yml:86` (`data/`). Concurrency groups pairwise distinct and non-cancelling. Both `harvest.yml:83/:99` and `ine-catalogue.yml:36-37` rewrite `data/crosswalk/ine.json` and `data/coverage/`. `tests/test_workflows.py:74` asserts each pushing workflow has *a* group — docstring: "Two concurrent runs of **the same committer**" — never compares groups across workflows. Only 3 of 10 workflows contain `gh issue create`. `sitemap.yml:91` is the one bare `git push` (every other pushing workflow rebases; `3fabbc9` fixed `spikes.yml` — the one the previous audit did *not* name — and left this one).
- **Impact:** A manual dispatch overlapping the nightly harvest discards one side's work behind a red run that opens no issue.
- **Fix:** One shared `group: repo-data-write, cancel-in-progress: false` across every data-writing workflow; add the rebase at `sitemap.yml:91`.
- **Prevention:** `tests/test_workflows.py`: parse each workflow's `git add` paths and fail if two workflows staging an overlapping path do not share a group, or if any `git push` lacks a preceding `git pull --rebase`.

### 17. mutmut's `paths_to_mutate` omits `build_eurostat_crosswalk.py` while `context.md` claims "full mutation testing on every push"
*(found by claims-vs-reality, cross-file-drift, dead-code, meta-command — four dimensions)*

- **Evidence:** `setup.cfg:2-14` lists 12 files. Set-difference against `scripts/*.py` minus the documented coverage omits leaves exactly five unmutated: `analyse_crosswalk.py`, `analyse_eurostat_crosswalk.py`, `build_eurostat_crosswalk.py` (436 lines), `fetch_eurostat_catalogue.py`, `probe_ine_availability.py`. All five are inside the coverage gate — measured by running the exact CI command: 99%, 89%, 99%, 96%, 89%. Its INE sibling `build_crosswalk.py` (561 lines, also 99%) **is** listed. `setup.cfg` **was** edited in the same series (`afdc18e` added `data/crosswalk/` to `also_copy`) without extending the scope. `context.md:110-111`: "plus full mutation testing on every push". `stryker.conf.json:4` uses a glob and auto-enrols.
- **Impact:** The 65.3% figure is computed over a denominator excluding the newest, least-settled logic — the Eurostat filters CLAUDE.md itself calls the delicate part. High line coverage is exactly what makes the gap invisible.
- **Fix:** Add `build_eurostat_crosswalk.py` and `fetch_eurostat_catalogue.py` (and decide explicitly, in a comment, about the `analyse_*` reporters and the probe); re-baseline the floor.
- **Prevention:** Test parsing `setup.cfg`'s `paths_to_mutate` and `tests.yml`'s coverage `--omit`, asserting they partition `scripts/*.py` identically modulo a named `MUTATION_EXEMPT` allowlist whose every member must exist on disk. Generalise to: **a gate's own scope is a claim** — diff every gate's configured scope against the file inventory.

### 18. The refuted "europa has neither period mechanism" premise survives in five places, and re-running the spike would rewrite it
*(found by claims-vs-reality, corners, edge-probes — three dimensions)*

- **Evidence:** `data/spikes/europa-period.md:3` says "Neither appears on europa" while its own table (`:9-13`) records 4 portugal-style year elements and 26–30 `<option>` years on all three sampled pages. That sentence is a **hardcoded literal** in `scripts/spike_europa_period.py` `render()` (~`:110-115`) that never reads `row["known"]`, so the `europa-period` probe regenerates the falsehood. Live at `CLAUDE.md:115`, `context.md:207`, `context.md:1062` (item 21's known-missing table), `context.md:694` (execution order), and `harvest_catalogue.py:117` (three lines above the extractor that already handles it). Contradicted by `tests/test_harvest.py:172-201` (green) and by `extract_period('<div class="YearOtherText">2000</div><div class="YearCurrentText">2023</div>')` → `('2000','2023')`, called unconditionally at `:188`. Zero of 2,196 records carry `period_start` — harvest lag, not a missing extractor.
- **Impact:** Item 21 is held on item 20 answering a question already answered. Worse: `period_ratio[europa] = 0.0` cannot detect a field becoming *wrongly* populated, so when item 21 fires 638 rows acquire a period from an extractor the docs say was never validated, and every gate passes. The spike script's own closing line names this hazard.
- **Fix:** Derive `render()`'s opening sentence from the measured `known` counts; strike the five statements; convert `period_ratio[europa]` from a floor into a plausibility gate (start ≤ end, both in range).
- **Prevention:** Test that `render()` over a synthetic result with non-zero `known` counts does **not** emit "Neither appears on europa" — i.e. the conclusion must be a function of the data. Plus a cross-file assertion that no doc matches `/europa (does |has )?neither/i`.

### 19. Detail pages default to Portuguese for a first-time visitor the SPA would give English
*(edge-probes)*

- **Evidence:** `build_detail_pages.py:308-314` (`BOOT`) checks `localStorage` only — no `navigator.language` fallback; pages ship `<html lang="pt">`. `site/src/lib/i18n.ts:159-165` falls back to `navigator.language.slice(0,2)` and returns `"en"` otherwise. `App.tsx:159-162` writes `lang` only on an explicit toggle, so an EN-resolved first visit stores nothing. Reproduced in Chromium (fresh context per locale, docs/ served locally): `en-US` → index `lang=en`, detail `lang=pt`; `es-ES` → same split; `pt-PT` → both pt. `tests/test_detail_pages.py:617-623` asserts only the theme half of BOOT.
- **Impact:** All 2,195 crawlable pages — the arrival path item 15 exists to serve — render Portuguese to a first-time non-Portuguese visitor. Contradicts BOOT's own comment ("so crossing between them does not flip appearance").
- **Fix:** Mirror `initialLang()` in BOOT (still nine lines, still inside the try/catch); keep served markup at `lang="pt"` so canonical language and JSON-LD pairing are unchanged.
- **Prevention:** A single shared test pinning `initialLang()`'s truth table and asserting BOOT implements the same table, so the two cannot drift.

### 20. The English half has no URL: `og:locale:alternate en_GB` and `inLanguage: [pt,en]` are advertised, with no hreflang anywhere
*(a11y-discoverability)*

- **Evidence:** `docs/index.html` declares both. `grep -r hreflang docs/` → **0 hits**; `docs/sitemap.xml` and `docs/sitemap-indicadores.xml` contain zero `xhtml:link` alternates. Language is localStorage-only. `docs/indicador/style.css:149-151` hides EN content by class; 0 of 2,195 pages carry a language control.
- **Impact:** No indexable English URL exists, so the English names the project invested in have no page; and an English speaker landing on `/indicador/portugal/10/` has no on-page way to switch.
- **Fix:** `?lang=en` honoured ahead of localStorage by both SPA and BOOT; `hreflang` pt-PT/en/x-default on index and every detail page; a two-item language control (pure CSS toggling already).
- **Prevention:** Bidirectional test: every locale in `og:locale:alternate` or `inLanguage` must have a corresponding `<link rel="alternate" hreflang>`, and vice versa.

### 21. Item 16 is scheduled to be "closed" by item 25, but its Eurostat half has zero implementation and its cited blocker is gone
*(roadmap-deps)*

- **Evidence:** `context.md:974` says "Eurostat still needs its TOC, which needs network"; `context.md:674`/`CLAUDE.md:122` say item 25 "Closes 16"; `context.md:668` classifies 16 as "(computed, owner pass open)". Measured: `grep -ci eurostat scripts/coverage_gap.py` → **0**; `ls data/coverage` → only `INE-GAP.md` + `ine-gap.json`. The blocker is stale: `data/eurostat/datasets.csv` is tracked (7,573 lines, committed `362f09f`), and `coverage_gap.py` runs offline reproducing both outputs byte-identically. Item 16's own title is "what INE **and Eurostat** have that PORDATA does not".
- **Impact:** Curating 302 INE concepts will mark 16 done while half the deliverable has never been computed — against the larger upstream (7,572 datasets, 616 in-scope rows) — and the cheapest unstarted work on the board is invisible to sequencing.
- **Fix:** Split into 16a (INE, closed by 25) and 16b (Eurostat, unblocked); delete the "needs network" clause; extend `coverage_gap.py` to emit `EUROSTAT-GAP.md`.
- **Prevention:** QA assertion that every distinct `source` in `data/crosswalk/*.json` has a matching report under `data/coverage/`, each newer than the cache it derives from. Fails immediately today.

### 22. Item 20 is ordered before item 21 but its finishing marker is unreachable without it
*(roadmap-deps)*

- **Evidence:** 20 is step 8, 21 is step 11 (`context.md:694,:699`); both name `unit_ratio[portugal]` as the marker (`:1043`, `:1081`). Measured: portugal 1/1053 rows carry a unit; `qa_catalogue.py:140` floors europa/municipios at 0.95. Re-fetch is purely lastmod-driven (`harvest_catalogue.py:214-243`). Joining to `data/sitemap-lastmod.tsv`: 60 portugal rows >365d, 56 >700d → ceiling `(1053-60)/1053 = 0.943`. No portugal row has been harvested since 2026-08-23, so zero accrual has occurred.
- **Impact:** Executing in order either reds the QA gate or discovers mid-item that item 21 (a ~12 h, three-dispatch job the roadmap wants fired last) is a hard precondition.
- **Fix:** Restate 20 as "raise floors to the *reachable* ceiling" and move its closing half into 21, or promote 21.
- **Prevention:** Publish the ceiling: add `refetchable_ratio` and `lastmod_older_than_365d` per area to QA.md, plus a test asserting no `PER_AREA_THRESHOLDS` floor exceeds its area's measured ceiling — an unreachable floor then fails at the moment someone writes it.

### 23. Item 14's precondition inventory is stale in both directions and contradicts itself inside one document
*(roadmap-deps)*

- **Evidence:** `context.md:883-884` says "europa simply has none yet" — measured: 118 routed (46 family / 37 single / 35 exact), `filter_resolved` false on **118 of 118**. Execution-order step 5 (`:684-687`) says "nobody has yet fetched a single INE series" while item 14 at `:886` says "**The pilot ran 2026-08-25**" and `data/spikes/ine-series.md` exists. `context.md:896`/`:318` cite "1,062 named ids"; the union of `candidates` is **1,069**, the number the regenerated `INE-GAP.md:7` prints.
- **Impact:** Item 14 as written designs an INE-only fetcher and re-runs a pilot already on disk, budgets nothing for the cube+filter shape the 118 Eurostat routes need, and sizes storage off the wrong id count.
- **Fix:** Rewrite the parenthetical with the real inputs; delete the duplicated pre-pilot paragraph; add a Eurostat sub-item whose acceptance criterion is "resolve the breakdown at fetch time or refuse".
- **Prevention:** Have both builders write `data/crosswalk/counts.json` (in_scope, matched, distinct_upstream_ids per source) and add a test that every crosswalk figure cited in the docs matches it — the pattern decision 7 already applies to catalogue numbers via QA.md.

### 24. `context.md` says "Eight" workflows and lists eight; there are ten
*(claims-vs-reality; overlaps cross-file-drift, dead-code)*

- **Evidence:** `ls .github/workflows/*.yml | wc -l` → 10. `context.md:38` enumerates 8, omitting `pages-health.yml` and `eurostat-catalogue.yml`; repeated at `context.md:441`, `tests/test_workflows.py:3`, `tests.yml:11`. `CLAUDE.md:181` is correct, and its table diffs IDENTICAL against the directory listing. Mitigation: `tests/test_workflows.py:28` globs from disk, so assertions cover all ten.
- **Impact:** `context.md` is declared the sole carrier of project state and its inventory is two short — one of them the only gate on the last hop to the public.
- **Fix:** Correct all four; better, point at CLAUDE.md's table.
- **Prevention:** Test asserting the workflow-file count equals the figure in `context.md`'s inventory row and that every filename appears in CLAUDE.md's table.

### 25. `context.md` cites a weekday sitemap cron that exists in no workflow
*(claims-vs-reality)*

- **Evidence:** `context.md:509`: "`30 16 * * 1-5`, ~17:30 Lisbon". `sitemap.yml:24-25` → `7 9 * * *` and `23 18 * * 1-5`. No `30 16` anywhere in the tree. The sentence sits inside the "Measured facts" block and is the stated justification for the cadence; the derived local time is also wrong (18:23 UTC ≈ 19:23 Lisbon WEST).
- **Fix:** Correct or delete the literal.
- **Prevention:** Doc-contract test: extract every 5-field cron literal from CLAUDE.md/context.md and assert each appears in some workflow's parsed `on.schedule`, and conversely.

### 26. "The 1,483 blank-lastmod pages are the whole /en tree plus structural pages" — only 756 of 2,967 /en URLs have a blank lastmod
*(claims-vs-reality)*

- **Evidence:** Computed against the cited snapshot (`git show 867bcee:data/sitemap-lastmod.tsv`) and the current file, identically: total 5906, blank 1483, /en 2967, **/en blank 756**. So 74.5% of the /en tree carries a real lastmod. The sentence is also internally impossible (727 PT blanks + the named structural counts + 2,967 far exceeds 1,483).
- **Impact:** A headline "measured fact" wrong by ~4× on its main term; roadmap 6's remaining /en work is sized off it, and three quarters of that tree could be harvested incrementally.
- **Fix:** Restate as 756 /en plus 337 quadro+resumo, 260 subtema, 48 tema, 29 retratos, 53 other (all reproduce).
- **Prevention:** A `--summary` mode writing the corpus breakdown via `lib.is_indicator_url` into a committed file, with a test re-deriving it. **The 2026-08-23 audit already prescribed exactly this** (`data/audits/2026-08-23-mega-audit.md:391`) and it was applied to the area counts but not this paragraph.

### 27. README (the public front door) says every hit links back to its PORDATA page; since item 15 it links to this project's page
*(claims-vs-reality)*

- **Evidence:** `README.md:6` and `context.md:89`. Code: `App.tsx:319` `href={detailHref(r)}` → `card.ts:60-62` `indicador/${area}/${id}/`. `context.md:163` states the truth, contradicting `:89` in the same file. All 2,195 detail pages carry the pordata.pt click-out.
- **Fix:** Correct README:6 and context.md:89.
- **Prevention:** Test reading `card.ts`'s `detailHref` template and asserting README contains `indicador/` and not "linking back to its PORDATA page". `site/src/` is already in `also_copy`.

### 28. Roadmap 21's known-missing table records europa's period as "unknown", which item 20 in the same file records as measured wrong
*(claims-vs-reality — same root cause as finding 18, listed separately because it is the item-21 gate)*

- **Evidence:** `context.md:1062` vs `context.md:1031-1039` and `data/spikes/europa-period.md`. Item 21's table is explicitly "what 21 exists to collect, and the parser must be widened … *before* 21 runs".
- **Fix:** Replace the row with "shipped 2026-08-25; accrues on re-fetch".
- **Prevention:** Generate the table from the parser's per-area field map, with a test asserting the doc rows match.

### 29. Sort and language menus expose no accessible selection state
*(a11y-discoverability)*

- **Evidence:** `App.tsx:254-262` / `:198-209` render plain `DropdownMenuItem` (`role="menuitem"`); `dropdown-menu.tsx` exports only Root/Trigger/Content/Item — no `RadioGroup`/`RadioItem`, so no `role="menuitemradio"` and no `aria-checked`. Selection is signalled solely by `<Check className="size-3.5" />` — and lucide-react adds `aria-hidden="true"` when no children and no a11y prop (confirmed in the shipped bundle: `...!d&&!X0(p)&&{"aria-hidden":"true"}`), so the indicator is **fully invisible to assistive tech**. `App.test.tsx` asserts `aria-pressed` on the chips (lines 89, 94, 254, 260, 286) and nothing about menus.
- **Fix:** Wrap and use `DropdownMenuRadioGroup`/`RadioItem` with `value={sortMode}` / `value={lang}`.
- **Prevention:** Mirror the existing aria-pressed tests; add `vitest-axe` in the jsdom setup, gated in `site.yml` — no automated a11y check runs today across ten workflows.

### 30. Label-in-name failure on the language button: visible "PT", accessible name "Idioma"
*(a11y-discoverability)*

- **Evidence:** `App.tsx:192-195` `aria-label={t("langLabel")}` over `{lang.toUpperCase()}`; `i18n.ts:24/41` define it as "Idioma"/"Language". Same inside the menu (`:199-208`, `aria-label={name}` over the code). The sort chip at `App.tsx:246` does it correctly, so the codebase knows the pattern. WCAG 2.5.3, Level A.
- **Fix:** `aria-label={`${t("langLabel")}: ${lang.toUpperCase()}`}`; add `aria-pressed={dark}` to the theme toggle.
- **Prevention:** Assertion that for every element with both visible text and an aria-label, the normalised text is a substring of the accessible name — axe-core's `label-content-name-mismatch` covers this and more.

### 31. 256 detail pages carry duplicate link accessible names — up to 12 links all called "JSON"
*(a11y-discoverability)*

- **Evidence:** Exhaustive scan of all 2,195: **198** pages with ≥2 links named exactly "JSON" (max 12, on `docs/indicador/municipios/100/`), **249** with ≥2 identically-named non-JSON links, **256** with any duplicate, **0** pages containing `aria-label`. On `docs/indicador/portugal/10/`: seven links with byte-identical text pointing at seven different INE ids, each followed by an unlabelled "JSON".
- **Impact:** The one-to-many family design makes this the normal case, not an edge case, on the pages CLAUDE.md calls "the crosswalk as provenance".
- **Fix:** `aria-label` including the series id on each link and each `a.api` — the id is already in the adjacent `<span class="id">`.
- **Prevention:** Test rendering a row whose entry has ≥2 candidates with identical titles and asserting the set of link names equals the list length; run the same as a `--strict` sweep.

### 32. `variableMeasured` is populated with the unit on 1,138 pages, telling crawlers the measured variable is "Indivíduo" or "%"
*(a11y-discoverability)*

- **Evidence:** `build_detail_pages.py:411` `"variableMeasured": row.get("unit") or None`; present on 1,138 of 2,195. Sampled: `europa/1247` → "Indivíduo", `/1258` → "Taxa - ‰". schema.org defines it as the variable measured; the unit belongs in `unitText` on a `PropertyValue`.
- **Impact:** Worse than omitting — a wrong assertion is indistinguishable from a right one to a machine, on the half of the deliverable that exists purely for machines. Collides with the project's "refusing beats guessing" principle.
- **Fix:** `{"@type":"PropertyValue","name": title or name,"unitText": unit}` when a unit exists; omit otherwise.
- **Prevention:** Shape test per JSON-LD property pinning which catalogue field feeds it; assert no `variableMeasured` value equals any catalogue `unit`.

### 33. Item 8(b) shipped at 127 organisations against a "~30" target, is certified healthy by a 140 ceiling, and reaches no consumer
*(roadmap-deps + data-gates + dead-code + corners)*

- **Evidence:** Measured: 165 distinct raw `fontes` strings (159 heads), **127 distinct `orgs`**, **26 on exactly one row**, 69 on ≤5 rows. Plan target `context.md:836-837` "~30". Ceiling `qa_catalogue.py:119 distinct_orgs_max: 140` accepts 127 as normal, so no gate can say the collapse fell short. Consumers: `grep -rn '\borgs\b' site/src` → nothing; absent from the built bundle; `App.tsx:311` still uses `shortSources(r.fontes)`; `build_detail_pages.py` → 0 references. Payload: gzip-9 with vs without → **3.7 KB gz** on every first load, against a 250 KB ceiling. Stale "159 → ~30" also at `build_catalogue.py:286`, `qa_catalogue.py:117`, `recency.ts:12`, `context.md:300`.
- **Impact:** The 8b pill will be designed for ~30 facets and built on 127 with a 26-facet singleton tail, discovered at implementation time. Meanwhile the field is dead weight in the budget item 6f exists to protect.
- **Fix:** Either finish the collapse and tighten the ceiling, or ship the consumer, or hold `orgs` out of the published JSON. Correct the "~30"/"159" figures.
- **Prevention:** Gate the facet's *shape*, not just its cardinality: `distinct_orgs_max: ~35` plus `orgs_singleton_max`, and a vitest assertion that the card/filter row actually reads `orgs`.

### 34. `site/src/lib/recency.ts` has zero call sites while sitting inside Stryker's 85% break gate
*(dead-code + corners)*

- **Evidence:** `grep -rn "recency\|STALE_YEARS"` (excl. node_modules/mutants/docs) hits only its own definition and test. `App.tsx:16-24` never imports it. `grep -c STALE_YEARS docs/assets/*.js` → 0 (tree-shaken). Inside `stryker.conf.json:4` `mutate: ["src/lib/**/*.ts"]` and vitest's coverage include. `context.md:310-313`, under "What has been built", says "Derived in the client, where it cannot rot".
- **Fix:** Wire it (a recency chip in App.tsx) or park it outside `src/lib` and correct the doc.
- **Prevention:** `knip`/`ts-prune` step in `site.yml` failing on unused files and exports, with an explicit ignore list so a parked module must be named.

### 35. The tombstone path is unreachable for the only case it exists for
*(dead-code)*

- **Evidence:** `pordata_lib.py:142-146` promises abandoned URLs are "tombstoned at build time, exactly like a page that left the sitemap"; `build_catalogue.py:13-14` states the contract. But `:497` `if "error" in rec: continue` precedes the `removed = True` branch at `:539-540`, and the id-1221 record in `pages.jsonl` is literally `{'url': …-1221, 'error': 'HTTP Error 500…'}` with **no `id` or `area` at all**. Measured: 2,195 rows, **0 with `removed`**; `grep -rl 'class="chip gone"' docs/indicador/` → 0.
- **Impact:** The catalogue silently shrank 2,196 → 2,195 with no machine-readable trace — the outcome the docstring says it exists to prevent. A render path across three files and six languages has never fired.
- **Fix:** Let an errored record whose URL is in `lib.abandoned()` fall through to the tombstone branch, or delete the claim.
- **Prevention:** Test feeding `main()` one errored abandoned-URL record and asserting the published row exists with `removed is True`; plus a QA threshold tying tombstone count to `abandoned()` ∩ record urls.

### 36. `analyse_*_crosswalk.py` carry byte-identical copies of the shipped matchers' operators and run in no workflow
*(dead-code)*

- **Evidence:** AST-diff between `build_eurostat_crosswalk.py` and `analyse_eurostat_crosswalk.py`: `STOPWORDS`, `UNIT_PAREN`, `PORDATA_TAIL`, `EUROSTAT_TAIL`, `norm_title`, `strip_accents` byte-identical; `tokens`, `strip_unit`, `in_scope` identical modulo docstrings. Four `def strip_accents` across `scripts/`. No workflow names them; `spikes.yml`'s nine options include no `a5`. No test imports both a `build_*` and an `analyse_*` module.
- **Impact:** Their output is the project's cited evidence ("plain containment reaches 18.3%", "ranking picked a winner on 10 of 83 ties", "drops 38 matches"), while the shipped matcher is rebuilt nightly — a change to `strip_unit` silently invalidates every figure with no correction point.
- **Fix:** Extract the shared operators into a module both import (`pordata_lib.py` is the precedent).
- **Prevention:** Until then, assert equality of the duplicated pairs in `tests/test_analysis_tools.py`; after extraction, an AST walk failing when the same function name is defined at module level in more than one script.

### 37. Detail pages have no `prefers-color-scheme` fallback, and the payload budget covers only the SPA
*(a11y-discoverability)*

- **Evidence:** `grep -c '@media' docs/indicador/style.css` → **0**; the `.dark` block (`:28-47`) is applied only by the inline boot script reading localStorage/matchMedia. Separately, `qa_catalogue.py:42-45` FIRST_LOAD covers only index.html + assets + catalogue.json; the render-blocking Google Fonts request and the whole 2,195-page set (raw 10.63 MiB, per-file gzip 3.86 MiB, mean 5,076 B, max 10,807 B at `europa/1617`) are ungated. CLAUDE.md's "packs to 4.45 MiB" reproduces under **no** method tried (git pack 0.755 MiB, deflate-9 4.14 MiB, zlib-1 4.16 MiB) and never did (4.06 MiB pre-Eurostat).
- **Impact:** JS-off dark-preference visitors get a white page with no on-page control, on pages CLAUDE.md describes as "no JS bundle". Detail-page growth — already driven by the Eurostat crosswalk — is weighed by nothing.
- **Fix:** Emit a third `@media (prefers-color-scheme: dark)` token block from `theme_tokens()`; add `detail_page_gzip_kb_max` and `detail_pages_total_mib_max` thresholds; recompute the 4.45 MiB figure from the gate's output.
- **Prevention:** Test asserting the generated stylesheet contains the media block declaring the identical property set to `.dark`; both new metrics in THRESHOLDS so `--strict` gates them.

### 38. Reproducibility is excellent and asserted nowhere; the environment it depends on is undeclared
*(meta-command)*

- **Evidence:** From a clean `git archive HEAD`, every Python-generated artifact rebuilds byte-identically — `catalogue.json`, all six crosswalk files, both coverage files, `sitemap-indicadores.xml`, and `diff -rq` over 2,196 detail pages → **zero** differences; only `stats.json`'s `built_at` differs. But `grep -rn setup-python .github/workflows/` → nothing, while `pordata_lib.py:70` calls `datetime.UTC` (3.11+); no `pyproject.toml`/`requirements*.txt`; `tests.yml:34,:52` run unpinned `pip install coverage pyyaml` / `mutmut pytest`, so the 58% floor is measured against a floating mutmut. `CLAUDE.md:219` lists a health-check path (`~/.claude/skills/cartographer/…`) that does not exist here.
- **Fix:** `actions/setup-python@v5` with `python-version: '3.11'` in every Python workflow; pin CI tooling in a committed `requirements-dev.txt`; vendor or replace the cartographer line.
- **Prevention:** A `reproducibility` job in `tests.yml` running the five build scripts on a clean checkout and failing if `git status --porcelain` shows anything but `stats.json`.

---

## Low

### 39. `gate()` silently skips any threshold whose metric is absent
`qa_catalogue.py:234-241` maps key→metric by `rsplit("_",1)` and `continue`s on `None`. All 22 keys resolve today (verified by spying on `gate`), and the skip is documented as deliberate at `:174-179`/`:415-419` for the payload metrics. Residual risk: a typo or rename silently disarms its own gate. **Fix:** explicit `OPTIONAL_METRICS` set; breach otherwise. **Prevention:** test asserting `{k.rsplit('_',1)[0]} - OPTIONAL_METRICS ⊆ set(metrics)`.

### 40. `MUNICIPAL_LEVELS` is a closed INE vocabulary with no membership assertion — a partial rename silently shrinks families
`build_crosswalk.py:93`, matched by exact string equality against `geo_lastlevel`, which already shows drift (42 distinct values incl. `'Região agrária'`/`'região agrária'`, `'NUTS II'`/`'NUTS 2'`). **Verified by simulation:** renaming the 1,457 `'Freguesia'` rows gives `199/839 matched, exit 0` (above the 170 floor) while 13 entries vanish, 15 shrink, and total candidates fall 8,452 → 7,196 (−14.9%) — e.g. `municipios/357` from 233 candidates to 35. That is exactly the under-reporting the design says it refuses. **Fix/Prevention:** assert every member occurs in the cache with a row-count floor, and add a candidate-total floor alongside MIN_MATCHED.

### 41. `mutation_gate` reports 100% and passes on a run that tested nothing
`mutation_gate.py:65-75` returns 1.0 when `killable == 0`; a log whose only tally is `no_tests` prints "100.0% killed … passes (floor 58%)" and exits 0 (reproduced with a real-emoji synthetic log). `tests.yml:53` discards `mutmut run`'s exit status via `|| true`. The all-untested state is exactly what `also_copy` exists to prevent — and finding 4's trigger gap makes it reachable. **Fix:** volume floor in `main()`. **Prevention:** test asserting an all-`no_tests` tally exits non-zero (`tests/test_mutation_gate.py:60-63` currently pins the opposite).

### 42. `load_records` accepts a JSON-valid line with a null `url`, breaking the zero-skipped-lines contract
`pordata_lib.py:186` catches only from `json.loads`/subscripting, so `{"url": null}` neither raises nor increments `SKIPPED_LINES`; `sorted(records)` at `build_catalogue.py:495` then dies with an unattributed `TypeError`. Docstring `:172-175` claims "never silently"; `qa_catalogue.py:51` gates `jsonl_skipped_lines_max: 0`. **Fix:** require `isinstance(rec.get("url"), str)` and non-empty. **Prevention:** extend the malformed-JSONL test with null/int/missing-url lines asserting `SKIPPED_LINES == 3`.

### 43. `strip_markup` deletes text between a bare `<` and the next `>`
`build_catalogue.py:268-274` runs `re.sub(r"<[^>]+>", "")` after harvest-time `html.unescape`. `strip_markup('PIB < 5% (2020 > 2021)')` → `'PIB 2021)'`. Latent: 0 occurrences today (all 25 raw names with `<` carry real tags). No `name` shape validator exists, unlike `fontes`/`unit`/date. **Fix:** strip only the tags PORDATA uses. **Prevention:** unit test pinning both directions plus a `parse_warnings` entry for an unrecognised `<`.

### 44. `is_indicator_url` matches "pordata.pt/" as a substring with no scheme or host check
`pordata_lib.py:117-133`. Reproduced: `https://evil.example/redir?u=pordata.pt/portugal/x-999` → True; `javascript:pordata.pt/portugal/x-1` → True; `ftp://x/pordata.pt/municipios/y-5` → True. Duplicated at `fetch_sitemap.py:52-53`. Exploitation requires PORDATA to serve a hostile `<loc>`, so this is defence-in-depth. **Fix:** `urlsplit`, require https and a pordata.pt netloc. **Prevention:** the three negative cases as tests, plus `foreign_host_urls_max: 0` over the published catalogue.

### 45. `fetch_featured_sets.py` overwrites `featured.json` wholesale, destroying the `overrides` block the worksheet tells the owner to add
`fetch_featured_sets.py:102-132` builds `result` from scratch and never reads the existing file; the consumer is `build_catalogue.py:129/:145-147`; `FEATURED-UNMATCHED.md:7-10` instructs the owner to add exactly that key. No `overrides` exists yet, and the deletion would land as a revertible git diff — but `featured-sets.yml:31-33` runs QA without `--strict`, so its floor is not even a gate. **Fix:** carry unknown keys forward, or move overrides to an owner-owned file. **Prevention:** test writing an `overrides` fixture, stubbing `fetch()`, running `main()`, and asserting it survives byte-identically.

### 46. Eurostat `period` is computed from the truncated 25-candidate slice
`build_eurostat_crosswalk.py:251-252` uses `stored = family[:25]` while `theme`/`theme_share`/`n_candidates`/`n_exact` use the full `family` (the truncation hazard was already reasoned about at `:241-243`). `europa/2970` (73 candidates) publishes 2016–2023 against a family spanning 2007–2024; `europa/3388` drops 1991. 2 pages affected. **Fix:** compute over `family`. **Prevention:** test asserting every whole-family statistic in `entry_summary` is invariant to `MAX_STORED`.

### 47. The Eurostat provenance panel renders PORDATA's own unit as upstream provenance
`build_eurostat_crosswalk.py:258` stores `row.get("unit")` verbatim; `build_detail_pages.py:516-517` renders it between the Eurostat-derived theme and period. All 118 entries' `unit` equals the PORDATA row's; 117 are non-empty. The INE entries carry no `unit` key at all. The panel gets `filter_resolved: false` right on the adjacent field. **Fix:** drop it (the value is already on the page) or rename to `wanted_unit` with an unresolved caveat. **Prevention:** assert the panel renders only keys derived from `family`/`stored` or prefixed `wanted_`.

### 48. `?`-for-en-dash is repaired in `name` only; 49 descriptions still carry it
`build_catalogue.py:499` is the sole `fix_separator` call site; 49 published descriptions contain `?` (vs 1 legitimate name). `separator_repairs` counts en dashes in **names**, so it is structurally blind — and counting en dashes cannot distinguish "normaliser died" from "PORDATA fixed it". **Fix:** apply to `description`; return a repair count. **Prevention:** `separator_defect_residual_max: 0` across **all** string fields — field-agnostic, so new fields are covered without editing the gate.

### 49. 57 rows lose acronym casing in `name_en`
`build_catalogue.py:247-265` titlecases the first letter of a lowercase slug: "higher education (isced 5 8)" against PT "(ISCED 5-8)". 2.60% of rows, uncounted because `name_en` has no quality metric at all (finding 9). **Fix:** uppercase any `\b[A-Z]{2,}\b` token from the PT name; refuse when there is none. **Prevention:** `name_en_acronym_case_max: 0`, also serving as the only quality signal on the slug-derivation path.

### 50. Stale INE headline figures and drifted prose metrics
Docs lead with "206 of 839 … 633 null" and "1,062 of 13,084" (`CLAUDE.md:45-47`, `context.md:318,:350-352,:785`); measured **212 / 627 / 1,069**. Each paragraph states two different counts. Also: "535 tests, 88% coverage" vs measured **678 tests, 90%**; SPA "~106 KB gzipped" vs 111.9 KiB bundle (264.9 total, matching QA.md); StrykerJS "92.13%" vs a run I executed at **91.69%**; "2,536 PT pages" vs **2,533** (and 2,196+337 = 2,533 internally). `data/crosswalk/QA.md` and `ine-gap.json` are already correct — only hand-written prose lags, and `context.md`'s own Verification section says counts should not be quoted. The 1,062 propagates into item 14's storage sizing. **Prevention:** doc tests asserting any `\d+ of 839` equals the non-null count and any `KB gzipped` figure matches a QA.md Gate value.

### 51. Two spike reports carry results their own code has refuted, unmarked
`a6-page-inventory.md:57-59,:246-248` say "none matched" while their own repeated-blocks lists show the questions; the parser fix (`8eaa9d2`, 13:37) postdates the report (`c8d706a`, 13:30). 13/15 in the report vs "15/15" asserted in four places. `a3-coverage-fields.md` records `'A carregar conteúdo': 0` on 7 pages — a false negative CLAUDE.md itself names — with no correction note. **Fix:** re-run a6, or add dated Correction blocks. **Prevention:** test failing when a spike report's commit timestamp predates its generating script's, unless it contains a "Correction" heading.

### 52. Nine smaller doc/code drifts
`build_eurostat_crosswalk.py:3` cites "roadmap 1" (it is item 2, per every sibling); `roadmap 12` is referenced from `qa_catalogue.py:59` and defined nowhere, and item 6's "code references 6b/6d/6f" omits three `6a` references; `openAt` is dead in six languages and its live Python twin has different wording, `chartSoon` has already drifted PT and EN, `AREA_LABELS` exists twice untested; `LABELS["coverage"]`, `page_path()`, `main_strict()` and `raw_both()` are dead or redundant; `site.yml`'s freshness gate uses `git diff` (blind to added untracked files — proven in a throwaway repo); Eurostat's TOC is parsed positionally while the header guard only checks a `code` column exists (a swap is caught today only coincidentally, by 69 duplicate titles tripping `collapse`); `check_pages_live`'s `ASSET_REF` hardcodes `./assets/` so a `base` change silently self-disables the check; the `removed` badge fails dark contrast at 2.79:1 (currently a dead path); landmarks put `<footer>` inside `<main>` with no skip link and no `<h2>` on the SPA; unused `outline`/`ghost` variants and `*Variants` exports; INE URL templates hardcoded in `build_detail_pages.py:71-73` while `data/ine/indicators.csv` carries the authoritative routes (0 mismatches across all 13,084 rows today) and the Eurostat sibling asserts its templates every build; both upstream caches are dispatch-only with no `fetched_at`; README documents 9 of 15 published fields; item 13's prevention has no machine-readable home; three findings from the 2026-08-23 audit are still open under a "closed 2026-08-24" heading; the owner's queue is costed at ninety minutes against ~35 minutes left for two substantial items; `qa_catalogue.py:134-137` names shipped item 19 as its unblock trigger; `.git` is 112 MB / 138 MB of blobs with no size budget or history secret scan (working tree and history both scan clean today); item 2a's pilot has no path through either builder; Dataset JSON-LD assigns `creator: PORDATA` where the DataCatalog assigns Benevolus; no CI check pins the 15 floating `actions/*@v4` refs or the (currently correct) permission surface.

---

## Systemic preventions worth building now

Ranked by findings-prevented per unit of effort.

**1. `also_copy` ⊆ `tests.yml` push paths, asserted in `tests/test_workflows.py`** *(≈1 assertion; prevents findings 4, and unblocks 41)*
`setup.cfg` already enumerates every off-disk input the Python suite reads, because mutmut needs it. Asserting that list is covered by the trigger makes the coupling self-maintaining. This is the single highest-leverage line in the report: four dimensions independently found the same hole.

**2. Present-vs-absent metric discipline in `qa_catalogue.py`** *(≈20 lines; prevents 9, 39, and the `featured_rows` skip)*
Two rules: (a) every field named in QA.md's Published layer as a bare percentage must be a THRESHOLDS key — enforce by parsing the generated QA.md; (b) a threshold key with no measured metric is a breach, not a skip, outside a named `OPTIONAL_METRICS` set. One parse of the project's own output closes the class permanently.

**3. Move derived-artifact checks *into* `qa_catalogue.py`** *(≈40 lines; prevents 3, 13, 14, 15, and half of 2)*
`detail_pages_missing_max: 0`, `ine_matched_min: 170`, `eurostat_matched_min: 100`, `crosswalk_cache_age_days_max`. These are pure filesystem/JSON checks, so they run on **every** path — including the `skipped` nightly that today re-derives nothing — and they make `EUROSTAT-QA.md`'s sentence true instead of wrong.

**4. Workflow invariants as data in `tests/test_workflows.py`** *(≈5 assertions; prevents 2, 5, 10, 16, and part of 3)*
(a) every `steps.X.outputs.Y` literal the YAML reads must be emittable on every exit path of X's script — the file already has this test for `diff_sitemap`; (b) every workflow committing under `docs/` must run `qa_catalogue.py --strict` and guard the commit on it; (c) two workflows staging an overlapping path must share a concurrency group; (d) every `git push` needs a preceding `git pull --rebase`; (e) every producer script implies its consumer in the same job.

**5. A computed-contrast test over the token table + axe-core in vitest** *(≈60 lines + one dep; prevents 7, 8, 29, 30, and most of 31/37)*
Parse `:root`/`.dark` out of `site/src/index.css`, convert oklch→sRGB, composite declared alpha, and fail below 3:1 (non-text) / 4.5:1 (text under 18.66px) across an enumerated pair table. `DesignSystemTest` already reads `site/src` from Python, so the plumbing exists — it currently asserts values *match* without ever asking whether they are legible. Add axe-core to the jsdom setup for the rest: **no automated accessibility check runs today across ten workflows.**

**6. Machine-readable counts, cited instead of restated** *(≈30 lines; prevents 23, 24, 25, 26, 33, 50)*
Have the builders write `data/crosswalk/counts.json` and a corpus-breakdown file derived via `lib.is_indicator_url`, then test that every figure cited in CLAUDE.md/context.md matches. **The 2026-08-23 audit already prescribed this and it was applied to the area counts but not the paragraph above them** — that is the evidence the rule needs teeth, not another round of hand-fixing.

**7. Decision- and licence-scope invariants** *(≈2 tests; prevents 1, and the class it belongs to)*
For each of the seven decisions and each licence scope claim, write the invariant over committed bytes and test it there. Decision 1 means scanning every file the data licence covers for observation values, not just the field the parser calls a value. A decision no code can falsify should be reported as unenforced.

**8. Gate-scope-is-a-claim test** *(≈15 lines; prevents 17, and the next instance)*
Assert `setup.cfg`'s `paths_to_mutate` and `tests.yml`'s coverage `--omit` partition `scripts/*.py` identically modulo a named exemption list whose every member must exist on disk. Prefer globs with explicit exclusions over hand-maintained lists — the JS side already gets this free from Stryker.

**9. Regression against the previous audit** *(process, not code; prevents the class in finding 16's history)*
Add a disposition record (`data/audits/DISPOSITIONS.md` or a `disposition:` field per finding) plus a test that every finding heading in the newest audit file has one. Note the inversion: for `data/audits/`, a claim that *no longer* reproduces is a success, not drift.

---

## What this audit did not check

**Network-dependent, in full.** No dimension could reach pordata.pt, ine.pt, ec.europa.eu, bpstat.bportugal.pt or the live Pages site. Therefore unverified: that the site is served at all ("shipped and live"); `pages-health.yml`'s live comparison and the served bundle's asset resolution; whether the 212 INE ids, 118 Eurostat codes, or any crosswalk URL still resolve upstream; whether PORDATA's markup still matches the parsers; whether the `/en` slug tree still exists; the INE/BPstat licence pages (403/404 from cloud IPs) and whether the recorded Eurostat quotes are current; the `@tanstack/charts` release cadence; crawler and indexing behaviour; and every network-derived spike figure (INE series sizes, A1–A4 probes, charts measurements) — read, not recomputed.

**GitHub-side runtime state.** Actions run history (so no finding here can say whether a failure path has already fired in production), branch protection and required checks, whether `main` has been force-pushed, Pages source configuration, open issues, and notification routing for bot-dispatched runs (finding 16's impact half rests on documented platform behaviour, not observation).

**Mutation testing, unevenly.** mutmut was run once by two dimensions (65.6% / 66.0%) and inherited from a pre-existing log by a third (65.4%); StrykerJS was executed once (91.69%). None is a distribution, and mutmut's own docstring documents ~1.6 points of run-to-run variance. Several dimensions did not run either.

**The JS toolchain, partly.** Some dimensions ran `npm run build` (byte-identical output confirmed, including from a fresh `git clone` against the lockfile-exact `node_modules`), vitest (94 tests) and Stryker; others read the config only. No dimension ran `npm ci` from scratch (no network), so lockfile-resolution drift would not have surfaced. One dimension recorded a near-miss worth keeping: an apparent stale-bundle finding turned out to be an artifact of building against a copied `node_modules`.

**Semantic correctness, mostly.** Counts, key-disjointness and reproducibility of both crosswalks were verified exhaustively; **whether a routed INE family or Eurostat cube is the *right* one was hand-read only in samples** — one demonstrably wrong case (finding 11), a handful of Eurostat entries, the largest INE families. The 302 gap concepts were not individually judged (that is item 25). `search.ts` was read and found sound but never executed adversarially against the bundle.

**Sampled rather than exhaustive.** Detail pages: whole-corpus greps for JSON-LD shape, canonical, link names, provenance panels and h1 counts are complete; **visual/structural review is a sample of two to three pages**, none rendered in a real browser except in the edge-probes dimension (Chromium only — no Firefox, WebKit, touch device, screen reader, reduced-motion or forced-colors, and with Google Fonts blocked so all rendering used fallbacks, served at `/` rather than the live `/pordata/` sub-path). Scripts: roughly half of `scripts/` was read in full; `repair_pages.py`, `coverage_gap.py`, the `analyse_*` pair, `probe_ine_availability.py` and most `spike_*.py` were grepped or skimmed. Git history was scanned in the last 60–200 commits for site-only pushes, not fully. Hostile inputs were hand-chosen (~120 calls), not fuzzed. The 2026-08-23 audit's 66 findings were re-tested at 3–14 of 66.

**Not covered at all.** BPstat (no data in the repo — disclosed). Translation quality of the six string tables and the 24-language list (parity counts verified; content not). `ledger/questions.csv` content beyond stratification counts, `outreach/` correspondence, `data/audits/` beyond headline counts. `npm audit` and per-package install-script review. The value-leak scan used the Portuguese decimal form only, so **9,579 is a floor, not a total** — grouped integers could not be separated from year runs in table headers. Git history was not scanned for values in deleted or rewritten files, which a fix to the working tree would not remove.

---

## Blind spots in the audit command itself

The meta dimension's central observation: **every blind spot in the previous run traced back to `.claude/commands/mega-audit.md`**, because that file's dimension list is an enumeration frozen at 2026-08-23 rather than a set of rules.

Concretely: `grep -ci crosswalk` on it → **0**, as do `eurostat` and `indicador` — so the three newest artifacts (both crosswalks, 2,195 pre-rendered pages, 330 provenance panels) are named by no dimension, and dimension 3's field list enumerates *card* fields that predate all of them. `concurrency` → 0. `security`/`inject`/`XSS` → 0 (dimension 9 stops at the CI supply chain and never reaches what the pipeline emits). "reproduce" appears twice, both meaning "a skeptic could reproduce the finding", never "a stranger can rebuild the artifacts". And nothing instructs the run to re-test the previous audit's findings, which is why three CONFIRMED findings and their proposed preventions survived a commit that recorded the backlog as "closed".

Proposed additions, in priority order: **12** stated decisions and licence scope as machine-checkable invariants, plus *a gate's own scope is a claim*; **13** algorithm *correctness* rather than coverage — sample outputs, report precision not recall, and check whether a confidence statistic the code computed is shown to the reader or discarded; **14** regression against the previous audit with an explicit disposition table (noting that dimension 10's "must reproduce" rule inverts for `data/audits/`); **15** concurrency and shared-resource contention between chains, extended to clock and timezone; **16** security of the published artifact and the ingest boundary, distinct from CI supply chain; **17** reproducibility, declared environment, and the repository as an artifact.

One correction the verifier made and this report accepts: a proposed finding that dimension 2's four-file claim inventory was itself the gap did **not** survive — dimension 9 already asks whether a licence "covers what the repo distributes" and dimension 10 already says "explicitly open **every directory in the repo**". The licence claim was inside scope and simply not executed. That is a sharper lesson than the one proposed: **the command's dimensions are broader than the last run's execution of them**, so widening the file is second in priority to making each dimension's checks mechanical enough that they cannot be skipped.