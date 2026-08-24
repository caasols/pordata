"""Roadmap 22's probe hits someone else's infrastructure on a schedule,
so its guards are the part that matters. None of these tests touch the
network: probe() is stubbed, and what is under test is whether the
script decides to call it at all."""

import io
import pathlib
import unittest
from unittest import mock

from helpers import RepoCase, load_script

probe_script = load_script("probe_ine_availability")

HEADER = ("date_utc,time_utc,weekday,method,http_status,ok,"
          "bytes_read,elapsed_s,note\n")
HISTORY = ("2026-08-22,09:00:53,Sat,full-pull,200,yes,,,served\n"
           "2026-08-24,07:34:27,Mon,full-pull,200,yes,,,served\n")


class ProbeGuardTest(RepoCase):
    def setUp(self):
        super().setUp()
        self.log = pathlib.Path("data/ine/availability.csv")
        self.log.parent.mkdir(parents=True, exist_ok=True)
        patcher = mock.patch.object(probe_script, "LOG", self.log)
        patcher.start()
        self.addCleanup(patcher.stop)

    def write(self, body=""):
        self.log.write_text(HEADER + body, encoding="utf-8")

    def run_on(self, date, body=""):
        """Run main() as if it were `date`, with probe() stubbed."""
        self.write(body)
        fake = {"date_utc": date, "time_utc": "09:45:00", "weekday": "Tue",
                "method": "HEAD", "http_status": 200, "ok": "yes",
                "bytes_read": 0, "elapsed_s": "0.2", "note": ""}
        with mock.patch.object(probe_script, "probe",
                               return_value=fake) as called, \
             mock.patch.object(probe_script.dt, "datetime") as clock:
            clock.now.return_value.strftime.side_effect = (
                lambda fmt: date if fmt == "%Y-%m-%d" else "09:45:00")
            probe_script.main()
        return called

    def test_does_not_sample_before_the_start_date(self):
        # a probe hours behind the 21 MB pull of 2026-08-24 is confounded
        called = self.run_on("2026-08-24", HISTORY)
        called.assert_not_called()

    def test_samples_on_the_start_date(self):
        called = self.run_on(probe_script.START_DATE, HISTORY)
        called.assert_called_once()

    def test_one_sample_per_day(self):
        already = ("2026-08-25,09:45:00,Tue,HEAD,200,yes,0,0.2,\n")
        called = self.run_on("2026-08-25", HISTORY + already)
        called.assert_not_called()

    def test_retires_itself_at_the_cap(self):
        rows = "".join(
            f"2026-09-{i + 1:02d},09:45:00,Tue,HEAD,200,yes,0,0.2,\n"
            for i in range(probe_script.MAX_SAMPLES))
        called = self.run_on("2026-10-01", HISTORY + rows)
        called.assert_not_called()

    def test_one_below_the_cap_still_samples(self):
        rows = "".join(
            f"2026-09-{i + 1:02d},09:45:00,Tue,HEAD,200,yes,0,0.2,\n"
            for i in range(probe_script.MAX_SAMPLES - 1))
        called = self.run_on("2026-10-01", HISTORY + rows)
        called.assert_called_once()

    def test_full_pull_history_does_not_count_toward_the_cap(self):
        # the seeded attempts are evidence, not samples; counting them
        # would retire the probe before it ever ran
        rows = "".join(
            f"2026-08-{i + 1:02d},09:00:00,Sat,full-pull,200,yes,,,seed\n"
            for i in range(probe_script.MAX_SAMPLES + 5))
        called = self.run_on("2026-08-25", rows)
        called.assert_called_once()


class ProbeSummaryTest(unittest.TestCase):
    def test_summary_counts_probes_only(self):
        rows = list(__import__("csv").DictReader(io.StringIO(
            HEADER + HISTORY
            + "2026-08-25,09:45:00,Tue,HEAD,403,no,0,0.1,\n")))
        with mock.patch("builtins.print") as out:
            probe_script.summarise(rows)
        text = " ".join(str(c.args[0]) for c in out.call_args_list)
        self.assertIn("samples: 1", text)      # not 3
        self.assertIn("blocked: 1", text)
