# PORDATA: making Portuguese public statistics consumable

Working notes on why PORDATA is hard to use, what is technically and legally possible on top of
it, and what a useful intervention would look like.

**Status:** research and problem definition. Nothing built, no solution chosen. This is
deliberate.
**Research date:** 2026-08-18. Figures were measured directly against the live site, not taken
from documentation. Re-measure before relying on them.

## What PORDATA is

Portugal's main free public statistics database, run by the Fundação Francisco Manuel dos Santos,
a private non-partisan foundation. It republishes official statistics in a browsable, chart-ready
form across demographics, economy, employment, health, education, housing, environment, justice
and digital, with series often reaching back to 1960.

Products: statistics at three levels (Portugal, the 308 municipalities, Europe), Retratos
(interactive profiles with 30+ indicators for one country or municipality), summary tables,
simulators including an inflation calculator covering 1960 to 2025, and publications.

It is genuinely good at one thing: presenting a single indicator, attractively, to someone who
already knows what they are looking for. Everything below is about what happens when that
condition does not hold.

## Measured facts

| Fact | Value | How established |
|---|---|---|
| Public API | None | No developer or API route in the sitemap; not listed as having an API in either community aggregator |
| Total URLs in sitemap | 5,907 | `PordataSitemap.aspx`, 846 KB |
| Portuguese-language URLs | 2,940 | Excluding the `/en` tree |
| Indicator pages (PT) | 2,268 | 1,054 Portugal, 638 Europe, 504 municipal, plus 29 Retratos, 17 ODS, 15 comunicação, 11 publicações |
| English duplicates | 2,967 URLs | Under `/en` |
| Platform | OutSystems | `OSFillParent` and `OSInline` classes in the markup |
| Query tool | Server-side postbacks | `/db/ambiente+de+consulta/nova+consulta` holds no JSON, XHR or REST endpoint. Only `jquery` and DataTables |
| Machine-readable path | Blocked | `robots.txt` disallows `/*Export*.aspx`, `/*Popup.aspx`, `/*PDF_*.aspx` |
| Source attribution | Present on every indicator page | Sampled page states `Fontes/Entidades: INE, PORDATA` |
| Freshness metadata | Present | Same page: `Última actualização: 2026-06-22`, plus a note that 2021 to 2024 values were revised by INE |
| Legal terms | Restrictive | Prohibit reproduction, commercialisation, transmission and public distribution of content without express authorisation. Silent on APIs, scraping and automated access. No stated attribution requirement |

Indicator pages have stable URLs, for example
`/portugal/populacao+residente++estimativas+a+31+de+dezembro+total+e+por+sexo-5`. The *query
tool* does not: because it runs on postbacks, a filtered view cannot be linked, bookmarked or
shared. You cannot send anyone a URL for "population of Bragança, 1960 to 2025".

## The central insight

**The scarce asset is not the numbers. It is the curation.**

Every indicator page names its upstream source, and those sources publish openly with real APIs:
INE, Eurostat, Banco de Portugal, and various ministries. So the numbers are already free and
already machine-readable elsewhere.

What only PORDATA has is the map: 2,268 human-meaningful indicator definitions, organised by
theme, harmonised across 65 years and 308 municipalities, each attributed to its source. That
curation is what makes a question answerable, and it is what no upstream API provides.

Two consequences follow:

1. The thing worth capturing is the **catalogue** (indicator metadata: title, theme, geography
   level, source entity, last updated, URL, and the English title as a free synonym), not the
   data values. A catalogue of facts *about* PORDATA's holdings is a different legal object from
   a copy of its content.
2. Any real tool should serve values from **INE and Eurostat**, which are openly licensed, using
   the catalogue as the crosswalk from a human question to the right upstream series.

Supporting evidence that this is the actual gap: PORDATA hand-builds Retratos and quadros resumo,
which are pre-assembled joins across indicators. Products built as workarounds are strong
evidence of a need users cannot meet themselves.

## The problem, stated properly

Four failure modes, and in this project's assessment all four are live simultaneously:

1. **Discovery.** With 2,268 indicators filed under a statistical taxonomy, you cannot tell
   whether what you want exists. You must already know the thing is called "Índice de
   envelhecimento" to ask "is my town getting older?".
2. **Extraction.** Once found, getting numbers out is manual and per-indicator, one spreadsheet
   at a time, laid out for eyes rather than machines, with no API and exports disallowed by
   `robots.txt`.
3. **Combination.** Nothing joins. Two indicators, or two geographies, or an indicator against a
   time window means downloading separately and aligning by hand. Every genuine question, such as
   whether wages track housing prices per municipality, is blocked.
4. **Interpretation.** Even holding the numbers, a person cannot tell what is normal, notable or
   fairly comparable. A figure without a baseline, a peer group, or a caveat about a revision or
   definition change is close to useless and can mislead.

These are not four separate problems. They are four stages of one pipeline: find the indicator,
get its numbers out, combine it with something, know what it means. If any stage is broken the
whole path from question to answer is broken. **This is why fixing one stage deeply produces
nothing usable, and a thin slice through all four beats a deep fix to any one.**

## Ecosystem: what already exists

| Source | What it offers | API |
|---|---|---|
| INE (Statistics Portugal) | The primary source behind most PORDATA tables | Yes, JSON, no auth |
| Eurostat | The European comparisons PORDATA republishes | Yes, REST dissemination API |
| Banco de Portugal (BPstat) | Monetary, financial, macro series | Yes, with an OpenAPI spec |
| dados.gov.pt | National open-data portal, CKAN-style | Yes, API key for writes only |
| api.ptdata.org | Community aggregator: geography, weather, public contracts, civil protection, transport, health, aviation, fiscal, plus a handful of macro indicators | Yes, `/v1/*` |
| api.openar.pt | Parliamentary data, different domain, but an excellent model of the shape PORDATA lacks. MIT, no auth, OpenAPI spec, ETags, incremental sync | Yes |
| PORDATA | 2,268 curated indicators | **No** |

`api.ptdata.org` is broad but its economic coverage is a handful of macro series; it does not
carry INE's statistical database or PORDATA's indicator catalogue. Nobody has built the layer
that takes a plain-language question about Portugal and returns the right series with its source.
That is the hole.

`openar.pt` is worth studying closely as a template. One volunteer wrapped a government data
programme in a clean API with an OpenAPI spec, weak ETags, `updated_since` incremental sync and a
100 requests per minute limit, then shipped both a web frontend and an MCP server on top. It is
proof that this scope is achievable by one person. See the sibling project notes in
`~/Documents/raycast-assembleia-da-republica/context.md`.

## Constraints to respect

- **Do not redistribute PORDATA's data values.** The legal terms forbid it and the upstream
  sources make it unnecessary.
- **Harvesting catalogue metadata is the defensible line.** Indicator pages are permitted by
  `robots.txt`; only Export, Popup and PDF paths are disallowed. Any harvest should be politely
  rate-limited and should credit PORDATA prominently.
- **Interpretation errors are the real danger.** A tool that answers a statistics question with a
  confident wrong number is worse than no tool, because a plausible figure gets repeated. Any
  answer must carry its source, its vintage, and any revision caveat. The sampled page's note
  about INE revising 2021 to 2024 is exactly the kind of thing that must not be silently dropped.

## Next steps

Ordered, and deliberately stopping short of committing to a build.

1. **Email FFMS.** Highest leverage action available. Their stated mission is making this data
   available; they may hand over the catalogue, bless a project, or reveal that an API is already
   planned. Any of those three changes everything downstream. Also worth contacting openAR's
   maintainer, who has solved the adjacent problem.
2. **Write the Question Ledger.** 30 to 50 questions a real person would ask, in their own words.
   Then attempt each one with today's tools, recording which of the four stages broke and how
   long it took. This converts an opinion into evidence and tells you what deserves building.
3. **Only then decide.** Candidate directions, recorded so they are not re-derived:
   - The **catalogue**: harvest indicator metadata, publish as open JSON and CSV with search.
     Simultaneously fixes Discovery, measures the other three stages, and is the crosswalk any
     real tool needs.
   - An **MCP server or skill** over INE and Eurostat, grounded in the catalogue. Note that a
     parliamentary equivalent already exists (`@openar/mcp`), which is a useful precedent for
     shape and scope.
   - A **consumer site**: type a question, get a chart plus its source. Broadest reach, most work,
     hardest to build from a phone.
   - **Data stories**: use existing data for a few striking visual pieces. Most immediately
     satisfying, leaves no reusable tool behind.

An explicit warning to future-me: going straight to the MCP is the tempting option and the wrong
first move. Without the catalogue, a model guesses at series identity, and it will guess
confidently and wrongly. For public statistics that is the worst available failure mode, and it
leaves Interpretation entirely unaddressed.

## Repo housekeeping

The `.gitignore` inherited from the initial commit is the GitHub template for **AL / Dynamics 365
Business Central** (`.alpackages/`, `*.bclicense`, `rad.json`). It is harmless but wrong for this
project. Replace it when the project's actual language is known.

## Verification commands

```bash
curl -s https://www.pordata.pt/robots.txt
curl -s https://www.pordata.pt/PordataSitemap.aspx | grep -c '<loc>'
curl -s https://www.ine.pt/xportal/xmain?xpid=INE\&xpgid=ine_api
curl -s https://api.ptdata.org/v1/economy/exchange-rates | head -c 300
```
