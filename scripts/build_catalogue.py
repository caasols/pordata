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
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pordata_lib as lib

FEATURED_FILE = pathlib.Path("data/catalogue/featured.json")
OUT_DIR = pathlib.Path("docs/data")

AREA_LABELS = {"portugal": "Portugal", "municipios": "Municípios",
               "europa": "Europa"}


# featured.json groups -> which catalogue area their names live in
GROUP_AREAS = {"quadro_resumo_municipios": "municipios",
               "quadro_resumo_europa": "europa"}


NAME_STOPWORDS = {"de", "da", "do", "das", "dos", "e", "em", "no", "na",
                  "nos", "nas", "por", "para", "a", "o", "os", "as", "com",
                  "que", "total", "%", "€"}


def norm_name(s: str) -> str:
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower().replace("-", "")  # auto-estradas == autoestradas
    s = re.sub(r"[^\w\s%€]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def content_tokens(s: str) -> set[str]:
    """Meaning-bearing tokens: stopwords out, crude plural strip so that
    limites==limite across the quadro and catalogue spellings."""
    tokens = set()
    for t in norm_name(s).split():
        if t in NAME_STOPWORDS or len(t) < 2:
            continue
        if len(t) > 3 and t.endswith("s"):
            t = t[:-1]
        tokens.add(t)
    return tokens


def resolve_featured(records: dict) -> tuple[dict[int, list[str]], dict]:
    """Match quadro-resumo indicator names to catalogue ids (the quadro
    pages carry names but no ids). Exact normalized match first, then
    best token-overlap >= 0.6 within the group's area."""
    if not FEATURED_FILE.exists():
        return {}, {}
    data = json.loads(FEATURED_FILE.read_text(encoding="utf-8"))
    flags: dict[int, list[str]] = {}
    stats: dict = {}
    for group, area in GROUP_AREAS.items():
        names = data.get(group, {}).get("indicator_names", [])
        if not names:
            continue
        pool = [(norm_name(r["name"]), content_tokens(r["name"]), r["id"])
                for r in records.values()
                if "error" not in r and r["area"] == area and r.get("name")]
        exact = {}
        for n, _, rid in pool:
            exact.setdefault(n, rid)
        matched, unmatched = 0, []
        for name in names:
            n = norm_name(name)
            rid = exact.get(n)
            if rid is None:
                tokens = content_tokens(name)
                best, best_score, best_extra = None, 0.0, 10**9
                if len(tokens) >= 2:
                    for _, pt, pid in pool:
                        # containment: quadro names are shortened subsets
                        score = len(tokens & pt) / len(tokens)
                        extra = len(pt - tokens)
                        if score > best_score or \
                                (score == best_score and extra < best_extra):
                            best, best_score, best_extra = pid, score, extra
                if best_score >= 0.7:
                    rid = best
            if rid is None:
                unmatched.append(name)
            else:
                matched += 1
                flags.setdefault(rid, [])
                if "quadro_resumo" not in flags[rid]:
                    flags[rid].append("quadro_resumo")
        stats[group] = {"names": len(names), "matched": matched,
                        "unmatched": unmatched}
    return flags, stats


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
    featured_flags, featured_stats = resolve_featured(records)

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
        if rec["id"] in featured_flags:
            row["featured"] = featured_flags[rec["id"]]
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
    if featured_stats:
        stats["featured"] = {
            g: {"names": s["names"], "matched": s["matched"],
                "unmatched": len(s["unmatched"])}
            for g, s in featured_stats.items()}
        for g, s in featured_stats.items():
            if s["unmatched"]:
                print(f"featured {g}: {s['matched']}/{s['names']} matched; "
                      f"unmatched: {s['unmatched'][:5]}")
    (OUT_DIR / "stats.json").write_text(
        json.dumps(stats, ensure_ascii=False), encoding="utf-8")
    print(f"built catalogue: {len(rows)} indicators "
          f"({', '.join(f'{a}: {n}' for a, n in sorted(by_area.items()))})")


if __name__ == "__main__":
    main()
