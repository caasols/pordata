#!/usr/bin/env python3
"""Cache Eurostat's dataset catalogue (roadmap 2, Eurostat half).

The mirror of `fetch_ine_catalogue.py`, and it exists for the same
reason: the crosswalk has to run offline on every harvest, so the
upstream catalogue lives in the repo rather than being re-fetched.

**Eurostat's unit is a dataset, not a series, and that is the finding
that shapes everything downstream** (spike `data/spikes/eurostat-toc.md`,
2026-08-25). INE publishes 13,084 *series*, each already a specific
slice, which is what made that relation one-to-many. Eurostat publishes
~8,500 *datasets*, each a multi-dimensional cube — `ei_bpm6ca_q`,
"Current account - quarterly data", holds 311,689 observations. So a
PORDATA `europa` row should map to **one dataset plus a dimension
filter**, not to a family of pre-sliced series, and the crosswalk schema
for it is a different shape from INE's. A5's finding was a fact about
INE, exactly as the roadmap warned.

Two endpoints, joined on the dataset code, because neither alone is
enough:

- **the table of contents** (TSV) carries the human title, the folder
  hierarchy those titles sit in, the period the data covers and the
  observation count — everything a matcher wants;
- **the file inventory** (TSV) carries the download URLs, which is the
  fetch route item 14 needs and the TOC does not have.

No observation values are fetched. This is the catalogue, which is
metadata about what Eurostat holds — the same thing the INE cache is.
"""

import collections
import csv
import io
import pathlib
import re
import sys
import urllib.request

USER_AGENT = (
    "pordata-map research (github.com/caasols/pordata; "
    "catalogue metadata only, cached in-repo)"
)
BASE = "https://ec.europa.eu/eurostat/api/dissemination"
TOC_URL = f"{BASE}/catalogue/toc/txt"
INVENTORY_URL = f"{BASE}/files/inventory?type=data"
OUT_DIR = pathlib.Path("data/eurostat")
OUT_CSV = OUT_DIR / "datasets.csv"
TIMEOUT = 300
# The file inventory lists 7,412 dataset codes, so the TOC should reach
# the same order of magnitude. Set under that, not at it: the two
# endpoints need not agree exactly.
MIN_DATASETS = 5000

# The TOC indents the title to show depth — four spaces per level — and
# marks each row as a folder or a table. Folders are the theme tree and
# tables are the datasets, so the hierarchy has to be tracked while
# scanning to give each dataset the path it sits under.
INDENT = 4

# The sampled TOC showed "folder" and "table", and parsing only those
# yielded 1,436 datasets where the file inventory lists 7,412 — so the
# tree carries at least one more leaf type. Rather than guess which,
# every type seen is counted and reported on both paths, so an unknown
# one is named in the log instead of silently dropped.
LEAF_TYPES = {"table", "dataset"}
FIELDS = ["code", "title", "theme", "last_update", "last_structure_change",
          "data_start", "data_end", "values", "tsv_url", "sdmx_url",
          "browser_url"]


def fetch(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return response.read().decode("utf-8", "replace")


def depth(title: str) -> int:
    return (len(title) - len(title.lstrip(" "))) // INDENT


def parse_toc(text: str) -> tuple[list[dict], collections.Counter]:
    """Datasets with the theme path they hang under, and a census of the
    row types seen.

    Rows arrive depth-first, so a running stack of folder titles is
    enough — no second pass and no tree to build. The census is returned
    rather than logged here because it is the evidence a floor breach
    needs: "only N parsed" says nothing without it."""
    rows = []
    seen: collections.Counter = collections.Counter()
    stack: list[str] = []
    reader = csv.reader(io.StringIO(text), delimiter="\t", quotechar='"')
    header = next(reader, None)
    if not header or "code" not in [h.strip().lower() for h in header]:
        raise SystemExit(
            "fetch_eurostat_catalogue: the TOC header is not what was "
            f"measured on 2026-08-25 ({header}). Eurostat changed the "
            "format; look before parsing it as if it had not.")
    for record in reader:
        if len(record) < 3:
            continue
        title, code, kind = record[0], record[1].strip(), record[2].strip()
        level = depth(title)
        name = title.strip()
        seen[kind] += 1
        if kind == "folder":
            del stack[level:]
            stack.append(name)
            continue
        if kind not in LEAF_TYPES:
            continue
        rows.append({
            "code": code.upper(),
            "title": name,
            # the immediate parent is the useful one; the full path is
            # recoverable from it and is mostly "Database by themes"
            "theme": " / ".join(stack[1:]) if len(stack) > 1 else
                     (stack[0] if stack else ""),
            "last_update": (record[3] or "").strip(),
            "last_structure_change": (record[4] or "").strip(),
            "data_start": (record[5] or "").strip(),
            "data_end": (record[6] or "").strip(),
            "values": (record[7] or "").strip() if len(record) > 7 else "",
        })
    return rows, seen


def parse_inventory(text: str) -> dict:
    """code -> the download URLs, which the TOC does not carry."""
    urls = {}
    reader = csv.DictReader(io.StringIO(text), delimiter="\t")
    for record in reader:
        code = (record.get("Code") or "").strip().upper()
        if not code:
            continue
        urls[code] = {
            "tsv_url": (record.get("Data download url (tsv)") or "").strip(),
            "sdmx_url": (record.get("Data download url (sdmx)") or "").strip(),
            "browser_url": (record.get("Open in Data Browser url")
                            or "").strip(),
        }
    return urls


def merge(datasets: list[dict], urls: dict) -> list[dict]:
    for row in datasets:
        row.update(urls.get(row["code"],
                            {"tsv_url": "", "sdmx_url": "", "browser_url": ""}))
    return datasets


def main() -> None:
    print(f"fetching {TOC_URL}")
    toc = fetch(TOC_URL)
    print(f"fetching {INVENTORY_URL}")
    inventory = fetch(INVENTORY_URL)

    parsed, seen = parse_toc(toc)
    datasets = merge(parsed, parse_inventory(inventory))
    census = ", ".join(f"{kind or '(blank)'}={count}"
                       for kind, count in seen.most_common())
    print(f"TOC row types: {census}")
    if len(datasets) < MIN_DATASETS:
        raise SystemExit(
            f"fetch_eurostat_catalogue: only {len(datasets)} datasets "
            f"parsed, under the floor of {MIN_DATASETS}; the file "
            "inventory lists 7,412. Refusing to overwrite the cache with "
            "a degraded pull — the same rule the sitemap corpus floor "
            f"follows.\n  row types seen: {census}\n  leaf types "
            f"accepted: {sorted(LEAF_TYPES)}\nIf a type above is a leaf "
            "and is not in that list, add it.")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with io.open(OUT_CSV, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(sorted(datasets, key=lambda r: r["code"]))
    routed = sum(1 for r in datasets if r["tsv_url"])
    print(f"eurostat catalogue: {len(datasets)} datasets, "
          f"{routed} with a download URL -> {OUT_CSV}")


if __name__ == "__main__":
    main()
