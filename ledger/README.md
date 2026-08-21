# Question Ledger

100 questions a real person might try to answer about Portugal, written in the asker's own
words. This is the demand-side sample that converts the four-stage problem framing in
`context.md` into evidence.

## Provenance

Drafted blind on 2026-08-21: no sitemap, catalogue or PORDATA browsing was consulted during
drafting, so the questions are not contaminated by knowledge of what PORDATA actually holds.
That is deliberate; it is what makes Discovery measurable. Backlog item 2 originally said 30 to
50 questions; expanded to 100 by owner decision on 2026-08-21.

Some questions may have no answer in PORDATA or anywhere. Those are kept on purpose: how a tool
fails on an unanswerable question is part of what the ledger measures.

## Protocol for attempts

Attempt each question with today's public tools (PORDATA's site, the upstream sources, a search
engine — whatever a real person would use). Per question record:

- `status`: `todo` → `done` (answered), `failed` (gave up), or `partial`.
- `stage_broken`: first pipeline stage that failed — `discovery`, `extraction`, `combination`,
  `interpretation` — or `none` if the answer came out clean.
- `minutes`: honest wall-clock time to answer or to give up.
- `notes`: what actually happened, briefly. Where the answer came from if not PORDATA.

The `kind` column is a **prediction**, made at drafting time, of the dominant challenge
(`lookup` = single series, `combo` = needs joining series/geographies/time, `interp` = needs a
baseline or peer group to mean anything). It is a hypothesis to test against `stage_broken`, not
a result.

## Stratification

Spread at drafting time: ~13 themes; national, municipal and European geographies; ten personas.
An audit of this spread against the real indicator list (sitemap slugs, `data/sitemap-urls.txt`
once fetched) is pending — see backlog.

## Files

- `questions.csv` — the ledger itself. One row per question. Commit after each work session;
  git history is the lab notebook.
