"""Spike: what shape is Eurostat's catalogue, and can we enumerate it?

Roadmap 2's open half. 638 `europa` rows are unrouted, and the roadmap
is explicit about the trap: **measure Eurostat the same way INE was
measured before specifying anything.** Spike A5's one-to-many finding is
a fact about INE's database, not a law of statistics offices, and
assuming it carries over is exactly the error decision 7 exists to stop.

**Candidates, not addresses.** Nobody here knows Eurostat's current
catalogue endpoint, and guessing one and reporting a 404 as "not
enumerable" would repeat the A3 mistake — a negative result manufactured
by a wrong query. Several are tried, every outcome is recorded including
the misses, and the report says plainly which resolved.

What the report has to answer, because the crosswalk design depends on
all four:

1. **Is it enumerable at all** without an API key?
2. **What is the unit** — a dataset, a dimension-sliced series, or
   something else? INE's unit is a series, which is what made the
   relation one-to-many. Eurostat may differ.
3. **How large** is the catalogue, so item 16's European half has a
   denominator?
4. **What identifies a dataset** — the code that a fetch URL needs.

Raw responses go to the workflow artifact only; `data/spikes/raw/` is
gitignored, so no upstream content lands in the repo.
"""

import collections
import gzip
import io
import pathlib
import re
import time
import urllib.error
import urllib.request

USER_AGENT = (
    "pordata-map research (github.com/caasols/pordata; "
    "measuring catalogue shape before building a crosswalk)"
)
RAW_DIR = pathlib.Path("data/spikes/raw/eurostat")
REPORT = pathlib.Path("data/spikes/eurostat-toc.md")
DELAY_SECONDS = 6
TIMEOUT = 120
MAX_RAW = 4_000_000

BASE = "https://ec.europa.eu/eurostat/api/dissemination"
CANDIDATES = [
    ("toc-txt", f"{BASE}/catalogue/toc/txt"),
    ("toc-xml", f"{BASE}/catalogue/toc/xml"),
    ("sdmx-dataflow", f"{BASE}/sdmx/2.1/dataflow/ESTAT/all/latest"),
    ("files-inventory",
     f"{BASE}/files/inventory?type=data"),
]

# A dataset code looks like `nama_10_gdp` or `gov_10a_exp` — lowercase
# letters, digits and underscores. Counting distinct ones is the honest
# way to size the catalogue whatever format came back.
CODE = re.compile(r"\b[a-z][a-z0-9]*(?:_[a-z0-9]+){1,6}\b")


def fetch(url: str) -> dict:
    request = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT,
                      "Accept-Encoding": "gzip, deflate"})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            body = response.read()
            if response.headers.get("Content-Encoding") == "gzip":
                body = gzip.decompress(body)
            return {"status": response.status, "final_url": response.url,
                    "bytes": len(body), "body": body,
                    "content_type": response.headers.get("Content-Type", "")}
    except urllib.error.HTTPError as exc:
        return {"status": exc.code, "final_url": url, "bytes": 0,
                "body": b"", "content_type": "", "error": f"HTTP {exc.code}"}
    except Exception as exc:                       # noqa: BLE001
        return {"status": 0, "final_url": url, "bytes": 0, "body": b"",
                "content_type": "", "error": f"{type(exc).__name__}: {exc}"}


def profile(name: str, body: bytes) -> dict:
    """Whatever came back, describe it without assuming a format."""
    text = body.decode("utf-8", "replace")
    lines = text.splitlines()
    codes = collections.Counter(CODE.findall(text.lower()))
    return {
        "lines": len(lines),
        "distinct_codes": len(codes),
        "top_codes": codes.most_common(8),
        "head": "\n".join(lines[:12])[:1500],
        "looks_like": ("xml" if text.lstrip().startswith("<") else
                       "json" if text.lstrip().startswith(("{", "[")) else
                       "tsv" if "\t" in (lines[0] if lines else "") else
                       "text"),
    }


def render(results: list) -> str:
    lines = [
        "# Spike: Eurostat's catalogue — shape, size and identifiers",
        "",
        "Roadmap 2's open half. **Measured before specifying anything**, "
        "because spike A5's one-to-many finding is a fact about INE's "
        "database and not a law of statistics offices. Candidates, not "
        "addresses: every outcome below is recorded, misses included, so "
        "a 404 reads as a wrong guess rather than as \"not enumerable\".",
        "",
    ]
    for name, url, attempt in results:
        mark = "ok" if attempt["status"] == 200 else "MISS"
        lines.append(f"## {mark} `{name}`")
        lines.append("")
        lines.append(f"- `{url}`")
        lines.append(f"- status {attempt['status']}, "
                     f"{attempt['bytes'] / 1024:.0f} KB, "
                     f"`{attempt.get('content_type', '')}`"
                     + (f" — {attempt['error']}" if attempt.get("error")
                        else ""))
        shape = attempt.get("profile")
        if shape:
            lines += [
                f"- looks like **{shape['looks_like']}**, "
                f"{shape['lines']} lines",
                f"- **{shape['distinct_codes']} distinct dataset-code-shaped "
                f"tokens**",
                "",
                "```",
                shape["head"],
                "```",
            ]
        lines.append("")
    lines += [
        "## What this has to settle before the crosswalk is written",
        "",
        "1. Enumerable without a key — yes/no.",
        "2. **What the unit is.** INE's is a series, which is what made "
        "the relation one-to-many. If Eurostat's unit is a *dataset* with "
        "dimensions, one PORDATA indicator may map to one dataset plus a "
        "dimension filter — a different shape needing a different schema.",
        "3. Catalogue size, so item 16's European half has a denominator.",
        "4. The identifier a fetch URL needs.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    results = []
    for index, (name, url) in enumerate(CANDIDATES):
        if index:
            time.sleep(DELAY_SECONDS)
        print(f"fetching {name}: {url}")
        attempt = fetch(url)
        if attempt["body"]:
            attempt["profile"] = profile(name, attempt["body"])
            (RAW_DIR / f"{name}.txt").write_bytes(attempt["body"][:MAX_RAW])
        attempt.pop("body", None)
        results.append((name, url, attempt))
    REPORT.write_text(render(results), encoding="utf-8")
    served = sum(1 for _n, _u, a in results if a["status"] == 200)
    print(f"eurostat toc: {served}/{len(results)} candidates served; "
          f"report at {REPORT}")


if __name__ == "__main__":
    main()
