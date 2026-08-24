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

# "ampliado" anchors the chart caption, which is where the unit lives:
# "…ver o gráfico ampliado <UNIT> ver tabela completa". Spike A3
# (2026-08-23) confirmed the caption is present in all three area
# templates including portugal, whose units were 0% only because no
# marker reached it — "Unidade" never appears in the page text. Anchoring
# ahead of the unit rather than behind it matters: the trailing window is
# 220 chars and the leading one only 60, so "ver tabela completa" as the
# marker would cut the unit off.
MARKER_WORDS = ["Fontes", "Entidades", "ltima atualiza", "ltima actualiza",
                "revis", "Unidade", "ampliado"]


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


# --- fields A6 found, captured here so future fetches pay for themselves ---
# Raw HTML is not stored, so a field learned about after a harvest costs a
# full re-fetch. That has happened twice (the unit caption, the period).
# These are added now, ahead of roadmap 21, so the freshness loop collects
# them for free as pages go stale.

# The plain-language question sits in <h2> on every page A6 sampled
# (15/15, all 9 structural fingerprints). Inline markup splits it —
# "…de CO<sub>2</sub>…?" — so tags are stripped before testing.
H2 = re.compile(r"<h2[^>]*>(.*?)</h2>", re.I | re.DOTALL)
MIN_QUESTION_LEN = 15
MAX_QUESTION_LEN = 240


def extract_question(html: str) -> str:
    for match in H2.finditer(html):
        inner = html_mod.unescape(
            re.sub(r"<[^>]+>", " ", lib.scripts_to_unicode(match.group(1))))
        text = re.sub(r"\s+", " ", inner).strip()
        # a footnote marker leaves "… pública ₁ ?" — close that gap
        text = re.sub(r"\s+([?!.,;:])", r"\1", text)
        if text.endswith("?") and MIN_QUESTION_LEN <= len(text) <= MAX_QUESTION_LEN:
            return text
    return ""


# The period's mechanism differs by area (A4 + A6): portugal names the
# first and last year in their own elements, municipios exposes a
# <select> year picker, europa does neither and is still unspecified.
YEAR_ELEMENT = re.compile(
    r'class="[^"]*Year(?:Current|Other)Text[^"]*"[^>]*>\s*(\d{4})\s*<', re.I)
YEAR_OPTION = re.compile(r'<option[^>]+value="(\d{4})"', re.I)
EARLIEST_YEAR, LATEST_YEAR = 1960, 2035


def extract_period(html: str) -> tuple:
    """(first, last) as strings, or ("", "") when the page does not say."""
    years = [int(y) for y in YEAR_ELEMENT.findall(html)]
    if not years:
        years = [int(y) for y in YEAR_OPTION.findall(html)]
    years = [y for y in years if EARLIEST_YEAR <= y <= LATEST_YEAR]
    if len(years) < 2:
        return "", ""
    return str(min(years)), str(max(years))


def parse(url: str, status: int, body: bytes) -> dict:
    html = body.decode("utf-8", errors="replace")
    path = url.split("pordata.pt/", 1)[-1]
    area, slug = path.split("/", 1)
    text = strip_text(html)

    warnings: list[str] = []

    title_m = re.search(r"<title[^>]*>(.*?)</title>", html, re.DOTALL)
    title = html_mod.unescape(title_m.group(1)).strip() if title_m else ""
    name = lib.name_from_title(title)
    if title and not name and "| Pordata" not in title:
        # the '<Area>: <Name> | Pordata' template changed under us
        warnings.append("title_template")

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
        if fontes and not lib.plausible_fontes(fontes):
            # boundary trimming missed new UI text: drop it rather than
            # publish page prose as an attributed source
            warnings.append("fontes_shape")
            fontes = ""

    ultima_m = re.search(
        r"[ÚU]ltima\s+a[ct]+ualiza[çc][ãa]o:?\s*([0-9]{4}-[0-9]{2}-[0-9]{2})",
        text) or re.search(
        r"[ÚU]ltima\s+a[ct]+ualiza[çc][ãa]o:?\s*(.{1,30})", text)
    ultima = ultima_m.group(1).strip() if ultima_m else ""
    if ultima and not lib.valid_date(ultima):
        # the loose fallback caught page text, or PORDATA post-dated a
        # release; either way the site sorts on this field by default
        warnings.append("date_shape")
        ultima = ""

    question = extract_question(html)
    if question and "|" in question:
        # a page-title fragment, not a question PORDATA wrote
        warnings.append("question_shape")
        question = ""
    first_year, last_year = extract_period(html)

    record = {
        "url": url,
        "id": int(re.search(r"-(\d+)$", url).group(1)),
        "area": area,
        "slug": slug,
        "name": name,
        "title": title,
        "description": html_mod.unescape(desc_m.group(1)) if desc_m else "",
        "fontes": fontes,
        "ultima_atualizacao": ultima,
        "json_ld": json_ld,
        "marker_windows": marker_windows(text),
        "question": question,
        "period_start": first_year,
        "period_end": last_year,
        "http_status": status,
        "bytes": len(body),
        "harvested_at": time.strftime("%Y-%m-%d", time.gmtime()),
    }
    if warnings:
        record["parse_warnings"] = warnings
    return record


def is_stale(url: str, rec: dict, mods: dict) -> bool:
    """Has PORDATA touched this page since we last fetched it?

    The old test was `lastmod > harvested_at`, and both are date-only.
    That loses any update published on the same day the page was
    harvested — permanently, not just once: the next run compares the
    same two equal dates and skips again, so the record stays wrong for
    ever. It is the freshness loop's one silent data-loss path.

    Comparing against the lastmod we *stored* fixes it exactly. Any
    change to the value re-fetches once, and after that the stored value
    matches again, so there is no loop — which a `>=` comparison would
    have caused, re-fetching every same-day page on every run.

    Records harvested before this field existed fall back to the old
    comparison. Without that, the first run after this change would call
    all 2,195 pages stale and fire a full re-harvest by accident — which
    is roadmap 21, and not something a bug fix should trigger.

    Still undetectable, and inherent to a date-only sitemap: PORDATA
    editing a page without moving `lastmod` at all.
    """
    current = mods.get(url)
    if not current:
        return False
    stored = rec.get("sitemap_lastmod")
    if stored:
        return current != stored
    return bool(rec.get("harvested_at")) and current > rec["harvested_at"]


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
        elif is_stale(u, rec, mods):
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
    lastmods = lib.lastmods()
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
            # what the sitemap said when this copy was taken, so the next
            # run can tell "changed" from "same day" (see is_stale)
            record["sitemap_lastmod"] = lastmods.get(url, "")
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
