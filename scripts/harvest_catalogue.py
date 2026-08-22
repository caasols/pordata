#!/usr/bin/env python3
"""Phase B: harvest PORDATA indicator-page metadata into the catalogue.

Targets the indicator pages in the three statistical areas (portugal,
municipios, europa; quadro+resumo summary tables excluded). For each page
it stores one JSON line in data/catalogue/pages.jsonl with the metadata
the catalogue needs: name, title, description, JSON-LD block, sources
(Fontes/Entidades), last-updated date, plus short text excerpts around
each metadata marker so parsing can be refined offline without
re-fetching. No data values are extracted or stored — metadata only, per
the project's constraints.

Resumable and chunked: pages already in the JSONL are skipped, and the
run stops at MAX_SECONDS (default 16,200 s = 4.5 h, safely under the 6 h
Actions job cap) or MAX_PAGES if set. Pacing is one request per
DELAY_SECONDS (default 20, owner's choice) — the full 2,225-page harvest
therefore spans about three chunked runs.

Run from the repo root. Environment overrides: MAX_PAGES, MAX_SECONDS,
DELAY_SECONDS.
"""

import html as html_mod
import json
import os
import pathlib
import re
import time
import urllib.request

USER_AGENT = (
    "pordata-map catalogue harvester "
    "(github.com/caasols/pordata; metadata only; 1 request per 20s)"
)
URLS_FILE = pathlib.Path("data/sitemap-urls.txt")
OUT_FILE = pathlib.Path("data/catalogue/pages.jsonl")
REPORT_FILE = pathlib.Path("data/catalogue/REPORT.md")

DELAY_SECONDS = int(os.environ.get("DELAY_SECONDS") or 20)
MAX_SECONDS = int(os.environ.get("MAX_SECONDS") or 16200)
MAX_PAGES = int(os.environ.get("MAX_PAGES") or 0)  # 0 = no page cap

MARKER_WORDS = ["Fontes", "Entidades", "ltima atualiza", "ltima actualiza",
                "revis", "Unidade"]
AREA_PREFIXES = ("portugal", "municipios", "europa")


def targets() -> list[str]:
    urls = URLS_FILE.read_text(encoding="utf-8").split()
    picked = []
    for u in urls:
        path = u.split("pordata.pt/", 1)[-1]
        area = path.split("/", 1)[0]
        if area in AREA_PREFIXES and "/en/" not in u \
                and "quadro+resumo" not in u and re.search(r"-\d+$", u):
            picked.append(u)
    return picked


def already_done() -> set[str]:
    if not OUT_FILE.exists():
        return set()
    done = set()
    for line in OUT_FILE.read_text(encoding="utf-8").splitlines():
        try:
            done.add(json.loads(line)["url"])
        except (ValueError, KeyError):
            continue
    return done


def strip_text(html: str) -> str:
    text = re.sub(r"<(script|style)\b.*?</\1>", " ", html,
                  flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html_mod.unescape(text)
    return re.sub(r"\s+", " ", text)


def marker_windows(text: str) -> dict[str, list[str]]:
    windows: dict[str, list[str]] = {}
    for word in MARKER_WORDS:
        spans = []
        for m in re.finditer(re.escape(word), text):
            start = max(0, m.start() - 60)
            spans.append(text[start:m.end() + 220])
            if len(spans) >= 3:
                break
        if spans:
            windows[word] = spans
    return windows


def parse(url: str, status: int, body: bytes) -> dict:
    html = body.decode("utf-8", errors="replace")
    path = url.split("pordata.pt/", 1)[-1]
    area, slug = path.split("/", 1)
    text = strip_text(html)

    title_m = re.search(r"<title[^>]*>(.*?)</title>", html, re.DOTALL)
    title = html_mod.unescape(title_m.group(1)).strip() if title_m else ""
    name = re.sub(r"\s*\|\s*Pordata\s*$", "", title)
    name = re.sub(r"^(Portugal|Municípios|Europa):\s*", "", name)

    desc_m = re.search(
        r'<meta\s+name="description"\s+content="([^"]*)"', html)
    json_ld = None
    ld_m = re.search(
        r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>',
        html, re.DOTALL)
    if ld_m:
        try:
            json_ld = json.loads(ld_m.group(1))
        except ValueError:
            json_ld = {"unparsed": ld_m.group(1)[:800]}

    fontes = ""
    fontes_m = re.search(r"Fontes?\s*/\s*Entidades:?\s*(.{1,250})", text)
    if fontes_m:
        fontes = re.split(
            r"Carregue|ver tabela|ver o gráfico|Última|Ultima|Consulte|©"
            r"|Fontes?\s*/\s*Entidades",
            fontes_m.group(1))[0].strip(" ,;|-")
    ultima_m = re.search(
        r"[ÚU]ltima\s+a[ct]+ualiza[çc][ãa]o:?\s*([0-9]{4}-[0-9]{2}-[0-9]{2})",
        text) or re.search(
        r"[ÚU]ltima\s+a[ct]+ualiza[çc][ãa]o:?\s*(.{1,30})", text)

    return {
        "url": url,
        "id": int(re.search(r"-(\d+)$", url).group(1)),
        "area": area,
        "slug": slug,
        "name": name,
        "title": title,
        "description": html_mod.unescape(desc_m.group(1)) if desc_m else "",
        "fontes": fontes,
        "ultima_atualizacao": ultima_m.group(1).strip() if ultima_m else "",
        "json_ld": json_ld,
        "marker_windows": marker_windows(text),
        "http_status": status,
        "bytes": len(body),
        "harvested_at": time.strftime("%Y-%m-%d", time.gmtime()),
    }


def write_report(all_targets: list[str]) -> None:
    records = []
    if OUT_FILE.exists():
        for line in OUT_FILE.read_text(encoding="utf-8").splitlines():
            try:
                records.append(json.loads(line))
            except ValueError:
                continue
    total = len(all_targets)
    n = len(records)

    def pct(k):
        return f"{sum(1 for r in records if r.get(k)) * 100 // max(n, 1)}%"

    by_area: dict[str, int] = {}
    for r in records:
        by_area[r.get("area", "?")] = by_area.get(r.get("area", "?"), 0) + 1
    lines = [
        "# Catalogue harvest progress", "",
        f"- harvested: **{n} / {total}** target pages "
        f"({', '.join(f'{a}: {c}' for a, c in sorted(by_area.items()))})",
        f"- field coverage: name {pct('name')}, description "
        f"{pct('description')}, fontes {pct('fontes')}, "
        f"ultima_atualizacao {pct('ultima_atualizacao')}, "
        f"json_ld {pct('json_ld')}",
        "",
        "Regenerated each run by `scripts/harvest_catalogue.py`.",
    ]
    REPORT_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    all_targets = targets()
    done = already_done()
    todo = [u for u in all_targets if u not in done]
    print(f"{len(all_targets)} targets, {len(done)} done, {len(todo)} to go")

    deadline = time.monotonic() + MAX_SECONDS
    harvested = 0
    with OUT_FILE.open("a", encoding="utf-8") as out:
        for url in todo:
            if time.monotonic() + DELAY_SECONDS >= deadline:
                print("time budget reached")
                break
            if MAX_PAGES and harvested >= MAX_PAGES:
                print("page cap reached")
                break
            if harvested:
                time.sleep(DELAY_SECONDS)
            req = urllib.request.Request(
                url, headers={"User-Agent": USER_AGENT})
            try:
                with urllib.request.urlopen(req, timeout=120) as resp:
                    record = parse(url, resp.status, resp.read())
            except Exception as exc:
                record = {"url": url, "error": str(exc)[:200],
                          "harvested_at": time.strftime(
                              "%Y-%m-%d", time.gmtime())}
            out.write(json.dumps(record, ensure_ascii=False) + "\n")
            out.flush()
            harvested += 1
            if harvested % 25 == 0:
                print(f"{harvested} pages this run "
                      f"({len(done) + harvested}/{len(all_targets)} total)")

    write_report(all_targets)
    print(f"run complete: {harvested} pages this run, "
          f"{len(done) + harvested}/{len(all_targets)} total")


if __name__ == "__main__":
    main()
