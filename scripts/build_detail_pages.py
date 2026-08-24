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
INE_CSV = pathlib.Path("data/ine/indicators.csv")
THEME_CSS = pathlib.Path("site/src/index.css")
OUT_ROOT = pathlib.Path("docs/indicador")
# Its own file rather than an edit to docs/sitemap.xml: that one is
# hand-maintained and lists the catalogue downloads, this one is 2,195
# generated URLs. robots.txt names both, which is how a crawler is meant
# to find more than one.
SITEMAP = pathlib.Path("docs/sitemap-indicadores.xml")
SITE = "https://caasols.github.io/pordata"
INE_JSON = ("https://www.ine.pt/ine/json_indicador/pindica.jsp"
            "?op=2&varcd={}&lang=PT")

# Lifted verbatim from site/src/index.css so the two cannot drift. The
# generator asserts both blocks exist rather than falling back to a copy.
ROOT_TOKENS = re.compile(r"^:root\s*\{(.*?)^\}", re.S | re.M)
DARK_TOKENS = re.compile(r"^\.dark\s*\{(.*?)^\}", re.S | re.M)
# The radius scale lives in the @theme inline block, not in :root, and
# `rounded-sm` / `rounded-lg` are what the Badge and Card use. Lifted
# rather than re-derived: writing calc(var(--radius) - 4px) here again
# would be a second copy of a number that has already moved once.
RADIUS_SCALE = re.compile(r"^\s*(--radius-(?:sm|md|lg):[^;]+;)", re.M)

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
     .field .k  <- App.tsx Meta label  (9.5px, .1em, muted-foreground/75)
     .field .v  <- App.tsx Meta value  (text-xs), stepped up one size
                   because this is a page to read, not a row to scan
     .card      <- components/ui/card.tsx
                   (rounded-lg border-border bg-card shadow-xs)
     .chart     <- App.tsx ChartSlot
                   (dashed border-border/70, bg-muted/30, 9.5px label)
   A hand-written approximation is how the first version ended up with
   an orange pill where the card has a grey one. */
*,*::before,*::after{box-sizing:border-box}
body{margin:0;background:var(--background);color:var(--foreground);
 font:16px/1.55 "Public Sans",ui-sans-serif,system-ui,sans-serif;
 -webkit-font-smoothing:antialiased}
main{max-width:46rem;margin:0 auto;padding:1.5rem 1.15rem 4rem}
a{color:inherit}
h1{font-size:1.6rem;line-height:1.25;margin:.2rem 0 .35rem;font-weight:650}
h2{font-size:.95rem;margin:2rem 0 .6rem;font-weight:600}
h3{font-size:.85rem;margin:1.3rem 0 .2rem;font-weight:600}
.back{display:inline-block;margin-bottom:1.1rem;font-size:.8rem;
 color:var(--muted-foreground);text-decoration:none}
.back:hover{color:var(--foreground)}
.coverage{margin:0 0 .9rem;color:var(--muted-foreground);font-size:.9rem}

/* badge.tsx: rounded-sm px-2 py-0.5 text-xs font-medium, secondary */
.chips{display:flex;flex-wrap:wrap;gap:.35rem;margin:.85rem 0 1.5rem}
.chip{display:inline-flex;align-items:center;border-radius:var(--radius-sm);
 padding:.125rem .5rem;font-size:.75rem;line-height:1rem;font-weight:500;
 background:var(--secondary);color:var(--secondary-foreground)}
.chip.gone{background:var(--destructive);color:var(--destructive-foreground)}

/* card.tsx */
.card{border:1px solid var(--border);border-radius:var(--radius-lg);
 background:var(--card);color:var(--card-foreground);
 box-shadow:0 1px 2px -1px rgb(0 0 0 / .08);padding:1rem 1.1rem}

/* App.tsx Meta: the label is the card's exactly; the value steps from
   text-xs to .8125rem because a page is read, not scanned */
.grid{display:grid;gap:.85rem 1.25rem;
 grid-template-columns:repeat(auto-fit,minmax(9rem,1fr))}
.field{min-width:0}
.field .k{display:block;font-size:9.5px;text-transform:uppercase;
 letter-spacing:.1em;color:var(--muted-foreground);opacity:.75}
.field .v{display:block;margin-top:.15rem;font-size:.8125rem;
 line-height:1.45;overflow-wrap:anywhere;font-variant-numeric:tabular-nums}

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
a.api{margin-left:.4rem;font-size:9.5px;letter-spacing:.08em;
 text-transform:uppercase;color:var(--muted-foreground);
 text-decoration:none;border:1px solid var(--border);
 border-radius:var(--radius-sm);padding:.05rem .35rem}
a.api:hover{color:var(--foreground)}

/* App.tsx ChartSlot: same dashed idiom and same 9.5px label, taller
   because on this page it is the focal point rather than a footnote */
.chart{border:1px dashed var(--border);border-radius:var(--radius-lg);
 padding:1.6rem 1.1rem;text-align:center;background:var(--muted)}
.chart .slot{display:block;font-size:9.5px;text-transform:uppercase;
 letter-spacing:.08em;color:var(--muted-foreground);opacity:.7}
.cta{display:inline-block;margin-top:.9rem;padding:.4rem .85rem;
 border-radius:var(--radius-md);background:var(--primary);
 color:var(--primary-foreground);text-decoration:none;font-size:.8125rem;
 font-weight:500}
footer{margin-top:3rem;border-top:1px solid var(--border);padding-top:1rem;
 color:var(--muted-foreground);font-size:.8rem}
[data-en]{display:none}
html[lang="en"] [data-pt]{display:none}
html[lang="en"] [data-en]{display:revert}
"""

# Same keys the SPA writes, so crossing between them does not flip
# appearance. Wrapped in try/catch because private mode throws on read.
BOOT = (
    '<script>(function(){try{var t=localStorage.getItem("theme"),'
    'l=localStorage.getItem("lang");'
    'if(t==="dark"||(!t&&matchMedia("(prefers-color-scheme:dark)").matches))'
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
    return (f":root{{{root.group(1).strip()}\n{radius}}}\n"
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


def field(key: str, value: str) -> str:
    if not value:
        return ""
    return (f'<div class="field"><div class="k">{both(key)}</div>'
            f'<div class="v">{value}</div></div>')


def page_path(row: dict) -> pathlib.Path:
    return OUT_ROOT / row["area"] / str(row["id"]) / "index.html"


def page_url(row: dict) -> str:
    return f"{SITE}/indicador/{row['area']}/{row['id']}/"


def json_ld(row: dict, entry: dict | None) -> str:
    """A `Dataset` per indicator.

    `isBasedOn` points at PORDATA's page and, where the crosswalk found
    one, at the INE operation — the machine-readable form of the same
    claim the provenance section makes to a reader."""
    based_on = [row["url"]]
    data = {
        "@context": "https://schema.org",
        "@type": "Dataset",
        "name": row.get("title") or row.get("name"),
        "alternateName": row.get("name_en") or None,
        "url": page_url(row),
        "isBasedOn": based_on,
        "creator": {"@type": "Organization", "name": "PORDATA"},
        "spatialCoverage": AREA_LABELS.get(row["area"], (row["area"],))[0],
        "dateModified": row.get("ultima_atualizacao") or None,
        "variableMeasured": row.get("unit") or None,
        "isAccessibleForFree": True,
    }
    if entry:
        data["provider"] = {"@type": "Organization",
                            "name": entry.get("operation")}
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


def provenance(entry: dict | None, titles: dict) -> str:
    if not entry:
        return (f'<h2>{both("provenance")}</h2>'
                f'<div class="card"><strong>{both("noCrosswalk")}</strong>'
                f'<p class="why">{both("noCrosswalkWhy")}</p></div>')
    rows = "".join(
        f'<li><span class="id">{esc(i)}</span>'
        f'<a href="https://www.ine.pt/xurl/indx/{esc(i)}/PT" rel="noopener">'
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
        f'<div class="grid">'
        + field("operation", esc(entry.get("operation")))
        + field("theme", esc(entry.get("theme")))
        + field("geo", esc(", ".join(entry.get("geo_levels") or [])))
        + field("periodicity", esc(", ".join(entry.get("periodicities") or [])))
        + f'</div><h3>{both("candidates")}</h3>'
        f'<p class="why">{raw_both("candidatesWhy")}</p>'
        f'<ol class="series">{rows}</ol>{more}</div>')


def render(row: dict, entry: dict | None, titles: dict, css_ref: str) -> str:
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
<link rel="stylesheet" href="{css_ref}">
{BOOT}
<script type="application/ld+json">{json_ld(row, entry)}</script>
</head>
<body>
<main>
<a class="back" href="{SITE}/">&larr; {both("back")}</a>
<h1>{esc(title)}</h1>
{f'<p class="coverage">{esc(coverage)}</p>' if coverage else ''}
<div class="chips">{"".join(chips)}</div>
<div class="card"><div class="grid">
{field("sources", esc(sources))}
{field("updated", esc(row.get("ultima_atualizacao")))}
{field("unit", esc(row.get("unit")))}
{field("area", f'<span data-pt>{area_pt}</span><span data-en>{area_en}</span>')}
{field("nameEn", esc(row.get("name_en")))}
</div></div>
{revision}
<div class="chart"><span class="slot">{both("chartSoon")}</span>
<p class="why">{both("chartWhy")}</p>
<a class="cta" href="{esc(row['url'])}" rel="noopener">{both("openAt")}</a>
</div>
{provenance(entry, titles)}
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
    digest = hashlib.sha256(css.encode("utf-8")).hexdigest()[:8]
    written = int(write_if_changed(out / "style.css", css))
    stats = {"pages": 0, "written": written, "with_crosswalk": 0,
             "css_version": digest}
    for row in rows:
        entry = crosswalk.get(f"{row['area']}/{row['id']}")
        # ../../style.css from indicador/<area>/<id>/index.html
        html_text = render(row, entry, titles, f"../../style.css?v={digest}")
        stats["pages"] += 1
        stats["with_crosswalk"] += 1 if entry else 0
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
    crosswalk = (json.loads(CROSSWALK.read_text(encoding="utf-8"))
                 if CROSSWALK.exists() else {})
    stats = build(rows, crosswalk, ine_titles())
    stats["written"] += int(write_if_changed(SITEMAP, sitemap(rows)))
    print(f"detail pages: {stats['pages']} indicators, "
          f"{stats['written']} files written, "
          f"{stats['with_crosswalk']} with INE provenance")

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
