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
    # Parse-time shape assertions (roadmap 6a). A PORDATA template change
    # shows up here first: fields are dropped rather than published, so
    # this trips before coverage does and names the cause.
    "parse_warnings_max": 0,
    # Coverage line on the card (roadmap 10). Both fields are DERIVED, so
    # they degrade silently if PORDATA changes how it writes titles or
    # renders the chart caption — which is exactly why they are gated
    # rather than trusted. Floors sit ~4 points under the measured 54.5%
    # and 51.8%. The card is designed to render without them, so a breach
    # is a "go look", not a broken site.
    "breakdown_ratio_min": 0.50,
    "unit_ratio_min": 0.47,
    # The '?'-for-en-dash defect is PORDATA's, and build-time
    # normalisation repairs it. A sharp rise means their encoding changed
    # again; zero means the normaliser stopped firing. Measured: 37.
    "separator_repairs_min": 20,
    "separator_repairs_max": 200,
    # Nothing may reach the published unit field except a unit: no UI
    # text, no data values. Any hit is a parser regression.
    "unit_contamination_max": 0,
}

# Coverage floors *per area*, for fields parsed out of page markup.
#
# The three areas are three PORDATA templates, so a catalogue-wide mean
# hides a template breaking: `unit_ratio` sat at 0.52 catalogue-wide and
# passed its 0.47 floor without complaint while the split was actually
# 100% / 100% / 0%. A mean cannot express "each template still works",
# which is the thing worth gating.
#
# Floors are per-area baselines, not aspirations: each sits just under
# what that area measures today, so a template change trips the area it
# broke and names it. **portugal's `unit_ratio` floor of 0.0 records a
# known gap, not an acceptable state** — the chart caption falls outside
# the excerpt the harvester stores there (roadmap 19). Raise it to match
# the others once 19 lands; until then a floor of 0.0 at least stops the
# other two areas regressing silently, which is what happened before.
PER_AREA_THRESHOLDS = {
    "unit_ratio": {"portugal": 0.0, "europa": 0.95, "municipios": 0.95},
    "breakdown_ratio": {"portugal": 0.50, "europa": 0.44,
                        "municipios": 0.55},
}


# UI fragments and long digit runs must never reach the unit field; the
# extractor searches marker slices individually so neither can splice in,
# and this is the check that says so out loud.
# A year ("base=2010", "a partir de 1/1/1999") is a legitimate part of a
# unit, so the digit rule keys on thousands-grouping — "210 015 800" —
# which is what a leaked data value actually looks like.
UNIT_CONTAMINATION = re.compile(
    r"ampliado|ver tabela|Carregue|Fontes|Última|\|\||\d{3}[ .\u00a0]\d{3}")


def recoverable_from_windows(rec: dict, field: str) -> bool:
    windows = rec.get("marker_windows") or {}
    blob = " ".join(s for spans in windows.values() for s in spans)
    if field == "fontes":
        return bool(re.search(r"Fontes?\s*/\s*Entidades", blob))
    if field == "ultima_atualizacao":
        return bool(re.search(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", blob))
    return False


def gate(metrics: dict) -> list[str]:
    """Compare measured metrics against THRESHOLDS and, for markup-parsed
    fields, against PER_AREA_THRESHOLDS; return breaches."""
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
    for metric, floors in PER_AREA_THRESHOLDS.items():
        measured = metrics.get(f"{metric}_by_area")
        if not measured:
            continue
        for area, floor in floors.items():
            value = measured.get(area)
            if value is None:
                breaches.append(f"{metric}[{area}]: area missing entirely")
            elif value < floor:
                breaches.append(
                    f"{metric}[{area}]: {value:.4g} < required {floor}")
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
        "parse-time shape assertion dropped a field (PORDATA changed?)":
            [r for r in ok if r.get("parse_warnings")],
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
                  f"{sum(1 for r in published if r.get('featured'))}",
                  f"- breakdown line: "
                  f"{coverage(published, 'breakdown') * 100:.0f}%",
                  f"- unit: {coverage(published, 'unit') * 100:.0f}%",
                  f"- either (coverage line renders): "
                  f"{sum(1 for r in published if r.get('breakdown') or r.get('unit')) / len(published) * 100:.0f}%"
                  if published else "- unit: n/a"]

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
        "parse_warnings": sum(1 for r in ok if r.get("parse_warnings")),
        "published_rows_ratio": (len(published) / len(ok)
                                 if published and ok else 1.0),
    }
    if published:
        metrics["breakdown_ratio"] = coverage(published, "breakdown")
        metrics["unit_ratio"] = coverage(published, "unit")
        for metric, field in (("breakdown_ratio", "breakdown"),
                              ("unit_ratio", "unit")):
            metrics[f"{metric}_by_area"] = {
                area: coverage([r for r in published if r["area"] == area],
                               field)
                for area in sorted({r["area"] for r in published})}
        metrics["separator_repairs"] = sum(
            1 for r in published if "–" in r.get("name", ""))
        metrics["unit_contamination"] = sum(
            1 for r in published
            if UNIT_CONTAMINATION.search(r.get("unit", "")))
    if featured_stats:
        metrics["featured_collisions"] = sum(
            g.get("collisions", 0) for g in featured_stats.values())
        metrics["featured_rows"] = sum(
            g.get("distinct_rows", 0) for g in featured_stats.values())
    breaches = gate(metrics)
    lines += ["", "## Gate", "",
              "Thresholds are machine-checked (decision 7b); `--strict` "
              "exits non-zero on breach so a bad harvest never publishes.", ""]
    for k, v in metrics.items():
        if isinstance(v, dict):
            inner = ", ".join(f"{a} {r * 100:.0f}%" for a, r in sorted(v.items()))
            lines.append(f"- {k}: {inner}")
        elif isinstance(v, float):
            lines.append(f"- {k}: {v:.4g}")
        else:
            lines.append(f"- {k}: {v}")
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
