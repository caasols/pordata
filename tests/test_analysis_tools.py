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
euro = load_script("analyse_eurostat_crosswalk")
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


class EurostatShapeTest(unittest.TestCase):
    """The measurement that specified the Eurostat matcher.

    It decides nothing and writes no crosswalk, but the numbers it
    reports are what the builder was specified from — including the ones
    that refuted the first idea — so the arithmetic behind them is worth
    pinning.
    """

    @staticmethod
    def dataset(title, themes="Economy"):
        return {"title": title, "themes": themes,
                "tokens": euro.tokens(title), "norm": euro.norm_title(title)}

    @staticmethod
    def row(name_en, area="europa", fontes=("Eurostat",)):
        return {"area": area, "name_en": name_en, "fontes": list(fontes)}

    def test_a_unit_parenthetical_is_stripped_before_comparing(self):
        self.assertEqual(euro.strip_unit("Area under organic farming "
                                         "(percentage)"),
                         "Area under organic farming")

    def test_an_acronym_in_parentheses_is_left_alone(self):
        keep = "Obesity rate by body mass index (BMI)"
        self.assertEqual(euro.strip_unit(keep), keep)

    def test_the_breakdown_is_split_off_both_sides(self):
        head, tail = euro.split_tail("Activity rate total and by sex",
                                     euro.PORDATA_TAIL)
        self.assertEqual(head, "Activity rate")
        self.assertIn("sex", tail)

    def test_a_title_with_no_breakdown_keeps_all_of_itself(self):
        head, tail = euro.split_tail("Crude divorce rate", euro.EUROSTAT_TAIL)
        self.assertEqual(head, "Crude divorce rate")
        self.assertEqual(tail, set())

    def test_the_operators_count_head_matches(self):
        got = euro.operators([self.row("Activity rate total and by sex")],
                             [self.dataset("Activity rate by sex")])
        self.assertEqual(got["head"], 1)
        self.assertEqual(got["survivors"], [1])

    def test_the_operators_count_the_veto(self):
        got = euro.operators(
            [self.row("Exports total and by type of energy product")],
            [self.dataset("Exports by industry (FIGARO application)")])
        self.assertEqual(got["head"], 1)
        self.assertEqual(got["vetoed"], 1)
        self.assertEqual(got["survivors"], [])

    def test_the_operators_record_what_a_token_floor_would_have_cost(self):
        """The rejected idea is kept as a number, not a memory: a floor
        of two content words deletes this pairing, whose titles are
        identical."""
        got = euro.operators([self.row("Obesity rate by body mass index")],
                             [self.dataset("Obesity rate by body mass "
                                           "index (BMI)")])
        self.assertEqual(got["floor_would_drop"], 1)
        self.assertEqual(got["survivors"], [1])

    def test_an_out_of_scope_row_is_not_measured(self):
        got = euro.operators([self.row("X", area="portugal")],
                             [self.dataset("X")])
        self.assertEqual(got["scope"], 0)

    def test_the_containment_measurement_finds_an_exact_title(self):
        got = euro.measure([self.row("Crude divorce rate")],
                           [self.dataset("Crude divorce rate")])
        self.assertEqual(got["exact"], 1)
        self.assertEqual(got["contained"], 1)

    def test_a_row_sharing_no_token_is_counted_apart(self):
        got = euro.measure([self.row("Crude divorce rate")],
                           [self.dataset("Ammonia emissions")])
        self.assertEqual(got["no_shared"], 1)
        self.assertEqual(got["contained"], 0)

    def test_the_report_states_the_head_and_veto_counts(self):
        got = euro.render_operators(euro.operators(
            [self.row("Activity rate total and by sex"),
             self.row("Exports total and by type of energy product")],
            [self.dataset("Activity rate by sex"),
             self.dataset("Exports by industry (FIGARO application)")]))
        self.assertIn("**2** rows", got.replace("**2**\n", "**2** rows"))
        self.assertIn("**1** refused outright", got)

    def test_the_shape_report_states_its_inputs(self):
        got = euro.render(euro.measure([self.row("Crude divorce rate")],
                                       [self.dataset("Crude divorce rate")]))
        self.assertIn("English name: **1**", got)
        self.assertIn("Eurostat datasets: **1**", got)

    def test_the_shape_report_survives_nothing_being_contained(self):
        """A report that raises when the operator finds nothing hides
        the finding — no containment at all would itself be the answer."""
        got = euro.render(euro.measure([self.row("Crude divorce rate")],
                                       [self.dataset("Ammonia emissions")]))
        self.assertIn("nothing to tie", got)


class BucketTest(unittest.TestCase):
    def test_values_land_in_the_band_that_contains_them(self):
        self.assertEqual(euro.bucket([0.1, 0.6, 1.0], [0.5]),
                         [(0.0, 0.5, 1), (0.5, 1.01, 2)])
