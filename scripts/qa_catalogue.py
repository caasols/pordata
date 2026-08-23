#!/usr/bin/env python3
"""QA pass over the harvested catalogue. Offline — reads
data/catalogue/pages.jsonl (and the published docs/data/catalogue.json
when present), writes data/catalogue/QA.md. Never fetches.

Checks: field coverage per area, error records, duplicate (area, id)
keys, suspicious fields (empty name, over-captured fontes, non-ISO
dates), how many weak fields are recoverable offline from the stored
marker_windows excerpts, and the published layer the site actually
serves.

**This is a gate, not just a report** (decision 7b): with --strict it
exits non-zero when a threshold in THRESHOLDS is breached, so a PORDATA
parser regression fails the harvest job instead of publishing silently.
"""

import json
import os
import pathlib
import re
import sys

if __package__:
    from . import pordata_lib as lib
else:  # executed directly, e.g. python3 scripts/qa_catalogue.py
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import pordata_lib as lib

QA_FILE = pathlib.Path("data/catalogue/QA.md")
PUBLISHED = pathlib.Path("docs/data/catalogue.json")
STATS = pathlib.Path("docs/data/stats.json")

# Machine-checked floors. Every metric a feature or roadmap item depends
# on belongs here, never in prose (decision 7b). Values sit just under
# the measured state so real regressions trip them and normal drift does
# not; raise them as the pipeline improves.
THRESHOLDS = {
    "jsonl_skipped_lines_max": 0,      # corrupt JSONL must never publish
    "ok_records_ratio_min": 0.98,      # of sitemap targets
    "name_coverage_min": 0.98,
    "description_coverage_min": 0.95,
    "fontes_coverage_min": 0.95,
    "date_iso_ratio_min": 1.0,         # of non-empty ultima_atualizacao
    "duplicate_area_id_max": 0,        # (area, id) is the catalogue key
    "published_rows_ratio_min": 0.98,  # published vs ok records
    # Featured (quadro-resumo) matching, the precondition roadmap 12's
    # pill depends on. Collisions must be zero — before injectivity one
    # catalogue id could be claimed by five quadro names, mis-flagging
    # four. The row floor sits just under the measured 43 so a matcher
    # regression trips instead of quietly shrinking the badge set.
    "featured_collisions_max": 0,
    "featured_rows_min": 40,
}


def recoverable_from_windows(rec: dict, field: str) -> bool:
    windows = rec.get("marker_windows") or {}
    blob = " ".join(s for spans in windows.values() for s in spans)
    if field == "fontes":
        return bool(re.search(r"Fontes?\s*/\s*Entidades", blob))
    if field == "ultima_atualizacao":
        return bool(re.search(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", blob))
    return False


def gate(metrics: dict) -> list[str]:
    """Compare measured metrics against THRESHOLDS; return breaches."""
    breaches = []
    for key, limit in THRESHOLDS.items():
        metric = key.rsplit("_", 1)[0]
        value = metrics.get(metric)
        if value is None:
            continue
        if key.endswith("_max") and value > limit:
            breaches.append(f"{metric}: {value} > allowed {limit}")
        elif key.endswith("_min") and value < limit:
            breaches.append(f"{metric}: {value:.4g} < required {limit}")
    return breaches


def main_strict() -> None:
    """main() with the gate armed; --strict on the CLI does the same."""
    main(strict=True)


def main(strict: bool = False) -> None:
    strict = strict or "--strict" in sys.argv
    records = lib.load_records()
    ok = [r for r in records.values() if "error" not in r]
    dead = lib.abandoned()
    errors = [r for r in records.values()
              if "error" in r and r["url"] not in dead]
    retired = [r for r in records.values()
               if "error" in r and r["url"] in dead]
    targets = lib.targets() if lib.URLS_FILE.exists() else []
    areas = sorted({r["area"] for r in ok if r.get("area")})
    fields = ["name", "description", "fontes", "ultima_atualizacao", "json_ld"]

    def coverage(subset, field):
        return (sum(1 for r in subset if r.get(field)) / len(subset)
                if subset else 0.0)

    lines = ["# Catalogue QA", "",
             f"Records: {len(records)} ({len(ok)} ok, {len(errors)} errored)",
             "", "## Field coverage (% non-empty)", "",
             "| area | n | " + " | ".join(fields) + " |",
             "|---|---|" + "---|" * len(fields)]
    for area in areas + ["ALL"]:
        subset = ok if area == "ALL" else [r for r in ok if r["area"] == area]
        row = [area, str(len(subset))]
        row += [f"{coverage(subset, f) * 100:.0f}%" for f in fields]
        lines.append("| " + " | ".join(row) + " |")

    # (area, id) is the catalogue key — ids repeat across areas by design,
    # so only a repeat *within* an area is a real collision.
    keys = [(r.get("area"), r.get("id")) for r in ok]
    dup_keys = sorted({k for k in keys if keys.count(k) > 1 and k[1] is not None},
                      key=lambda k: (str(k[0]), str(k[1])))
    weak = {
        "empty name": [r for r in ok if not r.get("name")],
        "empty fontes": [r for r in ok if not r.get("fontes")],
        "fontes contains UI boundary text (over-capture; run repair_pages.py)":
            [r for r in ok
             if r.get("fontes") and lib.clean_fontes(r["fontes"]) != r["fontes"]],
        "ultima_atualizacao not ISO date":
            [r for r in ok if r.get("ultima_atualizacao")
             and not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}",
                                  r["ultima_atualizacao"])],
        # informational: raw records may carry PORDATA's inline HTML
        # (<em>, <sub>, <sup>); the build strips it before publishing
        "name/description carries inline HTML (stripped at build)":
            [r for r in ok if re.search(r"<[^>]+>", (r.get("name") or "")
                                        + (r.get("description") or ""))],
        "re-fetch failed; serving the previous good record":
            [r for r in ok if r.get("refetch_error")],
    }
    lines += ["", "## Findings", ""]
    if dup_keys:
        lines.append(f"- duplicate (area, id) keys: {dup_keys[:20]}")
    for label, recs in weak.items():
        if not recs:
            continue
        lines.append(f"- {label}: {len(recs)}")
        for r in recs[:8]:
            lines.append(f"  - `{str(r.get('slug', r.get('url', '')))[:70]}`")
    for field in ("fontes", "ultima_atualizacao"):
        missing = [r for r in ok if not r.get(field)]
        rec_ok = sum(1 for r in missing if recoverable_from_windows(r, field))
        if missing:
            lines.append(f"- empty {field}: {len(missing)}, of which "
                         f"{rec_ok} look recoverable from marker_windows")
    if retired:
        lines += ["", "## Abandoned (listed by PORDATA, not served)", "",
                  "Skipped by the harvest plan and tombstoned at build "
                  "time; see `data/catalogue/abandoned.txt`.", ""]
        lines += [f"- `{r['url'].split('pordata.pt/')[-1][:80]}`: "
                  f"{r['error'][:60]}" for r in retired]
    if errors:
        lines += ["", "## Error records (will be retried next run)", ""]
        lines += [f"- `{r['url'].split('pordata.pt/')[-1][:80]}`: {r['error'][:80]}"
                  for r in errors[:15]]
    if not (dup_keys or errors or any(weak.values())):
        lines.append("- no findings; catalogue looks clean")

    # ---- published layer: what the site actually serves ----------------
    published = []
    if PUBLISHED.exists():
        published = json.loads(PUBLISHED.read_text(encoding="utf-8"))
        live = [r for r in published if not r.get("removed")]
        lines += ["", "## Published layer (docs/data/catalogue.json)", "",
                  f"- rows: {len(published)} ({len(live)} live, "
                  f"{len(published) - len(live)} tombstoned)",
                  f"- name_en present: {coverage(published, 'name_en') * 100:.0f}%",
                  f"- fontes non-empty: {coverage(published, 'fontes') * 100:.0f}%",
                  f"- featured flagged rows: "
                  f"{sum(1 for r in published if r.get('featured'))}"]

    featured_stats = {}
    if STATS.exists():
        featured_stats = json.loads(
            STATS.read_text(encoding="utf-8")).get("featured", {})

    dates = [r["ultima_atualizacao"] for r in ok if r.get("ultima_atualizacao")]
    metrics = {
        "jsonl_skipped_lines": lib.SKIPPED_LINES,
        "ok_records_ratio": len(ok) / len(targets) if targets else 1.0,
        "name_coverage": coverage(ok, "name"),
        "description_coverage": coverage(ok, "description"),
        "fontes_coverage": coverage(ok, "fontes"),
        "date_iso_ratio": (sum(
            1 for d in dates
            if re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", d)) / len(dates)
            if dates else 1.0),
        "duplicate_area_id": len(dup_keys),
        "published_rows_ratio": (len(published) / len(ok)
                                 if published and ok else 1.0),
    }
    if featured_stats:
        metrics["featured_collisions"] = sum(
            g.get("collisions", 0) for g in featured_stats.values())
        metrics["featured_rows"] = sum(
            g.get("distinct_rows", 0) for g in featured_stats.values())
    breaches = gate(metrics)
    lines += ["", "## Gate", "",
              "Thresholds are machine-checked (decision 7b); `--strict` "
              "exits non-zero on breach so a bad harvest never publishes.", ""]
    lines += [f"- {k}: {v:.4g}" if isinstance(v, float) else f"- {k}: {v}"
              for k, v in metrics.items()]
    lines += [""] + ([f"- **BREACH** {b}" for b in breaches]
                     if breaches else ["- all thresholds pass"])

    QA_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"QA written: {len(ok)} ok, {len(errors)} errors, "
          f"{sum(len(v) for v in weak.values())} weak-field findings")
    if breaches:
        print("QA GATE BREACHED:")
        for b in breaches:
            print(f"  - {b}")
        if strict:
            sys.exit(1)
    else:
        print("QA gate: all thresholds pass")


if __name__ == "__main__":
    main()
