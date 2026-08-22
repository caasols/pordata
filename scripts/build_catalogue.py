#!/usr/bin/env python3
"""Phase C: build the publishable catalogue from the harvested JSONL.

Reads data/catalogue/pages.jsonl (+ data/catalogue/featured.json if the
featured-sets job has run) and writes the static "API" the site and any
programmatic consumer use:

    docs/data/catalogue.json   one object per indicator (see fields below)
    docs/data/catalogue.csv    same rows, flat, for spreadsheet users
    docs/data/stats.json       counts + build date for the site header

Tombstones: a record whose url is no longer in the sitemap target list is
kept with removed=true, never deleted (deprecated indicators still matter
historically).

Offline; run after every harvest chunk. Error records are excluded from
the published catalogue until their retry succeeds.
"""

import csv
import json
import os
import pathlib
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pordata_lib as lib

FEATURED_FILE = pathlib.Path("data/catalogue/featured.json")
OUT_DIR = pathlib.Path("docs/data")

AREA_LABELS = {"portugal": "Portugal", "municipios": "Municípios",
               "europa": "Europa"}


def split_fontes(fontes: str) -> list[str]:
    # defensive re-trim: records harvested before the parser fix may still
    # carry trailing UI text; the JSONL is repaired in the 3d QA pass
    parts = re.split(r"[|,;]", lib.clean_fontes(fontes))
    seen, out = set(), []
    for p in (p.strip() for p in parts):
        if p and p not in seen:
            seen.add(p)
            out.append(p)
    return out


def main() -> None:
    records = lib.load_records()
    current = set(lib.targets())
    featured: dict[str, list[int]] = {}
    if FEATURED_FILE.exists():
        data = json.loads(FEATURED_FILE.read_text(encoding="utf-8"))
        for key in ("quadro_resumo", "retratos"):
            featured[key] = set(data.get(key, {}).get("indicator_ids", []))

    rows = []
    for url in sorted(records):
        rec = records[url]
        if "error" in rec:
            continue
        row = {
            "id": rec["id"],
            "area": rec["area"],
            "name": rec.get("name", ""),
            "description": rec.get("description", ""),
            "fontes": split_fontes(rec.get("fontes", "")),
            "ultima_atualizacao": rec.get("ultima_atualizacao", ""),
            "url": rec["url"],
            "harvested_at": rec.get("harvested_at", ""),
        }
        if url not in current:
            row["removed"] = True
        if featured:
            flags = []
            if rec["id"] in featured.get("quadro_resumo", ()):
                flags.append("quadro_resumo")
            if rec["id"] in featured.get("retratos", ()):
                flags.append("retrato")
            if flags:
                row["featured"] = flags
        rows.append(row)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "catalogue.json").write_text(
        json.dumps(rows, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8")

    with (OUT_DIR / "catalogue.csv").open("w", encoding="utf-8",
                                          newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["id", "area", "name", "fontes",
                         "ultima_atualizacao", "url", "removed", "featured"])
        for r in rows:
            writer.writerow([r["id"], r["area"], r["name"],
                             " | ".join(r["fontes"]), r["ultima_atualizacao"],
                             r["url"], "yes" if r.get("removed") else "",
                             ",".join(r.get("featured", []))])

    by_area = {}
    for r in rows:
        by_area[r["area"]] = by_area.get(r["area"], 0) + 1
    stats = {
        "indicators": len(rows),
        "by_area": by_area,
        "targets": len(current),
        "complete": len(rows) >= len(current),
        "built_at": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()),
    }
    (OUT_DIR / "stats.json").write_text(
        json.dumps(stats, ensure_ascii=False), encoding="utf-8")
    print(f"built catalogue: {len(rows)} indicators "
          f"({', '.join(f'{a}: {n}' for a, n in sorted(by_area.items()))})")


if __name__ == "__main__":
    main()
