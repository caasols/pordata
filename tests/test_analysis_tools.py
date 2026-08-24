"""Offline analysis and probe helpers.

These are the scripts that answer questions rather than run the
pipeline, so they were never covered. The pure functions in them still
decide what gets reported, and a wrong answer here has already sent one
roadmap item off in the wrong direction, so they get the same treatment
as pipeline code.
"""

import io
import json
import pathlib
import unittest
import unittest.mock

from helpers import RepoCase, load_script

cross = load_script("analyse_crosswalk")
gate = load_script("mutation_gate")
probe = load_script("probe_ine_availability")


class NormalisationTest(unittest.TestCase):
    def test_accents_are_folded_and_case_lowered(self):
        self.assertEqual(cross.strip_accents("População Média"),
                         "populacao media")

    def test_a_trailing_unit_parenthesis_is_dropped(self):
        # INE suffixes units its titles; PORDATA never does
        self.assertEqual(cross.norm_title("Docentes (N.º)"), "docentes")
        self.assertEqual(cross.norm_title("Mercadorias (t)"), "mercadorias")

    def test_a_parenthesis_that_is_not_trailing_survives(self):
        self.assertIn("nace", cross.norm_title("Emprego (NACE) por setor"))

    def test_a_long_parenthesis_is_not_treated_as_a_unit(self):
        got = cross.norm_title("Emprego (uma explicação bastante longa)")
        self.assertIn("explicacao", got)

    def test_punctuation_becomes_single_spaces(self):
        self.assertEqual(cross.norm_title("A-B, C/D"), "a b c d")

    def test_tokens_drop_stopwords_and_short_words(self):
        got = cross.tokens("Taxa de natalidade e de mortalidade")
        self.assertIn("natalidade", got)
        self.assertNotIn("de", got)
        self.assertNotIn("e", got)

    def test_tokens_are_accent_blind(self):
        self.assertEqual(cross.tokens("População"), cross.tokens("populacao"))

    def test_total_is_a_stopword_because_nearly_every_title_has_it(self):
        self.assertNotIn("total", cross.tokens("Docentes total"))


class IneSourcedTest(unittest.TestCase):
    @staticmethod
    def row(area, *fontes):
        return {"area": area, "fontes": list(fontes), "name": "X"}

    def test_keeps_rows_citing_ine(self):
        rows = [self.row("portugal", "INE", "PORDATA")]
        self.assertEqual(len(cross.ine_sourced(rows)), 1)

    def test_matches_ine_with_a_survey_gloss(self):
        rows = [self.row("municipios", "INE - Inquérito ao emprego")]
        self.assertEqual(len(cross.ine_sourced(rows)), 1)

    def test_drops_rows_with_no_ine_source(self):
        self.assertEqual(cross.ine_sourced([self.row("europa", "Eurostat")]), [])

    def test_drops_europa_because_it_has_no_ine_geography(self):
        self.assertEqual(cross.ine_sourced([self.row("europa", "INE")]), [])

    def test_a_row_without_fontes_is_not_a_crash(self):
        self.assertEqual(cross.ine_sourced([{"area": "portugal", "name": "X"}]),
                         [])


class MutationGateMainTest(RepoCase):
    LINE = "⠹ 100/100  🎉 70 🫥 0  ⏰ 0  🤔 0  🙁 30  🔇 0"

    def run_main(self, argv):
        with unittest.mock.patch.object(gate.sys, "argv", argv):
            try:
                gate.main()
            except SystemExit as exc:
                return exc.code
        return 0

    def test_a_passing_rate_exits_zero(self):
        pathlib.Path("run.log").write_text(self.LINE, encoding="utf-8")
        self.assertEqual(self.run_main(["gate", "run.log"]), 0)

    def test_a_failing_rate_exits_one(self):
        pathlib.Path("run.log").write_text(
            "⠹ 100/100  🎉 10 🫥 0  ⏰ 0  🤔 0  🙁 90  🔇 0", encoding="utf-8")
        self.assertEqual(self.run_main(["gate", "run.log"]), 1)

    def test_a_missing_log_is_a_failure_not_a_pass(self):
        # a gate that passes when its input vanished is not a gate
        self.assertEqual(self.run_main(["gate", "nope.log"]), 1)

    def test_an_unreadable_log_is_a_failure(self):
        pathlib.Path("run.log").write_text("mutmut crashed", encoding="utf-8")
        self.assertEqual(self.run_main(["gate", "run.log"]), 1)

    def test_no_argument_is_a_usage_error(self):
        self.assertEqual(self.run_main(["gate"]), 2)


class IneProbeRequestTest(RepoCase):
    """The probe's HTTP handling, with the network stubbed."""

    def setUp(self):
        super().setUp()
        patcher = unittest.mock.patch.object(
            probe, "LOG", pathlib.Path("data/ine/availability.csv"))
        patcher.start()
        self.addCleanup(patcher.stop)

    @staticmethod
    def response(status, body=b""):
        resp = unittest.mock.MagicMock()
        resp.status = status
        resp.read.return_value = body
        resp.__enter__.return_value = resp
        return resp

    def test_a_served_head_is_recorded_as_serving(self):
        with unittest.mock.patch.object(probe.urllib.request, "urlopen",
                                        return_value=self.response(200)):
            row = probe.probe()
        self.assertEqual(row["ok"], "yes")
        self.assertEqual(row["method"], "HEAD")
        self.assertEqual(row["http_status"], 200)

    def test_a_403_is_recorded_as_blocked(self):
        err = probe.urllib.error.HTTPError("u", 403, "no", {}, None)
        with unittest.mock.patch.object(probe.urllib.request, "urlopen",
                                        side_effect=err):
            row = probe.probe()
        self.assertEqual(row["ok"], "no")
        self.assertEqual(row["http_status"], 403)

    def test_head_not_allowed_falls_back_to_a_range_request(self):
        # refusing HEAD on a JSP is an endpoint quirk, not a block, so it
        # must not be logged as one
        err = probe.urllib.error.HTTPError("u", 405, "no", {}, None)
        with unittest.mock.patch.object(
                probe.urllib.request, "urlopen",
                side_effect=[err, self.response(206, b"x" * 100)]):
            row = probe.probe()
        self.assertEqual(row["method"], "RANGE")
        self.assertEqual(row["ok"], "yes")
        self.assertEqual(row["bytes_read"], 100)
        self.assertIn("Range", row["note"])

    def test_a_timeout_is_recorded_without_a_status(self):
        with unittest.mock.patch.object(probe.urllib.request, "urlopen",
                                        side_effect=TimeoutError("slow")):
            row = probe.probe()
        self.assertEqual(row["http_status"], "")
        self.assertEqual(row["ok"], "no")
        self.assertIn("TimeoutError", row["note"])

    def test_a_row_carries_the_weekday_for_the_weekend_question(self):
        with unittest.mock.patch.object(probe.urllib.request, "urlopen",
                                        return_value=self.response(200)):
            row = probe.probe()
        self.assertIn(row["weekday"],
                      ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"))

    def test_appending_writes_a_header_once(self):
        row = {k: "" for k in probe.FIELDS}
        row["date_utc"] = "2026-08-25"
        probe.append(row)
        probe.append(row)
        text = probe.LOG.read_text(encoding="utf-8")
        self.assertEqual(text.count("date_utc"), 1)
        self.assertEqual(text.count("2026-08-25"), 2)
