#!/usr/bin/env python3
"""Roadmap 22: is INE serving us, and when?

One cheap sample a day, appended to data/ine/availability.csv.

Why this exists: the catalogue fetch succeeded twice on a Saturday
morning, failed on the next two attempts within 45 minutes, failed again
after a 22.6 h gap, and then succeeded after an 11.3 h gap. Neither "INE
is down at weekends" nor "there is a fixed cooldown" fits that. Item 14
needs sustained INE access, so its refresh cadence is a guess until the
pattern is known.

**Deliberately cheaper than the question.** Re-pulling the 21 MB
catalogue to test availability is what caused the block in the first
place. A HEAD — or a Range request for the first couple of KB when HEAD
is not allowed — separates "blocked" from "serving" for a few hundred
bytes, so a daily sample stays far lighter than that one Saturday burst.

**No back-off on failure, deliberately.** The design note for item 22
first said to back off on repeated 403s. At one request a day that is
wrong: a block is precisely when the interesting measurement is
happening, and skipping it would hide the recovery this probe exists to
observe. What guards against nuisance instead is a hard lifetime cap —
the probe retires itself once it has enough days to answer the question,
so it can never quietly become a permanent heartbeat.
"""

import csv
import datetime as dt
import io
import pathlib
import sys
import time
import urllib.error
import urllib.request

URL = "https://www.ine.pt/ine/xml_indic.jsp?opc=2&lang=PT"
USER_AGENT = (
    "pordata-map availability probe (github.com/caasols/pordata; "
    "1 request/day, headers only)"
)
LOG = pathlib.Path("data/ine/availability.csv")
FIELDS = ["date_utc", "time_utc", "weekday", "method", "http_status",
          "ok", "bytes_read", "elapsed_s", "note"]

TIMEOUT = 120
PEEK_BYTES = 2048
# Retire after this many probe samples. Item 22 asks a bounded question;
# a probe with no end date is a heartbeat nobody agreed to.
MAX_SAMPLES = 21
# First sampling day. The catalogue was pulled in full on 2026-08-24 at
# 07:34 UTC, so a probe at 09:45 the same day would sit ~2 h behind a
# 21 MB request — the exact confound that makes the existing seven
# attempts uninterpretable. Starting the next day buys a clean ~26 h gap.
START_DATE = "2026-08-25"


def load_log() -> list:
    if not LOG.exists():
        return []
    with io.open(LOG, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def append(row: dict) -> None:
    exists = LOG.exists()
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with io.open(LOG, "a", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        if not exists:
            writer.writeheader()
        writer.writerow(row)


def probe() -> dict:
    """HEAD if allowed, else read only the first bytes of a Range GET."""
    started = time.monotonic()
    method, status, read, note = "HEAD", "", 0, ""
    try:
        req = urllib.request.Request(
            URL, method="HEAD", headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            status = resp.status
    except urllib.error.HTTPError as exc:
        status = exc.code
        # Some servers refuse HEAD on a JSP but serve GET fine; that is a
        # quirk of the endpoint, not a block, so it must not be logged as
        # one.
        if exc.code in (405, 501):
            method, note = "RANGE", "HEAD not allowed, fell back to Range"
            try:
                req = urllib.request.Request(URL, headers={
                    "User-Agent": USER_AGENT,
                    "Range": f"bytes=0-{PEEK_BYTES - 1}"})
                with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                    status = resp.status
                    read = len(resp.read(PEEK_BYTES))
            except urllib.error.HTTPError as inner:
                status = inner.code
            except Exception as inner:                   # noqa: BLE001
                status, note = "", f"{type(inner).__name__}: {inner}"[:120]
    except Exception as exc:                             # noqa: BLE001
        status, note = "", f"{type(exc).__name__}: {exc}"[:120]

    now = dt.datetime.now(dt.timezone.utc)
    ok = isinstance(status, int) and 200 <= status < 400
    return {
        "date_utc": now.strftime("%Y-%m-%d"),
        "time_utc": now.strftime("%H:%M:%S"),
        "weekday": now.strftime("%a"),
        "method": method,
        "http_status": status,
        "ok": "yes" if ok else "no",
        "bytes_read": read,
        "elapsed_s": f"{time.monotonic() - started:.1f}",
        "note": note,
    }


def summarise(rows: list) -> None:
    probes = [r for r in rows if r["method"] in ("HEAD", "RANGE")]
    if not probes:
        print("no probe samples yet")
        return
    ok = sum(1 for r in probes if r["ok"] == "yes")
    print(f"samples: {len(probes)}, serving: {ok}, blocked: {len(probes)-ok}")
    by_day = {}
    for r in probes:
        hit, miss = by_day.get(r["weekday"], (0, 0))
        by_day[r["weekday"]] = ((hit + 1, miss) if r["ok"] == "yes"
                                else (hit, miss + 1))
    for day in ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"):
        if day in by_day:
            hit, miss = by_day[day]
            print(f"  {day}: {hit} serving / {miss} blocked")
    if len(probes) < MAX_SAMPLES:
        print(f"  ({MAX_SAMPLES - len(probes)} samples until this probe "
              f"retires; weekday effect needs a few of each day)")


def main() -> None:
    rows = load_log()
    probes = [r for r in rows if r["method"] in ("HEAD", "RANGE")]

    if len(probes) >= MAX_SAMPLES:
        print(f"probe retired: {len(probes)} samples collected "
              f"(cap {MAX_SAMPLES}). Record the finding in context.md "
              f"item 22 and delete the workflow.")
        summarise(rows)
        return

    today = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
    if today < START_DATE:
        print(f"not sampling before {START_DATE}: too close behind the "
              f"full catalogue pull of 2026-08-24 to be interpretable")
        return
    if any(r["date_utc"] == today and r["method"] in ("HEAD", "RANGE")
           for r in rows):
        print(f"already sampled {today}; one probe per day by design")
        summarise(rows)
        return

    row = probe()
    append(row)
    print(f"{row['date_utc']} {row['time_utc']} {row['weekday']}: "
          f"{row['method']} -> {row['http_status'] or 'no response'} "
          f"({'serving' if row['ok'] == 'yes' else 'BLOCKED'})"
          + (f" [{row['note']}]" if row["note"] else ""))
    summarise(load_log())


if __name__ == "__main__":
    if "--summary" in sys.argv:
        summarise(load_log())
    else:
        main()
