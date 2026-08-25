"""Exact-boundary tests for every threshold constant.

Mutation testing showed the shape assertions were tested for obvious
cases and not at their limits, so mutants that shift a comparison by one
(`>` to `>=`, a constant to a neighbour) survived. Each test here pins a
threshold from *both* sides: the largest value that must pass and the
smallest that must fail. A test that only checks "far too long" cannot
tell those mutants apart.
"""

import datetime
import pathlib
import re
import unittest

from helpers import load_script

lib = load_script("pordata_lib")
build = load_script("build_catalogue")
harvest = load_script("harvest_catalogue")


class ValidDateBoundaryTest(unittest.TestCase):
    TODAY = "2026-08-24"

    def test_the_earliest_plausible_date_passes(self):
        self.assertTrue(lib.valid_date(lib.EARLIEST_PLAUSIBLE_DATE, self.TODAY))

    def test_the_day_before_it_fails(self):
        earlier = (datetime.date.fromisoformat(lib.EARLIEST_PLAUSIBLE_DATE)
                   - datetime.timedelta(days=1)).isoformat()
        self.assertFalse(lib.valid_date(earlier, self.TODAY))

    def test_today_plus_two_days_of_slack_passes(self):
        # slack exists for timezones and for PORDATA post-dating a release
        limit = (datetime.date.fromisoformat(self.TODAY)
                 + datetime.timedelta(days=2)).isoformat()
        self.assertTrue(lib.valid_date(limit, self.TODAY))

    def test_one_day_past_the_slack_fails(self):
        beyond = (datetime.date.fromisoformat(self.TODAY)
                  + datetime.timedelta(days=3)).isoformat()
        self.assertFalse(lib.valid_date(beyond, self.TODAY))

    def test_today_itself_passes(self):
        self.assertTrue(lib.valid_date(self.TODAY, self.TODAY))

    def test_a_well_shaped_but_unreal_date_fails(self):
        self.assertFalse(lib.valid_date("2026-02-31", self.TODAY))
        self.assertFalse(lib.valid_date("2026-13-01", self.TODAY))

    def test_shape_alone_is_not_enough(self):
        for value in ("", "2026-8-24", "24-08-2026", "2026/08/24",
                      "2026-08-24 ", "not a date", None):
            self.assertFalse(lib.valid_date(value, self.TODAY), repr(value))

    def test_defaults_to_today_when_not_told(self):
        # the real signature takes `today` only so tests can pin it
        self.assertTrue(lib.valid_date(
            datetime.datetime.now(datetime.UTC).date().isoformat()))


class PlausibleFontesBoundaryTest(unittest.TestCase):
    @staticmethod
    def of_length(total):
        """A comma-separated value of exactly `total` characters whose
        parts each stay inside MAX_FONTE_PART_LEN, so only the overall
        length limit is under test."""
        part = "A" * (lib.MAX_FONTE_PART_LEN - 10)
        parts, length = [], 0
        while length + len(part) + 1 <= total:
            parts.append(part)
            length += len(part) + 1
        value = ",".join(parts)
        return value + "," + "A" * (total - len(value) - 1)

    def test_a_value_at_the_length_limit_passes(self):
        value = self.of_length(lib.MAX_FONTES_LEN)
        self.assertEqual(len(value), lib.MAX_FONTES_LEN)
        self.assertTrue(lib.plausible_fontes(value))

    def test_one_character_past_the_limit_fails(self):
        value = self.of_length(lib.MAX_FONTES_LEN + 1)
        self.assertEqual(len(value), lib.MAX_FONTES_LEN + 1)
        self.assertFalse(lib.plausible_fontes(value))

    def test_a_part_at_the_part_length_limit_passes(self):
        self.assertTrue(lib.plausible_fontes("X" * lib.MAX_FONTE_PART_LEN))

    def test_a_part_one_character_over_fails(self):
        self.assertFalse(
            lib.plausible_fontes("X" * (lib.MAX_FONTE_PART_LEN + 1)))

    def test_a_part_at_the_word_limit_passes(self):
        self.assertTrue(lib.plausible_fontes(
            " ".join(["w"] * lib.MAX_FONTE_PART_WORDS)))

    def test_a_part_one_word_over_fails(self):
        self.assertFalse(lib.plausible_fontes(
            " ".join(["w"] * (lib.MAX_FONTE_PART_WORDS + 1))))

    def test_empty_is_never_plausible(self):
        # a mutant flipping this to True publishes page prose as a source
        self.assertFalse(lib.plausible_fontes(""))
        self.assertFalse(lib.plausible_fontes(None))

    def test_each_separator_splits_parts(self):
        long_part = "X" * (lib.MAX_FONTE_PART_LEN + 1)
        for sep in ("|", ",", ";"):
            self.assertFalse(lib.plausible_fontes(f"INE{sep}{long_part}"), sep)
            self.assertTrue(lib.plausible_fontes(f"INE{sep}PORDATA"), sep)

    def test_blank_parts_between_separators_are_skipped(self):
        self.assertTrue(lib.plausible_fontes("INE,,PORDATA"))


class UnitBoundaryTest(unittest.TestCase):
    def test_a_unit_at_the_length_limit_passes(self):
        self.assertTrue(build.plausible_unit("u" * build.MAX_UNIT_LEN))

    def test_one_character_over_fails(self):
        self.assertFalse(build.plausible_unit("u" * (build.MAX_UNIT_LEN + 1)))

    def test_a_unit_at_the_word_limit_passes(self):
        self.assertTrue(build.plausible_unit(
            " ".join(["wo"] * build.MAX_UNIT_WORDS)))

    def test_one_word_over_fails(self):
        self.assertFalse(build.plausible_unit(
            " ".join(["wo"] * (build.MAX_UNIT_WORDS + 1))))

    def test_digit_ratio_at_the_limit_passes(self):
        # 3 digits in 10 characters = 0.30, inside the 0.35 ceiling
        value = "123abcdefg"
        self.assertLessEqual(3 / len(value), build.MAX_UNIT_DIGIT_RATIO)
        self.assertTrue(build.plausible_unit(value))

    def test_digit_ratio_past_the_limit_fails(self):
        value = "1234abcdef"          # 0.40
        self.assertGreater(4 / len(value), build.MAX_UNIT_DIGIT_RATIO)
        self.assertFalse(build.plausible_unit(value))

    def test_superscript_two_is_not_a_digit_for_this_purpose(self):
        # str.isdigit() is True for '²', which once rejected "Km²"
        self.assertTrue(build.plausible_unit("Km²"))


class RevisionBoundaryTest(unittest.TestCase):
    STEM = "A revisão"          # short enough to sit under the floor

    def sentence(self, length):
        assert length >= len(self.STEM)
        return self.STEM + "x" * (length - len(self.STEM))

    def test_a_note_at_the_minimum_length_passes(self):
        note = self.sentence(build.MIN_REVISION_LEN)
        self.assertEqual(len(note), build.MIN_REVISION_LEN)
        self.assertEqual(
            build.extract_revision({"marker_windows": {"revis": [note]}}), note)

    def test_one_character_under_the_minimum_is_refused(self):
        note = self.sentence(build.MIN_REVISION_LEN - 1)
        self.assertEqual(
            build.extract_revision({"marker_windows": {"revis": [note]}}), "")

    def test_one_character_over_the_maximum_is_refused(self):
        note = self.sentence(build.MAX_REVISION_LEN + 1)
        self.assertEqual(
            build.extract_revision({"marker_windows": {"revis": [note]}}), "")


class QuestionBoundaryTest(unittest.TestCase):
    def question(self, length):
        return "Q" * (length - 1) + "?"

    def test_a_question_at_the_minimum_length_passes(self):
        q = self.question(harvest.MIN_QUESTION_LEN)
        self.assertEqual(harvest.extract_question(f"<h2>{q}</h2>"), q)

    def test_one_character_under_the_minimum_is_refused(self):
        q = self.question(harvest.MIN_QUESTION_LEN - 1)
        self.assertEqual(harvest.extract_question(f"<h2>{q}</h2>"), "")

    def test_a_question_at_the_maximum_length_passes(self):
        q = self.question(harvest.MAX_QUESTION_LEN)
        self.assertEqual(harvest.extract_question(f"<h2>{q}</h2>"), q)

    def test_one_character_over_the_maximum_is_refused(self):
        q = self.question(harvest.MAX_QUESTION_LEN + 1)
        self.assertEqual(harvest.extract_question(f"<h2>{q}</h2>"), "")

    def test_the_first_qualifying_h2_wins(self):
        html = ("<h2>Metainformação</h2>"
                "<h2>Quantos médicos existem?</h2>"
                "<h2>Outra pergunta diferente?</h2>")
        self.assertEqual(harvest.extract_question(html),
                         "Quantos médicos existem?")


class PeriodBoundaryTest(unittest.TestCase):
    def elements(self, first, last):
        return (f'<div class="YearCurrentText">{last}</div>'
                f'<div class="YearOtherText">{first}</div>')

    def test_the_earliest_and_latest_allowed_years_pass(self):
        self.assertEqual(
            harvest.extract_period(
                self.elements(harvest.EARLIEST_YEAR, harvest.LATEST_YEAR)),
            (str(harvest.EARLIEST_YEAR), str(harvest.LATEST_YEAR)))

    def test_a_year_below_the_floor_is_dropped(self):
        got = harvest.extract_period(
            self.elements(harvest.EARLIEST_YEAR - 1, 2006))
        self.assertEqual(got, ("", ""))       # only one year survives

    def test_a_year_above_the_ceiling_is_dropped(self):
        got = harvest.extract_period(
            self.elements(1991, harvest.LATEST_YEAR + 1))
        self.assertEqual(got, ("", ""))

    def test_year_elements_take_precedence_over_the_option_picker(self):
        html = (self.elements(1991, 2006)
                + '<option value="2019">2019</option>'
                + '<option value="2020">2020</option>')
        self.assertEqual(harvest.extract_period(html), ("1991", "2006"))

    def test_the_picker_is_used_when_there_are_no_year_elements(self):
        html = ('<option value="2019">a</option>'
                '<option value="2024">b</option>')
        self.assertEqual(harvest.extract_period(html), ("2019", "2024"))


class RefutedPremiseTest(unittest.TestCase):
    """A conclusion its own data disproved, repeated in five places.

    `data/spikes/europa-period.md` opened with "Neither appears on
    europa" directly above a table counting 4 year elements and 26-30
    picker options on all three sampled pages — a hardcoded literal in
    `render()`, so the probe regenerated it. `data/audits/` is exempt:
    an audit report recording what *was* true is a dated record, not a
    live claim."""

    # `europa` as the subject, not merely nearby: A4's docstring says
    # years appeared "on every sampled portugal and europa page and on
    # **neither** municipios page", which is about municipios and true.
    PATTERN = re.compile(r"europa\b\s*(?:does|has|is|uses)?\s*,?\s*"
                         r"\*{0,2}neither\b", re.I)

    def test_no_live_document_says_europa_has_neither_mechanism(self):
        root = pathlib.Path(__file__).resolve().parents[1]
        for path in list(root.glob("*.md")) + list(
                (root / "scripts").glob("*.py")) + list(
                (root / "data" / "spikes").glob("*.md")):
            text = path.read_text(encoding="utf-8", errors="replace")
            self.assertIsNone(
                self.PATTERN.search(text),
                f"{path.name} still says europa has neither period "
                "mechanism; the spike's own table refutes it")


class SpikeCorrectionTest(unittest.TestCase):
    """A spike report older than the code it describes needs saying so.

    Three did. `a6-page-inventory.md` records "none matched" for a
    selector fixed seven minutes after the report was written;
    `a3-coverage-fields.md` records a marker count of 0 that was a false
    negative from matching a literal against entity-encoded HTML;
    `europa-period.md` opened with a conclusion its own table refuted.
    A stale spike is not harmless — each of these propagated into
    CLAUDE.md or a roadmap item as a settled fact."""

    STALE = {
        "a6-page-inventory.md": "the h2 selector was fixed after this ran",
        "a3-coverage-fields.md": "the marker count was a false negative",
        "europa-period.md": "the opening sentence contradicted its table",
    }

    def test_each_known_stale_report_carries_a_correction(self):
        root = pathlib.Path(__file__).resolve().parents[1] / "data" / "spikes"
        for name, why in self.STALE.items():
            path = root / name
            if not path.exists():
                continue
            self.assertIn(
                "Correction", path.read_text(encoding="utf-8")[:2000],
                f"{name} is known stale ({why}) and carries no correction")

    def test_the_list_names_reports_that_exist(self):
        root = pathlib.Path(__file__).resolve().parents[1] / "data" / "spikes"
        for name in self.STALE:
            self.assertTrue((root / name).exists(), name)
