#!/usr/bin/env python3
"""Phase B: fetch and cache the INE indicator catalogue (spike A2 result).

One request to xml_indic.jsp?opc=2 (~21 MB XML listing every INE
indicator with theme/subtheme). INE's bot protection 403s repeat pulls
from cloud IPs, so this runs rarely, on manual dispatch only, and the
result is cached in the repo:

    data/ine/catalogue.xml.gz   the full catalogue, gzipped
    data/ine/indicators.csv     id + per-indicator fields, one row each
    data/ine/SUMMARY.md         counts, themes, field inventory

A 403 or short payload exits non-zero with a clear message: retry later
(not harder), per the spike A2 caveat.
"""

import csv
import gzip
import pathlib
import re
import sys
import urllib.request

USER_AGENT = "pordata-map research (github.com/caasols/pordata; single catalogue fetch)"
URL = "https://www.ine.pt/ine/xml_indic.jsp?opc=2&lang=PT"
OUT_DIR = pathlib.Path("data/ine")


def main() -> None:
    req = urllib.request.Request(URL, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=600) as resp:
            body = resp.read()
            status = resp.status
    except Exception as exc:
        sys.exit(f"INE fetch failed ({exc}); bot protection likely — retry "
                 "on another day, not immediately.")
    if status != 200 or len(body) < 1_000_000:
        sys.exit(f"Unexpected response: HTTP {status}, {len(body)} bytes — "
                 "probably blocked; retry later.")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "catalogue.xml.gz").write_bytes(gzip.compress(body, 9))
    xml = body.decode("utf-8", errors="replace")

    blocks = re.findall(r'<indicator id="([^"]+)">(.*?)</indicator>',
                        xml, re.DOTALL)
    field_names: set[str] = set()
    rows = []
    for ind_id, block in blocks:
        fields = {"id": ind_id}
        for tag, value in re.findall(
                r"<(\w+)>\s*(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?\s*</\1>",
                block, re.DOTALL):
            fields[tag] = re.sub(r"\s+", " ", value).strip()
            field_names.add(tag)
        rows.append(fields)

    columns = ["id"] + sorted(field_names)
    with (OUT_DIR / "indicators.csv").open("w", encoding="utf-8",
                                           newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)

    themes: dict[str, int] = {}
    for r in rows:
        t = r.get("theme", "?")
        themes[t] = themes.get(t, 0) + 1
    lines = [
        "# INE indicator catalogue (cached)", "",
        f"Fetched from `{URL}`; raw copy in `catalogue.xml.gz`, parsed rows "
        "in `indicators.csv`.", "",
        f"- indicators: **{len(rows)}** ({len({r['id'] for r in rows})} distinct ids)",
        f"- fields per entry: {', '.join(sorted(field_names))}",
        f"- themes ({len(themes)}):", "",
    ]
    lines += [f"- {t}: {n}"
              for t, n in sorted(themes.items(), key=lambda kv: -kv[1])]
    (OUT_DIR / "SUMMARY.md").write_text("\n".join(lines) + "\n",
                                        encoding="utf-8")
    print(f"cached {len(rows)} indicators, {len(body):,} bytes raw")


if __name__ == "__main__":
    main()
