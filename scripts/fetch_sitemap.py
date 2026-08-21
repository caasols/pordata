#!/usr/bin/env python3
"""Fetch the PORDATA sitemap and write a sorted URL list for diffing.

One polite request per run. Run from the repo root:

    python3 scripts/fetch_sitemap.py

Writes data/sitemap-urls.txt (all URLs, deduplicated, sorted) and prints
counts by first path segment plus whether <lastmod> is present. Commit the
output; git history then records every page added or removed between runs.

Must run from a network that can reach pordata.pt (the remote Claude
sandbox cannot; a laptop can).
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
OUT_FILE = pathlib.Path("data/sitemap-urls.txt")


def main() -> None:
    req = urllib.request.Request(SITEMAP_URL, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=120) as resp:
        xml = resp.read().decode("utf-8", errors="replace")

    urls = sorted(set(re.findall(r"<loc>\s*(.*?)\s*</loc>", xml)))
    if not urls:
        sys.exit("No <loc> entries found; has the sitemap format changed?")

    OUT_FILE.parent.mkdir(exist_ok=True)
    OUT_FILE.write_text("\n".join(urls) + "\n", encoding="utf-8")

    segments = collections.Counter(
        (url.split("pordata.pt/", 1)[-1].split("/", 1)[0] or "(root)")
        for url in urls
    )
    print(f"{len(urls)} URLs written to {OUT_FILE}")
    for segment, count in segments.most_common(20):
        print(f"{count:6d}  /{segment}")
    print("lastmod present:", "<lastmod>" in xml)


if __name__ == "__main__":
    main()
