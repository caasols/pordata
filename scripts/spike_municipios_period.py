#!/usr/bin/env python3
"""Spike A4 (roadmap 19): where does the period live on municipios pages?

Spike A3 found years inside a `<table>` on every sampled portugal and
europa page and on **neither** municipios page — yet both municipios
pages carried years elsewhere in the document (1991-2026, 2009-2026).
So the period is there; A3 only established that a table is the wrong
place to look for it.

A3 could not say more because it counted years by container type without
recording which container. This probe does exactly that and nothing
else: for every 4-digit year in the page, name the innermost element
that encloses it. The output is a ranked list of "years appear inside
<X> N times", which is what an extractor needs before it can be written.

Municipios pages are also the biggest (289-359 KB vs ~175 KB elsewhere),
so a second question worth answering in the same request: what is that
weight? If it is 308 município rows inline, the geographic granularity
is sitting there too.

Structure and counts only. No cell values are extracted or recorded —
years are coverage metadata, which is the thing being harvested
(decision 1). Raw HTML goes to the workflow artifact, never the repo.
"""

import collections
import json
import pathlib
import re
import time
import urllib.request

USER_AGENT = (
    "pordata-map research (github.com/caasols/pordata; "
    "3 sample pages, 20s apart)"
)
CATALOGUE = pathlib.Path("docs/data/catalogue.json")
RAW_DIR = pathlib.Path("data/spikes/raw")
REPORT = pathlib.Path("data/spikes/a4-municipios-period.md")
DELAY_SECONDS = 20
SAMPLE_SIZE = 3

YEAR = re.compile(r"\b(19[6-9]\d|20[0-2]\d)\b")
# Opening or closing tag, with the name captured.
TAG = re.compile(r"<(/?)([a-zA-Z][\w-]*)[^>]*?(/?)>")
# Years in these are almost always chrome, not data.
CHROME = {"script", "style", "head", "title", "meta", "link", "footer"}


def pick_samples() -> list:
    rows = json.loads(CATALOGUE.read_text(encoding="utf-8"))
    picked = []
    for r in rows:
        if r["area"] == "municipios" and not r.get("removed"):
            picked.append(r)
        if len(picked) >= SAMPLE_SIZE:
            break
    return picked


def enclosing_elements(html: str) -> collections.Counter:
    """Innermost open element at each year's position.

    A single pass with an explicit stack rather than a parser: the point
    is to name containers, and a lenient scan survives the malformed
    markup a scraped page routinely contains.
    """
    found = collections.Counter()
    stack: list[str] = []
    pos = 0
    for tag in TAG.finditer(html):
        segment = html[pos:tag.start()]
        if segment.strip():
            inner = stack[-1] if stack else "(root)"
            for _ in YEAR.finditer(segment):
                found[inner] += 1
        closing, name, self_closing = tag.groups()
        name = name.lower()
        if closing:
            if name in stack:
                while stack and stack.pop() != name:
                    pass
        elif not self_closing and name not in {
                "br", "hr", "img", "input", "meta", "link", "source"}:
            stack.append(name)
        pos = tag.end()
    return found


def attribute_years(html: str) -> collections.Counter:
    """Years hiding in attributes — a year-picker's value= or data-*."""
    found = collections.Counter()
    for tag in TAG.finditer(html):
        text = tag.group(0)
        if not YEAR.search(text):
            continue
        name = tag.group(2).lower()
        for attr in re.finditer(r'([\w-]+)\s*=\s*"([^"]*)"', text):
            if YEAR.search(attr.group(2)):
                found[f"<{name} {attr.group(1)}=>"] += 1
    return found


def probe(row: dict) -> dict:
    req = urllib.request.Request(row["url"],
                                 headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=120) as resp:
        raw = resp.read()
        status = resp.status
    html = raw.decode("utf-8", errors="replace")
    slug = row["url"].rstrip("/").rsplit("/", 1)[-1][:80]
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    (RAW_DIR / f"{slug}.html").write_bytes(raw)

    text_years = enclosing_elements(html)
    data_years = attribute_years(html)
    options = re.findall(r"(?is)<option[^>]*>(.*?)</option>", html)
    option_years = sum(1 for o in options if YEAR.search(o))
    return {
        "url": row["url"], "id": row["id"], "status": status,
        "bytes": len(raw),
        "in_elements": text_years.most_common(12),
        "in_attributes": data_years.most_common(8),
        "options_total": len(options),
        "options_with_a_year": option_years,
        "select_count": len(re.findall(r"(?i)<select\b", html)),
    }


def verdict(results: list) -> list:
    out = []
    merged = collections.Counter()
    for r in results:
        for name, count in r.get("in_elements", []):
            if name not in CHROME:
                merged[name] += count
    if not merged:
        return ["No years found in page content at all — the period is "
                "not in the HTML and must come from upstream (item 14)."]
    top = merged.most_common(3)
    out.append("**Years in page content sit inside: "
               + ", ".join(f"`<{n}>` ({c})" for n, c in top) + ".**")
    if any(r["options_with_a_year"] for r in results):
        total = sum(r["options_with_a_year"] for r in results)
        out.append(f"**{total} `<option>` elements carry a year** — the "
                   "period is very likely a year picker, so first/last "
                   "come from the option list, not from a table. That is "
                   "a different extractor from portugal/europa.")
    if any(r["in_attributes"] for r in results):
        out.append("Years also appear in attributes: "
                   + ", ".join(sorted({a for r in results
                                       for a, _ in r["in_attributes"]}))
                   + " — check these before parsing visible text.")
    opts = sum(r["options_total"] for r in results) / max(1, len(results))
    out.append(f"Average {opts:.0f} `<option>` elements per page. If the "
               "geography set were inline there would be ~308; there is "
               "not, so granularity still needs its own answer.")
    return out


def main() -> None:
    samples = pick_samples()
    print(f"probing {len(samples)} municipios pages, {DELAY_SECONDS}s apart")
    results = []
    for i, row in enumerate(samples):
        if i:
            time.sleep(DELAY_SECONDS)
        try:
            info = probe(row)
        except Exception as exc:                        # noqa: BLE001
            info = {"url": row["url"], "id": row["id"],
                    "error": f"{type(exc).__name__}: {exc}"}
        results.append(info)
        print(f"  municipios/{info['id']}: "
              f"{info.get('status', info.get('error'))}")

    ok = [r for r in results if "error" not in r]
    lines = [
        "# Spike A4 - where the period lives on municipios pages",
        "",
        "Roadmap 19, following A3: years were inside a `<table>` on every "
        "portugal and europa page and on neither municipios page, though "
        "both carried years elsewhere. This names the container.",
        "",
        "Structure and counts only - no cell values (decision 1). Raw HTML "
        "is a workflow artifact, never committed.",
        "",
        "## Verdict",
        "",
    ]
    lines += [f"- {v}" for v in (verdict(ok) if ok
                                 else ["All probes failed; see below."])]
    lines += ["", "## Per page", ""]
    for r in results:
        lines.append(f"### municipios/{r['id']}")
        lines.append("")
        if "error" in r:
            lines += [f"- **failed**: {r['error']}", ""]
            continue
        lines += [
            f"- status {r['status']}, {r['bytes']:,} bytes",
            f"- `<select>`: {r['select_count']}, `<option>`: "
            f"{r['options_total']} of which {r['options_with_a_year']} "
            f"contain a year",
            "- years by enclosing element: "
            + ", ".join(f"`{n}` {c}" for n, c in r["in_elements"]),
            "- years in attributes: "
            + (", ".join(f"`{a}` {c}" for a, c in r["in_attributes"])
               or "none"),
            "",
        ]
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"report written: {REPORT}")


if __name__ == "__main__":
    main()
