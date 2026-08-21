#!/usr/bin/env python3
"""Fetch the PORDATA sitemap and write sorted snapshots for diffing.

One polite request per run. Run from the repo root:

    python3 scripts/fetch_sitemap.py

Writes:
    data/sitemap-urls.txt     one URL per line, sorted — the page inventory
    data/sitemap-lastmod.tsv  "url<TAB>lastmod" per line, sorted — update tracking

Commit the outputs; git history then records every page added, removed or
touched between runs. `scripts/diff_sitemap.py` turns that into a report.

Must run from a network that can reach pordata.pt (the remote Claude
sandbox cannot; a laptop or a GitHub Actions runner can).
"""

import collections
import pathlib
import re
import sys
import urllib.request

SITEMAP_URL = "https://www.pordata.pt/PordataSitemap.aspx"
USER_AGENT = (
    "pordata-map research (github.com/caasols/pordata; "
    "single sitemap request per run)"
)
URLS_FILE = pathlib.Path("data/sitemap-urls.txt")
LASTMOD_FILE = pathlib.Path("data/sitemap-lastmod.tsv")


def main() -> None:
    req = urllib.request.Request(SITEMAP_URL, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=120) as resp:
        xml = resp.read().decode("utf-8", errors="replace")

    entries: dict[str, str] = {}
    for block in re.findall(r"<url\b[^>]*>(.*?)</url>", xml, re.DOTALL):
        loc = re.search(r"<loc>\s*(.*?)\s*</loc>", block)
        if not loc:
            continue
        lastmod = re.search(r"<lastmod>\s*(.*?)\s*</lastmod>", block)
        entries[loc.group(1)] = lastmod.group(1) if lastmod else ""
    if not entries:  # sitemap without <url> wrappers; fall back to bare <loc>
        entries = {u: "" for u in re.findall(r"<loc>\s*(.*?)\s*</loc>", xml)}
    if not entries:
        sys.exit("No <loc> entries found; has the sitemap format changed?")

    URLS_FILE.parent.mkdir(exist_ok=True)
    urls = sorted(entries)
    URLS_FILE.write_text("\n".join(urls) + "\n", encoding="utf-8")
    LASTMOD_FILE.write_text(
        "".join(f"{u}\t{entries[u]}\n" for u in urls), encoding="utf-8"
    )

    segments = collections.Counter(
        (url.split("pordata.pt/", 1)[-1].split("/", 1)[0] or "(root)")
        for url in urls
    )
    print(f"{len(urls)} URLs written to {URLS_FILE} and {LASTMOD_FILE}")
    for segment, count in segments.most_common(20):
        print(f"{count:6d}  /{segment}")
    with_lastmod = sum(1 for v in entries.values() if v)
    print(f"lastmod present on {with_lastmod}/{len(entries)} entries")


if __name__ == "__main__":
    main()
