---
description: Ultra-deep cross-consistency audit - hidden dependencies, claims vs reality, data-quality gates, drift, dead code
---

Perform an exhaustive cross-consistency audit of this repository. Use a workflow
(multi-agent orchestration) to fan the dimensions out in parallel and adversarially
verify every finding before reporting it. Be comprehensive; token cost is not a
constraint. The purpose is to catch the class of problem where **a plan, claim, or
feature silently depends on something whose real state contradicts it** — the way the
"featured pill" roadmap item once depended on a 29/56 match rate recorded only in a
stats file.

Ground rules for every dimension:
- Verify against **primary sources only**: measured data (`docs/data/stats.json`,
  `data/catalogue/QA.md`, `data/catalogue/REPORT.md`, the JSONL, the sitemap snapshot),
  actual code, actual workflow YAML, actual test output — never against another
  document's claim. A doc agreeing with a doc proves nothing.
- Every finding needs: evidence (file:line or a measured number you computed), impact,
  a proposed fix, and a **prevention** (a test, a QA check, or a CI gate that would have
  caught it automatically). Findings without a prevention are half-finished.
- Adversarially verify each finding before reporting (would a skeptic reproduce it?).
  Rank by severity. No silent caps: say what you did not check.

Audit dimensions:

1. **Roadmap dependency audit.** For every roadmap item in `context.md`: enumerate its
   real preconditions — data-quality metrics, owner decisions, other items, external
   blockers — then verify each against measured state. Flag any item that, executed as
   written and in the stated order, would ship degraded, blocked, or contradicting
   another item. Check the stated execution order for hidden inversions.

2. **Claims vs reality.** Every quantitative or status claim in `CLAUDE.md`,
   `context.md`, `README.md`, and code comments: counts, percentages, coverage numbers,
   test counts, cron schedules, "shipped/live/complete" statements, feature lists.
   Verify each against the thing itself. Stale numbers and aspirational claims are
   findings.

3. **Data-quality gates for user-facing features.** For each thing the site displays or
   filters on (names PT/EN, descriptions, fontes, dates, featured flags, areas,
   tombstones): compute actual coverage/quality from `docs/data/catalogue.json` and the
   raw JSONL. Anything below ~95% coverage that a current or planned UI feature relies
   on is a ship-blocker finding. Propose QA-report thresholds so regressions surface in
   `data/catalogue/QA.md` automatically.

4. **Cross-file drift.** Workflow YAML vs documented schedules; roadmap item numbers
   referenced from code/docs vs the actual items; i18n key parity across all STRINGS
   blocks and AREA_LABELS; keys referenced by `t()` that do not exist; site build output
   in `docs/` vs `site/src` (is the committed bundle current? compare a fresh build);
   `package.json` scripts vs CI workflow steps; gitignore vs tracked files.

5. **Silent failure paths.** Trace every automated chain end to end (sitemap watch →
   dispatch → harvest → build → commit → Pages; nightly cron; issue opening; INE):
   for each step, what happens if it fails? Which failures reach a human and which
   vanish? Flag any failure mode that leaves the system degraded with nobody notified,
   and propose the cheapest detection for each.

6. **Assumption inventory.** List every structural assumption the code makes about
   external reality — sitemap URL shapes, `(area, id)` uniqueness, lastmod format,
   slug patterns, EN/PT id sharing, quadro page structure, fontes boundary words,
   HTML markup in titles — and for each: where is it enforced or tested, and what
   happens when PORDATA changes it? Untested assumptions are findings.

7. **Dead and duplicated code.** Both codebases (`scripts/`, `site/src`): unreachable
   branches (mutation survivors are leads), unused exports/variants/config keys/i18n
   strings, logic duplicated between Python and TypeScript that could drift (e.g.
   name-derivation rules), stale workflow steps.

8. **Edge-case probes.** Actually execute, do not just read: the site headless against
   the built bundle (empty results state, absurdly long query, query of only stopwords,
   localStorage disabled, data fetch 404, all filters + search + sort combined, tiny
   viewport) and the Python pipeline against synthetic hostile inputs (sitemap entry
   with no id, duplicate urls, record with every field empty, future dates, malformed
   JSONL line).

Deliverable: a prioritized findings report (severity-ordered), each finding with
evidence / impact / fix / prevention, followed by a short list of the systemic
preventions worth building immediately (QA thresholds, new CI checks, doc-claim
verifications). Do not change code during the audit; propose, then wait for the owner
to choose what to apply.
