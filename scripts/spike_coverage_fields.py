#!/usr/bin/env python3
"""Spike A3 (roadmap 19): are period, geography and unit in the HTML?

The coverage line on the card reaches 78.4% of rows and stops there for
two reasons, one diagnosed and one unknown. This probe settles both
before anyone commits to a ~12 h re-harvest.

**Diagnosed.** Unit coverage is 100% for europa and municipios and 0%
for portugal, because the chart-caption markers appear in 1 of 1,053
portugal pages' stored `marker_windows`. That could mean the caption is
absent from the portugal template, or that it sits outside the excerpt
the harvester saves around "Fontes". Only a full HTML dump tells them
apart, and the answer decides whether the fix is a new marker (cheap) or
a different source entirely.

**Unknown.** The period (first and last year) and the geographic
granularity live in the data table, and harvested pages contain
"A carregar conteudo...", so the table may be client-rendered and absent
from the HTML. If it is, the period comes from upstream with roadmap 14
instead and this probe saves the re-harvest.

Sampling is deliberate, not random: portugal rows *without* a unit are
the case under test, europa and municipios rows *with* one are the
control. Raw HTML goes to data/spikes/raw/ for the workflow artifact and
is never committed. The report records structure and counts only - years
are coverage metadata, which is the thing we want to harvest; no cell
values are extracted or written anywhere (decision 1).
"""

import json
import pathlib
import re
import time
import urllib.request

USER_AGENT = (
    "pordata-map research (github.com/caasols/pordata; "
    "7 sample pages, 20s apart)"
)
CATALOGUE = pathlib.Path("docs/data/catalogue.json")
RAW_DIR = pathlib.Path("data/spikes/raw")
REPORT = pathlib.Path("data/spikes/a3-coverage-fields.md")
DELAY_SECONDS = 20

# Chart caption: what extract_unit() keys on today.
CAPTION_MARKERS = ["ver tabela completa", "gráfico ampliado", "ampliado"]
# Client-rendering tells: if the table arrives by XHR the years are not
# in the document at all.
CLIENT_MARKERS = ["A carregar conteúdo", "carregar conteúdo",
                  "/screenservices/", "OutSystems", "application/json"]
# Structure the period would live in.
TABLE_MARKERS = ["<table", "<thead", "<select", "<option"]

YEAR = re.compile(r"\b(19[6-9]\d|20[0-2]\d)\b")
TAG = re.compile(r"<[^>]+>")


def pick_samples() -> list[dict]:
    """Three portugal rows with no unit (the case under test) and four
    europa/municipios rows with one (the control)."""
    rows = json.loads(CATALOGUE.read_text(encoding="utf-8"))
    picked, seen = [], set()

    def take(pred, want):
        got = 0
        for r in rows:
            if got >= want or r["url"] in seen or r.get("removed"):
                continue
            if pred(r):
                seen.add(r["url"])
                picked.append(r)
                got += 1

    take(lambda r: r["area"] == "portugal" and not r.get("unit"), 3)
    take(lambda r: r["area"] == "europa" and r.get("unit"), 2)
    take(lambda r: r["area"] == "municipios" and r.get("unit"), 2)
    return picked


def visible_text(html: str) -> str:
    body = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", html)
    return re.sub(r"\s+", " ", TAG.sub(" ", body))


def probe(row: dict) -> dict:
    req = urllib.request.Request(row["url"],
                                 headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=120) as resp:
        raw = resp.read()
        status = resp.status
    html = raw.decode("utf-8", errors="replace")
    slug = row["url"].rstrip("/").rsplit("/", 1)[-1][:80]
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    (RAW_DIR / f"{slug}.html").write_bytes(raw)

    text = visible_text(html)
    years = sorted({int(y) for y in YEAR.findall(text)})
    # Years inside a table are the period; years anywhere (copyright,
    # cookie notices) are noise, so both are reported.
    tables = re.findall(r"(?is)<table.*?</table>", html)
    table_years = sorted({int(y) for t in tables
                          for y in YEAR.findall(visible_text(t))})
    options = len(re.findall(r"(?i)<option\b", html))

    return {
        "url": row["url"], "area": row["area"], "id": row["id"],
        "status": status, "bytes": len(raw),
        "unit_in_catalogue": row.get("unit", ""),
        "caption": {m: html.count(m) for m in CAPTION_MARKERS},
        "client": {m: html.count(m) for m in CLIENT_MARKERS},
        "structure": {m: html.count(m) for m in TABLE_MARKERS},
        "option_count": options,
        "years_any": (min(years), max(years), len(years)) if years else None,
        "years_in_tables": ((min(table_years), max(table_years),
                             len(table_years)) if table_years else None),
        "table_count": len(tables),
    }


def verdicts(results: list[dict]) -> list[str]:
    """State what the numbers mean, so the report answers the question
    rather than leaving it to whoever reads it next."""
    out = []
    pt = [r for r in results if r["area"] == "portugal"]
    other = [r for r in results if r["area"] != "portugal"]

    def has_caption(r):
        return any(v for v in r["caption"].values())

    if pt and all(has_caption(r) for r in pt):
        out.append("**Unit, portugal: the caption IS in the HTML.** The "
                   "harvester's marker windows miss it, so the fix is a "
                   "new marker plus a re-harvest, not a new data source. "
                   "Closes most of roadmap 20.")
    elif pt and not any(has_caption(r) for r in pt):
        out.append("**Unit, portugal: the caption is NOT in the HTML.** "
                   "The portugal template does not carry it; the unit "
                   "must come from upstream with roadmap 14 instead.")
    else:
        out.append("**Unit, portugal: mixed.** The caption appears on "
                   "some portugal pages and not others - sample more "
                   "before deciding.")
    if other and all(has_caption(r) for r in other):
        out.append("Control holds: europa/municipios pages do carry the "
                   "caption, as their 100% unit coverage implies.")

    with_table_years = [r for r in results if r["years_in_tables"]]
    if len(with_table_years) == len(results):
        spans = ", ".join(f"{r['years_in_tables'][0]}-{r['years_in_tables'][1]}"
                          for r in with_table_years)
        out.append(f"**Period: server-rendered.** Every sampled page has "
                   f"years inside a `<table>` ({spans}). Harvesting "
                   f"first/last year is viable - roadmap 19 proceeds.")
    elif not with_table_years:
        out.append("**Period: NOT in the HTML.** No sampled page has "
                   "years inside a table, so the table is client-"
                   "rendered. The period must come from upstream with "
                   "roadmap 14; do not spend the 12 h re-harvest on it.")
    else:
        out.append(f"**Period: partial.** {len(with_table_years)} of "
                   f"{len(results)} pages have table years. Find what "
                   f"separates them before committing.")

    if all(r["option_count"] > 50 for r in results):
        out.append("Geography: every page carries a large `<option>` "
                   "list, so the geography set looks harvestable too.")
    return out


def main() -> None:
    samples = pick_samples()
    print(f"probing {len(samples)} pages, {DELAY_SECONDS}s apart")
    results = []
    for i, row in enumerate(samples):
        if i:
            time.sleep(DELAY_SECONDS)
        try:
            info = probe(row)
        except Exception as exc:                       # noqa: BLE001
            info = {"url": row["url"], "area": row["area"], "id": row["id"],
                    "error": f"{type(exc).__name__}: {exc}"}
        results.append(info)
        print(f"  {info['area']}/{info['id']}: "
              f"{info.get('status', info.get('error'))}")

    ok = [r for r in results if "error" not in r]
    lines = [
        "# Spike A3 - period, geography and unit in the page HTML",
        "",
        "Roadmap 19. Answers whether a re-harvest can recover the "
        "coverage fields the card is missing, or whether they have to "
        "come from upstream instead.",
        "",
        "Structure and counts only - no PORDATA cell values are "
        "extracted or recorded here (decision 1). Raw HTML is a workflow "
        "artifact, never committed.",
        "",
        "## Verdict",
        "",
    ]
    lines += [f"- {v}" for v in (verdicts(ok) if ok else
                                 ["All probes failed; see below."])]
    lines += ["", "## Per page", ""]
    for r in results:
        lines.append(f"### {r['area']}/{r['id']}")
        lines.append("")
        if "error" in r:
            lines += [f"- **failed**: {r['error']}", ""]
            continue
        lines += [
            f"- status {r['status']}, {r['bytes']:,} bytes",
            f"- unit in catalogue today: "
            f"{r['unit_in_catalogue'] or '(none)'}",
            f"- caption markers: {r['caption']}",
            f"- client-render markers: {r['client']}",
            f"- structure: {r['structure']}, {r['table_count']} tables, "
            f"{r['option_count']} options",
            f"- years anywhere: {r['years_any']}",
            f"- years inside tables: {r['years_in_tables']}",
            "",
        ]
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"report written: {REPORT}")


if __name__ == "__main__":
    main()
