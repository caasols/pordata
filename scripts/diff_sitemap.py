#!/usr/bin/env python3
"""Report what changed between the last committed sitemap snapshot and the
working-tree one just written by fetch_sitemap.py.

Prints a markdown summary of added, removed and updated pages. With
--changelog, also appends that summary under a date heading to
data/CHANGELOG.md (skipped when nothing changed).

When $GITHUB_OUTPUT is set (i.e. under GitHub Actions), writes:
    changed=true|false   any difference worth committing
    notify=true|false    pages were added or removed (issue-worthy)
    added/removed/updated=<counts>

Adds and removes come from sitemap-urls.txt so the first run after the
lastmod file was introduced still diffs cleanly against the older
urls-only baseline.
"""

import datetime
import os
import pathlib
import subprocess
import sys

URLS_FILE = "data/sitemap-urls.txt"
LASTMOD_FILE = "data/sitemap-lastmod.tsv"
CHANGELOG = pathlib.Path("data/CHANGELOG.md")
MAX_LISTED_UPDATES = 50
MASS_CHURN_THRESHOLD = 200


def committed(path: str) -> str | None:
    result = subprocess.run(
        ["git", "show", f"HEAD:{path}"], capture_output=True, text=True
    )
    return result.stdout if result.returncode == 0 else None


def parse_tsv(text: str) -> dict[str, str]:
    entries = {}
    for line in text.splitlines():
        url, _, lastmod = line.partition("\t")
        if url:
            entries[url] = lastmod
    return entries


def short(url: str) -> str:
    return url.split("pordata.pt/", 1)[-1]


def main() -> None:
    new_urls_text = pathlib.Path(URLS_FILE).read_text(encoding="utf-8")
    new_urls = set(new_urls_text.split())
    old_urls_text = committed(URLS_FILE)
    old_urls = set(old_urls_text.split()) if old_urls_text else set()

    added = sorted(new_urls - old_urls) if old_urls else []
    removed = sorted(old_urls - new_urls) if old_urls else []

    new_mods = parse_tsv(pathlib.Path(LASTMOD_FILE).read_text(encoding="utf-8"))
    old_mods_text = committed(LASTMOD_FILE)
    old_mods = parse_tsv(old_mods_text) if old_mods_text else {}
    updated = sorted(
        u for u in new_urls & set(old_mods)
        if u in new_mods and old_mods[u] != new_mods[u]
    ) if old_mods else []

    today = datetime.date.today().isoformat()
    lines = [f"### Sitemap diff {today}", ""]
    if not old_urls:
        lines.append(f"Baseline established: {len(new_urls)} pages. No diff possible.")
    elif not old_mods and not added and not removed:
        lines.append(f"lastmod baseline established for {len(new_mods)} pages. "
                     "No page additions or removals.")
    elif not (added or removed or updated):
        lines.append("No changes.")
    else:
        lines.append(f"**{len(added)} added, {len(removed)} removed, "
                     f"{len(updated)} updated (lastmod).**")
        if added:
            lines += ["", "#### Added"] + [f"- `{short(u)}`" for u in added]
        if removed:
            lines += ["", "#### Removed"] + [f"- `{short(u)}`" for u in removed]
        if updated:
            lines.append("")
            if len(updated) > MASS_CHURN_THRESHOLD:
                lines.append(
                    f"#### Updated: {len(updated)} pages — wholesale lastmod "
                    "churn, likely a sitemap regeneration; not listed individually."
                )
            else:
                lines.append("#### Updated")
                lines += [f"- `{short(u)}` → {new_mods[u]}"
                          for u in updated[:MAX_LISTED_UPDATES]]
                if len(updated) > MAX_LISTED_UPDATES:
                    lines.append(f"- … and {len(updated) - MAX_LISTED_UPDATES} more")

    summary = "\n".join(lines) + "\n"
    print(summary)

    changed = (
        not old_urls
        or bool(added or removed or updated)
        or old_urls_text != new_urls_text
        or old_mods_text != pathlib.Path(LASTMOD_FILE).read_text(encoding="utf-8")
    )
    notify = bool(added or removed)

    if changed and "--changelog" in sys.argv and (added or removed or updated or not old_urls):
        prev = CHANGELOG.read_text(encoding="utf-8") if CHANGELOG.exists() else (
            "# PORDATA sitemap changelog\n\nAppended by the sitemap watch "
            "workflow. Newest entries at the bottom.\n"
        )
        CHANGELOG.write_text(prev + "\n" + summary, encoding="utf-8")

    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a", encoding="utf-8") as fh:
            fh.write(f"changed={'true' if changed else 'false'}\n")
            fh.write(f"notify={'true' if notify else 'false'}\n")
            fh.write(f"added={len(added)}\n")
            fh.write(f"removed={len(removed)}\n")
            fh.write(f"updated={len(updated)}\n")


if __name__ == "__main__":
    main()
