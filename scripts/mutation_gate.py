#!/usr/bin/env python3
"""Turn mutmut's output into a gate (roadmap 6d).

`tests.yml` ran mutmut with `|| true`, so the score was reported and
never enforced — the site's StrykerJS run has had a hard `break`
threshold since day one and Python did not.

**Why the floor is where it is.** Measured 2026-08-24: 1,834 of 2,860
killable mutants die, a 64.1% kill rate. The ceiling is well under 100%
for two reasons worth writing down rather than rediscovering:

- **Equivalent mutants.** `body.decode("utf-8")` versus `body.decode()`,
  `"UTF-8"` versus `"utf-8"`, `split(x, 1)` versus `rsplit(x, 1)` on a
  string containing one occurrence, `[-1]` versus `[+1]` on a two-element
  list — all behave identically, so no test can kill them. `parse()`
  alone contributes ~54 of these.
- **Report prose.** Roughly 80% of survivors live in the four `main()`
  functions and the two report writers, where a mutant changes a markdown
  label. Asserting exact prose would make the suite brittle for no
  correctness gain; `tests/test_reports.py` asserts the *figures and
  sections* instead, which is the part a reader depends on.

So the floor sits under the measured rate: high enough that a real
regression trips it, low enough that ordinary refactoring does not.
Raise it when the rate rises, the way the per-area QA floors work.

**Leave margin for run-to-run variance.** Two consecutive runs of the
same tree scored 64.1% and 62.5% — mutmut's results are not perfectly
deterministic, so a floor set just under a single measurement would flake
and a flaky gate gets disabled. The floor allows for a few points of
drift below the lower observation.
"""

import pathlib
import re
import sys

FLOOR = 0.58

# mutmut's progress line carries the tallies, and `mutmut results` does
# not: it lists survivors only, so the killed count has to come from the
# run output. The line looks like:
#   2981/2981  🎉 1834 🫥 121  ⏰ 0  🤔 0  🙁 1026  🔇 0  🧙 0
MARKERS = {"killed": "🎉", "no_tests": "🫥", "timeout": "⏰",
           "suspicious": "🤔", "survived": "🙁", "skipped": "🔇"}


def tally(text: str) -> dict:
    """Counts from the last progress line that carries them."""
    counts: dict = {}
    for line in reversed(text.replace("\r", "\n").splitlines()):
        found = {}
        for name, marker in MARKERS.items():
            match = re.search(re.escape(marker) + r"\s*(\d+)", line)
            if match:
                found[name] = int(match.group(1))
        if "killed" in found and "survived" in found:
            counts = found
            break
    return counts


def kill_rate(counts: dict) -> float:
    """Killed over killable.

    A timeout means the mutant broke the suite, so it counts as caught.
    `no_tests` and `skipped` are mutants mutmut never ran, so they sit in
    neither half — counting them as failures would penalise code the tool
    itself declined to exercise, and counting them as kills would flatter
    the score."""
    killed = counts.get("killed", 0) + counts.get("timeout", 0)
    killable = killed + counts.get("survived", 0) + counts.get("suspicious", 0)
    return killed / killable if killable else 1.0


def main() -> None:
    if len(sys.argv) < 2:
        print("usage: mutation_gate.py <mutmut-run-output-file>")
        sys.exit(2)
    log = pathlib.Path(sys.argv[1])
    if not log.exists():
        print(f"mutation gate: {log} not found — did `mutmut run` fail?")
        sys.exit(1)
    counts = tally(log.read_text(encoding="utf-8", errors="replace"))
    if not counts:
        print("mutation gate: no tallies in the run output")
        sys.exit(1)
    rate = kill_rate(counts)
    print(f"mutation gate: {rate * 100:.1f}% killed "
          f"({counts.get('killed', 0)} killed, "
          f"{counts.get('survived', 0)} survived, "
          f"{counts.get('no_tests', 0)} untested)")
    if rate < FLOOR:
        print(f"BREACH: {rate * 100:.1f}% < required {FLOOR * 100:.0f}%")
        sys.exit(1)
    print(f"mutation gate: passes (floor {FLOOR * 100:.0f}%)")


if __name__ == "__main__":
    main()
