#!/usr/bin/env python3
"""Is the site the repo describes the site the public gets? (roadmap 6b)

Everything else in this pipeline is gated. The last hop is not: `docs/`
is committed and GitHub Pages deploys it out of band, so a failed
`pages-build-deployment`, a purged CDN object or a half-published bundle
leaves the repo green, the harvest happy and the live site stale or
blank. Nobody hears it — the owner is not reloading the page daily and
the QA gate has no idea the page exists.

So check the deliverable from outside, the way a visitor meets it:

- **`data/stats.json` serves, and its `built_at` matches the committed
  one.** That is one field proving the whole chain — Pages built, Pages
  deployed, and the object being served is this commit's data rather
  than a cached older one.
- **The assets the served `index.html` names actually resolve.** Vite
  writes content-hashed filenames, so a partial deploy hands the browser
  `index-oiCPKUGL.js`, gets a 404 and renders a white page with a
  perfectly healthy-looking 200 on `/`. Checking `/` alone would call
  that fine. The asset list is read from the *live* HTML, not the local
  one, because it is the live pairing that has to be consistent.

A difference is not automatically a fault: Pages takes a few minutes
after a push, so a build younger than the grace window reads as
`deploying`, not `behind`. That distinction is the whole reason this
runs on its own schedule rather than as a step at the end of the
harvest.

Fetching lives in `main()` and the judgement does not, because this
sandbox has no route to github.io — the same reason the PORDATA fetchers
are exercised in Actions. `verdict()` and the parsers are pure and
unit-tested; only the two `urlopen` calls are not.
"""

import datetime
import json
import os
import pathlib
import re
import sys
import urllib.error
import urllib.request

SITE = "https://caasols.github.io/pordata/"
LOCAL_STATS = pathlib.Path("docs/data/stats.json")
TIMEOUT = 30
USER_AGENT = "pordata-map-pages-health (+https://github.com/caasols/pordata)"

# Pages is not instant and this job may fire minutes after a harvest
# pushed. Below this age a mismatch is a deploy in flight, not a fault.
GRACE_MINUTES = 30

# `<script ... src="./assets/index-oiCPKUGL.js">` and the stylesheet
# link. Restricted to ./assets/ deliberately: the page also links
# pordata.pt and the JSON-LD carries absolute URLs, and this check is
# about the bundle's own integrity, not about third parties being up.
ASSET_REF = re.compile(r'(?:src|href)="(\./assets/[^"]+)"')

BUILT_AT = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}) UTC$")

# The vocabulary, named once. pages-health.yml branches on these strings,
# and a typo there is invisible: `!= 'deploy'` is true for every real
# state, so every in-flight deploy would file an issue. The workflow test
# asserts its literals against HEALTHY rather than trusting the pair to
# stay in step across two files.
STATES = ("ok", "deploying", "behind", "broken", "unreachable")
HEALTHY = ("ok", "deploying")


def asset_paths(html: str) -> list[str]:
    """Relative asset paths named by a served index.html, in order."""
    seen, out = set(), []
    for path in ASSET_REF.findall(html):
        if path not in seen:
            seen.add(path)
            out.append(path)
    return out


def parse_built_at(value: str | None) -> datetime.datetime | None:
    """`built_at` as written by build_catalogue.py: "%Y-%m-%d %H:%M UTC".

    Anything else returns None rather than raising: an unparseable
    stamp is a reason to report, not to crash the health check."""
    match = BUILT_AT.match((value or "").strip())
    if not match:
        return None
    return datetime.datetime.strptime(match.group(1), "%Y-%m-%d %H:%M").replace(
        tzinfo=datetime.timezone.utc)


def age_minutes(built_at: datetime.datetime | None,
                now: datetime.datetime) -> float | None:
    return None if built_at is None else (now - built_at).total_seconds() / 60


def verdict(local: dict, live: dict | None, missing_assets: list[str],
            age: float | None) -> tuple[str, list[str]]:
    """One of ok / deploying / behind / broken / unreachable, plus report
    lines. Ordered by severity: a site that does not answer is worse news
    than one answering with yesterday's data, and both outrank a stale
    stamp on a page that otherwise works."""
    lines = []
    if live is None:
        return "unreachable", [
            f"`{SITE}data/stats.json` did not serve. Pages is down, the "
            "deployment failed, or the site was unpublished."]

    local_stamp = local.get("built_at")
    live_stamp = live.get("built_at")
    lines.append(f"- committed `built_at`: `{local_stamp}`")
    lines.append(f"- served `built_at`:    `{live_stamp}`")
    lines.append(f"- served indicators: {live.get('indicators')} "
                 f"(committed {local.get('indicators')})")

    if missing_assets:
        lines.append("")
        lines.append("The served `index.html` names assets that do not "
                     "resolve — the page loads and renders nothing:")
        lines += [f"- `{path}`" for path in missing_assets]
        return "broken", lines

    if live_stamp == local_stamp:
        return "ok", lines

    lines.append("")
    if age is not None and age < GRACE_MINUTES:
        lines.append(f"The commit is {age:.0f} min old, inside the "
                     f"{GRACE_MINUTES}-minute deploy window.")
        return "deploying", lines
    stale = "unknown" if age is None else f"{age / 60:.1f} h"
    lines.append(f"The committed build is {stale} old and the live site is "
                 "still serving an older one. The Pages deployment did not "
                 "run, or it failed.")
    return "behind", lines


def now() -> datetime.datetime:
    """A seam, so the staleness tests are not hostage to the wall clock:
    "is this build older than the deploy window" is time arithmetic, and
    a test that asserts it against `datetime.now()` changes meaning as it
    ages and eventually passes for the wrong reason."""
    return datetime.datetime.now(datetime.timezone.utc)


def get(url: str) -> tuple[int, bytes]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, b""
    except (urllib.error.URLError, OSError, ValueError):
        return 0, b""


def main() -> None:
    local = json.loads(LOCAL_STATS.read_text(encoding="utf-8"))

    status_code, body = get(f"{SITE}data/stats.json")
    try:
        live = json.loads(body) if status_code == 200 else None
    except json.JSONDecodeError:
        # a 200 carrying something that is not the file (a CDN error
        # page, an interstitial) is exactly as broken as a 404
        live = None

    missing: list[str] = []
    if live is not None:
        html_code, html = get(SITE)
        if html_code != 200:
            live = None
        else:
            for path in asset_paths(html.decode("utf-8", "replace")):
                code, _ = get(SITE + path.lstrip("./"))
                if code != 200:
                    missing.append(path)

    age = age_minutes(parse_built_at(local.get("built_at")), now())
    state, lines = verdict(local, live, missing, age)

    report = "\n".join([f"### Pages health: {state}", "", *lines]) + "\n"
    print(report)

    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a", encoding="utf-8") as handle:
            handle.write(f"status={state}\n")
    report_path = os.environ.get("PAGES_REPORT")
    if report_path:
        pathlib.Path(report_path).write_text(report, encoding="utf-8")

    sys.exit(0 if state in HEALTHY else 1)


if __name__ == "__main__":
    main()
