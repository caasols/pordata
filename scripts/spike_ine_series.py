"""Spike: what does an INE series actually look like? (roadmap 14)

The crosswalk hands item 14 a `varcd` and a URL, and **nobody has ever
fetched one**. Item 14 lists three things to settle "from a pilot rather
than in the abstract" — size, vintages, and how to render "no series" —
and all three are unanswerable until someone looks at a response.

**This is measurement, not archiving.** Decision 1 permits values from
upstream under upstream's terms, and item 13 has not recorded INE's yet,
so nothing fetched here is committed: the bodies go to the workflow
artifact (`data/spikes/raw/` is gitignored) and only the *shape* — key
names, counts, sizes — reaches the repo. That distinction is the whole
reason this can run before item 13 does.

**Politeness, and a confound worth recording.** Eight requests, spaced,
against per-indicator JSON endpoints — not the 21 MB catalogue whose
repeat pulls caused the block. But item 22 is sampling INE's
availability once a day precisely to characterise that block, and eight
requests on the same day is exactly the kind of confound its own guards
were written to avoid. The report says so, so whoever reads the
availability log knows this day is not clean.
"""

import collections
import json
import pathlib
import re
import time
import urllib.error
import urllib.request

USER_AGENT = (
    "pordata-map research (github.com/caasols/pordata; "
    "8 sample series, measuring response shape only)"
)
CROSSWALK = pathlib.Path("data/crosswalk/ine.json")
RAW_DIR = pathlib.Path("data/spikes/raw/ine-series")
REPORT = pathlib.Path("data/spikes/ine-series.md")
JSON_URL = ("https://www.ine.pt/ine/json_indicador/pindica.jsp"
            "?op=2&varcd={}&lang=PT")
DELAY_SECONDS = 25
TIMEOUT = 90
SAMPLE = 8


def pick(crosswalk: dict) -> list:
    """A spread, not the first eight.

    Taking the head of a sorted file samples one area and one theme. The
    interesting variation for a size estimate is exactly the opposite:
    a municipal series with 308 geographies against a national one with
    a handful."""
    entries = [(key, value) for key, value in sorted(crosswalk.items())
               if value and value.get("candidates")]
    if not entries:
        return []
    step = max(1, len(entries) // SAMPLE)
    picked, seen = [], set()
    for key, value in entries[::step]:
        varcd = value["candidates"][0]
        if varcd in seen:
            continue
        seen.add(varcd)
        picked.append((key, varcd, value.get("operation", ""),
                       value.get("geo_levels", [])))
        if len(picked) == SAMPLE:
            break
    return picked


def fetch(url: str) -> dict:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            body = response.read()
            return {"status": response.status, "bytes": len(body),
                    "body": body}
    except urllib.error.HTTPError as exc:
        return {"status": exc.code, "bytes": 0, "body": b"",
                "error": f"HTTP {exc.code}"}
    except Exception as exc:                       # noqa: BLE001
        return {"status": 0, "bytes": 0, "body": b"",
                "error": f"{type(exc).__name__}: {exc}"}


def walk_keys(node, prefix="", out=None, depth=0):
    """Every key path in the document, so the schema is described rather
    than guessed at from one example."""
    out = {} if out is None else out
    if depth > 6:
        return out
    if isinstance(node, dict):
        for key, value in node.items():
            path = f"{prefix}.{key}" if prefix else key
            out[path] = type(value).__name__
            walk_keys(value, path, out, depth + 1)
    elif isinstance(node, list) and node:
        walk_keys(node[0], f"{prefix}[]", out, depth + 1)
    return out


def profile(body: bytes) -> dict:
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return {"parsed": False,
                "head": body[:400].decode("utf-8", "replace")}
    keys = walk_keys(data)
    # a data point is where the numbers live; count them without
    # recording any
    text = body.decode("utf-8", "replace")
    return {
        "parsed": True,
        "top_type": type(data).__name__,
        "key_paths": sorted(keys)[:40],
        "key_count": len(keys),
        "value_like_keys": [k for k in keys if re.search(
            r"valor|value|dim_|geo|dsg|ano|periodo", k, re.I)][:20],
        "numbers_in_body": len(re.findall(r'"\d+[.,]?\d*"', text)),
    }


def render(rows: list, note: str) -> str:
    lines = [
        "# Spike: the shape of an INE series (roadmap 14)",
        "",
        "The crosswalk hands item 14 a `varcd`; nobody had fetched one. "
        "Item 14's three open questions — size, vintages, and how to "
        "render \"no series\" — are all unanswerable in the abstract, so "
        "this looks at real responses.",
        "",
        "**Measurement, not archiving.** No value fetched here is "
        "committed: bodies go to the workflow artifact and only the "
        "shape reaches the repo. That is what lets this run before item "
        "13 records INE's reuse terms.",
        "",
        f"**Confound, recorded:** {note}",
        "",
        "## Responses",
        "",
        "| row | varcd | status | KB | parsed | key paths |",
        "|---|---|---|---|---|---|",
    ]
    for row in rows:
        shape = row.get("profile") or {}
        lines.append(
            f"| `{row['key']}` | `{row['varcd']}` | {row['status']} | "
            f"{row['bytes'] / 1024:.1f} | "
            f"{'yes' if shape.get('parsed') else 'no'} | "
            f"{shape.get('key_count', '—')} |")
    served = [r for r in rows if r.get("profile", {}).get("parsed")]
    lines += ["", "## Size", ""]
    if served:
        sizes = [r["bytes"] / 1024 for r in served]
        lines += [
            f"- median **{sorted(sizes)[len(sizes) // 2]:.1f} KB**, "
            f"max **{max(sizes):.1f} KB** across {len(served)} series",
            f"- extrapolated over the crosswalk's 1,062 named ids: "
            f"**~{sum(sizes) / len(sizes) * 1062 / 1024:.0f} MB** raw",
            "",
            "That is the number item 14's first open question wanted: it "
            "decides whether the archive lives next to `catalogue.json` "
            "in git or needs different storage.",
            "",
            "## Schema",
            "",
            "Key paths from the first parsed response, so the long-format "
            "target schema (indicator, geography, period, value, unit, "
            "flag) can be mapped rather than invented:",
            "",
            "```",
        ]
        lines += served[0]["profile"]["key_paths"]
        lines += ["```", ""]
        if served[0]["profile"].get("value_like_keys"):
            lines += ["Keys that look like the dimensions we need:", ""]
            lines += [f"- `{k}`"
                      for k in served[0]["profile"]["value_like_keys"]]
            lines.append("")
    else:
        lines += ["No response parsed as JSON. If every status is 403 "
                  "this is the cloud-IP block item 22 is measuring, and "
                  "says nothing about the endpoint.", ""]
    return "\n".join(lines)


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    crosswalk = json.loads(CROSSWALK.read_text(encoding="utf-8"))
    picked = pick(crosswalk)
    print(f"probing {len(picked)} series, {DELAY_SECONDS}s apart")
    rows = []
    for index, (key, varcd, operation, geo) in enumerate(picked):
        if index:
            time.sleep(DELAY_SECONDS)
        url = JSON_URL.format(varcd)
        print(f"  {key} -> {varcd}")
        attempt = fetch(url)
        row = {"key": key, "varcd": varcd, "operation": operation,
               "geo": geo, "status": attempt["status"],
               "bytes": attempt["bytes"]}
        if attempt["body"]:
            row["profile"] = profile(attempt["body"])
            (RAW_DIR / f"{varcd}.json").write_bytes(attempt["body"])
        rows.append(row)
    note = (f"{len(picked)} requests to INE on this date. Item 22 samples "
            "availability once a day to characterise INE's block; its "
            "reading for this day inherits this traffic and should not be "
            "treated as a clean sample.")
    REPORT.write_text(render(rows, note), encoding="utf-8")
    ok = sum(1 for r in rows if r["status"] == 200)
    print(f"ine series: {ok}/{len(rows)} served; report at {REPORT}")


if __name__ == "__main__":
    main()
