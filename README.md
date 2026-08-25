# pordata

Making Portuguese public statistics consumable.

**Search the catalogue: [caasols.github.io/pordata](https://caasols.github.io/pordata/)** — a
fuzzy index of all 2,196 PORDATA indicators, metadata only, each entry opening a page of
its own with the sources, the revision note and the upstream crosswalk — and a click-out to
PORDATA from there. Machine-readable at stable paths, no key and no rate limit:
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
(Planned work fetches series from INE, Eurostat and BPstat directly, under those bodies'
own reuse terms; PORDATA's own values are never republished.)

## What's here

- **The search site** (`site/` → built into `docs/`): React + Vite + Tailwind with
  shadcn-style components — ranked fuzzy search (accent-blind, typo-tolerant), UI in
  Portuguese and English (four more languages prepared, pending indicator-content
  translation), indicator names in both, area filters, sorting, infinite scroll, light/dark
  theme, and a schema.org `DataCatalog` description of itself. Served as a fully static build
  from GitHub Pages.
- **A self-maintaining pipeline** (GitHub Actions), as a detector→worker pair: a sitemap
  watcher that opens an issue when PORDATA adds or removes indicators and dispatches the
  harvester only when there is work, and a polite harvester (one request per 20 s, metadata
  only) that keeps the catalogue fresh — new pages fetched, updated pages re-harvested,
  removed indicators tombstoned as "descontinuado", the site rebuilt on every change.
- **Quality gates**: unit tests with coverage gates and mutation testing on both sides —
  Python (unittest + mutmut) and the site (vitest + StrykerJS, score gated) — plus a
  **data gate**: the harvest refuses to publish when coverage drops, records vanish, the
  JSONL is corrupt or the sitemap loses a chunk of the corpus, reverting the build and
  opening an issue instead of deploying a degraded catalogue. Counts live in
  [context.md](context.md), measured rather than quoted here.
- **Research** ([context.md](context.md)): measured facts about PORDATA, the four-stage
  problem framing (discovery → extraction → combination → interpretation), decisions, and the
  roadmap — next up, a crosswalk from each indicator to its upstream API series.
- **Audits** (`data/audits/`): periodic cross-consistency sweeps that check the project's own
  plans and claims against measured state, not against each other.

All project state lives in [context.md](context.md).

## Using the data

`catalogue.json` is one object per indicator: `id`, `area` (`portugal` | `municipios` |
`europa`), `name`, `name_en`, `description`, `fontes` (the sources PORDATA credits),
`ultima_atualizacao`, `url`, `harvested_at`, plus `removed: true` for discontinued
indicators and `featured`
for those PORDATA curates into its summary tables. `(area, id)` is the key — ids repeat across
areas. `stats.json` carries counts and the build timestamp. Both are rebuilt by the pipeline
and served from the same origin as the site, so a browser, a script or an agent can read them
directly.

## Licensing

Code is [MIT](LICENSE). The catalogue metadata (`docs/data/`, `data/catalogue/`) is derived
from PORDATA's public indicator pages and is offered under
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) — see [LICENSE-DATA](LICENSE-DATA): reuse it freely with attribution to
**PORDATA / Fundação Francisco Manuel dos Santos** (the curators of the underlying indicators)
and a link back to [pordata.pt](https://www.pordata.pt). No PORDATA data values are contained
in or redistributed by this repository.
