"""Spike: where does the period live on europa pages? (roadmap 20)

The last open question in the field-capture thread. `extract_period`
covers two of PORDATA's three templates and neither mechanism appears on
the third:

- **portugal** — named year elements (`YearCurrentText` / `YearOtherText`)
- **municipios** — a `<select>` of year `<option>`s
- **europa** — neither, so `period_ratio[europa]` sits at a floor of 0

A4 answered the same question for municipios by naming, for every
4-digit year in the page, the innermost element enclosing it. That is
the right shape of question — it produces a selector rather than a
hypothesis — so this is A4 pointed at europa, plus an explicit check for
the two mechanisms already known, because "europa uses the municipios
picker after all" is the cheapest possible answer and worth ruling in or
out first.

Structure and counts only. Years are coverage metadata, which is what
this project harvests; no cell values are extracted (decision 1). Raw
HTML goes to the workflow artifact, never the repo.
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
REPORT = pathlib.Path("data/spikes/europa-period.md")
DELAY_SECONDS = 20
SAMPLE_SIZE = 3
TIMEOUT = 60

YEAR = re.compile(r"\b(19[6-9]\d|20[0-2]\d)\b")
TAG = re.compile(r"<(/?)([a-zA-Z][\w-]*)([^>]*?)(/?)>")
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input",
        "link", "meta", "param", "source", "track", "wbr"}
CLASS = re.compile(r'class="([^"]*)"')

# The two mechanisms already implemented, checked by name so the answer
# can be "it is the one we already handle" without any new parsing.
KNOWN = {
    "portugal year element": re.compile(
        r'class="[^"]*Year(?:Current|Other)Text', re.I),
    "municipios year picker": re.compile(r'<option[^>]+value="(?:19|20)\d\d"',
                                         re.I),
    "select element at all": re.compile(r"<select\b", re.I),
    "time element": re.compile(r"<time\b", re.I),
    "data attribute with a year": re.compile(
        r'data-[\w-]+="(?:19|20)\d\d"', re.I),
}


def enclosing(html: str) -> collections.Counter:
    """For every year in the document, the innermost element around it.

    A stack walk rather than a regex over context, because the useful
    answer is "years sit inside <span class='X'>" and a context window
    cannot say which of the surrounding tags is the innermost."""
    counts = collections.Counter()
    stack = []
    position = 0
    for match in TAG.finditer(html):
        text = html[position:match.start()]
        if text.strip() and YEAR.search(text):
            top = stack[-1] if stack else ("(document)", "")
            label = f"<{top[0]}>" + (f" class=\"{top[1]}\"" if top[1] else "")
            counts[label] += len(YEAR.findall(text))
        closing, name, attrs, self_closing = match.groups()
        name = name.lower()
        if closing:
            for index in range(len(stack) - 1, -1, -1):
                if stack[index][0] == name:
                    del stack[index:]
                    break
        elif not self_closing and name not in VOID:
            found = CLASS.search(attrs)
            stack.append((name, found.group(1)[:60] if found else ""))
        position = match.end()
    return counts


def pick() -> list:
    rows = json.loads(CATALOGUE.read_text(encoding="utf-8"))
    europa = [r for r in rows if r["area"] == "europa"]
    if not europa:
        return []
    step = max(1, len(europa) // SAMPLE_SIZE)
    return europa[::step][:SAMPLE_SIZE]


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return response.read()


def render(results: list) -> str:
    lines = [
        "# Spike: the period on europa pages (roadmap 20)",
        "",
        "`extract_period` handles portugal's named year elements and the "
        "municipios `<select>` picker. Neither appears on europa, so "
        "`period_ratio[europa]` is gated at a floor of 0 — a recorded "
        "gap, not an acceptable state. A4 answered this for municipios "
        "by naming the innermost element around every year in the page; "
        "this is the same question pointed at the third template.",
        "",
        "## Are the mechanisms we already handle present?",
        "",
        "Cheapest possible answer first — if europa uses the picker, "
        "there is nothing to write.",
        "",
        "| page | " + " | ".join(KNOWN) + " |",
        "|---" * (len(KNOWN) + 1) + "|",
    ]
    for row in results:
        cells = " | ".join(str(row["known"].get(k, 0)) for k in KNOWN)
        lines.append(f"| `{row['slug']}` | {cells} |")
    lines += ["", "## Where the years actually are", ""]
    for row in results:
        lines += [f"### `{row['slug']}` ({row['bytes'] / 1024:.0f} KB, "
                  f"{row['years']} years found)", ""]
        if not row["enclosing"]:
            lines += ["No 4-digit year in any text node. That is a result "
                      "about this page, and if it repeats across all three "
                      "the period is not in the served HTML at all — which "
                      "would make europa's floor of 0 correct rather than "
                      "provisional.", ""]
            continue
        lines += ["| enclosing element | years |", "|---|---|"]
        for label, count in row["enclosing"].most_common(10):
            lines.append(f"| `{label}` | {count} |")
        lines.append("")
    lines += [
        "## What to do with this",
        "",
        "A selector that appears on all three sampled pages is a "
        "candidate for `extract_period`; one that appears on a single "
        "page is a coincidence. If nothing is shared, say so and leave "
        "the floor at 0 — a wrong extractor is worse than a recorded "
        "gap, because the gate would then pass while the field was junk.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    samples = pick()
    print(f"probing {len(samples)} europa pages, {DELAY_SECONDS}s apart")
    results = []
    for index, row in enumerate(samples):
        if index:
            time.sleep(DELAY_SECONDS)
        print(f"  {row['url']}")
        try:
            body = fetch(row["url"])
        except Exception as exc:                   # noqa: BLE001
            print(f"    failed: {exc}")
            continue
        html = body.decode("utf-8", "replace")
        slug = row["url"].split("pordata.pt/", 1)[-1]
        (RAW_DIR / f"europa-{row['id']}.html").write_bytes(body)
        results.append({
            "slug": slug,
            "bytes": len(body),
            "years": len(YEAR.findall(html)),
            "enclosing": enclosing(html),
            "known": {name: len(pattern.findall(html))
                      for name, pattern in KNOWN.items()},
        })
    REPORT.write_text(render(results), encoding="utf-8")
    print(f"europa period: {len(results)} pages profiled; report at {REPORT}")


if __name__ == "__main__":
    main()
