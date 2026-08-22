#!/usr/bin/env python3
"""Spike A1: is PORDATA indicator-page metadata server-rendered?

Fetches three sample indicator pages (one per statistical area) with 20
seconds between requests, saves the raw HTML under data/spikes/raw/ (not
committed; uploaded as a workflow artifact), and writes an analysis to
data/spikes/a1-pordata-probe.md answering: does the server HTML already
contain the metadata the catalogue needs (name, Fontes/Entidades, última
atualização), or is it injected client-side by OutSystems — and if
client-side, do the /screenservices/ JSON endpoints show up as the
alternative harvest route?
"""

import pathlib
import re
import time
import urllib.request

USER_AGENT = (
    "pordata-map research (github.com/caasols/pordata; "
    "3 sample pages, 20s apart)"
)
URLS_FILE = pathlib.Path("data/sitemap-urls.txt")
RAW_DIR = pathlib.Path("data/spikes/raw")
REPORT = pathlib.Path("data/spikes/a1-pordata-probe.md")
DELAY_SECONDS = 20

MARKERS = [
    "Fontes", "Entidades", "atualiza", "actualiza", "OSFillParent",
    "screenservices", "application/json", "<table", "og:title",
]


def pick_samples() -> list[str]:
    urls = URLS_FILE.read_text(encoding="utf-8").split()
    samples = []
    for prefix in ("/portugal/", "/municipios/", "/europa/"):
        for u in urls:
            if prefix in u and "/en/" not in u and "quadro+resumo" not in u \
                    and re.search(r"-\d+$", u):
                samples.append(u)
                break
    return samples


def probe(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=120) as resp:
        body = resp.read()
        info = {
            "url": url,
            "status": resp.status,
            "content_type": resp.headers.get("Content-Type", ""),
            "bytes": len(body),
        }
    html = body.decode("utf-8", errors="replace")
    slug = url.rstrip("/").rsplit("/", 1)[-1][:80]
    (RAW_DIR / f"{slug}.html").write_bytes(body)

    info["title"] = (re.search(r"<title[^>]*>(.*?)</title>", html, re.S) or [None, ""])[1].strip()[:200]
    info["markers"] = {m: html.count(m) for m in MARKERS}
    info["script_tags"] = len(re.findall(r"<script\b", html))
    info["screenservices_paths"] = sorted(set(
        re.findall(r"[\"'](/[^\"']*screenservices[^\"']*)[\"']", html)
    ))[:10]
    info["json_ld"] = len(re.findall(
        r'<script[^>]+application/ld\+json', html))
    return info


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    samples = pick_samples()
    results = []
    for i, url in enumerate(samples):
        if i:
            time.sleep(DELAY_SECONDS)
        print("probing", url)
        results.append(probe(url))

    lines = ["# Spike A1: PORDATA indicator page probe", "",
             "Question: is catalogue metadata in the server-rendered HTML, or "
             "client-side? Raw HTML in the workflow artifact `spike-raw`.", ""]
    for r in results:
        lines += [
            f"## `{r['url'].split('pordata.pt/')[-1]}`",
            "",
            f"- HTTP {r['status']}, {r['bytes']:,} bytes, {r['content_type']}",
            f"- `<title>`: {r['title']!r}",
            f"- `<script>` tags: {r['script_tags']}, JSON-LD blocks: {r['json_ld']}",
            "- Marker counts: " + ", ".join(
                f"`{m}`={n}" for m, n in r["markers"].items()),
        ]
        if r["screenservices_paths"]:
            lines.append("- screenservices paths found:")
            lines += [f"  - `{p}`" for p in r["screenservices_paths"]]
        lines.append("")

    server_rendered = all(
        r["markers"]["Fontes"] > 0 or r["markers"]["Entidades"] > 0
        for r in results
    )
    lines += ["## Verdict (heuristic)", "",
              "Fontes/Entidades present in server HTML on every sampled page: "
              f"**{server_rendered}**. "
              + ("A plain-HTTP harvester should work."
                 if server_rendered else
                 "Metadata appears client-side; inspect the raw HTML artifact "
                 "and the screenservices endpoints for the JSON route, or "
                 "fall back to a headless browser.")]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("report written to", REPORT)


if __name__ == "__main__":
    main()
