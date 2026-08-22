#!/usr/bin/env python3
"""3c: extract PORDATA's featured-indicator sets.

Fetches TWO municipios/quadro+resumo pages (to confirm the indicator set
is identical across municipalities) and up to two Retratos pages, and
records which indicator pages each references (links matching
/{area}/{slug}-{id}). Four requests total, 20 s apart — the editorial
selection is captured without harvesting 308 near-identical pages, and no
data values are stored.

Output: data/catalogue/featured.json, which build_catalogue.py merges as
`featured` flags on catalogue entries.
"""

import json
import pathlib
import re
import time
import urllib.request

USER_AGENT = (
    "pordata-map research (github.com/caasols/pordata; "
    "4 sample pages, 20s apart)"
)
URLS_FILE = pathlib.Path("data/sitemap-urls.txt")
OUT_FILE = pathlib.Path("data/catalogue/featured.json")
DELAY_SECONDS = 20

LINK_RE = re.compile(
    r'href="(?:https?://www\.pordata\.pt)?'
    r'(/(?:portugal|municipios|europa)/[^"#?]+-(\d+))"')


def indicator_ids(html: str) -> set[int]:
    return {int(m.group(2)) for m in LINK_RE.finditer(html)}


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read().decode("utf-8", errors="replace")


def href_inventory(html: str) -> dict[str, int]:
    """First path segment of every href on the page, for diagnosis when no
    indicator links are found (the page may build links client-side)."""
    counts: dict[str, int] = {}
    for m in re.finditer(r'href="([^"]+)"', html):
        href = m.group(1)
        path = href.split("pordata.pt", 1)[-1] if "pordata.pt" in href else href
        seg = "/".join(path.lstrip("/").split("/")[:2])[:60] or "(empty)"
        counts[seg] = counts.get(seg, 0) + 1
    return dict(sorted(counts.items(), key=lambda kv: -kv[1])[:30])


def main() -> None:
    urls = URLS_FILE.read_text(encoding="utf-8").split()
    quadros_mun = [u for u in urls if "municipios/quadro+resumo" in u][:2]
    quadros_eur = [u for u in urls if "europa/quadro+resumo" in u][:1]
    retratos = [u for u in urls
                if u.split("pordata.pt/", 1)[-1].startswith("retratos/")]
    retratos = (sorted(retratos, key=lambda u: "municip" not in u))[:1]

    raw_dir = pathlib.Path("data/catalogue/featured-raw")
    raw_dir.mkdir(parents=True, exist_ok=True)
    result = {"fetched_at": time.strftime("%Y-%m-%d", time.gmtime())}
    first = True
    sets = {}
    for group, sample_urls in (("quadro_resumo_municipios", quadros_mun),
                               ("quadro_resumo_europa", quadros_eur),
                               ("retratos", retratos)):
        per_page = []
        for url in sample_urls:
            if not first:
                time.sleep(DELAY_SECONDS)
            first = False
            print("fetching", url)
            html = fetch(url)
            slug = url.rstrip("/").rsplit("/", 1)[-1][:60]
            (raw_dir / f"{group}-{slug}.html").write_text(
                html, encoding="utf-8")
            per_page.append((url, indicator_ids(html), href_inventory(html)))
        if not per_page:
            continue
        union = set().union(*(ids for _, ids, _ in per_page))
        identical = len(per_page) < 2 or per_page[0][1] == per_page[1][1]
        sets[group] = {
            "indicator_ids": sorted(union),
            "identical_across_samples": identical,
            "samples": [u for u, _, _ in per_page],
            "counts_per_sample": [len(ids) for _, ids, _ in per_page],
        }
        if not union:  # nothing matched; keep the diagnosis
            sets[group]["debug_hrefs"] = per_page[0][2]
        print(f"{group}: {len(union)} indicators referenced, "
              f"identical_across_samples={identical}")

    result.update(sets)
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(json.dumps(result, ensure_ascii=False, indent=1),
                        encoding="utf-8")
    print("written", OUT_FILE)


if __name__ == "__main__":
    main()
