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
import os
import pathlib
import re
import sys
import urllib.request

if __package__:
    from . import pordata_lib as lib
else:  # executed directly
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import pordata_lib as lib

SITEMAP_URL = "https://www.pordata.pt/PordataSitemap.aspx"
USER_AGENT = (
    "pordata-map research (github.com/caasols/pordata; "
    "single sitemap request per run)"
)
URLS_FILE = pathlib.Path("data/sitemap-urls.txt")
LASTMOD_FILE = pathlib.Path("data/sitemap-lastmod.tsv")

# A snapshot that loses more than this fraction of indicator targets is
# refused: PORDATA switching to a <sitemapindex> (or any format change
# the parser mis-reads) would otherwise write a near-empty snapshot,
# and the build would tombstone the whole catalogue as "descontinuado"
# automatically. Set ALLOW_MASS_REMOVAL=1 to accept a genuine one.
MIN_TARGET_RATIO = 0.95


def count_targets(urls: list[str]) -> list[str]:
    """Indicator targets among a fresh URL list, by the same definition
    the harvester uses (lib.targets reads a file; this reads memory)."""
    picked = []
    for u in urls:
        path = u.split("pordata.pt/", 1)[-1]
        area = path.split("/", 1)[0]
        if area in lib.AREA_PREFIXES and "/en/" not in u \
                and "quadro+resumo" not in u and re.search(r"-\d+$", u):
            picked.append(u)
    return picked


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

    # Corpus floor: compare indicator targets, not raw URL count, so the
    # check tracks what the catalogue is actually built from.
    new_targets = len(count_targets(urls))
    if URLS_FILE.exists() and not os.environ.get("ALLOW_MASS_REMOVAL"):
        old_targets = len(lib.targets(URLS_FILE))
        if old_targets and new_targets < old_targets * MIN_TARGET_RATIO:
            sys.exit(
                f"Refusing to overwrite the snapshot: indicator targets "
                f"fell {old_targets} -> {new_targets} "
                f"({new_targets / old_targets:.1%} of baseline, floor "
                f"{MIN_TARGET_RATIO:.0%}). Either the sitemap format "
                f"changed or PORDATA removed a large share of pages. "
                f"Inspect, then re-run with ALLOW_MASS_REMOVAL=1 to accept."
            )

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
