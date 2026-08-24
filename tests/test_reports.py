"""The report writers were the largest blind spot mutation testing found:
`qa_catalogue.main`, `build_catalogue.main`, `harvest_catalogue.write_report`
and `build_catalogue.write_unmatched_worksheet` held 81% of all surviving
mutants, because nothing asserted what they actually emit.

These tests assert *content* — the numbers and section names a reader
relies on — rather than exact prose, so they survive wording changes but
catch a figure computed wrongly or a section silently disappearing.
"""

import json
import pathlib
import unittest
import unittest.mock

from helpers import PT, RepoCase, load_script, record

harvest = load_script("harvest_catalogue")
build = load_script("build_catalogue")
qa = load_script("qa_catalogue")


class HarvestReportTest(RepoCase):
    def setUp(self):
        super().setUp()
        self.write_records([
            record("portugal/a-1", 1, "portugal", "A"),
            record("portugal/b-2", 2, "portugal", "B"),
            record("europa/c-3", 3, "europa", "C"),
            record("municipios/d-4", 4, "municipios", "D",
                   error="HTTP 500", http_status=500),
        ])

    def report(self, targets=None, plan=None):
        harvest.write_report(
            targets or [f"{PT}/portugal/a-1", f"{PT}/portugal/b-2",
                        f"{PT}/europa/c-3", f"{PT}/municipios/d-4"],
            plan or {"missing": [], "errored": ["x"], "stale": []})
        return pathlib.Path("data/catalogue/REPORT.md").read_text(
            encoding="utf-8")

    def test_counts_only_records_without_an_error(self):
        # 4 records, one of them an error record
        self.assertIn("3 / 4", self.report())

    def test_breaks_the_count_down_by_area(self):
        text = self.report()
        for fragment in ("europa: 1", "portugal: 2"):
            self.assertIn(fragment, text)

    def test_reports_each_pending_bucket_separately(self):
        text = self.report(plan={"missing": ["a", "b"], "errored": ["c"],
                                 "stale": ["d", "e", "f"]})
        self.assertIn("2 missing", text)
        self.assertIn("1 errored", text)
        self.assertIn("3 stale", text)

    def test_abandoned_urls_are_excluded_from_the_target_count(self):
        pathlib.Path("data/catalogue/abandoned.txt").write_text(
            f"{PT}/municipios/d-4\n", encoding="utf-8")
        # one target retired, so the denominator drops
        self.assertIn("3 / 3", self.report())

    def test_field_coverage_is_a_percentage_of_ok_records(self):
        self.assertIn("name 100%", self.report())

    def test_a_missing_field_shows_as_a_lower_percentage(self):
        self.write_records([
            record("portugal/a-1", 1, "portugal", "A"),
            record("portugal/b-2", 2, "portugal", "B", fontes=""),
        ])
        self.assertIn("fontes 50%", self.report())


class UnmatchedWorksheetTest(RepoCase):
    def test_lists_the_names_the_matcher_refused(self):
        self.write_records([record("europa/a-1", 1, "europa", "Alfa")])
        stats = {"quadro_resumo_europa": {
            "names": 3, "matched": 1, "distinct_rows": 1, "collisions": 0,
            "unmatched": ["Nome sem par", "Outro nome sem par"]}}
        build.write_unmatched_worksheet(build.lib.load_records(), stats)
        text = pathlib.Path(
            "data/catalogue/FEATURED-UNMATCHED.md").read_text(encoding="utf-8")
        self.assertIn("Nome sem par", text)
        self.assertIn("Outro nome sem par", text)

    def test_says_nothing_is_pending_when_everything_matched(self):
        self.write_records([record("europa/a-1", 1, "europa", "Alfa")])
        build.write_unmatched_worksheet(
            build.lib.load_records(),
            {"quadro_resumo_europa": {"names": 3, "matched": 3,
                                      "distinct_rows": 3, "collisions": 0,
                                      "unmatched": []}})
        text = pathlib.Path(
            "data/catalogue/FEATURED-UNMATCHED.md").read_text(encoding="utf-8")
        self.assertNotIn("- `", text)


class QaReportTest(RepoCase):
    def setUp(self):
        super().setUp()
        self.write_records([
            record("portugal/taxa+de+natalidade-99", 99, "portugal", "Taxa"),
            record("municipios/medicos+por+habitante-200", 200,
                   "municipios", "Médicos"),
            record("europa/indice+de+gini-300", 300, "europa", "Gini"),
        ])

    def read(self):
        qa.main()
        return pathlib.Path("data/catalogue/QA.md").read_text(encoding="utf-8")

    # Some metrics are conditional on inputs that a bare records file does
    # not provide (featured stats, the published catalogue), so the
    # unconditional set is asserted here and the conditional ones below.
    ALWAYS = ("jsonl_skipped_lines", "ok_records_ratio", "name_coverage",
              "description_coverage", "fontes_coverage", "date_iso_ratio",
              "duplicate_area_id", "parse_warnings")

    def test_every_unconditional_metric_is_printed(self):
        text = self.read()
        for metric in self.ALWAYS:
            self.assertIn(metric, text, metric)

    def test_published_metrics_appear_once_a_catalogue_exists(self):
        pathlib.Path("docs/data").mkdir(parents=True, exist_ok=True)
        pathlib.Path("docs/data/catalogue.json").write_text(json.dumps([
            {"area": "portugal", "id": 99, "name": "Taxa", "unit": "Euro",
             "breakdown": "total e por sexo", "revision": "", "question": "",
             "period": ""}]), encoding="utf-8")
        text = self.read()
        for metric in ("breakdown_ratio", "unit_ratio", "question_ratio",
                       "period_ratio", "revision_ratio",
                       "unit_translated_ratio"):
            self.assertIn(metric, text, metric)

    def test_per_area_coverage_is_reported_not_just_the_mean(self):
        # a catalogue-wide mean once hid a 100/100/0 unit split
        pathlib.Path("docs/data").mkdir(parents=True, exist_ok=True)
        pathlib.Path("docs/data/catalogue.json").write_text(json.dumps([
            {"area": "portugal", "id": 1, "name": "A", "unit": ""},
            {"area": "europa", "id": 2, "name": "B", "unit": "Euro"}]),
            encoding="utf-8")
        self.assertIn("unit_ratio_by_area", self.read())

    def test_the_gate_section_states_the_outcome(self):
        self.assertIn("all thresholds pass", self.read())

    def test_a_breach_is_named_in_the_report(self):
        self.write_records([
            record("portugal/taxa+de+natalidade-99", 99, "portugal", ""),
            record("municipios/medicos+por+habitante-200", 200,
                   "municipios", ""),
            record("europa/indice+de+gini-300", 300, "europa", ""),
        ])
        text = self.read()
        self.assertIn("BREACH", text)
        self.assertIn("name_coverage", text)

    def test_records_are_counted_per_area(self):
        text = self.read()
        for area in ("portugal", "municipios", "europa"):
            self.assertIn(area, text)


class UnitTranslationCoverageTest(RepoCase):
    """The gate reads the same vocabulary file the site renders from.

    The table is written into the fixture rather than read from the repo:
    depending on a file outside the fixture made this pass under unittest
    and fail under mutmut, which runs from a copied tree.
    """

    def setUp(self):
        super().setUp()
        terms = pathlib.Path("site/src/lib/unit-terms.json")
        terms.parent.mkdir(parents=True, exist_ok=True)
        terms.write_text(json.dumps(
            {"pt": {}, "en": {"Euro": "Euro", "Milhões": "Millions"}}),
            encoding="utf-8")
        patcher = unittest.mock.patch.object(qa, "UNIT_TERMS", terms)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_a_fully_translated_unit_counts_as_covered(self):
        ratio, missing = qa.unit_translation_coverage(
            [{"unit": "Euro - Milhões"}])
        self.assertEqual(ratio, 1.0)
        self.assertEqual(missing, {})

    def test_an_unknown_term_is_named_with_its_row_count(self):
        ratio, missing = qa.unit_translation_coverage(
            [{"unit": "Coisa inventada - Milhões"},
             {"unit": "Coisa inventada"}])
        self.assertEqual(ratio, 0.0)
        self.assertEqual(missing, {"Coisa inventada": 2})

    def test_one_unknown_part_makes_the_whole_row_untranslated(self):
        ratio, _ = qa.unit_translation_coverage(
            [{"unit": "Euro - Desconhecido"}])
        self.assertEqual(ratio, 0.0)

    def test_rows_without_a_unit_are_not_counted_against_coverage(self):
        ratio, _ = qa.unit_translation_coverage(
            [{"unit": ""}, {"unit": "Euro"}])
        self.assertEqual(ratio, 1.0)

    def test_no_units_at_all_is_full_coverage_not_a_divide_by_zero(self):
        self.assertEqual(qa.unit_translation_coverage([]), (1.0, {}))

    def test_a_missing_vocabulary_file_does_not_fail_the_gate(self):
        with unittest.mock.patch.object(
                qa, "UNIT_TERMS", pathlib.Path("nao/existe.json")):
            self.assertEqual(
                qa.unit_translation_coverage([{"unit": "Euro"}]), (1.0, {}))
