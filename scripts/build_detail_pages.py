#!/usr/bin/env python3
"""A page per indicator, pre-rendered (roadmap 15).

Until now every result card opened pordata.pt. That was always a
placeholder: the card was rebuilt as a *routing decision* with an inert
chart slot precisely so a page of this project's own could inherit it.

**Pre-rendered, not hash-routed.** The roadmap leans this way and the
reason is the project's stated purpose: hash routes are unshareable and
invisible to crawlers, and a catalogue whose whole claim is machine
discoverability cannot have 2,195 indicators with no addresses. Each
page gets a real canonical URL and its own `Dataset` JSON-LD.

**No JavaScript bundle.** A metadata page is a document, not an app, so
these are plain HTML against one shared stylesheet — a few KB that render
instantly, rather than the SPA's 112 KB of bundle to display twenty
fields. The only script is nine lines restoring the reader's stored
theme and language, using the same `localStorage` keys the SPA writes,
so crossing between them does not flip appearance.

**Written only when the bytes change.** 2,195 files regenerated on every
harvest would put a few MB of identical HTML into git history every
night. The generator compares before writing, so a harvest that touched
five indicators rewrites five pages.

**One source of truth for the theme.** The colour tokens are read out of
`site/src/index.css` at build time rather than copied here; if that
block moves or is renamed the build fails loudly instead of quietly
serving pages in stale colours. The same rule `unit-terms.json` already
follows.

**What is on the page, and why.** The metadata PORDATA shows, plus the
two things it does not: the **revision note** rendered *with* the
indicator rather than in a footer (decision 5 — a caveat that does not
travel with the series is a caveat nobody reads), and the **crosswalk**
as provenance — which INE operation publishes this, at what
granularity and periodicity, and the candidate series with links into
INE's API. That last section is the thing no one else has.

The chart stays inert and says so, with the click-out to PORDATA beside
it. It becomes real in item 14, and the slot is already shaped for it.
"""

import hashlib
import html
import json
import pathlib
import re
import sys

CATALOGUE = pathlib.Path("docs/data/catalogue.json")
CROSSWALK = pathlib.Path("data/crosswalk/ine.json")
EUROSTAT_CROSSWALK = pathlib.Path("data/crosswalk/eurostat.json")
INE_CSV = pathlib.Path("data/ine/indicators.csv")
THEME_CSS = pathlib.Path("site/src/index.css")
OUT_ROOT = pathlib.Path("docs/indicador")
# Its own file rather than an edit to docs/sitemap.xml: that one is
# hand-maintained and lists the catalogue downloads, this one is 2,195
# generated URLs. robots.txt names both, which is how a crawler is meant
# to find more than one.
SITEMAP = pathlib.Path("docs/sitemap-indicadores.xml")
SITE = "https://caasols.github.io/pordata"
# Eurostat's routes are the dataset code in a template — measured
# across all 7,572 rows by `build_eurostat_crosswalk.py`, which asserts
# it on every build, so the crosswalk stores codes and the page builds
# the links.
EUROSTAT_BROWSER = ("https://ec.europa.eu/eurostat/databrowser/product"
                    "/view/{}")
EUROSTAT_TSV = ("https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1"
                "/data/{}/?format=TSV")
INE_PAGE = "https://www.ine.pt/xurl/indx/{}/PT"
INE_JSON = ("https://www.ine.pt/ine/json_indicador/pindica.jsp"
            "?op=2&varcd={}&lang=PT")

# Naming "Public Sans" in a font stack does not load it. The SPA pulls it
# from Google Fonts in its own <head>; without these three lines the
# detail pages fell through to the system sans and looked like a
# different site next to the index.
FONT_LINKS = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
    '<link href="https://fonts.googleapis.com/css2?family=Public+Sans:'
    'wght@400;500;600;700&display=swap" rel="stylesheet">')

# Lifted verbatim from site/src/index.css so the two cannot drift. The
# generator asserts both blocks exist rather than falling back to a copy.
ROOT_TOKENS = re.compile(r"^:root\s*\{(.*?)^\}", re.S | re.M)
DARK_TOKENS = re.compile(r"^\.dark\s*\{(.*?)^\}", re.S | re.M)
# The radius scale lives in the @theme inline block, not in :root, and
# `rounded-sm` / `rounded-lg` are what the Badge and Card use. Lifted
# rather than re-derived: writing calc(var(--radius) - 4px) here again
# would be a second copy of a number that has already moved once.
RADIUS_SCALE = re.compile(r"^\s*(--radius-(?:sm|md|lg):[^;]+;)", re.M)
# Also lifted: the detail pages were declaring a four-item hand-written
# subset of the site's stack, so the two rendered in different fallbacks
# the moment Public Sans failed to load.
FONT_STACK = re.compile(r"^\s*(--font-sans:[^;]+;)", re.M | re.S)

AREA_LABELS = {
    "portugal": ("Portugal", "Portugal"),
    "municipios": ("Municípios", "Municipalities"),
    "europa": ("Europa", "Europe"),
}

# Labels carry both languages and a nine-line script picks one, rather
# than doubling the page count for a translation of twelve words.
LABELS = {
    "back": ("Voltar à pesquisa", "Back to search"),
    "sources": ("Fontes", "Sources"),
    "updated": ("Última atualização", "Last updated"),
    "unit": ("Unidade", "Unit"),
    "area": ("Área", "Area"),
    "coverage": ("Cobertura", "Coverage"),
    "nameEn": ("Nome em inglês", "Name in English"),
    "revision": ("Nota de revisão da PORDATA", "PORDATA revision note"),
    "revisionWhy": (
        "A PORDATA assinala que esta série foi revista. A ressalva aparece "
        "aqui, junto ao indicador, e não em rodapé.",
        "PORDATA notes that this series was revised. The caveat belongs "
        "with the indicator, not in a footer."),
    "provenance": ("De onde vêm os números", "Where the numbers come from"),
    "operation": ("Operação estatística do INE", "INE statistical operation"),
    "theme": ("Tema", "Theme"),
    "geo": ("Detalhe geográfico", "Geographic detail"),
    "periodicity": ("Periodicidade", "Periodicity"),
    "candidates": ("Séries candidatas no INE", "Candidate INE series"),
    "candidatesWhy": (
        "Um indicador da PORDATA corresponde a uma <em>família</em> de "
        "séries do INE, separadas por geografia, periodicidade e versão. "
        "A escolha da série faz-se ao ir buscar os valores, não aqui — "
        "guardar uma só seria escolher ao acaso e registar a escolha como "
        "facto.",
        "One PORDATA indicator corresponds to a <em>family</em> of INE "
        "series, split by geography, periodicity and vintage. Choosing "
        "one happens when the values are fetched, not here — storing a "
        "single id would be choosing arbitrarily and recording the choice "
        "as fact."),
    "datasets": ("Conjuntos de dados candidatos no Eurostat",
                 "Candidate Eurostat datasets"),
    "datasetsWhy": (
        "O Eurostat publica <em>cubos</em> multidimensionais, não séries "
        "já fatiadas: um indicador da PORDATA corresponde a um conjunto "
        "de dados <em>mais</em> um filtro sobre as suas dimensões. Ao "
        "contrário da família do INE, estes candidatos são "
        "<em>rivais</em> — só um está certo — pelo que uma lista longa é "
        "uma pergunta em aberto, não um facto sobre o Eurostat.",
        "Eurostat publishes multi-dimensional <em>cubes</em>, not "
        "pre-sliced series: one PORDATA indicator corresponds to a "
        "dataset <em>plus</em> a filter over its dimensions. Unlike the "
        "INE family these candidates are <em>rivals</em> — only one is "
        "right — so a long list is an open question rather than a fact "
        "about Eurostat."),
    "filter": ("Recorte pedido", "Breakdown wanted"),
    "filterWhy": (
        "A PORDATA pede este recorte; o catálogo do Eurostat guarda "
        "títulos, não nomes de dimensões, pelo que <strong>não foi "
        "verificado</strong> que algum destes cubos possa ser fatiado "
        "assim. Fica registado por verificar em vez de dado como certo.",
        "PORDATA asks for this breakdown; Eurostat's catalogue stores "
        "titles, not dimension names, so it is <strong>not "
        "verified</strong> that any of these cubes can be sliced that "
        "way. Recorded as unverified rather than assumed."),
    "period": ("Período coberto", "Period covered"),
    "noEurostat": ("Sem correspondência no Eurostat", "No Eurostat match"),
    "noEurostatWhy": (
        "O emparelhador recusa-se a adivinhar: nenhum conjunto de dados "
        "do Eurostat passou os filtros para este indicador. Isso não "
        "prova que não exista — prova que não temos a certeza.",
        "The matcher refuses to guess: no Eurostat dataset passed the "
        "filters for this indicator. That is not evidence none exists — "
        "it is evidence we are not sure."),
    "discontinued": ("descontinuado", "discontinued"),
    "noCrosswalk": ("Sem correspondência no INE", "No INE match"),
    "noCrosswalkWhy": (
        "O emparelhador recusa-se a adivinhar: nenhuma série do INE passou "
        "os filtros para este indicador. Isso não prova que não exista — "
        "prova que não temos a certeza.",
        "The matcher refuses to guess: no INE series passed the filters "
        "for this indicator. That is not evidence none exists — it is "
        "evidence we are not sure."),
    "chartSoon": ("Gráfico em breve", "Chart coming soon"),
    "chartWhy": (
        "Este projeto ainda não arquiva os valores. Até lá, a PORDATA "
        "mostra-os.",
        "This project does not archive the values yet. Until it does, "
        "PORDATA shows them."),
    "openAt": ("Ver na PORDATA", "View on PORDATA"),
    "featured": ("No quadro-resumo da PORDATA", "In PORDATA's summary table"),
    "metadataOnly": (
        "Apenas metadados. Os valores estão na PORDATA e nas fontes "
        "oficiais.",
        "Metadata only. The values live on PORDATA and at the official "
        "sources."),
    "notAvailable": ("n/d", "n/a"),
}

STYLESHEET = """
/* Every value below is lifted from the component the card already uses,
   so the two read as one design rather than two. The sources:
     .chip      <- components/ui/badge.tsx, `secondary` variant
                   (rounded-sm px-2 py-0.5 text-xs font-medium)
     .field .k  <- App.tsx Meta label  (11px, .1em, muted-foreground)
     .field .v  <- App.tsx Meta value  (text-xs), stepped up one size
                   because this is a page to read, not a row to scan
     .card      <- components/ui/card.tsx
                   (rounded-lg border-border bg-card shadow-xs)
     .cta       <- components/ui/button.tsx, `outline` variant — the
                   only button this site has; there is no filled primary
                   variant, so the orange CTA was inventing an idiom
     .chart     <- App.tsx ChartSlot
                   (dashed border-border/70, bg-muted/30, 11px label)
   A hand-written approximation is how the first version ended up with
   an orange pill where the card has a grey one. */
*,*::before,*::after{box-sizing:border-box}
body{margin:0;background:var(--background);color:var(--foreground);
 font:16px/1.55 var(--font-sans);-webkit-font-smoothing:antialiased}
main{max-width:46rem;margin:0 auto;padding:1.5rem 1.15rem 4rem}
a{color:inherit}
h1{font-size:1.5rem;line-height:1.3;letter-spacing:-.025em;
 margin:.2rem 0 .35rem;font-weight:700}
h2{font-size:.95rem;margin:2rem 0 .6rem;font-weight:600}
h3{font-size:.85rem;margin:1.3rem 0 .2rem;font-weight:600}
.back{display:inline-block;margin-bottom:1.1rem;font-size:.875rem;
 color:var(--muted-foreground);text-decoration:none}
.back:hover{color:var(--foreground)}
.coverage{margin:0 0 .9rem;color:var(--muted-foreground);font-size:.875rem}

/* badge.tsx: rounded-sm px-2 py-0.5 text-xs font-medium, secondary */
.chips{display:flex;flex-wrap:wrap;gap:.35rem;margin:.85rem 0 1.5rem}
.chip{display:inline-flex;align-items:center;border-radius:var(--radius-sm);
 padding:.125rem .5rem;font-size:.75rem;line-height:1rem;font-weight:500;
 background:var(--secondary);color:var(--secondary-foreground)}
.chip.gone{background:var(--destructive);color:var(--destructive-foreground)}

/* card.tsx */
.card{border:1px solid var(--border);border-radius:var(--radius-lg);
 background:var(--card);color:var(--card-foreground);
 box-shadow:0 1px 2px 0 #0000000d;padding:1rem 1.1rem}

/* The card's own meta grid: a cell per field, label above value. Two
   things have to hold at once. Stability comes from a *fixed* three
   columns and a cell that is never omitted — `auto-fit` plus a dropped
   empty field is what made ÁREA land where UNIDADE sat on the page
   before. Legibility comes from keeping the card's stacked cell rather
   than a two-column label/value list, which reads as a form and leaves
   a wide empty gutter.
   `wide` fields span the row because they are sentences: fontes, the
   English name, the INE operation. That is fixed per field, not decided
   from the value, or the layout is back at the mercy of the data.
   App.tsx Meta supplies the type: the label is the card's exactly, the
   value steps from text-xs to .8125rem because a page is read, not
   scanned. */
.meta{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));
 gap:1rem .9rem}
.field{min-width:0;display:flex;flex-direction:column}
.field.wide{grid-column:1/-1}
.field .k{font-size:11px;text-transform:uppercase;letter-spacing:.1em;
 color:var(--muted-foreground);line-height:1.5}
.field .v{margin-top:.1rem;font-size:.8125rem;line-height:1.45;
 overflow-wrap:anywhere;font-variant-numeric:tabular-nums}
/* the card dims a missing value so the gap reads as deliberate; the
   unit is genuinely absent on 48% of rows */
.na{color:var(--muted-foreground);font-style:italic}

.note{border-left:2px solid var(--border);padding:.1rem 0 .1rem .85rem;
 margin:.5rem 0;font-size:.875rem;line-height:1.5}
.why{color:var(--muted-foreground);font-size:.8rem;margin:.3rem 0 0;
 line-height:1.5}

ol.series{list-style:none;padding:0;margin:.5rem 0 0}
ol.series li{padding:.45rem 0;border-top:1px solid var(--border);
 font-size:.8125rem;line-height:1.45}
ol.series li:first-child{border-top:0}
ol.series .id{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;
 font-size:.7rem;color:var(--muted-foreground);margin-right:.45rem}
a.api{margin-left:.4rem;font-size:11px;letter-spacing:.08em;
 text-transform:uppercase;color:var(--muted-foreground);
 text-decoration:none;border:1px solid var(--border);
 border-radius:var(--radius-sm);padding:.05rem .35rem}
a.api:hover{color:var(--foreground)}

/* App.tsx ChartSlot: same dashed idiom and same 11px label, taller
   because on this page it is the focal point rather than a footnote */
.chart{border:1px dashed var(--border);border-radius:var(--radius-lg);
 padding:1.6rem 1.1rem;text-align:center;background:var(--muted)}
.chart .slot{display:block;font-size:11px;text-transform:uppercase;
 letter-spacing:.08em;color:var(--muted-foreground)}
.cta{display:inline-flex;align-items:center;justify-content:center;
 margin-top:.9rem;height:2rem;padding:0 .625rem;
 border-radius:var(--radius-md);border:1px solid var(--border);
 background:transparent;color:var(--foreground);text-decoration:none;
 font-size:.875rem;font-weight:500;transition:background-color .15s}
.cta:hover{background:var(--accent);color:var(--accent-foreground)}
footer{margin-top:3rem;border-top:1px solid var(--border);padding-top:1rem;
 color:var(--muted-foreground);font-size:.875rem}

/* the SPA rings every focusable thing; these pages had the browser
   default, which is both inconsistent and worse. Full opacity and an
   offset ring: at 30% the indicator computed to 1.29:1 against WCAG
   1.4.11's 3:1, and `outline:none` beside it made that worse than
   shipping no focus style at all — every link on 2,195 pages. */
a:focus-visible{outline:none;border-radius:var(--radius-sm);
 box-shadow:0 0 0 2px var(--background),0 0 0 5px var(--ring)}
[data-en]{display:none}
html[lang="en"] [data-pt]{display:none}
html[lang="en"] [data-en]{display:revert}
"""

# Same keys the SPA writes, so crossing between them does not flip
# appearance. Wrapped in try/catch because private mode throws on read.
BOOT = (
    '<script>(function(){try{var t=localStorage.getItem("theme"),'
    'l=localStorage.getItem("lang");'
    'if(t==="dark"||(t!=="light"&&'
    'matchMedia("(prefers-color-scheme: dark)").matches))'
    'document.documentElement.classList.add("dark");'
    'if(l==="en")document.documentElement.lang="en";}catch(e){}})()</script>'
)


def theme_tokens(path: pathlib.Path = None) -> str:
    """The :root and .dark blocks, read from the site's own stylesheet."""
    css = (path or THEME_CSS).read_text(encoding="utf-8")
    root, dark = ROOT_TOKENS.search(css), DARK_TOKENS.search(css)
    if not root or not dark:
        raise SystemExit(
            "build_detail_pages: could not find the :root and .dark token "
            f"blocks in {path or THEME_CSS}. They are the single source of "
            "truth for the detail pages' colours — failing rather than "
            "shipping a stale copy.")
    radius = "\n".join(RADIUS_SCALE.findall(css))
    font = FONT_STACK.search(css)
    if not font:
        raise SystemExit(
            "build_detail_pages: no --font-sans in "
            f"{path or THEME_CSS}. The detail pages render in the site's "
            "typeface or they are a different site.")
    return (f":root{{{root.group(1).strip()}\n{radius}\n"
            f"{font.group(1).strip()}}}\n"
            f".dark{{{dark.group(1).strip()}}}\n")


def esc(value) -> str:
    return html.escape(str(value or ""), quote=True)


def both(key: str) -> str:
    """A label in both languages; CSS shows one."""
    pt, en = LABELS[key]
    return f'<span data-pt>{pt}</span><span data-en>{en}</span>'


def raw_both(key: str) -> str:
    """As `both`, for labels whose text carries its own markup."""
    pt, en = LABELS[key]
    return f'<span data-pt>{pt}</span><span data-en>{en}</span>'


UNIT_TERMS = pathlib.Path("site/src/lib/unit-terms.json")
UNIT_SEPARATOR = " - "


def unit_tables() -> dict:
    """The same vocabulary the SPA renders from.

    Read rather than reimplemented, and read from the file the SPA
    imports and `qa_catalogue.py` gates against, because a second copy is
    a second thing to keep true. The page and the card disagreed on
    1,111 rows for an English reader — `m³ - Millions` on the card,
    `m 3 - Milhões` on the page it opens — which is a contradiction one
    click apart on the canonical URL people share."""
    return json.loads(UNIT_TERMS.read_text(encoding="utf-8"))


def format_unit(unit: str, lang: str, tables: dict) -> str:
    """A port of `site/src/lib/units.ts formatUnit`.

    Portuguese passes through its table too: those entries are repairs,
    not translations — the chart caption loses superscripts, so `m 3` is
    wrong in Portuguese as well. An unknown term falls back rather than
    blanking."""
    if not unit:
        return ""
    table = tables.get(lang) or {}
    repair = tables.get("pt") or {}
    parts = [p.strip() for p in unit.split(UNIT_SEPARATOR) if p.strip()]
    return UNIT_SEPARATOR.join(table.get(p) or repair.get(p) or p
                               for p in parts)


def unit_cell(unit: str, tables: dict) -> str:
    """The unit in both languages, so the switch reaches it like every
    other visible string."""
    if not unit:
        return ""
    pt = esc(format_unit(unit, "pt", tables))
    en = esc(format_unit(unit, "en", tables))
    if pt == en:
        return pt
    return f'<span data-pt>{pt}</span><span data-en>{en}</span>'


def field(key: str, value: str, wide: bool = False) -> str:
    """One cell — label above value, exactly like the card's `Meta`, and
    **always rendered**.

    Two things have to hold at once and the first attempt at this traded
    one for the other. Dropping an empty cell let the rest slide up, so
    `ÁREA` sat where `UNIDADE` had been on the page before; replacing the
    grid with a two-column list fixed that and lost the card's design —
    a narrow label column against a wide empty gutter, which is a form,
    not a card. So: keep the card's stacked cell, and get stability from
    a *fixed* column count plus a cell that is never omitted.

    `wide` is a property of the field, not of its content — `fontes` and
    the English name are sentences and always span the row. Deciding
    that per value would put the layout back at the mercy of the data.
    """
    shown = value or f'<span class="na">{both("notAvailable")}</span>'
    cls = "field wide" if wide else "field"
    return (f'<div class="{cls}"><span class="k">{both(key)}</span>'
            f'<span class="v">{shown}</span></div>')


def page_path(row: dict) -> pathlib.Path:
    return OUT_ROOT / row["area"] / str(row["id"]) / "index.html"


def page_url(row: dict) -> str:
    return f"{SITE}/indicador/{row['area']}/{row['id']}/"


def dataset_description(row: dict, tables: dict) -> str:
    """A sentence built from fields already in hand.

    Google requires `description` for a Dataset to be eligible at all,
    and all 2,195 blocks omitted it — on pages whose stated reason for
    being pre-rendered is machine discoverability. Synthesised rather
    than invented: every clause is a field, so it cannot say more than
    the catalogue knows. PORDATA's own `description` is not used — 96.3%
    of them are its SEO template."""
    name = row.get("title") or row.get("name") or ""
    area = AREA_LABELS.get(row["area"], (row["area"],))[0]
    parts = [f"{name} — {area}."]
    if row.get("breakdown"):
        parts.append(f"Cobertura: {row['breakdown']}.")
    unit = format_unit(row.get("unit") or "", "pt", tables)
    if unit:
        parts.append(f"Unidade: {unit}.")
    if row.get("fontes"):
        parts.append(f"Fontes: {', '.join(row['fontes'])}.")
    parts.append("Metadados apenas; os valores estão na PORDATA e nas "
                 "fontes oficiais.")
    return " ".join(parts)


def json_ld(row: dict, entry: dict | None, tables: dict) -> str:
    """A `Dataset` per indicator.

    `isBasedOn` points at PORDATA's page and, where the crosswalk is
    confident enough to name one, at the upstream series or datasets
    whose title is the indicator's — the machine-readable form of the
    same claim the provenance section makes to a reader. Only the exact
    matches: a crawler cannot read "rival candidates, choice deferred"
    off a list of URLs, so listing a whole family here would assert
    something the page itself declines to."""
    based_on = [row["url"]]
    if entry:
        route = (EUROSTAT_BROWSER if entry.get("source") == "Eurostat"
                 else INE_PAGE)
        based_on += [route.format(i) for i in entry.get("exact_title", [])]
    # The variable measured is the indicator; the unit is a property of
    # it. Assigning the unit directly told crawlers the measured variable
    # was "Indivíduo" or "%" on 1,138 pages.
    measured = {
        "@type": "PropertyValue",
        "name": row.get("title") or row.get("name"),
    }
    unit = format_unit(row.get("unit") or "", "pt", tables)
    if unit:
        measured["unitText"] = unit
    data = {
        "@context": "https://schema.org",
        "@type": "Dataset",
        "name": row.get("title") or row.get("name"),
        "alternateName": row.get("name_en") or None,
        "description": dataset_description(row, tables),
        "url": page_url(row),
        "isBasedOn": based_on,
        "creator": {"@type": "Organization", "name": "PORDATA"},
        # The metadata on this page is the thing being licensed, and it
        # is the same CC BY 4.0 the catalogue ships under. Stating it
        # here rather than only in a file makes it machine-readable,
        # which is the whole argument for pre-rendering these.
        "license": "https://creativecommons.org/licenses/by/4.0/",
        "spatialCoverage": AREA_LABELS.get(row["area"], (row["area"],))[0],
        "dateModified": row.get("ultima_atualizacao") or None,
        "variableMeasured": measured,
        "isAccessibleForFree": True,
    }
    keywords = [AREA_LABELS.get(row["area"], (row["area"],))[0]]
    keywords += [o for o in (row.get("orgs") or [])]
    data["keywords"] = keywords
    # `operation` is INE's field and Eurostat entries have no equivalent,
    # so naming the provider from it emitted `{"name": null}` on every
    # europa page. A provider without a name is not a provider.
    provider = (entry.get("operation") or entry.get("source")) if entry else ""
    if provider:
        data["provider"] = {"@type": "Organization", "name": provider}
    return escape_for_script(
        json.dumps({k: v for k, v in data.items() if v},
                   ensure_ascii=False, separators=(",", ":")))


def escape_for_script(payload: str) -> str:
    r"""JSON that is safe to sit inside a `<script>` element.

    HTML-escaping it would corrupt the JSON, so the standard mitigation
    applies instead: `<` and `>` become their `\u` escapes, which a JSON
    parser decodes back to the same string while `</script>` can never
    appear literally. Every value in here is an indicator name PORDATA
    wrote, so "it will never contain markup" is not a claim this project
    gets to make — and a name that closed the script element early would
    put the rest of the block into the document as live HTML.
    """
    return (payload.replace("<", "\\u003c").replace(">", "\\u003e")
            .replace("\u2028", "\\u2028").replace("\u2029", "\\u2029"))


def provenance(entry: dict | None, titles: dict,
               area: str = "portugal") -> str:
    """The crosswalk, rendered as the reader meets it.

    Dispatched on the entry's `source` rather than on the area, because
    the two crosswalks answer differently shaped questions and saying so
    is the point: INE's candidates are a *family* of pre-sliced series
    that all belong to the indicator, so a long list is a fact about
    INE; Eurostat's are *rival cubes* of which one is right, so a long
    list is an open question. A single panel that blurred them would
    misreport both."""
    if not entry:
        absent, why = (("noEurostat", "noEurostatWhy") if area == "europa"
                       else ("noCrosswalk", "noCrosswalkWhy"))
        return (f'<h2>{both("provenance")}</h2>'
                f'<div class="card"><strong>{both(absent)}</strong>'
                f'<p class="why">{both(why)}</p></div>')
    if entry.get("source") == "Eurostat":
        return eurostat_provenance(entry)
    rows = "".join(
        f'<li><span class="id">{esc(i)}</span>'
        f'<a href="{esc(INE_PAGE.format(i))}" rel="noopener">'
        f'{esc(titles.get(i, i))}</a>'
        # the machine-readable route, which is the whole point of having
        # a crosswalk: an id you cannot fetch from is a footnote
        f'<a class="api" rel="noopener" href="{esc(INE_JSON.format(i))}">'
        f'JSON</a></li>'
        for i in entry["candidates"][:12])
    more = ""
    if entry["n_candidates"] > 12:
        more = (f'<p class="why">+{entry["n_candidates"] - 12} '
                f'<span data-pt>outras séries na mesma família</span>'
                f'<span data-en>more series in the same family</span></p>')
    return (
        f'<h2>{both("provenance")}</h2><div class="card">'
        f'<div class="meta">'
        + field("operation", esc(entry.get("operation")), wide=True)
        + field("theme", esc(entry.get("theme")))
        + field("geo", esc(", ".join(entry.get("geo_levels") or [])))
        + field("periodicity", esc(", ".join(entry.get("periodicities") or [])))
        + f'</div><h3>{both("candidates")}</h3>'
        f'<p class="why">{raw_both("candidatesWhy")}</p>'
        f'<ol class="series">{rows}</ol>{more}</div>')


def eurostat_provenance(entry: dict) -> str:
    """The Eurostat panel, whose defining feature is what it refuses to
    claim: the breakdown is shown as *wanted*, never as satisfied."""
    stored = entry.get("titles") or {}
    exact = set(entry.get("exact_title") or [])
    rows = "".join(
        f'<li><span class="id">{esc(code)}</span>'
        f'<a href="{esc(EUROSTAT_BROWSER.format(code))}" rel="noopener">'
        f'{esc(stored.get(code, code))}</a>'
        # the fetch route, which is the whole point of having a
        # crosswalk: a code you cannot fetch from is a footnote
        f'<a class="api" rel="noopener" '
        f'href="{esc(EUROSTAT_TSV.format(code))}">TSV</a>'
        + ('<span class="chip" data-pt>título idêntico</span>'
           '<span class="chip" data-en>title matches</span>'
           if code in exact else '')
        + '</li>'
        for code in entry.get("candidates", [])[:12])
    more = ""
    if entry.get("n_candidates", 0) > 12:
        more = (f'<p class="why">+{entry["n_candidates"] - 12} '
                f'<span data-pt>outros conjuntos de dados candidatos</span>'
                f'<span data-en>more candidate datasets</span></p>')
    wanted = entry.get("filter") or ""
    caveat = (f'<h3>{both("filter")}</h3>'
              f'<p class="why"><strong>{esc(wanted)}</strong> — '
              f'{raw_both("filterWhy")}</p>') if wanted else ""
    return (
        f'<h2>{both("provenance")}</h2><div class="card">'
        f'<div class="meta">'
        + field("theme", esc(entry.get("theme")), wide=True)
        + field("period", esc(", ".join(entry.get("period") or [])))
        + f'</div>{caveat}<h3>{both("datasets")}</h3>'
        f'<p class="why">{raw_both("datasetsWhy")}</p>'
        f'<ol class="series">{rows}</ol>{more}</div>')


def render(row: dict, entry: dict | None, titles: dict, css_ref: str,
           tables: dict | None = None) -> str:
    tables = unit_tables() if tables is None else tables
    title = row.get("title") or row.get("name") or ""
    coverage = row.get("breakdown") or ""
    area_pt, area_en = AREA_LABELS.get(row["area"], (row["area"], row["area"]))
    sources = ", ".join(row.get("fontes") or [])
    chips = [f'<span class="chip">{area_pt}</span>']
    if row.get("featured"):
        chips.append(f'<span class="chip">{both("featured")}</span>')
    if row.get("removed"):
        chips.append(f'<span class="chip gone">{both("discontinued")}</span>')
    revision = ""
    if row.get("revision"):
        revision = (f'<h2>{both("revision")}</h2>'
                    f'<div class="note">{esc(row["revision"])}'
                    f'<p class="why">{both("revisionWhy")}</p></div>')
    return f"""<!DOCTYPE html>
<html lang="pt">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} — pordata map</title>
<meta name="description" content="{esc(title)} — {esc(sources)}. {LABELS['metadataOnly'][0]}">
<link rel="canonical" href="{page_url(row)}">
<meta property="og:type" content="article">
<meta property="og:title" content="{esc(title)}">
<meta property="og:url" content="{page_url(row)}">
{FONT_LINKS}
<link rel="stylesheet" href="{css_ref}">
{BOOT}
<script type="application/ld+json">{json_ld(row, entry, tables)}</script>
</head>
<body>
<main>
<a class="back" href="{SITE}/">&larr; {both("back")}</a>
<h1>{esc(title)}</h1>
{f'<p class="coverage">{esc(coverage)}</p>' if coverage else ''}
<div class="chips">{"".join(chips)}</div>
<div class="card"><div class="meta">
{field("sources", esc(sources), wide=True)}
{field("updated", esc(row.get("ultima_atualizacao")))}
{field("unit", unit_cell(row.get("unit") or "", tables))}
{field("area", f'<span data-pt>{area_pt}</span><span data-en>{area_en}</span>')}
{field("nameEn", esc(row.get("name_en")), wide=True)}
</div></div>
{revision}
<div class="chart"><span class="slot">{both("chartSoon")}</span>
<p class="why">{both("chartWhy")}</p>
<a class="cta" href="{esc(row['url'])}" rel="noopener">{both("openAt")}</a>
</div>
{provenance(entry, titles, row["area"])}
<footer>{both("metadataOnly")}</footer>
</main>
</body>
</html>
"""


def ine_titles(path: pathlib.Path = None) -> dict:
    """id -> title, for the candidate list. Absent cache is not fatal:
    the ids still link, they just read as ids."""
    import csv
    import io
    target = path or INE_CSV
    if not target.exists():
        return {}
    csv.field_size_limit(sys.maxsize)
    with io.open(target, encoding="utf-8") as handle:
        return {r["id"]: r["title"] for r in csv.DictReader(handle)}


def write_if_changed(path: pathlib.Path, text: str) -> bool:
    """True when the file was actually written.

    2,195 files rewritten nightly would put megabytes of identical HTML
    into git history for nothing."""
    data = text.encode("utf-8")
    if path.exists() and path.read_bytes() == data:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return True


def build(rows: list, crosswalk: dict, titles: dict,
          root: pathlib.Path = None) -> dict:
    out = root or OUT_ROOT
    css = theme_tokens() + STYLESHEET
    tables = unit_tables()
    digest = hashlib.sha256(css.encode("utf-8")).hexdigest()[:8]
    written = int(write_if_changed(out / "style.css", css))
    stats = {"pages": 0, "written": written, "with_crosswalk": 0,
             "ine": 0, "eurostat": 0, "css_version": digest}
    for row in rows:
        entry = crosswalk.get(f"{row['area']}/{row['id']}")
        # ../../style.css from indicador/<area>/<id>/index.html
        html_text = render(row, entry, titles, f"../../style.css?v={digest}",
                           tables)
        stats["pages"] += 1
        stats["with_crosswalk"] += 1 if entry else 0
        if entry:
            stats["eurostat" if entry.get("source") == "Eurostat"
                  else "ine"] += 1
        stats["written"] += int(
            write_if_changed(out / row["area"] / str(row["id"]) / "index.html",
                             html_text))
    return stats


def sitemap(rows: list) -> str:
    """Pre-rendering buys nothing a crawler cannot reach.

    `lastmod` is the indicator's own update date, not the build date:
    stamping today on 2,195 URLs every night tells a crawler everything
    changed when nothing did, and it stops believing the field."""
    urls = "".join(
        f"<url><loc>{esc(page_url(r))}</loc>"
        + (f"<lastmod>{esc(r['ultima_atualizacao'])}</lastmod>"
           if re.fullmatch(r"\d{4}-\d{2}-\d{2}",
                           r.get("ultima_atualizacao") or "") else "")
        + "</url>\n"
        for r in rows)
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            f"{urls}</urlset>\n")


def missing_pages(rows: list, root: pathlib.Path = None) -> list:
    """Rows with no page on disk.

    Every card now links here, so a missing page is a 404 the visitor
    meets, not a build detail. Checked after the write rather than
    trusted from the return value: the point is what is on disk."""
    out = root or OUT_ROOT
    return [f"{r['area']}/{r['id']}" for r in rows
            if not (out / r["area"] / str(r["id"]) / "index.html").exists()]


def main() -> None:
    rows = json.loads(CATALOGUE.read_text(encoding="utf-8"))
    # The two are disjoint by construction — INE routes portugal and
    # municipios, Eurostat routes europa — so merging them is a union,
    # not a precedence question. Each entry names its own source and the
    # panel dispatches on that.
    crosswalk = {}
    for path in (CROSSWALK, EUROSTAT_CROSSWALK):
        if path.exists():
            crosswalk.update(json.loads(path.read_text(encoding="utf-8")))
    stats = build(rows, crosswalk, ine_titles())
    stats["written"] += int(write_if_changed(SITEMAP, sitemap(rows)))
    print(f"detail pages: {stats['pages']} indicators, "
          f"{stats['written']} files written, "
          f"{stats['with_crosswalk']} with provenance "
          f"({stats['ine']} INE, {stats['eurostat']} Eurostat)")

    if "--strict" in sys.argv:
        missing = missing_pages(rows)
        if missing:
            print(f"BREACH: {len(missing)} published rows have no page — "
                  f"every card links here, so each one is a 404 a visitor "
                  f"meets. First few: {missing[:5]}")
            sys.exit(1)
        print(f"detail pages: every one of {len(rows)} rows has a page")


if __name__ == "__main__":
    main()
