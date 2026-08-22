#!/usr/bin/env python3
"""3d: QA pass over the harvested catalogue. Offline — reads
data/catalogue/pages.jsonl, writes data/catalogue/QA.md. Never fetches.

Checks: field coverage per area, error records, duplicate ids, suspicious
fields (empty name, over-long fontes, non-ISO dates), and how many weak
fields are recoverable offline from the stored marker_windows excerpts.
"""

import os
import pathlib
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pordata_lib as lib

QA_FILE = pathlib.Path("data/catalogue/QA.md")


def recoverable_from_windows(rec: dict, field: str) -> bool:
    windows = rec.get("marker_windows") or {}
    blob = " ".join(s for spans in windows.values() for s in spans)
    if field == "fontes":
        return bool(re.search(r"Fontes?\s*/\s*Entidades", blob))
    if field == "ultima_atualizacao":
        return bool(re.search(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", blob))
    return False


def main() -> None:
    records = lib.load_records()
    ok = [r for r in records.values() if "error" not in r]
    errors = [r for r in records.values() if "error" in r]
    areas = sorted({r["area"] for r in ok})
    fields = ["name", "description", "fontes", "ultima_atualizacao", "json_ld"]

    lines = ["# Catalogue QA", "",
             f"Records: {len(records)} ({len(ok)} ok, {len(errors)} errored)",
             "", "## Field coverage (% non-empty)", "",
             "| area | n | " + " | ".join(fields) + " |",
             "|---|---|" + "---|" * len(fields)]
    for area in areas + ["ALL"]:
        subset = ok if area == "ALL" else [r for r in ok if r["area"] == area]
        row = [area, str(len(subset))]
        for f in fields:
            row.append(f"{sum(1 for r in subset if r.get(f)) * 100 // max(len(subset), 1)}%")
        lines.append("| " + " | ".join(row) + " |")

    ids = [r["id"] for r in ok]
    dup_ids = sorted({i for i in ids if ids.count(i) > 1})
    weak = {
        "empty name": [r for r in ok if not r.get("name")],
        "empty fontes": [r for r in ok if not r.get("fontes")],
        "fontes contains UI boundary text (over-capture; repair in 3d pass)":
            [r for r in ok
             if r.get("fontes") and lib.clean_fontes(r["fontes"]) != r["fontes"]],
        "ultima_atualizacao not ISO date":
            [r for r in ok if r.get("ultima_atualizacao")
             and not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}",
                                  r["ultima_atualizacao"])],
    }
    lines += ["", "## Findings", ""]
    if dup_ids:
        lines.append(f"- duplicate ids: {dup_ids[:20]}")
    for label, recs in weak.items():
        if not recs:
            continue
        lines.append(f"- {label}: {len(recs)}")
        for r in recs[:8]:
            lines.append(f"  - `{r['slug'][:70]}`")
    for field in ("fontes", "ultima_atualizacao"):
        missing = [r for r in ok if not r.get(field)]
        rec_ok = sum(1 for r in missing if recoverable_from_windows(r, field))
        if missing:
            lines.append(f"- empty {field}: {len(missing)}, of which "
                         f"{rec_ok} look recoverable from marker_windows")
    if errors:
        lines += ["", "## Error records (will be retried next run)", ""]
        lines += [f"- `{r['url'].split('pordata.pt/')[-1][:80]}`: {r['error'][:80]}"
                  for r in errors[:15]]
    if not (dup_ids or errors or any(weak.values())):
        lines.append("- no findings; catalogue looks clean")

    QA_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"QA written: {len(ok)} ok, {len(errors)} errors, "
          f"{sum(len(v) for v in weak.values())} weak-field findings")


if __name__ == "__main__":
    main()
