#!/usr/bin/env python3
"""Phase B: harvest PORDATA indicator-page metadata into the catalogue.

Targets the indicator pages in the three statistical areas (portugal,
municipios, europa; quadro+resumo summary tables excluded — see
pordata_lib.targets). For each page it stores one JSON line in
data/catalogue/pages.jsonl with the metadata the catalogue needs: name,
title, description, JSON-LD block, sources (Fontes/Entidades),
last-updated date, plus short text excerpts around each metadata marker
so parsing can be refined offline without re-fetching. No data values are
extracted or stored — metadata only, per the project's constraints.

Each run fetches, in order:
1. pages never harvested (includes indicators newly added to the sitemap,
   since the target list is the watcher's committed snapshot);
2. pages whose previous attempt errored;
3. stale pages — the watcher's <lastmod> moved past the record's
   harvested_at (re-harvest replaces the old record).

Resumable and chunked: stops at MAX_SECONDS (default 16,200 s = 4.5 h,
safely under the 6 h Actions job cap) or MAX_PAGES if set. Pacing is one
request per DELAY_SECONDS (default 20, owner's choice). At the end the
JSONL is rewritten deduplicated (last record per url wins).

Run from the repo root. Environment overrides: MAX_PAGES, MAX_SECONDS,
DELAY_SECONDS.
"""

import html as html_mod
import json
import os
import pathlib
import re
import sys
import time
import urllib.request

if __package__:
    from . import pordata_lib as lib
else:  # executed directly, e.g. python3 scripts/harvest_catalogue.py
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import pordata_lib as lib

USER_AGENT = (
    "pordata-map catalogue harvester "
    "(github.com/caasols/pordata; metadata only; 1 request per 20s)"
)
OUT_FILE = lib.PAGES_FILE
REPORT_FILE = pathlib.Path("data/catalogue/REPORT.md")

DELAY_SECONDS = int(os.environ.get("DELAY_SECONDS") or 20)
MAX_SECONDS = int(os.environ.get("MAX_SECONDS") or 16200)
MAX_PAGES = int(os.environ.get("MAX_PAGES") or 0)  # 0 = no page cap

MARKER_WORDS = ["Fontes", "Entidades", "ltima atualiza", "ltima actualiza",
                "revis", "Unidade"]


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
        fontes = lib.clean_fontes(fontes_m.group(1))
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


def plan(all_targets: list[str], records: dict[str, dict]) -> dict[str, list[str]]:
    mods = lib.lastmods()
    dead = lib.abandoned()
    missing, errored, stale = [], [], []
    for u in all_targets:
        if u in dead:
            continue
        rec = records.get(u)
        if rec is None:
            missing.append(u)
        elif "error" in rec:
            errored.append(u)
        elif mods.get(u) and rec.get("harvested_at") \
                and mods[u] > rec["harvested_at"]:
            stale.append(u)
    return {"missing": missing, "errored": errored, "stale": stale}


def write_report(all_targets: list[str], todo_plan: dict) -> None:
    records = lib.load_records()
    dead = lib.abandoned()
    ok = [r for r in records.values() if "error" not in r]
    n = len(ok)

    def pct(k):
        return f"{sum(1 for r in ok if r.get(k)) * 100 // max(n, 1)}%"

    by_area: dict[str, int] = {}
    for r in ok:
        by_area[r.get("area", "?")] = by_area.get(r.get("area", "?"), 0) + 1
    lines = [
        "# Catalogue harvest progress", "",
        f"- harvested: **{n} / {len(all_targets) - len(dead)}** reachable "
        f"target pages "
        f"({', '.join(f'{a}: {c}' for a, c in sorted(by_area.items()))})",
        f"- pending: {len(todo_plan['missing'])} missing, "
        f"{len(todo_plan['errored'])} errored, {len(todo_plan['stale'])} stale",
        f"- abandoned: {len(dead)} listed by PORDATA but not served "
        f"(see `data/catalogue/abandoned.txt`)",
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
    all_targets = lib.targets()
    records = lib.load_records()
    todo_plan = plan(all_targets, records)
    todo = todo_plan["missing"] + todo_plan["errored"] + todo_plan["stale"]
    print(f"{len(all_targets)} targets | "
          f"{len(todo_plan['missing'])} missing, "
          f"{len(todo_plan['errored'])} errored, "
          f"{len(todo_plan['stale'])} stale")

    deadline = time.monotonic() + MAX_SECONDS
    harvested = 0
    for url in todo:
        if time.monotonic() + DELAY_SECONDS >= deadline:
            print("time budget reached")
            break
        if MAX_PAGES and harvested >= MAX_PAGES:
            print("page cap reached")
            break
        if harvested:
            time.sleep(DELAY_SECONDS)
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                record = parse(url, resp.status, resp.read())
        except Exception as exc:
            # A failed re-fetch must never erase a good record: the build
            # skips error records, so overwriting would silently drop a
            # live indicator from the published catalogue over one
            # transient 500. Only pages with no good record so far become
            # error records; the rest keep their data and carry a marker
            # (plan() still re-fetches them, since they stay stale).
            now = time.strftime("%Y-%m-%d", time.gmtime())
            prev = records.get(url)
            if prev and "error" not in prev:
                prev["refetch_error"] = str(exc)[:200]
                prev["refetch_failed_at"] = now
                record = prev
            else:
                record = {"url": url, "error": str(exc)[:200],
                          "harvested_at": now}
        records[url] = record
        harvested += 1
        if harvested % 25 == 0:
            lib.write_records(records)  # checkpoint, safe against job loss
            print(f"{harvested} pages this run")

    lib.write_records(records)
    write_report(all_targets, plan(all_targets, records))
    print(f"run complete: {harvested} pages this run, "
          f"{len(records)}/{len(all_targets)} total records")


if __name__ == "__main__":
    main()
