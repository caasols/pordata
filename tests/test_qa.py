import re
import pathlib
import unittest

from helpers import PT, RepoCase, load_script, record

qa = load_script("qa_catalogue")


class RecoverableTest(unittest.TestCase):
    def test_fontes_recoverable_from_windows(self):
        rec = {"marker_windows": {"Fontes": ["... Fontes/Entidades: INE ..."]}}
        self.assertTrue(qa.recoverable_from_windows(rec, "fontes"))
        self.assertFalse(qa.recoverable_from_windows(rec, "ultima_atualizacao"))

    def test_date_recoverable(self):
        rec = {"marker_windows": {"ltima atualiza": ["em 2026-06-22 foi"]}}
        self.assertTrue(qa.recoverable_from_windows(rec, "ultima_atualizacao"))

    def test_empty_windows(self):
        self.assertFalse(qa.recoverable_from_windows({}, "fontes"))


class ValueLeakTest(unittest.TestCase):
    """The gate that makes decision 1 falsifiable.

    `unit_contamination_max` inspects the published `unit` field only,
    which is why 15,946 observation values sat in the committed corpus
    through months of green CI. This one reads every window of every
    record."""

    def test_a_window_carrying_values_is_counted(self):
        rec = {"marker_windows": {"Fontes": ["3,2 1,9 10,4 Fontes: INE"]}}
        self.assertEqual(qa.value_tokens(rec), 3)

    def test_a_clean_window_counts_zero(self):
        rec = {"marker_windows":
               {"Fontes": ["Fontes/Entidades: INE, PORDATA"],
                "ltima actualiza": ["Última actualização: 2025-12-22"]}}
        self.assertEqual(qa.value_tokens(rec), 0)

    def test_a_record_with_no_windows_counts_zero(self):
        self.assertEqual(qa.value_tokens({"error": "500"}), 0)

    def test_a_window_stored_as_a_bare_string_is_still_read(self):
        """Older records store a string where newer ones store a list;
        a checker that only understood one shape would pass the other."""
        self.assertEqual(qa.value_tokens({"marker_windows": {"F": "1,5"}}), 1)

    def test_the_checker_and_the_redactor_share_one_pattern(self):
        """Two copies of a redaction pattern drift, and the one that
        drifts is the checker — which then certifies the leak it exists
        to catch."""
        harvest = load_script("harvest_catalogue")
        self.assertIs(qa.harvest.VALUE_TOKEN, harvest.VALUE_TOKEN)

    def test_the_threshold_is_zero_and_not_a_ratio(self):
        """A leak budget is a licence violation budget."""
        self.assertEqual(qa.THRESHOLDS["jsonl_value_leak_max"], 0)


class GateAttributionTest(unittest.TestCase):
    """A report naming its own enforcer has to be right about it.

    `EUROSTAT-QA.md` said "gated at `qa_catalogue.py --strict` with a
    floor of 100 matches" while that module contained no crosswalk
    threshold at all — so a refactorer could delete the real `SystemExit`
    believing the line was held elsewhere. The two are not
    interchangeable either: a `qa_catalogue` breach reverts `docs/` and
    opens an issue, a builder breach only aborts its own step.

    Both are true now, and this asserts they stay true."""

    REPORTS = ["data/crosswalk/QA.md", "data/crosswalk/EUROSTAT-QA.md"]

    def test_a_report_naming_qa_catalogue_has_a_threshold_there(self):
        for name in self.REPORTS:
            text = pathlib.Path(name).read_text(encoding="utf-8")
            for key in re.findall(r"`([a-z_]+_(?:min|max))`", text):
                self.assertIn(key, qa.THRESHOLDS,
                              f"{name} names {key} which qa_catalogue "
                              "does not define")

    def test_the_registered_floors_match_the_builders(self):
        """Two numbers for one floor drift. These are separate constants
        by necessity — the builder must refuse before writing and the QA
        gate must check the committed file — so they are asserted equal
        rather than left to agree by habit."""
        ine = load_script("build_crosswalk")
        eurostat = load_script("build_eurostat_crosswalk")
        self.assertEqual(qa.THRESHOLDS["ine_matched_min"], ine.MIN_MATCHED)
        self.assertEqual(qa.THRESHOLDS["eurostat_matched_min"],
                         eurostat.MIN_MATCHED)


class UnmeasuredThresholdTest(unittest.TestCase):
    """A threshold whose metric never arrives gates nothing.

    `gate` maps key to metric by stripping the `_min`/`_max` suffix, so a
    rename or typo on either side made the check vanish rather than fail.
    The assertion lives at the call site, not in `gate`: callers
    legitimately hand `gate` one metric at a time, and only `main` knows
    it measured everything."""

    def test_a_full_metric_set_reports_nothing(self):
        metrics = {k.rsplit("_", 1)[0]: 0 for k in qa.THRESHOLDS}
        self.assertEqual(qa.unmeasured_thresholds(metrics), [])

    def test_a_missing_metric_is_named(self):
        metrics = {k.rsplit("_", 1)[0]: 0 for k in qa.THRESHOLDS}
        del metrics["name_coverage"]
        self.assertEqual(qa.unmeasured_thresholds(metrics),
                         ["name_coverage_min"])

    def test_the_optional_ones_are_allowed_to_be_absent(self):
        """Each for a named reason: the payload metrics need a built
        bundle, the crosswalk counts need their builders to have run."""
        self.assertEqual(qa.unmeasured_thresholds({}),
                         sorted(k for k in qa.THRESHOLDS
                                if k.rsplit("_", 1)[0]
                                not in qa.OPTIONAL_METRICS))

    def test_every_optional_metric_has_a_threshold(self):
        """An entry here excusing a threshold that no longer exists
        silently widens the exemption."""
        keys = {k.rsplit("_", 1)[0] for k in qa.THRESHOLDS}
        self.assertTrue(qa.OPTIONAL_METRICS <= keys)


class QaMainTest(RepoCase):
    def test_writes_report_with_findings(self):
        self.write_records([
            record("portugal/taxa+de+natalidade-99", 99, "portugal",
                   "Taxa de natalidade"),
            record("municipios/sem+nome-200", 200, "municipios", "",
                   marker_windows={"Fontes": ["Fontes/Entidades: INE"]}),
            record("europa/overcapture-300", 300, "europa", "Overcapture",
                   fontes="INE, PORDATA Carregue aqui para ver"),
            {"url": f"{PT}/europa/falhado-888", "error": "timeout",
             "harvested_at": "2026-08-22"},
        ])
        qa.main()
        report = pathlib.Path("data/catalogue/QA.md").read_text(
            encoding="utf-8")
        self.assertIn("3 ok, 1 errored", report)
        self.assertIn("empty name: 1", report)
        self.assertIn("over-capture", report)
        self.assertIn("Error records", report)

    def test_clean_catalogue_reports_no_findings(self):
        self.write_records([
            record("portugal/taxa+de+natalidade-99", 99, "portugal",
                   "Taxa de natalidade"),
        ])
        qa.main()
        report = pathlib.Path("data/catalogue/QA.md").read_text(
            encoding="utf-8")
        self.assertIn("no findings", report)


if __name__ == "__main__":
    unittest.main()
