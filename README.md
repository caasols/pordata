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
Portugal's main free statistics database: 2,196 curated indicator pages covering the country, its
308 municipalities and Europe, with series back to 1960. It is excellent at presenting one
indicator to someone who already knows its name, and hard to use for everything else: no API,
no linkable queries, no way to see what exists without already knowing the taxonomy.

The scarce asset is not the numbers — the official sources behind them (INE, Eurostat, Banco
de Portugal) publish openly through real APIs. It is the **curation**: PORDATA's map of
human-meaningful indicator definitions, organised by theme, harmonised across six decades,
each attributed to its source. This project makes that layer machine-readable and searchable.
No PORDATA data values are redistributed — metadata only, values stay at the sources.

## What's here

- **The search site** (`site/` → built into `docs/`): React + Vite + Tailwind with
  shadcn-style components — ranked fuzzy search, UI in Portuguese and English
  (four more languages prepared, pending indicator-content translation),
  indicator names in Portuguese and English, area filters, sorting, infinite scroll,
  light/dark theme. Served as a fully static build from GitHub Pages.
- **A self-maintaining pipeline** (GitHub Actions): a daily sitemap watcher that opens an
  issue when PORDATA adds or removes indicators, and a polite harvester (one request per 20 s,
  metadata only) that keeps the catalogue fresh — new pages fetched, updated pages
  re-harvested, removed indicators tombstoned as "descontinuado", the site rebuilt on every
  change.
- **Quality gates**: unit tests with coverage gates and mutation testing on both sides —
  Python (unittest + mutmut) and the site (vitest + StrykerJS, mutation score gated) — plus a
  data-quality gate that blocks publishing when the harvest degrades. Counts live in
  [context.md](context.md), measured rather than quoted here.
- **Research** ([context.md](context.md)): measured facts about PORDATA, the four-stage
  problem framing (discovery → extraction → combination → interpretation), decisions, and the
  roadmap — next up, a crosswalk from each indicator to its upstream API series.

All project state lives in [context.md](context.md).

## Licensing

Code is [MIT](LICENSE). The catalogue metadata (`docs/data/`, `data/catalogue/`) is derived
from PORDATA's public indicator pages and is offered under
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) — see [LICENSE-DATA](LICENSE-DATA): reuse it freely with attribution to
**PORDATA / Fundação Francisco Manuel dos Santos** (the curators of the underlying indicators)
and a link back to [pordata.pt](https://www.pordata.pt). No PORDATA data values are contained
in or redistributed by this repository.
