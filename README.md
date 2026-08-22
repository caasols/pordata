# pordata

Making Portuguese public statistics consumable.

**Search the catalogue: [caasols.github.io/pordata](https://caasols.github.io/pordata/)** — a
fuzzy, multilingual index of every PORDATA indicator, metadata only, each entry linking back to
its PORDATA page. Machine-readable at stable paths:
[catalogue.json](https://caasols.github.io/pordata/data/catalogue.json) ·
[catalogue.csv](https://caasols.github.io/pordata/data/catalogue.csv) ·
[stats.json](https://caasols.github.io/pordata/data/stats.json).

## Why

[PORDATA](https://www.pordata.pt) — run by the Fundação Francisco Manuel dos Santos — is
Portugal's main free statistics database: 2,268 curated indicators covering the country, its
308 municipalities and Europe, with series back to 1960. It is excellent at presenting one
indicator to someone who already knows its name, and hard to use for everything else: no API,
no linkable queries, no way to see what exists without already knowing the taxonomy.

The scarce asset is not the numbers — the official sources behind them (INE, Eurostat, Banco
de Portugal) publish openly through real APIs. It is the **curation**: PORDATA's map of
human-meaningful indicator definitions, organised by theme, harmonised across six decades,
each attributed to its source. This project makes that layer machine-readable and searchable.
No PORDATA data values are redistributed — metadata only, values stay at the sources.

## What's here

- **The search site** (`docs/`): zero-dependency static page — ranked fuzzy search, six UI
  languages (PT/EN/ES/FR/DE/IT), indicator names in Portuguese and English, light/dark theme.
- **A self-maintaining pipeline** (GitHub Actions): a daily sitemap watcher that opens an
  issue when PORDATA adds or removes indicators, and a polite harvester (one request per 20 s,
  metadata only) that keeps the catalogue fresh — new pages fetched, updated pages
  re-harvested, removed indicators tombstoned as "descontinuado", the site rebuilt on every
  change.
- **Quality gates**: 40+ unit tests with a coverage gate and full mutation testing (mutmut)
  on every push.
- **Research** ([context.md](context.md)): measured facts about PORDATA, the four-stage
  problem framing (discovery → extraction → combination → interpretation), decisions, and the
  roadmap — next up, a crosswalk from each indicator to its upstream API series.

All project state lives in [context.md](context.md).

## Licensing

Code is [MIT](LICENSE). The catalogue metadata (`docs/data/`, `data/catalogue/`) is derived
from PORDATA's public indicator pages and is offered under
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/): reuse it freely with attribution to
**PORDATA / Fundação Francisco Manuel dos Santos** (the curators of the underlying indicators)
and a link back to [pordata.pt](https://www.pordata.pt). No PORDATA data values are contained
in or redistributed by this repository.
