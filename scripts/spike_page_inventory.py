#!/usr/bin/env python3
"""Spike A6: what else is on a PORDATA page that we never captured?

Two fields have now been discovered *after* the harvest that could have
been captured during it — the chart caption carrying the unit (A3) and
the period (A4) — and the owner has spotted a third: every indicator page
carries a plain-language **question** under the title, which nothing in
`pages.jsonl` holds. Raw HTML is not stored, so each late discovery costs
another full fetch.

This probe therefore does not go looking for questions. Targeted probes
are what keep missing things. It **inventories the page**: every
text-bearing element, grouped by tag and class, with counts and short
samples, so the next reader sees what is actually there rather than what
someone thought to search for. Item 21 fires once "what else should we
be pulling off these pages?" stops changing; this is how that question
gets answered instead of guessed.

Structure and short metadata samples only — headings, labels, questions.
No data values are extracted or written (decision 1); numeric-looking
text is counted and redacted rather than recorded. Raw HTML goes to the
workflow artifact, never the repo.
"""

import collections
import html as html_mod
import json
import pathlib
import re
import time
import urllib.request

USER_AGENT = (
    "pordata-map research (github.com/caasols/pordata; "
    "one page per area, 20s apart)"
)
CATALOGUE = pathlib.Path("docs/data/catalogue.json")
RAW_DIR = pathlib.Path("data/spikes/raw")
REPORT = pathlib.Path("data/spikes/a6-page-inventory.md")
DELAY_SECONDS = 20

# Elements that hold page furniture rather than content.
SKIP_TAGS = {"script", "style", "noscript", "svg", "path", "head"}
# A run of digits with grouping is a data value; never record one.
VALUE_LIKE = re.compile(r"\d[\d\s., ]{4,}\d")
TEXT_BLOCK = re.compile(
    r"<(?P<tag>h1|h2|h3|h4|h5|p|li|dt|dd|caption|figcaption|label|"
    r"summary|legend|th|button|a|span|div)\b(?P<attrs>[^>]*)>"
    r"(?P<inner>.*?)</(?P=tag)>",
    re.I | re.S)
CLASS = re.compile(r'class\s*=\s*"([^"]*)"', re.I)
TAG = re.compile(r"<[^>]+>")


def clean(fragment: str) -> str:
    text = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", fragment)
    text = html_mod.unescape(TAG.sub(" ", text))
    return re.sub(r"\s+", " ", text).strip()


def redact(text: str) -> str:
    """Keep the shape of a string without recording any figures."""
    return VALUE_LIKE.sub("<number>", text)


def inventory(html: str) -> dict:
    """Every text-bearing block, grouped by tag + first class token."""
    groups = collections.defaultdict(list)
    for m in TEXT_BLOCK.finditer(html):
        tag = m.group("tag").lower()
        if tag in SKIP_TAGS:
            continue
        text = clean(m.group("inner"))
        # a block whose text is only its children's is noise at this level
        if not text or len(text) > 400:
            continue
        classes = CLASS.search(m.group("attrs") or "")
        first = (classes.group(1).split()[0] if classes
                 and classes.group(1).strip() else "")
        groups[f"{tag}.{first}" if first else tag].append(text)
    return groups


def questions(html: str) -> list:
    """Sentences ending in '?' — the field that prompted this probe."""
    found, seen = [], set()
    for m in TEXT_BLOCK.finditer(html):
        text = clean(m.group("inner"))
        if not text or len(text) > 240 or not text.rstrip().endswith("?"):
            continue
        if text not in seen:
            seen.add(text)
            found.append(text)
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

    groups = inventory(html)
    # rank by how distinctive a group is: few instances, real text
    ranked = sorted(groups.items(), key=lambda kv: (len(kv[1]), -len(kv[1][0])))
    return {
        "url": row["url"], "area": row["area"], "id": row["id"],
        "status": status, "bytes": len(raw),
        "name": row.get("title") or row["name"],
        "group_count": len(groups),
        "questions": [redact(q) for q in questions(html)][:8],
        "singletons": [(k, redact(v[0])[:150]) for k, v in ranked
                       if len(v) == 1][:22],
        "repeated": [(k, len(v), redact(v[0])[:80]) for k, v in
                     sorted(groups.items(), key=lambda kv: -len(kv[1]))[:10]],
    }


def main() -> None:
    rows = json.loads(CATALOGUE.read_text(encoding="utf-8"))
    picked, seen = [], set()
    for r in rows:
        if r["area"] not in seen and not r.get("removed"):
            seen.add(r["area"])
            picked.append(r)
    print(f"probing {len(picked)} pages (one per area), "
          f"{DELAY_SECONDS}s apart")

    results = []
    for i, row in enumerate(picked):
        if i:
            time.sleep(DELAY_SECONDS)
        try:
            info = probe(row)
        except Exception as exc:                        # noqa: BLE001
            info = {"url": row["url"], "area": row["area"], "id": row["id"],
                    "error": f"{type(exc).__name__}: {exc}"}
        results.append(info)
        print(f"  {info['area']}/{info['id']}: "
              f"{info.get('status', info.get('error'))}")

    lines = [
        "# Spike A6 - full page inventory",
        "",
        "Two fields were discovered *after* the harvest that could have "
        "been captured during it (the unit caption, the period), and the "
        "owner spotted a third: the plain-language **question** under "
        "each title. Raw HTML is not stored, so each late discovery costs "
        "another full fetch.",
        "",
        "So this does not search for questions. It inventories every "
        "text-bearing element by tag and class, so the next reader sees "
        "what is on the page rather than what someone thought to look "
        "for. Item 21 fires once \"what else should we pull off these "
        "pages?\" stops changing; this is how that gets answered.",
        "",
        "Structure and metadata only. Numeric runs are redacted to "
        "`<number>` rather than recorded (decision 1); raw HTML is a "
        "workflow artifact, never committed.",
        "",
    ]
    for r in results:
        lines += [f"## {r['area']}/{r['id']}", ""]
        if "error" in r:
            lines += [f"- **failed**: {r['error']}", ""]
            continue
        lines += [
            f"*{r['name']}*",
            "",
            f"- status {r['status']}, {r['bytes']:,} bytes, "
            f"{r['group_count']} distinct tag/class groups",
            "",
            "### Questions found on the page",
            "",
        ]
        lines += ([f"- {q}" for q in r["questions"]]
                  or ["- none matched"])
        lines += ["", "### One-of-a-kind blocks (candidate fields)", ""]
        lines += [f"- `{k}` — {v}" for k, v in r["singletons"]]
        lines += ["", "### Most repeated blocks (page furniture)", ""]
        lines += [f"- `{k}` ×{n} — {sample}"
                  for k, n, sample in r["repeated"]]
        lines.append("")
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"report written: {REPORT}")


if __name__ == "__main__":
    main()
