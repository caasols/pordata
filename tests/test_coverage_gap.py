"""Where PORDATA is thin against INE (roadmap 16).

The item's own warning is the thing to defend against here: the scarce
asset is the curation, not the numbers, so a report that enumerates
rather than selects would be a regression dressed as progress. These
tests pin the three decisions that keep it a selection — ranking by
distinct indicators rather than series, collapsing a concept written
twice, and refusing to compute the series-level complement at all — plus
the honesty of what the report says about itself.
"""

import json
import pathlib
import unittest
from unittest import mock

from helpers import RepoCase, load_script

g = load_script("coverage_gap")
x = load_script("build_crosswalk")


def entry(title, theme="População", subtheme="Censos", geo="Portugal",
          ident="0001"):
    return {"id": ident, "title": title, "tokens": x.content_tokens(title),
            "head": x.head(title), "derivation": x.derivation_markers(title),
            "unit": x.unit_markers(x.trailing_unit(title)),
            "negations": x.negations(title), "geo": geo,
            "periodicity": "Anual", "source": "INE, Censos",
            "theme": theme, "subtheme": subtheme}


def repeated(title, times, **kwargs):
    """One INE indicator republished across geographies — the shape that
    inflates a series count without adding anything to say."""
    return [entry(title, ident=f"{i:07d}", **kwargs) for i in range(times)]


class VocabularyTest(unittest.TestCase):
    def test_it_reads_every_name_field(self):
        got = g.pordata_vocabulary([{"name": "Casamentos",
                                     "name_en": "Marriages",
                                     "breakdown": "por sexo",
                                     "title": "Casamentos"}])
        self.assertLessEqual({"casamentos", "marriages", "sexo"}, got)

    def test_the_description_is_deliberately_excluded(self):
        """96.3% of descriptions are the SEO template with the name
        substituted in, so they widen the vocabulary with nothing the
        name did not already say — and a word that only ever appears in
        boilerplate would mask a real gap."""
        got = g.pordata_vocabulary([{"name": "Casamentos",
                                     "description": "Conheça as estatísticas "
                                                    "atualizadas de tumores"}])
        self.assertNotIn("tumores", got)

    def test_it_accumulates_across_rows(self):
        """A gap is a word *no* indicator uses, so the vocabulary is the
        union over 2,195 rows. Assigning instead of accumulating would
        leave only the last row's words and report almost everything
        PORDATA has as missing."""
        got = g.pordata_vocabulary([{"name": "Casamentos"},
                                    {"name": "Divórcios"},
                                    {"name": "Nascimentos"}])
        self.assertLessEqual({"casamentos", "divorcios", "nascimentos"}, got)

    def test_a_row_with_only_a_title_still_contributes(self):
        """`title` is `name` with the breakdown clause split off, and a
        row can carry one without the other."""
        self.assertIn("casamentos",
                      g.pordata_vocabulary([{"title": "Casamentos"}]))

    def test_a_row_with_no_names_contributes_nothing(self):
        self.assertEqual(g.pordata_vocabulary([{}]), set())


class AbsentConceptTest(unittest.TestCase):
    def concepts(self, entries, vocab=frozenset(), floor=2):
        return g.absent_concepts(entries, set(vocab), min_series=floor)

    def test_a_word_pordata_uses_is_not_a_gap(self):
        got = self.concepts(repeated("Casamentos católicos", 4),
                            vocab={"casamentos", "catolicos"})
        self.assertEqual(got, [])

    def test_a_word_pordata_never_uses_is_reported(self):
        got = self.concepts(repeated("Tumores malignos", 4),
                            vocab={"outra"})
        self.assertTrue(got)
        self.assertIn(got[0]["token"], {"tumores", "malignos"})

    def test_the_floor_drops_the_long_tail(self):
        entries = repeated("Tumores malignos", 3)
        self.assertEqual(self.concepts(entries, floor=4), [])
        self.assertTrue(self.concepts(entries, floor=3))

    def test_bare_numbers_are_not_concepts(self):
        got = self.concepts(repeated("Casamentos 2021", 4))
        self.assertNotIn("2021", [c["token"] for c in got])

    def test_ranking_is_by_distinct_indicators_not_series(self):
        """INE republishes one title across geographies. "TDT" carries 54
        series and is a single indicator repeated; ranking by series put
        it near the top of the shortlist, and ranking by distinct title
        drops it out — which is the correct answer for a list about where
        PORDATA is thin."""
        entries = (repeated("Assinantes de TDT", 30)
                   + [entry(f"Horas trabalhadas no setor {n}", ident=f"h{n}")
                      for n in range(9)])
        ranked = [c["token"] for c in self.concepts(entries)]
        # the repeated title carries 30 series and one indicator; the
        # nine distinct ones carry nine of each
        self.assertEqual(ranked[0], "horas")

    def test_series_count_is_still_reported(self):
        """The report shows both: distinct indicators is the ranking, the
        series count is how widely INE cut them."""
        got = self.concepts(repeated("Tumores malignos", 5))[0]
        self.assertEqual(got["series"], 5)
        self.assertEqual(got["titles"], 1)

    def test_examples_are_distinct_titles(self):
        """The naive slice printed the same sentence three times, which
        teaches a reader nothing about the concept."""
        entries = (repeated("Assinantes de televisão", 6)
                   + [entry("Televisão digital em casa", ident="z")])
        got = self.concepts(entries)[0]
        self.assertEqual(len(set(got["examples"])), len(got["examples"]))

    def test_the_dominant_subtheme_is_recorded(self):
        entries = repeated("Tumores malignos", 4, theme="Saúde",
                           subtheme="Mortalidade")
        got = self.concepts(entries)[0]
        self.assertEqual(got["theme"], "Saúde / Mortalidade")
        self.assertEqual(got["theme_share"], 1.0)


class SynonymTest(unittest.TestCase):
    def test_a_concept_written_twice_takes_one_slot(self):
        """"tumor" and "maligno" carry the same titles and are one
        concept. A slot spent on the second word of a phrase is a slot
        not spent on the next gap. Which of two exact synonyms survives
        is arbitrary but deterministic — the sort decides — so the claim
        is that one does, not which."""
        got = g.absent_concepts(repeated("Tumores malignos", 4), set(),
                                min_series=2)
        self.assertEqual(len(got), 1)
        self.assertIn(got[0]["token"], {"tumores", "malignos"})

    def test_the_collapsed_words_are_recorded_not_lost(self):
        """Which of two exact synonyms survives is arbitrary, so the
        entry has to carry the other: "aparelho" alone is half a phrase.
        """
        got = g.absent_concepts(repeated("Tumores malignos", 4), set(),
                                min_series=2)
        self.assertEqual(len(got[0]["also"]), 1)
        self.assertNotEqual(got[0]["also"][0], got[0]["token"])

    def test_a_partly_overlapping_concept_survives(self):
        """Overlap has to be near-total to collapse: "tumores" spans both
        groups here and "circulatorio" spans one, so they are two
        subjects and both keep their slot."""
        entries = (repeated("Tumores malignos", 4)
                   + [entry(f"Doenças do aparelho circulatório {n}",
                            ident=f"b{n}") for n in range(6)])
        tokens = [c["token"] for c in
                  g.absent_concepts(entries, set(), min_series=2)]
        self.assertEqual(len(tokens), 2)
        self.assertTrue({"aparelho", "circulatorio", "doencas"} & set(tokens))
        self.assertTrue({"tumores", "malignos"} & set(tokens))

    def test_the_helper_key_never_reaches_the_output(self):
        """`_titles` is a working set, not part of the record — it would
        not survive json.dumps."""
        got = g.absent_concepts(repeated("Tumores malignos", 4), set(),
                                min_series=2)
        for concept in got:
            self.assertNotIn("_titles", concept)
        json.dumps(got)


class AnnotationTest(unittest.TestCase):
    def test_bookkeeping_is_flagged_rather_than_deleted(self):
        """The filter is a judgement about what counts as a subject, so
        the report has to be able to show it — a silently cleaner list is
        a list nobody can contest."""
        got = g.absent_concepts(repeated("Empresas (Série antiga)", 4),
                                set(), min_series=2)
        flagged = [c for c in got if c["annotation"]]
        self.assertTrue(flagged)

    def test_the_vintage_and_adjustment_vocabulary_is_covered(self):
        for word in ("serie", "cae", "sazonalidade", "calendario",
                     "trimestral", "deflacionado"):
            with self.subTest(word):
                self.assertIn(word, g.ANNOTATION)

    def test_a_real_subject_is_not_annotation(self):
        for word in ("tumores", "inovacao", "horas", "encomendas"):
            with self.subTest(word):
                self.assertNotIn(word, g.ANNOTATION)


class ReachTest(unittest.TestCase):
    def test_it_counts_the_ids_the_crosswalk_actually_names(self):
        crosswalk = {"a": {"candidates": ["1", "2"]},
                     "b": {"candidates": ["2", "3"]},
                     "c": None}
        got = g.crosswalk_reach(crosswalk, 10)
        self.assertEqual(got["named_ids"], 3)
        self.assertEqual(got["share"], 0.3)

    def test_an_empty_catalogue_is_not_a_divide_by_zero(self):
        self.assertEqual(g.crosswalk_reach({}, 0)["share"], 0.0)


class ReportTest(unittest.TestCase):
    def setUp(self):
        entries = (repeated("Tumores malignos do estômago", 9, theme="Saúde",
                            subtheme="Mortalidade")
                   + repeated("Empresas (Série antiga)", 9))
        self.concepts = g.absent_concepts(entries, set(), min_series=8)
        self.reach = {"named_ids": 1062, "total_series": 13084, "share": 0.0812}
        self.text = g.report(self.concepts, self.reach, 2687, 2195)

    def test_it_says_the_series_complement_is_not_computable(self):
        """The most dangerous version of this report is the one that
        subtracts 1,062 from 13,084 and calls the remainder a gap."""
        self.assertIn("not computable", self.text)
        self.assertIn("8.1%", self.text)

    def test_it_calls_itself_a_selection(self):
        self.assertIn("selection, not an inventory", self.text)
        self.assertIn("curation", self.text)

    def test_it_shows_what_the_annotation_filter_removed(self):
        self.assertIn("What was filtered out", self.text)
        self.assertIn("`antiga`", self.text)

    def test_a_subject_appears_under_its_theme(self):
        self.assertIn("Saúde / Mortalidade", self.text)
        self.assertIn("estômago", self.text)

    def test_bookkeeping_stays_out_of_the_shortlist_itself(self):
        shortlist = self.text.split("## What was filtered out")[0]
        self.assertNotIn("`antiga`", shortlist)


class MainTest(RepoCase):
    def setUp(self):
        super().setUp()
        pathlib.Path("docs/data").mkdir(parents=True)
        pathlib.Path("docs/data/catalogue.json").write_text(
            json.dumps([{"area": "portugal", "id": 1, "name": "Casamentos",
                         "name_en": "Marriages", "fontes": ["INE"]}]),
            encoding="utf-8")
        pathlib.Path("cw.json").write_text(
            json.dumps({"portugal/1": {"candidates": ["0000001"]}}),
            encoding="utf-8")
        entries = repeated("Tumores malignos do estômago", 9)
        for name, value in (("CATALOGUE", "docs/data/catalogue.json"),
                            ("CROSSWALK", "cw.json"),
                            ("OUT_JSON", "out/gap.json"),
                            ("OUT_REPORT", "out/GAP.md")):
            patch = mock.patch.object(g, name, pathlib.Path(value))
            patch.start()
            self.addCleanup(patch.stop)
        loader = mock.patch.object(g.xw, "load_ine", return_value=entries)
        loader.start()
        self.addCleanup(loader.stop)
        with mock.patch("builtins.print"):
            g.main()

    def test_both_outputs_are_written(self):
        self.assertTrue(pathlib.Path("out/gap.json").exists())
        self.assertTrue(pathlib.Path("out/GAP.md").exists())

    def test_the_json_carries_the_reach_it_refuses_to_subtract(self):
        got = json.loads(pathlib.Path("out/gap.json").read_text(
            encoding="utf-8"))
        self.assertEqual(got["crosswalk_reach"]["named_ids"], 1)
        self.assertEqual(got["crosswalk_reach"]["total_series"], 9)
        self.assertGreater(got["pordata_vocabulary"], 0)

    def test_a_word_from_the_catalogue_is_not_in_the_gap(self):
        got = json.loads(pathlib.Path("out/gap.json").read_text(
            encoding="utf-8"))
        self.assertNotIn("casamentos", [c["token"] for c in got["concepts"]])


if __name__ == "__main__":
    unittest.main()
