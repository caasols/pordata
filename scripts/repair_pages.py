#!/usr/bin/env python3
"""3d: offline repair pass over data/catalogue/pages.jsonl.

Records harvested before the fontes-boundary fixes still store trailing
UI text ("Carregue aqui…", the municipal toolbar words) in their fontes
field. The build already re-trims at read time, so the published
catalogue is clean; this pass makes the stored JSONL itself clean by
applying lib.clean_fontes and rewriting the file once. Idempotent, never
fetches.
"""

import os
import sys

if __package__:
    from . import pordata_lib as lib
else:  # executed directly, e.g. python3 scripts/repair_pages.py
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import pordata_lib as lib


def repair(records: dict) -> int:
    """Trim over-captured fontes in place; returns how many changed."""
    repaired = 0
    for rec in records.values():
        raw = rec.get("fontes")
        if not raw or "error" in rec:
            continue
        cleaned = lib.clean_fontes(raw)
        if cleaned != raw:
            rec["fontes"] = cleaned
            repaired += 1
    return repaired


def main() -> None:
    records = lib.load_records()
    repaired = repair(records)
    if repaired:
        lib.write_records(records)
    print(f"repair: {repaired} fontes trimmed of {len(records)} records")


if __name__ == "__main__":
    main()
