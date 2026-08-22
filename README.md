# pordata

Making Portuguese public statistics consumable.

**Search the catalogue: [caasols.github.io/pordata](https://caasols.github.io/pordata/)** — a
fuzzy, multilingual (PT/EN/ES/FR/DE/IT) index of PORDATA's indicators, metadata only, every
entry linking back to its PORDATA page. Machine-readable:
[catalogue.json](docs/data/catalogue.json) · [catalogue.csv](docs/data/catalogue.csv).

[PORDATA](https://www.pordata.pt) is Portugal's main free statistics database: 2,268 curated
indicators covering the country, its 308 municipalities and Europe, with series reaching back to
1960. It is excellent at presenting a single indicator to someone who already knows its name, and
hard to use for everything else: there is no API, a filtered query cannot be linked or shared,
and combining indicators means manual spreadsheet work.

The scarce asset is not the numbers. The official sources behind them (INE, Eurostat, Banco de
Portugal) already publish openly through real APIs. What only PORDATA has is the curation: a
catalogue of human-meaningful indicator definitions, organised by theme, harmonised across six
decades and 308 municipalities, each attributed to its source. This project explores making that
layer machine-readable: an open catalogue of indicator *metadata* that always points to the
official sources for the values and credits PORDATA prominently. No PORDATA data values are
redistributed.

**Status:** research and problem definition. Nothing built yet, deliberately. FFMS, the
foundation behind PORDATA, has been contacted.

All project state — measured facts, problem framing, decisions and the backlog — lives in
[context.md](context.md).

## Licensing

Code is [MIT](LICENSE). The catalogue metadata (`docs/data/`, `data/catalogue/`) is derived
from PORDATA's public indicator pages and is offered under
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/): reuse it freely with attribution to
**PORDATA / Fundação Francisco Manuel dos Santos** (the curators of the underlying indicators)
and a link back to [pordata.pt](https://www.pordata.pt). No PORDATA data values are contained
in or redistributed by this repository.
