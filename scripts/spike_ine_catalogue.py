#!/usr/bin/env python3
"""Spike A2: does INE expose an enumerable indicator catalogue?

Backlog item 3. INE has a JSON API for fetching a series given a code you
already know; the open question is whether the *catalogue* (the list of
all indicators with codes and names) is fetchable, which would hand us
much of the PORDATA-to-INE crosswalk for free.

Tries a set of candidate endpoints (documented and folklore), records
status, content type, size and a content sample for each, counts
catalogue-like entries where the payload parses, and scrapes the API docs
page for further endpoint names. Raw responses under data/spikes/raw/
(workflow artifact); analysis in data/spikes/a2-ine-catalogue.md.
"""

import json
import pathlib
import re
import time
import urllib.request

USER_AGENT = "pordata-map research (github.com/caasols/pordata)"
RAW_DIR = pathlib.Path("data/spikes/raw")
REPORT = pathlib.Path("data/spikes/a2-ine-catalogue.md")
DELAY_SECONDS = 2

CANDIDATES = [
    ("docs-page", "https://www.ine.pt/xportal/xmain?xpid=INE&xpgid=ine_api"),
    ("json-series-example",
     "https://www.ine.pt/ine/json_indicador/pindica.jsp?op=2&varcd=0000611&lang=PT"),
    ("json-metadata-example",
     "https://www.ine.pt/ine/json_indicador/pindicaMeta.jsp?varcd=0000611&lang=PT"),
    ("xml-catalogue-opc1", "https://www.ine.pt/ine/xml_indic.jsp?opc=1&lang=PT"),
    ("xml-catalogue-opc2", "https://www.ine.pt/ine/xml_indic.jsp?opc=2&lang=PT"),
    ("dadosgov-ine-search",
     "https://dados.gov.pt/api/1/datasets/?q=ine%20indicadores&page_size=5"),
]

ENTRY_PATTERNS = [r"<indicador\b", r'"IndicadorCod"', r'"varcd"', r"<indic\b"]


def fetch(name: str, url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = resp.read()
            status = resp.status
            ctype = resp.headers.get("Content-Type", "")
    except Exception as exc:  # record the failure, keep probing
        return {"name": name, "url": url, "error": str(exc)[:200]}
    (RAW_DIR / f"ine-{name}.txt").write_bytes(body[:2_000_000])
    text = body.decode("utf-8", errors="replace")
    entry_counts = {p: len(re.findall(p, text)) for p in ENTRY_PATTERNS}
    parsed_json_items = None
    if "json" in ctype or text.lstrip()[:1] in "[{":
        try:
            payload = json.loads(text)
            parsed_json_items = len(payload) if isinstance(payload, list) else \
                len(payload.get("data", payload)) if isinstance(payload, dict) else None
        except ValueError:
            pass
    return {
        "name": name, "url": url, "status": status, "content_type": ctype,
        "bytes": len(body), "sample": re.sub(r"\s+", " ", text[:280]),
        "entry_counts": entry_counts, "parsed_json_items": parsed_json_items,
    }


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    results = []
    for i, (name, url) in enumerate(CANDIDATES):
        if i:
            time.sleep(DELAY_SECONDS)
        print("fetching", name)
        results.append(fetch(name, url))

    docs = next((r for r in results if r["name"] == "docs-page"
                 and "error" not in r), None)
    discovered = []
    if docs:
        raw = (RAW_DIR / "ine-docs-page.txt").read_text(
            encoding="utf-8", errors="replace")
        discovered = sorted(set(re.findall(
            r"[\w/\.]*(?:jsp|servlet)[^\s\"'<>]*", raw)))[:30]

    lines = ["# Spike A2: INE catalogue enumerability", "",
             "Question: can the full INE indicator catalogue be listed "
             "programmatically? Raw responses in the `spike-raw` artifact.", ""]
    for r in results:
        lines.append(f"## {r['name']}")
        lines.append("")
        lines.append(f"`{r['url']}`")
        lines.append("")
        if "error" in r:
            lines.append(f"- FAILED: {r['error']}")
        else:
            lines.append(f"- HTTP {r['status']}, {r['bytes']:,} bytes, "
                         f"{r['content_type']}")
            counts = ", ".join(f"`{p}`={n}" for p, n in r["entry_counts"].items() if n)
            lines.append(f"- entry-pattern counts: {counts or 'none'}")
            if r["parsed_json_items"] is not None:
                lines.append(f"- parsed as JSON: {r['parsed_json_items']} top-level items")
            lines.append(f"- sample: `{r['sample']}`")
        lines.append("")
    if discovered:
        lines += ["## Endpoint names found on the docs page", ""]
        lines += [f"- `{e}`" for e in discovered]
        lines.append("")
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("report written to", REPORT)


if __name__ == "__main__":
    main()
