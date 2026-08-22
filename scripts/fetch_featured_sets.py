#!/usr/bin/env python3
"""3c: extract PORDATA's featured-indicator sets from quadro+resumo pages.

Fetches two municipios/quadro+resumo pages (to confirm the set is
identical across municipalities) and one europa quadro. Quadro rows are
OutSystems postbacks with no indicator links or ids, but the indicator
NAMES are server-rendered — each name appears as a duplicated text line
(mobile + desktop rendering). We extract the names; build_catalogue.py
matches them to catalogue entries to produce `featured` flags. No data
values are stored.

Retratos pages were checked (2026-08-22) and are e-book publication
pages with no per-indicator list, so they carry no featured signal.

Output: data/catalogue/featured.json.
"""

import json
import pathlib
import re
import time
import unicodedata
import urllib.request

USER_AGENT = (
    "pordata-map research (github.com/caasols/pordata; "
    "3 sample pages, 20s apart)"
)
URLS_FILE = pathlib.Path("data/sitemap-urls.txt")
OUT_FILE = pathlib.Path("data/catalogue/featured.json")
DELAY_SECONDS = 20

STOPLIST = {"simbologia", "exportar dados", "pdf", "excel", "todas",
            "videos", "livros", "quadro resumo", "quadros resumo"}


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read().decode("utf-8", errors="replace")


def to_lines(html: str) -> list[str]:
    import html as html_mod
    text = re.sub(r"<(script|style)\b.*?</\1>", " ", html,
                  flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"</(tr|li|div|h\d|td|span|p)>", "\n", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html_mod.unescape(text)
    text = re.sub(r"[ \t]+", " ", text)
    return [ln.strip() for ln in text.splitlines() if ln.strip()]


def norm(s: str) -> str:
    s = re.sub(r"\(\d\)", "", s)          # footnote markers
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s).strip().lower()


def extract_names(html: str) -> list[str]:
    """Indicator names: lines duplicated within the next two lines,
    starting with an uppercase letter, not obvious UI text."""
    lines = to_lines(html)
    names, seen = [], set()
    for i, line in enumerate(lines):
        n = norm(line)
        if len(n) < 10 or n in seen or n in STOPLIST:
            continue
        if not line[:1].isupper():
            continue
        following = [norm(x) for x in lines[i + 1:i + 3]]
        if n in following:
            name = re.sub(r"\s*\(\d\)\s*$", "", line).strip()
            # name/desc/name/desc rendering: absorb the subtitle line —
            # it disambiguates matching (e.g. which "renováveis" series)
            subtitle = lines[i + 1].strip() if len(lines) > i + 3 else ""
            if norm(lines[i + 2]) == n and subtitle \
                    and norm(subtitle) == norm(lines[i + 3]) \
                    and not re.fullmatch(r"\(\d+\)", subtitle) \
                    and len(subtitle) > 4:
                name = f"{name} — {subtitle}"
                seen.add(norm(subtitle))
            names.append(name)
            seen.add(n)
    return names


def main() -> None:
    urls = URLS_FILE.read_text(encoding="utf-8").split()
    groups = {
        "quadro_resumo_municipios":
            [u for u in urls if "municipios/quadro+resumo" in u][:2],
        "quadro_resumo_europa":
            [u for u in urls if "europa/quadro+resumo" in u][:1],
    }

    result = {
        "fetched_at": time.strftime("%Y-%m-%d", time.gmtime()),
        "note": ("Quadro rows are postbacks without ids; names are matched "
                 "to catalogue entries at build time. Retratos pages are "
                 "e-book publications with no per-indicator list."),
    }
    first = True
    for group, sample_urls in groups.items():
        per_page = []
        for url in sample_urls:
            if not first:
                time.sleep(DELAY_SECONDS)
            first = False
            print("fetching", url)
            per_page.append((url, extract_names(fetch(url))))
        if not per_page:
            continue
        base = per_page[0][1]
        identical = all(
            [norm(n) for n in names] == [norm(n) for n in base]
            for _, names in per_page[1:])
        result[group] = {
            "indicator_names": base,
            "identical_across_samples": identical,
            "samples": [u for u, _ in per_page],
            "counts_per_sample": [len(names) for _, names in per_page],
        }
        print(f"{group}: {len(base)} names, identical={identical}")

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(json.dumps(result, ensure_ascii=False, indent=1),
                        encoding="utf-8")
    print("written", OUT_FILE)


if __name__ == "__main__":
    main()
