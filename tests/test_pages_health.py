"""The last unwatched hop: is the live site this commit's site?

Only `main()` touches the network, so everything decidable offline is
decided here. The cases are the ways a Pages deployment fails *without*
failing: a 200 on `/` while the bundle 404s, a served stamp that is
simply an older build, a stamp shape nobody parses.
"""

import datetime
import json
import os
import pathlib
import unittest
from unittest import mock

from helpers import RepoCase, load_script

c = load_script("check_pages_live")

NOW = datetime.datetime(2026, 8, 24, 18, 0, tzinfo=datetime.timezone.utc)
LOCAL = {"built_at": "2026-08-24 16:14 UTC", "indicators": 2195}
LIVE_SAME = dict(LOCAL)
LIVE_OLD = {"built_at": "2026-08-20 09:00 UTC", "indicators": 2190}

HTML = """<!DOCTYPE html><html><head>
<link rel="canonical" href="https://caasols.github.io/pordata/">
<script type="module" crossorigin src="./assets/index-oiCPKUGL.js"></script>
<link rel="stylesheet" crossorigin href="./assets/index-Dah0uG9s.css">
<link rel="stylesheet" crossorigin href="./assets/index-Dah0uG9s.css">
</head><body><a href="https://www.pordata.pt/portugal">x</a></body></html>"""


class AssetPathsTest(unittest.TestCase):
    def test_finds_script_and_stylesheet(self):
        self.assertEqual(c.asset_paths(HTML),
                         ["./assets/index-oiCPKUGL.js",
                          "./assets/index-Dah0uG9s.css"])

    def test_ignores_offsite_and_non_asset_links(self):
        """The canonical link and the PORDATA outbound are not this
        bundle's integrity, and a check that fails when pordata.pt is
        having a bad day is a check that gets muted."""
        for path in c.asset_paths(HTML):
            self.assertTrue(path.startswith("./assets/"))

    def test_deduplicates_but_keeps_order(self):
        """A repeated stylesheet link should cost one request, not two,
        and the report should read in page order."""
        self.assertEqual(len(c.asset_paths(HTML)), 2)

    def test_no_assets_is_empty_not_an_error(self):
        self.assertEqual(c.asset_paths("<html><body>hi</body></html>"), [])


class BuiltAtTest(unittest.TestCase):
    def test_parses_the_format_build_catalogue_writes(self):
        got = c.parse_built_at("2026-08-24 16:14 UTC")
        self.assertEqual(got, datetime.datetime(
            2026, 8, 24, 16, 14, tzinfo=datetime.timezone.utc))

    def test_result_is_utc_aware(self):
        """A naive datetime here would raise on the subtraction in
        age_minutes, turning a stale-site report into a crash."""
        self.assertIsNotNone(c.parse_built_at("2026-08-24 16:14 UTC").tzinfo)

    def test_unparseable_returns_none_rather_than_raising(self):
        for value in ("", None, "2026-08-24T16:14Z", "24/08/2026 16:14 UTC",
                      "2026-08-24 16:14", "2026-08-24 16:14 WEST", "nonsense"):
            with self.subTest(value):
                self.assertIsNone(c.parse_built_at(value))

    def test_surrounding_whitespace_is_tolerated(self):
        self.assertIsNotNone(c.parse_built_at("  2026-08-24 16:14 UTC "))

    def test_age_is_in_minutes(self):
        self.assertAlmostEqual(
            c.age_minutes(c.parse_built_at("2026-08-24 16:14 UTC"), NOW), 106)

    def test_age_of_an_unparseable_stamp_is_none(self):
        self.assertIsNone(c.age_minutes(None, NOW))


class VerdictTest(unittest.TestCase):
    def state(self, live, missing=(), age=200.0, local=None):
        return c.verdict(local or LOCAL, live, list(missing), age)[0]

    def test_matching_stamp_is_ok(self):
        self.assertEqual(self.state(LIVE_SAME), "ok")

    def test_no_response_is_unreachable(self):
        self.assertEqual(self.state(None), "unreachable")

    def test_unreachable_beats_everything_else(self):
        """Reported before the stamp comparison, which would otherwise
        raise on a None body."""
        self.assertEqual(self.state(None, missing=["./assets/a.js"], age=1.0),
                         "unreachable")

    def test_missing_asset_is_broken_even_when_data_is_current(self):
        """The 200-on-slash trap: stats.json is fine, the stamp matches,
        and the visitor still gets a white page."""
        self.assertEqual(self.state(LIVE_SAME, missing=["./assets/x.js"]),
                         "broken")

    def test_broken_outranks_behind(self):
        self.assertEqual(self.state(LIVE_OLD, missing=["./assets/x.js"]),
                         "broken")

    def test_older_stamp_past_the_window_is_behind(self):
        self.assertEqual(self.state(LIVE_OLD, age=c.GRACE_MINUTES + 1),
                         "behind")

    def test_older_stamp_inside_the_window_is_deploying(self):
        self.assertEqual(self.state(LIVE_OLD, age=c.GRACE_MINUTES - 1),
                         "deploying")

    def test_the_window_boundary_is_not_a_grace(self):
        """At exactly the grace value the deploy has had its full window,
        so this is a fault. Pinned because an off-by-one here shows up as
        an alert that fires a minute early, once a month, and gets muted."""
        self.assertEqual(self.state(LIVE_OLD, age=float(c.GRACE_MINUTES)),
                         "behind")

    def test_unknown_age_with_a_stale_stamp_still_reports(self):
        """An unparseable local stamp must not silence the check: the
        site is demonstrably serving something else."""
        self.assertEqual(self.state(LIVE_OLD, age=None), "behind")

    def test_a_fresh_deploy_of_matching_data_is_ok_not_deploying(self):
        self.assertEqual(self.state(LIVE_SAME, age=1.0), "ok")


class StateVocabularyTest(unittest.TestCase):
    def test_states_is_exactly_what_verdict_can_return(self):
        """STATES is what pages-health.yml is checked against, so it has
        to be the real set: a state verdict() can return but STATES does
        not name would go unbranched in the workflow and unnoticed here."""
        reachable = {
            c.verdict(LOCAL, None, [], 1.0)[0],
            c.verdict(LOCAL, LIVE_SAME, [], 1.0)[0],
            c.verdict(LOCAL, LIVE_OLD, [], 1.0)[0],
            c.verdict(LOCAL, LIVE_OLD, [], 999.0)[0],
            c.verdict(LOCAL, LIVE_SAME, ["./assets/a.js"], 1.0)[0],
        }
        self.assertEqual(reachable, set(c.STATES))

    def test_healthy_is_a_subset_of_states(self):
        self.assertLessEqual(set(c.HEALTHY), set(c.STATES))


class ReportTest(unittest.TestCase):
    def test_both_stamps_are_shown(self):
        _state, lines = c.verdict(LOCAL, LIVE_OLD, [], 500.0)
        body = "\n".join(lines)
        self.assertIn("2026-08-24 16:14 UTC", body)
        self.assertIn("2026-08-20 09:00 UTC", body)

    def test_indicator_counts_are_shown(self):
        _state, lines = c.verdict(LOCAL, LIVE_OLD, [], 500.0)
        body = "\n".join(lines)
        self.assertIn("2190", body)
        self.assertIn("2195", body)

    def test_every_missing_asset_is_named(self):
        _state, lines = c.verdict(LOCAL, LIVE_SAME,
                                  ["./assets/a.js", "./assets/b.css"], 500.0)
        body = "\n".join(lines)
        self.assertIn("./assets/a.js", body)
        self.assertIn("./assets/b.css", body)

    def test_behind_reports_how_stale_in_hours(self):
        _state, lines = c.verdict(LOCAL, LIVE_OLD, [], 600.0)
        self.assertIn("10.0 h", "\n".join(lines))

    def test_unreachable_names_the_url_that_failed(self):
        _state, lines = c.verdict(LOCAL, None, [], 500.0)
        self.assertIn("stats.json", "\n".join(lines))


class MainTest(RepoCase):
    """main() end to end with the two urlopen calls stubbed.

    Worth driving rather than trusting: the wiring between fetch results
    and verdict() is where a healthy-looking site gets reported, and it
    is the part no test could reach once the sandbox lost its route to
    github.io."""

    def setUp(self):
        super().setUp()
        pathlib.Path("docs/data").mkdir(parents=True)
        pathlib.Path("docs/data/stats.json").write_text(
            json.dumps(LOCAL), encoding="utf-8")
        self.output = pathlib.Path("gh_output").resolve()
        self.output.write_text("", encoding="utf-8")
        os.environ["GITHUB_OUTPUT"] = str(self.output)
        os.environ["PAGES_REPORT"] = str(pathlib.Path("report.md").resolve())
        self.addCleanup(os.environ.pop, "GITHUB_OUTPUT", None)
        self.addCleanup(os.environ.pop, "PAGES_REPORT", None)

    def run_main(self, responses):
        """responses: url-suffix -> (status, bytes). Unlisted urls 404."""
        def fake_get(url):
            for suffix, reply in responses.items():
                if url.endswith(suffix):
                    return reply
            return 404, b""
        with mock.patch.object(c, "get", side_effect=fake_get), \
                mock.patch.object(c, "now", return_value=NOW), \
                mock.patch("builtins.print"):
            with self.assertRaises(SystemExit) as exit_info:
                c.main()
        emitted = dict(line.split("=", 1)
                       for line in self.output.read_text().splitlines())
        return exit_info.exception.code, emitted["status"], \
            pathlib.Path("report.md").read_text(encoding="utf-8")

    def healthy(self, stats=None):
        return {"data/stats.json": (200, json.dumps(stats or LOCAL).encode()),
                "pordata/": (200, HTML.encode()),
                "index-oiCPKUGL.js": (200, b"x"),
                "index-Dah0uG9s.css": (200, b"x")}

    def test_healthy_site_exits_zero(self):
        code, status, report = self.run_main(self.healthy())
        self.assertEqual((code, status), (0, "ok"))
        self.assertIn("Pages health: ok", report)

    def test_a_404_on_stats_is_unreachable_and_fails(self):
        code, status, _ = self.run_main({})
        self.assertEqual((code, status), (1, "unreachable"))

    def test_a_200_that_is_not_json_is_unreachable(self):
        """A CDN error page or an interstitial answers 200 with HTML.
        Treating that as a live catalogue would report a healthy site."""
        code, status, _ = self.run_main(
            {"data/stats.json": (200, b"<html>edge error</html>")})
        self.assertEqual((code, status), (1, "unreachable"))

    def test_index_failing_while_stats_serves_is_unreachable(self):
        """Pages can serve a stored object after the app itself is gone.
        Checking only the JSON would miss it."""
        responses = self.healthy()
        responses["pordata/"] = (500, b"")
        code, status, _ = self.run_main(responses)
        self.assertEqual((code, status), (1, "unreachable"))

    def test_a_404_bundle_is_broken_and_fails(self):
        responses = self.healthy()
        responses["index-oiCPKUGL.js"] = (404, b"")
        code, status, report = self.run_main(responses)
        self.assertEqual((code, status), (1, "broken"))
        self.assertIn("index-oiCPKUGL.js", report)

    def test_an_older_served_build_fails(self):
        """NOW is 106 min past the committed build, well outside the
        30-minute deploy window, so this is a fault and not a deploy in
        flight — pinned by the frozen clock, not by when the suite runs."""
        code, status, report = self.run_main(self.healthy(LIVE_OLD))
        self.assertEqual((code, status), (1, "behind"))
        self.assertIn("2026-08-20 09:00 UTC", report)

    def test_assets_are_requested_at_the_site_root(self):
        """`./assets/x.js` joined naively onto the site URL gives
        `.../pordata/./assets/x.js`, which Pages does serve — but the
        relative prefix has to come off for the report to name what a
        browser would actually request."""
        seen = []

        def fake_get(url):
            seen.append(url)
            return (200, json.dumps(LOCAL).encode()) if url.endswith(
                "stats.json") else (200, HTML.encode())
        with mock.patch.object(c, "get", side_effect=fake_get), \
                mock.patch.object(c, "now", return_value=NOW), \
                mock.patch("builtins.print"):
            with self.assertRaises(SystemExit):
                c.main()
        self.assertIn(c.SITE + "assets/index-oiCPKUGL.js", seen)


if __name__ == "__main__":
    unittest.main()
