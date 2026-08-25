"""The Eurostat matcher, written as the wrong answers it refuses.

Every rule here was a bad pairing before it was a rule, so each test
names the pairing rather than the rule: `Exports total and by type of
energy product` is not `Exports by industry (FIGARO application)`, and
the assertion is that it no longer survives.

The second half is the honesty of what is stored. This crosswalk cannot
verify a breakdown — the cached catalogue carries titles, not dimension
names — so `filter_resolved` must be false on every entry, and a large
candidate set must not read like the INE crosswalk's family, where size
was never a reason to doubt.
"""

import json
import pathlib
import unittest
from unittest import mock

from helpers import RepoCase, load_script

x = load_script("build_eurostat_crosswalk")


def dataset(title, code="D1", themes="Economy", start="2000", end="2020"):
    head, tail = x.split_tail(title, x.EUROSTAT_TAIL)
    return {
        "code": code, "title": title, "themes": themes, "theme_count": "1",
        "data_start": start, "data_end": end, "values": "1",
        "head": x.norm_title(head), "tail_tokens": x.tokens(tail),
        "tsv_url": x.TSV_TEMPLATE.format(code=code),
        "browser_url": x.BROWSER_TEMPLATE.format(code=code),
        "last_update": "", "last_structure_change": "",
    }


def row(name_en, ident=1, unit="", area="europa", fontes=("Eurostat",)):
    return {"id": ident, "area": area, "name_en": name_en,
            "name": name_en, "unit": unit, "fontes": list(fontes)}


class ScopeTest(unittest.TestCase):
    def test_a_europa_row_citing_eurostat_is_in_scope(self):
        self.assertTrue(x.in_scope(row("Crude divorce rate")))

    def test_portugal_belongs_to_the_ine_crosswalk(self):
        self.assertFalse(x.in_scope(row("X", area="portugal")))

    def test_a_row_with_no_english_name_has_nothing_to_match(self):
        """The catalogue is entirely English; matching a Portuguese name
        against it would be guessing across a translation gap."""
        never = row("X")
        never["name_en"] = ""
        self.assertFalse(x.in_scope(never))

    def test_a_europa_row_not_citing_eurostat_is_out_of_scope(self):
        self.assertFalse(x.in_scope(row("X", fontes=("OCDE", "PORDATA"))))

    def test_the_source_is_matched_on_the_organisation_not_the_qualifier(self):
        self.assertTrue(x.in_scope(row("X", fontes=("Eurostat - LFS 2024",))))


class UnitTest(unittest.TestCase):
    """PORDATA writes the unit into a trailing parenthetical and Eurostat
    carries it as a dimension of the cube, so the word is never in the
    title. `percentage` alone blocked 35 rows."""

    def test_a_unit_parenthetical_is_stripped(self):
        self.assertEqual(x.strip_unit("Area under organic farming (percentage)"),
                         "Area under organic farming")

    def test_a_period_parenthetical_is_stripped(self):
        self.assertEqual(x.strip_unit("Financial aid to students (1999 2011)"),
                         "Financial aid to students")

    def test_a_unit_and_a_period_together_are_both_stripped(self):
        self.assertEqual(x.strip_unit("Employment (2004 2020) (percentage)"),
                         "Employment")

    def test_an_acronym_in_parentheses_is_part_of_the_concept(self):
        """`(BMI)`, `(COFOG)` and `(LULUCF)` name the thing measured. A
        rule that stripped any trailing parenthetical would delete
        them, which is why the units are listed rather than inferred."""
        for keep in ("Obesity rate by body mass index (BMI)",
                     "General government expenditure by function (COFOG)"):
            self.assertEqual(x.strip_unit(keep), keep)


class SplitTest(unittest.TestCase):
    def test_pordata_opens_its_breakdown_with_total_and_by(self):
        head, tail = x.split_tail("Activity rate total and by sex",
                                  x.PORDATA_TAIL)
        self.assertEqual(head, "Activity rate")
        self.assertEqual(tail, "total and by sex")

    def test_pordata_also_opens_it_with_a_bare_by(self):
        """`Obesity rate by body mass index` has no "total and", so a
        split that required one would miss the breakdown entirely."""
        head, _tail = x.split_tail("Obesity rate by body mass index",
                                   x.PORDATA_TAIL)
        self.assertEqual(head, "Obesity rate")

    def test_eurostat_lists_its_dimensions_after_by(self):
        head, tail = x.split_tail(
            "Unemployment by sex, age and metropolitan region",
            x.EUROSTAT_TAIL)
        self.assertEqual(head, "Unemployment")
        self.assertIn("sex", tail)

    def test_a_title_with_no_breakdown_keeps_all_of_itself(self):
        head, tail = x.split_tail("Crude divorce rate", x.PORDATA_TAIL)
        self.assertEqual(head, "Crude divorce rate")
        self.assertEqual(tail, "")


class MatchTest(unittest.TestCase):
    """The head is matched exactly, and the breakdown may only veto."""

    @staticmethod
    def match(name, titles, unit=""):
        index = x.build_index([dataset(t, code=f"D{n}")
                               for n, t in enumerate(titles)])
        return x.candidates(row(name, unit=unit), index)

    def test_an_exact_head_is_matched(self):
        found, _tail, _vetoed = self.match("Crude divorce rate",
                                         ["Crude divorce rate"])
        self.assertEqual([d["code"] for d in found], ["D0"])

    def test_the_unit_is_stripped_before_the_head_is_compared(self):
        found, _t, _v = self.match("Area under organic farming (percentage)",
                                 ["Area under organic farming"])
        self.assertTrue(found)

    def test_a_breakdown_on_one_side_only_is_not_a_contradiction(self):
        """A cube whose title names no dimension may still carry the one
        PORDATA wants; there is no offline way to know. Refusing on
        silence would refuse the exact matches."""
        found, _t, vetoed = self.match("Prisoners total and by sex",
                                     ["Prisoners"])
        self.assertTrue(found)
        self.assertFalse(vetoed)

    def test_two_breakdowns_sharing_no_word_are_not_the_same_slice(self):
        """`Exports total and by type of energy product` is not `Exports
        by industry (FIGARO application)` — the pairing this veto was
        added to stop."""
        found, _t, vetoed = self.match(
            "Exports total and by type of energy product",
            ["Exports by industry (FIGARO application)"])
        self.assertEqual(found, [])
        self.assertTrue(vetoed)

    def test_expenditure_by_category_is_not_expenditure_by_function(self):
        found, _t, _v = self.match(
            "General government expenditure by category (euro)",
            ["General government expenditure by function (COFOG)"])
        self.assertEqual(found, [])

    def test_an_overlapping_breakdown_survives(self):
        found, _t, _v = self.match("Activity rate total and by sex",
                                 ["Activity rate by sex"])
        self.assertTrue(found)

    def test_the_veto_prunes_within_a_set_rather_than_dropping_it(self):
        found, _t, vetoed = self.match(
            "Activity rate total and by sex",
            ["Activity rate by sex", "Activity rate by age"])
        self.assertEqual([d["code"] for d in found], ["D0"])
        self.assertFalse(vetoed)

    def test_a_head_that_matches_nothing_is_not_a_veto(self):
        """Never finding a head and rejecting every candidate are
        different facts, and the review file separates them."""
        found, _t, vetoed = self.match("Something Eurostat never names",
                                     ["Crude divorce rate"])
        self.assertEqual(found, [])
        self.assertFalse(vetoed)

    def test_a_short_head_is_not_refused_for_being_short(self):
        """A content-token floor was the first guard against a generic
        head and it deleted this pairing, whose titles are identical.
        Length is not the failure; contradiction is."""
        found, _t, _v = self.match("Obesity rate by body mass index",
                                 ["Obesity rate by body mass index (BMI)"])
        self.assertTrue(found)

    def test_a_digit_is_content(self):
        """A two-character floor on tokens swallowed age brackets in the
        INE matcher; the same floor here would drop `65` from a
        breakdown and let the veto pass on nothing."""
        self.assertIn("65", x.tokens("population aged 65"))


class EntryTest(unittest.TestCase):
    def summary(self, name, titles, unit=""):
        family = [dataset(t, code=f"D{n}") for n, t in enumerate(titles)]
        _head, tail = x.split_tail(x.strip_unit(name), x.PORDATA_TAIL)
        return x.entry_summary(row(name, unit=unit), family, tail)

    def test_an_identical_title_is_recorded_as_exact(self):
        got = self.summary("Crude divorce rate", ["Crude divorce rate"])
        self.assertEqual(got["confidence"], "exact")
        self.assertEqual(got["exact_title"], ["D0"])

    def test_one_candidate_without_an_identical_title_is_single(self):
        got = self.summary("Prisoners total and by sex", ["Prisoners"])
        self.assertEqual(got["confidence"], "single")

    def test_rival_cubes_are_a_family_with_the_choice_deferred(self):
        got = self.summary("Activity rate",
                           ["Activity rate by sex", "Activity rate by age"])
        self.assertEqual(got["confidence"], "family")
        self.assertEqual(got["n_candidates"], 2)

    def test_the_breakdown_is_stored_unresolved(self):
        """The whole point. The catalogue has no dimension names, so
        whether the cube can be sliced this way is unknown until item 14
        fetches its structure."""
        got = self.summary("Activity rate total and by sex",
                           ["Activity rate by sex"])
        self.assertEqual(got["filter"], "total and by sex")
        self.assertIs(got["filter_resolved"], False)

    def test_an_entry_with_no_breakdown_still_says_it_is_unresolved(self):
        got = self.summary("Crude divorce rate", ["Crude divorce rate"])
        self.assertIs(got["filter_resolved"], False)

    def test_a_long_set_is_truncated_and_says_so(self):
        titles = [f"Population by dimension {n}" for n in range(x.MAX_STORED + 5)]
        got = self.summary("Population", titles)
        self.assertEqual(len(got["candidates"]), x.MAX_STORED)
        self.assertTrue(got["truncated"])
        self.assertEqual(got["n_candidates"], x.MAX_STORED + 5)

    def test_the_exact_list_never_names_a_code_outside_the_stored_set(self):
        """A reader must not meet a code in one list and not the other."""
        titles = [f"Population by dimension {n}" for n in range(x.MAX_STORED + 5)]
        titles[-1] = "Population"
        got = self.summary("Population", titles)
        self.assertEqual(got["exact_title"], [])
        self.assertEqual(got["n_exact"], 1)

    def test_whole_family_statistics_ignore_the_stored_cap(self):
        """`period` was computed over `family[:MAX_STORED]` while every
        other whole-family figure used `family` — so europa/2970, with 73
        candidates, published a span narrower than its own set."""
        wide = [dataset(f"Population by dimension {n}", code=f"D{n}",
                        start=str(1990 + n), end=str(2000 + n))
                for n in range(x.MAX_STORED + 5)]
        _head, tail = x.split_tail("Population", x.PORDATA_TAIL)
        got = x.entry_summary(row("Population"), wide, tail)
        self.assertEqual(got["n_candidates"], x.MAX_STORED + 5)
        self.assertIn(f"{1990 + x.MAX_STORED + 4}-{2000 + x.MAX_STORED + 4}",
                      got["period"])

    def test_the_pordata_unit_is_named_as_pordatas(self):
        """It sat here as plain `unit` and the detail page rendered it
        between the Eurostat theme and period, so the panel headed "where
        the numbers come from" showed our own field as upstream."""
        _head, tail = x.split_tail("Crude divorce rate", x.PORDATA_TAIL)
        got = x.entry_summary(row("Crude divorce rate", unit="Taxa"),
                              [dataset("Crude divorce rate")], tail)
        self.assertEqual(got["wanted_unit"], "Taxa")
        self.assertNotIn("unit", got)

    def test_titles_are_stored_and_urls_are_not(self):
        """URLs are the code in a template — measured across all 7,572
        datasets — so storing them per candidate repeats the template."""
        got = self.summary("Crude divorce rate", ["Crude divorce rate"])
        self.assertEqual(got["titles"], {"D0": "Crude divorce rate"})
        self.assertNotIn("tsv_urls", got)
        self.assertNotIn("browser_urls", got)


class BuildTest(unittest.TestCase):
    def test_a_refusal_is_stored_as_null_not_omitted(self):
        """`null` is a result — this row was looked at and no dataset
        claimed — where a missing key would read as never examined."""
        crosswalk, stats = x.build(
            [row("Nothing Eurostat publishes", ident=7)],
            [dataset("Crude divorce rate")])
        self.assertIn("europa/7", crosswalk)
        self.assertIsNone(crosswalk["europa/7"])
        self.assertEqual(stats["refused"], 1)

    def test_an_out_of_scope_row_is_absent_entirely(self):
        crosswalk, stats = x.build([row("X", ident=7, area="portugal")],
                                   [dataset("X")])
        self.assertEqual(crosswalk, {})
        self.assertEqual(stats["in_scope"], 0)

    def test_a_veto_is_counted_apart_from_a_missing_head(self):
        crosswalk, stats = x.build(
            [row("Exports total and by type of energy product", ident=1),
             row("Nothing Eurostat publishes", ident=2)],
            [dataset("Exports by industry (FIGARO application)")])
        self.assertEqual(stats["refused"], 2)
        self.assertEqual(stats["vetoed"], 1)
        self.assertEqual(len(stats["refusals"]), 1)


class ReportTest(unittest.TestCase):
    """The figures a reader depends on, not the prose around them.

    Roughly four of every five surviving mutants in this project's
    report writers are markdown labels; asserting the wording pins the
    sentence rather than the claim."""

    @staticmethod
    def built(names, titles):
        return x.build([row(n, ident=i) for i, n in enumerate(names)],
                       [dataset(t, code=f"D{i}")
                        for i, t in enumerate(titles)])

    def test_the_qa_report_states_the_coverage_it_measured(self):
        _cross, stats = self.built(
            ["Crude divorce rate", "Nothing Eurostat publishes"],
            ["Crude divorce rate"])
        got = x.qa_report(stats)
        self.assertIn("English name): **2**", got)
        self.assertIn("at least one dataset: **1** (50.0%)", got)
        self.assertIn("indicator's): **1** (100.0%)", got)

    def test_the_qa_report_separates_the_veto_from_the_refusals(self):
        _cross, stats = self.built(
            ["Exports total and by type of energy product"],
            ["Exports by industry (FIGARO application)"])
        self.assertIn("**1** found a head", x.qa_report(stats))

    def test_the_qa_report_counts_the_unresolved_filters(self):
        """The number that says how much of this crosswalk is a
        question rather than an answer."""
        _cross, stats = self.built(["Activity rate total and by sex"],
                                   ["Activity rate by sex"])
        self.assertIn("**1** of 1", x.qa_report(stats))

    def test_the_qa_report_survives_an_empty_build(self):
        """Division by the scope, which is zero before anything is in
        it — a report that raises here hides why the build was empty."""
        _cross, stats = x.build([], [])
        self.assertIn("**0**", x.qa_report(stats))

    def test_the_review_report_lists_both_kinds_of_refusal(self):
        _cross, stats = self.built(
            ["Exports total and by type of energy product",
             "Nothing Eurostat publishes"],
            ["Exports by industry (FIGARO application)"])
        got = x.review_report(stats)
        self.assertIn("Exports total and by type of energy product", got)
        self.assertIn("Nothing Eurostat publishes", got)

    def test_the_review_report_says_how_many_it_did_not_list(self):
        _cross, stats = self.built(
            [f"Concept {n} Eurostat never names"
             for n in range(x.REVIEW_SAMPLE + 3)],
            ["Crude divorce rate"])
        self.assertIn("3 more", x.review_report(stats))


class MedianTest(unittest.TestCase):
    def test_an_odd_count_takes_the_middle(self):
        self.assertEqual(x.median([3, 1, 2]), 2.0)

    def test_an_even_count_averages_the_two_middles(self):
        self.assertEqual(x.median([1, 2, 3, 4]), 2.5)

    def test_no_candidates_is_zero_not_a_crash(self):
        self.assertEqual(x.median([]), 0.0)


class LoadTest(RepoCase):
    HEADER = ("code,title,themes,theme_count,last_update,"
              "last_structure_change,data_start,data_end,values,"
              "tsv_url,sdmx_url,browser_url\n")

    def write(self, code="D1", tsv=None, browser=None):
        path = pathlib.Path("data/eurostat/datasets.csv")
        path.parent.mkdir(parents=True, exist_ok=True)
        tsv = x.TSV_TEMPLATE.format(code=code) if tsv is None else tsv
        browser = (x.BROWSER_TEMPLATE.format(code=code)
                   if browser is None else browser)
        path.write_text(
            self.HEADER + f"{code},A title,Economy,1,,,2000,2020,1,"
            f"{tsv},,{browser}\n", encoding="utf-8")
        return path

    def test_the_catalogue_is_read_and_annotated(self):
        got = x.load_eurostat(self.write())
        self.assertEqual(got[0]["head"], "a title")

    def test_an_empty_catalogue_refuses_rather_than_routing_nothing(self):
        path = pathlib.Path("data/eurostat/datasets.csv")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.HEADER, encoding="utf-8")
        with self.assertRaises(SystemExit):
            x.load_eurostat(path)

    def test_a_url_that_leaves_the_template_stops_the_build(self):
        """Entries store codes and consumers build routes from them, so a
        changed pattern would turn every stored candidate into a dead
        link rather than an error."""
        with self.assertRaises(SystemExit) as caught:
            x.load_eurostat(self.write(tsv="https://elsewhere/D1.tsv"))
        self.assertIn("URL templates", str(caught.exception))


class GateTest(RepoCase):
    def test_a_collapsed_build_refuses_to_overwrite_the_crosswalk(self):
        out = pathlib.Path("data/crosswalk/eurostat.json")
        with mock.patch.object(x, "load_eurostat",
                               return_value=[dataset("Nothing")]), \
                mock.patch.object(
                    pathlib.Path, "read_text",
                    return_value=json.dumps([row("Crude divorce rate")])), \
                mock.patch("builtins.print"):
            with self.assertRaises(SystemExit):
                x.main()
        self.assertFalse(out.exists())

    def test_a_healthy_build_writes_all_three_files(self):
        rows = [row(f"Concept {n}", ident=n) for n in range(x.MIN_MATCHED)]
        datasets = [dataset(f"Concept {n}", code=f"D{n}")
                    for n in range(x.MIN_MATCHED)]
        with mock.patch.object(x, "load_eurostat", return_value=datasets), \
                mock.patch.object(pathlib.Path, "read_text",
                                  return_value=json.dumps(rows)), \
                mock.patch("builtins.print"):
            x.main()
        for name in ("eurostat.json", "EUROSTAT-QA.md", "EUROSTAT-REVIEW.md"):
            self.assertTrue(pathlib.Path("data/crosswalk", name).exists(), name)

    def test_the_floor_sits_under_the_measured_run(self):
        """118 rows route today. The gate catches a collapse, not a
        wobble, so it is set under that rather than at it."""
        self.assertLess(x.MIN_MATCHED, 118)
        self.assertGreater(x.MIN_MATCHED, 50)


class ShippedTest(unittest.TestCase):
    """The committed crosswalk, read as a reader meets it."""

    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(
            pathlib.Path("data/crosswalk/eurostat.json").read_text("utf-8"))

    def test_every_key_is_a_europa_row(self):
        self.assertTrue(all(k.startswith("europa/") for k in self.data))

    def test_no_entry_claims_a_resolved_filter(self):
        for key, entry in self.data.items():
            if entry:
                self.assertIs(entry["filter_resolved"], False, key)

    def test_the_stored_set_always_contains_its_exact_titles(self):
        for key, entry in self.data.items():
            if entry:
                self.assertTrue(
                    set(entry["exact_title"]) <= set(entry["candidates"]), key)

    def test_refusals_are_present_as_null(self):
        self.assertTrue(any(v is None for v in self.data.values()))


if __name__ == "__main__":
    unittest.main()
