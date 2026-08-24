"""The crosswalk's filters, each pinned to the match it was added to stop.

Every filter here exists because it was a wrong answer first, so the
tests are written as those wrong answers: the assertion is that the
specific bad pairing no longer survives. A filter that stops nothing is
a filter nobody can justify keeping.

The other half is the shape of what is stored. `crosswalk: null` is a
result, not a gap, and `candidates` is a set with evidence rather than a
winner — the invariants that keep it honest (exact titles first, stored
ids a superset of the exact ones, size never used to refuse) are
asserted directly.
"""

import json
import pathlib
import unittest
from unittest import mock

from helpers import RepoCase, load_script

x = load_script("build_crosswalk")


def entry(title, geo="Município", theme="População",
          source="INE, Censos", subtheme="X", ident="0001",
          periodicity="Anual"):
    return {
        "id": ident, "title": title, "tokens": x.content_tokens(title),
        "head": x.head(title), "derivation": x.derivation_markers(title),
        "unit": x.unit_markers(x.trailing_unit(title)),
        "negations": x.negations(title), "geo": geo,
        "periodicity": periodicity, "source": source,
        "theme": theme, "subtheme": subtheme,
    }


def row(name, area="municipios", rid=1, **extra):
    return {"name": name, "area": area, "id": rid,
            "fontes": ["INE"], **extra}


def family_for(name, titles, area="municipios", **kwargs):
    entries = [entry(t, ident=f"{i:07d}", **kwargs)
               for i, t in enumerate(titles)]
    return x.candidates(row(name, area=area), entries, x.build_index(entries))


class TokenisingTest(unittest.TestCase):
    def test_accents_and_case_are_flattened(self):
        self.assertEqual(x.content_tokens("Água Distribuída"),
                         x.content_tokens("agua distribuida"))

    def test_stopwords_and_short_words_are_dropped(self):
        self.assertEqual(x.content_tokens("Casamentos por sexo"),
                         {"casamentos", "sexo"})

    def test_head_is_the_first_content_word(self):
        self.assertEqual(x.head("Total de casamentos dissolvidos"),
                         "casamentos")

    def test_head_of_an_empty_phrase_is_none(self):
        self.assertIsNone(x.head("  de e  "))

    def test_numbers_are_kept_however_short(self):
        """Age brackets are numbers. Dropping them let "População
        residente com 16 a 64 anos" match "…com menos de 15 anos"."""
        self.assertEqual(x.content_tokens("População com 16 a 64 anos"),
                         {"populacao", "16", "64", "anos"})

    def test_an_age_bracket_must_be_the_same_bracket(self):
        entries = [entry("População residente com menos de 15 anos (N.º)")]
        got = x.candidates(row("População residente com 16 a 64 anos"),
                           entries, x.build_index(entries))
        self.assertEqual(got, [])

    def test_order_survives_deduplication(self):
        self.assertEqual(x.ordered_tokens("casamentos e casamentos civis"),
                         ["casamentos", "civis"])


class DerivationTest(unittest.TestCase):
    def test_a_rate_and_a_count_do_not_agree(self):
        self.assertNotEqual(x.derivation_markers("Água distribuída"),
                            x.derivation_markers("Água distribuída por habitante"))

    def test_the_unit_suffix_is_not_a_word_marker(self):
        """INE suffixes the unit and PORDATA carries it in a separate
        field, so reading `%` out of the title gave every INE rate a
        marker its counterpart could not have — "Taxa de desemprego" was
        refused against "Taxa de desemprego (Série 2021 - %)"."""
        self.assertEqual(x.derivation_markers("Taxa de desemprego"),
                         x.derivation_markers("Taxa de desemprego (%)"))

    def test_per_mil_and_per_thousand_are_the_same_marker(self):
        self.assertEqual(x.derivation_markers("Óbitos por mil habitantes"),
                         x.derivation_markers("Óbitos por 1000 habitantes"))

    def test_plain_por_is_not_a_derivation(self):
        """"por sexo" is a breakdown, which is the one-to-many shape
        itself — treating it as a derivation would refuse the families
        this crosswalk exists to record."""
        self.assertEqual(x.derivation_markers("Casamentos por sexo"), set())


    def test_a_word_marker_is_read_from_the_phrase(self):
        self.assertIn("proporcao",
                      x.derivation_markers("Proporção de casamentos"))
        self.assertEqual(x.derivation_markers("Casamentos"), set())


class UnitMarkerTest(unittest.TestCase):
    """The unit, read from wherever each side happens to write it."""

    def test_pordata_writes_the_symbol_in_its_unit_field(self):
        self.assertEqual(x.unit_markers("Taxa - %"), {"pct"})

    def test_ine_writes_it_in_the_title_suffix(self):
        self.assertEqual(x.unit_markers(
            x.trailing_unit("Taxa de desemprego (Série 2021 - %)")), {"pct"})

    def test_permille_is_named_and_distinct(self):
        """Named, not merely different from `%`: comparing two marked
        strings passes whatever the marker is called."""
        self.assertEqual(x.unit_markers("Taxa - ‰"), {"permil"})
        self.assertNotIn("permil", x.unit_markers("Taxa - %"))

    def test_a_count_carries_no_rate_marker(self):
        self.assertEqual(x.unit_markers("N.º"), set())

    def test_a_missing_unit_is_empty_not_an_error(self):
        self.assertEqual(x.unit_markers(None), set())
        self.assertEqual(x.unit_markers(""), set())

    def test_a_title_with_no_suffix_has_no_unit(self):
        self.assertEqual(x.trailing_unit("Poder de compra per capita"), "")

    def test_the_suffix_is_returned_without_its_parentheses(self):
        self.assertEqual(x.trailing_unit("Casamentos (N.º)"), "N.º")

    def test_a_long_suffix_is_still_read_for_its_symbol(self):
        """INE writes the vintage into the same parenthesis. The 12-char
        cap that keeps a breakdown from passing as an exact title cannot
        see "(Série 2021 - %)", so the symbol read uses its own rule."""
        self.assertEqual(
            x.unit_markers(x.trailing_unit("Taxa (Série 2021 - %)")),
            {"pct"})

    def test_a_breakdown_suffix_is_still_not_a_unit_for_title_equality(self):
        self.assertNotEqual(
            x.normalised_title("Casamentos (Entre pessoas de sexo oposto)"),
            x.normalised_title("Casamentos"))


class UnitParityTest(unittest.TestCase):
    """Compared only when PORDATA has a unit to compare with."""

    def family(self, name, titles, unit=None):
        entries = [entry(t, ident=f"{i:07d}") for i, t in enumerate(titles)]
        r = row(name)
        if unit:
            r["unit"] = unit
        return [e["title"] for e in
                x.candidates(r, entries, x.build_index(entries))]

    def test_a_declared_percentage_excludes_the_count(self):
        got = self.family("Casamentos católicos",
                          ["Casamentos católicos (%)",
                           "Casamentos católicos (N.º)"],
                          unit="Proporção - %")
        self.assertEqual(got, ["Casamentos católicos (%)"])

    def test_a_declared_count_excludes_the_percentage(self):
        got = self.family("Casamentos católicos",
                          ["Casamentos católicos (%)",
                           "Casamentos católicos (N.º)"],
                          unit="Casamento")
        self.assertEqual(got, ["Casamentos católicos (N.º)"])

    def test_with_no_unit_both_stay_in_the_family(self):
        """The unit is recorded on 270 of 839 in-scope rows. Requiring
        parity regardless would refuse every row that simply has none —
        and both series genuinely belong to the family, with the exact
        title leading it."""
        got = self.family("Casamentos católicos",
                          ["Casamentos católicos (%)",
                           "Casamentos católicos (N.º)"])
        self.assertEqual(len(got), 2)

    def test_the_word_marker_still_separates_them_without_a_unit(self):
        """"Proporção (%) de casamentos" says in words what the unit says
        in symbols, so the count/rate split survives a missing unit."""
        got = self.family("Casamentos católicos",
                          ["Proporção (%) de casamentos católicos",
                           "Casamentos católicos (N.º)"])
        self.assertEqual(got, ["Casamentos católicos (N.º)"])


class NegationTest(unittest.TestCase):
    def test_negations_are_detected(self):
        self.assertEqual(x.negations("Alojamentos não clássicos"), {"nao"})

    def test_a_word_containing_a_negation_is_not_one(self):
        self.assertEqual(x.negations("Naogueira semanal"), set())


class GeoTest(unittest.TestCase):
    def test_a_municipal_question_needs_a_municipal_series(self):
        self.assertTrue(x.geo_ok("municipios", "Município"))
        self.assertTrue(x.geo_ok("municipios", "Freguesia"))
        self.assertFalse(x.geo_ok("municipios", "NUTS II"))

    def test_a_national_question_accepts_any_level(self):
        """`geo_lastlevel` is the *finest* level INE publishes, so a
        municipal series still answers a national question — filtering
        portugal by level dropped 196 rows to nothing when it was tried."""
        for level in ("Portugal", "Município", "Freguesia", "NUTS III"):
            self.assertTrue(x.geo_ok("portugal", level))


class FilterRegressionTest(unittest.TestCase):
    """One test per wrong match that put a filter in the code."""

    def test_full_containment_stops_the_common_word_slipping_through(self):
        """"Dimensão média das empresas" matched "Dimensão média das
        famílias clássicas" while only rare tokens had to be present."""
        got = family_for("Dimensão média das empresas",
                         ["Dimensão média das famílias clássicas (N.º)",
                          "Dimensão média das empresas (N.º)"])
        self.assertEqual([e["title"] for e in got],
                         ["Dimensão média das empresas (N.º)"])

    def test_the_ine_head_must_be_a_word_pordata_used(self):
        """"População residente com idade entre 16 e 89 anos" matched
        "Tempo de acesso a pé da população residente…". Only this
        direction is checked: full containment already guarantees
        PORDATA's head is present, so the mirror test was dead code."""
        got = family_for("População residente",
                         ["Tempo de acesso a pé da população residente (min)",
                          "População residente (N.º)"])
        self.assertEqual([e["title"] for e in got], ["População residente (N.º)"])

    def test_a_rate_is_not_a_count(self):
        got = family_for("Água distribuída",
                         ["Água distribuída por habitante (m³/ hab.)",
                          "Água distribuída (m³)"])
        self.assertEqual([e["title"] for e in got], ["Água distribuída (m³)"])

    def test_a_negated_series_is_a_different_series(self):
        got = family_for("Alojamentos familiares clássicos",
                         ["Alojamentos familiares não clássicos (N.º)",
                          "Alojamentos familiares clássicos (N.º)"])
        self.assertEqual([e["title"] for e in got],
                         ["Alojamentos familiares clássicos (N.º)"])

    def test_geography_filters_a_municipal_row(self):
        got = family_for("População residente",
                         ["População residente (N.º)"], geo="NUTS II")
        self.assertEqual(got, [])

    def test_nothing_credible_returns_an_empty_family(self):
        self.assertEqual(family_for("Habitantes por bombeiro",
                                    ["Óbitos por causas de morte (N.º)"]), [])


class CategoryPrefixTest(unittest.TestCase):
    """PORDATA's colon prefix, and the case where taking it off is wrong.

    Colon prefixes are 6x over-represented among refusals — 15.5% of the
    633, against 2.4% of matches — because INE names the indicator alone
    and full containment cannot forgive a word the title never had. But
    a colon does not always mean a category, so the tests that matter
    are the ones where the rule has to decline.
    """

    def heads(self, *names):
        return x.category_heads([{"name": n} for n in names])

    def test_a_repeated_head_is_a_category(self):
        """Measured, not listed: `sns` heads 20 rows, `cinema` 14,
        `administrações públicas` 13. A hand-written vocabulary would be
        one more thing to maintain and would miss the next one."""
        got = self.heads("Cinema: ecrãs", "Cinema: sessões", "Óbitos: total")
        self.assertIn("cinema", got)

    def test_a_head_that_appears_once_is_the_indicator(self):
        """"Densidade populacional: estatísticas por município" has the
        indicator in front and boilerplate behind. Taking the tail would
        throw the indicator away."""
        got = self.heads("Densidade populacional: estatísticas por município",
                         "Cinema: ecrãs", "Cinema: sessões")
        self.assertNotIn("densidade populacional", got)

    def test_the_threshold_is_two(self):
        self.assertEqual(x.MIN_CATEGORY_ROWS, 2)

    def test_a_category_is_split_off(self):
        got = x.split_category("SNS: internamentos nos hospitais", {"sns"})
        self.assertEqual(got, ("internamentos nos hospitais", "SNS"))

    def test_a_phrase_with_no_colon_passes_through(self):
        self.assertEqual(x.split_category("Casamentos", {"sns"}),
                         ("Casamentos", ""))

    def test_an_unrepeated_head_passes_through_whole(self):
        phrase = "Densidade populacional: estatísticas por município"
        self.assertEqual(x.split_category(phrase, {"sns"}), (phrase, ""))

    def test_a_contentless_tail_is_a_breakdown_not_an_indicator(self):
        """"População residente: total" and "Pessoal ao serviço nas
        empresas: total" both have heads repeated often enough to look
        like categories, and both *lost* their match before this guard
        existed — `total` is a stopword, so the phrase reduced to
        nothing to match on."""
        phrase = "População residente: total"
        self.assertEqual(x.split_category(phrase, {"populacao residente"}),
                         (phrase, ""))

    def test_the_accent_stripped_head_is_what_is_compared(self):
        got = x.split_category("Espetáculos ao vivo: sessões",
                               {"espetaculos ao vivo"})
        self.assertEqual(got[0], "sessões")

    def test_phrase_of_applies_it_only_when_categories_are_given(self):
        """`phrase_of` is called in places that have no catalogue to
        derive categories from; it must not guess there."""
        row = {"name": "SNS: internamentos nos hospitais"}
        self.assertEqual(x.phrase_of(row), "SNS: internamentos nos hospitais")
        self.assertEqual(x.phrase_of(row, {"sns"}),
                         "internamentos nos hospitais")

    def test_the_category_reaches_the_entry_as_evidence(self):
        """A reader should be able to see that "SNS" was set aside before
        the titles were compared."""
        entries = [entry("Internamentos (N.º) nos hospitais")]
        rows = [row("SNS: internamentos nos hospitais", rid=1),
                row("SNS: partos nos hospitais", rid=2)]
        crosswalk, stats = x.build(rows, entries)
        self.assertEqual(crosswalk["municipios/1"]["category"], "SNS")
        self.assertEqual(stats["decategorised"], 1)
        self.assertEqual(stats["categories"], 1)

    def test_a_row_with_no_category_carries_no_category_key(self):
        entries = [entry("Casamentos (N.º)")]
        crosswalk, _ = x.build([row("Casamentos", rid=1)], entries)
        self.assertNotIn("category", crosswalk["municipios/1"])


class FamilyOrderTest(unittest.TestCase):
    def test_exact_titles_lead_the_family(self):
        """Stored candidates are truncated, so the order decides what
        survives: a worse candidate must never displace a better one."""
        got = family_for("Casamentos", [
            "Casamentos celebrados entre pessoas do sexo oposto (N.º)",
            "Casamentos (N.º)",
        ])
        self.assertEqual(got[0]["title"], "Casamentos (N.º)")

    def test_ties_break_on_title_so_runs_are_reproducible(self):
        titles = ["Casamentos civis (N.º)", "Casamentos católicos (N.º)"]
        first = [e["title"] for e in family_for("Casamentos", titles)]
        second = [e["title"] for e in family_for("Casamentos", titles[::-1])]
        self.assertEqual(first, second)

    def test_a_broad_indicator_keeps_its_whole_family(self):
        """Size is reported, never used to refuse: a 62-entry family is
        INE genuinely publishing 62 series, not a matcher failure."""
        titles = [f"Casamentos {n} (N.º)" for n in range(80)]
        self.assertEqual(len(family_for("Casamentos", titles)), 80)


class SummaryTest(unittest.TestCase):
    def build(self, name, titles, **kwargs):
        entries = [entry(t, ident=f"{i:07d}", **kwargs)
                   for i, t in enumerate(titles)]
        r = row(name)
        fam = x.candidates(r, entries, x.build_index(entries))
        return x.entry_summary(r, fam)

    def test_exact_ids_are_a_subset_of_the_stored_candidates(self):
        """Otherwise a reader meets an id in `exact_title` that is not in
        `candidates` — which happened until the family was ordered."""
        titles = [f"Casamentos {n} (N.º)" for n in range(40)] + \
                 ["Casamentos (N.º)"]
        got = self.build("Casamentos", titles)
        self.assertLessEqual(set(got["exact_title"]), set(got["candidates"]))

    def test_truncation_is_declared_and_the_true_size_kept(self):
        got = self.build("Casamentos",
                         [f"Casamentos {n} (N.º)" for n in range(40)])
        self.assertTrue(got["truncated"])
        self.assertEqual(len(got["candidates"]), x.MAX_STORED)
        self.assertEqual(got["n_candidates"], 40)

    def test_a_small_family_is_not_marked_truncated(self):
        got = self.build("Casamentos", ["Casamentos (N.º)"])
        self.assertFalse(got["truncated"])
        self.assertEqual(got["n_candidates"], 1)

    def test_an_exact_title_raises_confidence(self):
        self.assertEqual(
            self.build("Casamentos", ["Casamentos (N.º)"])["confidence"],
            "exact")

    def test_containment_without_an_exact_title_is_only_a_family(self):
        self.assertEqual(
            self.build("Casamentos",
                       ["Casamentos celebrados (N.º)"])["confidence"],
            "family")

    def test_the_trailing_unit_does_not_block_an_exact_match(self):
        """INE suffixes the unit and PORDATA never does, so "(N.º)" would
        otherwise make every exact title inexact."""
        self.assertEqual(x.normalised_title("Casamentos (N.º)"),
                         x.normalised_title("Casamentos"))

    def test_theme_and_operation_shares_are_reported_not_enforced(self):
        """A share below 1.0 is information for a reader, not grounds to
        refuse: INE files the same series under two themes, and refusing
        on that dropped exact matches like "Poder de compra per capita"."""
        entries = [entry("Casamentos (N.º)", theme="População", ident="1"),
                   entry("Casamentos (N.º)", theme="Saúde", ident="2")]
        r = row("Casamentos")
        got = x.entry_summary(r, x.candidates(r, entries,
                                              x.build_index(entries)))
        self.assertEqual(got["theme_share"], 0.5)
        self.assertEqual(got["n_candidates"], 2)


class ScopeTest(unittest.TestCase):
    def test_ine_sourced_portugal_and_municipios_are_in_scope(self):
        for area in ("portugal", "municipios"):
            self.assertTrue(x.in_scope(row("x", area=area)))

    def test_europa_is_out_of_scope(self):
        """Eurostat has not been measured, and A5's shape must not be
        assumed to carry over."""
        self.assertFalse(x.in_scope(row("x", area="europa")))

    def test_a_row_with_no_ine_source_is_out_of_scope(self):
        self.assertFalse(x.in_scope({"area": "portugal",
                                     "fontes": ["DGEEC - algo"]}))

    def test_a_qualified_ine_source_still_counts(self):
        """PORDATA writes "INE (a partir de 2016)" when a series breaks."""
        self.assertTrue(x.in_scope({"area": "portugal",
                                    "fontes": ["INE (a partir de 2016)"]}))

    def test_a_row_with_no_sources_is_out_of_scope(self):
        self.assertFalse(x.in_scope({"area": "portugal"}))

    def test_the_breakdown_clause_is_not_part_of_the_phrase(self):
        """`split_breakdown` already demoted the tail; matching on it
        would ask INE for a slicing instruction."""
        self.assertEqual(x.phrase_of({"title": "Casamentos",
                                      "name": "Casamentos – total e por sexo"}),
                         "Casamentos")

    def test_a_row_with_no_title_falls_back_to_the_name(self):
        self.assertEqual(x.phrase_of({"name": "Casamentos"}), "Casamentos")


class BuildTest(unittest.TestCase):
    def setUp(self):
        self.entries = [entry("Casamentos (N.º)", ident="0000001"),
                        entry("Óbitos (N.º)", ident="0000002")]

    def test_a_refusal_is_recorded_as_null_not_omitted(self):
        """An absent key and a null are different claims: null says the
        row was considered and nothing credible was found."""
        rows = [row("Habitantes por bombeiro", rid=7)]
        crosswalk, stats = x.build(rows, self.entries)
        self.assertIn("municipios/7", crosswalk)
        self.assertIsNone(crosswalk["municipios/7"])
        self.assertEqual(stats["refused"], 1)

    def test_out_of_scope_rows_get_no_key_at_all(self):
        rows = [row("Casamentos", area="europa", rid=9)]
        crosswalk, stats = x.build(rows, self.entries)
        self.assertEqual(crosswalk, {})
        self.assertEqual(stats["in_scope"], 0)

    def test_the_key_carries_the_area_because_ids_repeat_across_them(self):
        rows = [row("Casamentos", area="portugal", rid=3),
                row("Casamentos", area="municipios", rid=3)]
        crosswalk, _stats = x.build(rows, self.entries)
        self.assertEqual(sorted(crosswalk), ["municipios/3", "portugal/3"])

    def test_counts_add_up_to_the_rows_in_scope(self):
        rows = [row("Casamentos", rid=1), row("Nada de nada", rid=2)]
        _crosswalk, stats = x.build(rows, self.entries)
        self.assertEqual(stats["matched"] + stats["refused"],
                         stats["in_scope"])
        self.assertEqual(stats["exact"] + stats["family"], stats["matched"])


class ReportTest(unittest.TestCase):
    def stats(self):
        rows = [row("Casamentos", rid=1), row("Nada de nada", rid=2)]
        entries = [entry("Casamentos (N.º)")]
        return x.build(rows, entries)[1]

    def test_qa_reports_both_halves_of_the_split(self):
        text = x.qa_report(self.stats())
        self.assertIn("**1**", text)
        self.assertIn("refused", text)
        self.assertIn("matched", text)

    def test_qa_says_size_is_never_a_refusal(self):
        self.assertIn("never used to refuse", x.qa_report(self.stats()))

    def test_review_lists_the_refusals(self):
        self.assertIn("Nada de nada", x.review_report(self.stats()))

    def test_review_survives_having_nothing_to_review(self):
        empty = {"refusals": [], "sizes": [], "in_scope": 0, "matched": 0,
                 "refused": 0, "exact": 0, "family": 0}
        self.assertIn("0 rows", x.review_report(empty))

    def test_qa_survives_an_empty_run(self):
        empty = {"refusals": [], "sizes": [], "in_scope": 0, "matched": 0,
                 "refused": 0, "exact": 0, "family": 0}
        self.assertIn("**0**", x.qa_report(empty))


class LoadTest(unittest.TestCase):
    """The CSV INE actually publishes, not a dict literal."""

    HEADER = ("id,dates,description,geo_lastlevel,html,json,keywords,"
              "periodicity,source,subtheme,theme,title,update_type,varcd\n")

    def load(self, body):
        import pathlib as pl
        import tempfile
        tmp = tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False,
                                          encoding="utf-8")
        tmp.write(self.HEADER + body)
        tmp.close()
        self.addCleanup(pl.Path(tmp.name).unlink)
        return x.load_ine(pl.Path(tmp.name))

    def test_a_row_becomes_a_prepared_entry(self):
        got = self.load('0000764,d,desc,Município,h,j,k,Anual,'
                        '"INE, Censos",Água,Ambiente,Água captada (m³),A,0000764\n')
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["id"], "0000764")
        self.assertEqual(got[0]["geo"], "Município")
        self.assertEqual(got[0]["theme"], "Ambiente")

    def test_tokens_and_markers_are_derived_at_load(self):
        """Derived once for 13,084 entries rather than per comparison —
        and asserted here so a field renamed upstream fails loudly rather
        than quietly matching nothing."""
        got = self.load('1,d,desc,Portugal,h,j,k,Anual,s,sub,tema,'
                        'Água distribuída por habitante (m³),A,1\n')[0]
        self.assertIn("agua", got["tokens"])
        self.assertEqual(got["head"], "agua")
        self.assertIn("per", got["derivation"])

    def test_an_empty_catalogue_loads_as_an_empty_list(self):
        self.assertEqual(self.load(""), [])


class EmptyPhraseTest(unittest.TestCase):
    def test_a_row_with_no_content_words_refuses(self):
        """Nothing to contain means nothing can be contained: without the
        guard the token intersection is over an empty sequence."""
        entries = [entry("Casamentos (N.º)")]
        self.assertEqual(
            x.candidates(row("de e a"), entries, x.build_index(entries)), [])

    def test_a_row_whose_words_appear_nowhere_refuses(self):
        entries = [entry("Casamentos (N.º)")]
        self.assertEqual(
            x.candidates(row("bombeiros"), entries, x.build_index(entries)), [])


class MainTest(RepoCase):
    """The three files it writes, and that they agree with each other."""

    HEADER = ("id,dates,description,geo_lastlevel,html,json,keywords,"
              "periodicity,source,subtheme,theme,title,update_type,varcd\n")

    def setUp(self):
        super().setUp()
        pathlib.Path("docs/data").mkdir(parents=True)
        pathlib.Path("docs/data/catalogue.json").write_text(json.dumps([
            {"area": "municipios", "id": 1, "name": "Casamentos",
             "fontes": ["INE"]},
            {"area": "municipios", "id": 2, "name": "Habitantes por bombeiro",
             "fontes": ["INE"]},
            {"area": "europa", "id": 3, "name": "Casamentos",
             "fontes": ["Eurostat"]},
        ]), encoding="utf-8")
        pathlib.Path("ine.csv").write_text(
            self.HEADER + '0000001,d,desc,Município,h,j,k,Anual,'
            '"INE, Censos",Casamentos,População,Casamentos (N.º),A,1\n',
            encoding="utf-8")
        for name, value in (("CATALOGUE", "docs/data/catalogue.json"),
                            ("INE_CSV", "ine.csv"),
                            ("OUT_JSON", "out/ine.json"),
                            ("OUT_QA", "out/QA.md"),
                            ("OUT_REVIEW", "out/REVIEW.md")):
            patch = mock.patch.object(x, name, pathlib.Path(value))
            patch.start()
            self.addCleanup(patch.stop)
        with mock.patch("builtins.print"):
            x.main()
        self.written = json.loads(
            pathlib.Path("out/ine.json").read_text(encoding="utf-8"))

    def test_the_output_directory_is_created(self):
        """OUT_JSON's parent does not exist on a fresh checkout."""
        self.assertTrue(pathlib.Path("out/ine.json").exists())

    def test_a_match_and_a_refusal_both_appear(self):
        self.assertIsNotNone(self.written["municipios/1"])
        self.assertIsNone(self.written["municipios/2"])

    def test_the_out_of_scope_row_is_absent(self):
        self.assertNotIn("europa/3", self.written)

    def test_keys_are_sorted_so_the_diff_is_readable(self):
        """This file is committed on every harvest; unstable key order
        would make every rebuild look like a change."""
        self.assertEqual(list(self.written), sorted(self.written))

    def test_the_reports_are_written_alongside(self):
        self.assertIn("in scope",
                      pathlib.Path("out/QA.md").read_text(encoding="utf-8"))
        self.assertIn("Habitantes por bombeiro",
                      pathlib.Path("out/REVIEW.md").read_text(encoding="utf-8"))


class StrictTest(RepoCase):
    """The floor, and that it only fires when asked."""

    def setUp(self):
        super().setUp()
        pathlib.Path("docs/data").mkdir(parents=True)
        pathlib.Path("docs/data/catalogue.json").write_text(
            json.dumps([{"area": "portugal", "id": 1, "name": "Nada",
                         "fontes": ["INE"]}]), encoding="utf-8")
        pathlib.Path("ine.csv").write_text(
            "id,dates,description,geo_lastlevel,html,json,keywords,"
            "periodicity,source,subtheme,theme,title,update_type,varcd\n",
            encoding="utf-8")
        for name, value in (("CATALOGUE", "docs/data/catalogue.json"),
                            ("INE_CSV", "ine.csv"), ("OUT_JSON", "o/i.json"),
                            ("OUT_QA", "o/QA.md"), ("OUT_REVIEW", "o/R.md")):
            patch = mock.patch.object(x, name, pathlib.Path(value))
            patch.start()
            self.addCleanup(patch.stop)

    def run_main(self, *argv):
        import sys
        old = sys.argv
        sys.argv = ["build_crosswalk.py", *argv]
        try:
            with mock.patch("builtins.print"):
                x.main()
            return 0
        except SystemExit as exit_info:
            return exit_info.code
        finally:
            sys.argv = old

    def test_zero_matches_breaches_the_floor_under_strict(self):
        self.assertEqual(self.run_main("--strict"), 1)

    def test_the_same_run_is_silent_without_strict(self):
        """The floor is a CI gate, not a reason a local rebuild fails —
        and the files are still written either way."""
        self.assertEqual(self.run_main(), 0)
        self.assertTrue(pathlib.Path("o/i.json").exists())

    def test_the_floor_leaves_margin_below_the_measurement(self):
        """192 matched when this was written. A floor at the measurement
        turns any rewording upstream into a red harvest."""
        self.assertLess(x.MIN_MATCHED, 192)
        self.assertGreater(x.MIN_MATCHED, 100)


class MedianTest(unittest.TestCase):
    def test_odd_length(self):
        self.assertEqual(x.median([3, 1, 2]), 2)

    def test_even_length_averages_the_middle_pair(self):
        self.assertEqual(x.median([1, 2, 3, 4]), 2.5)

    def test_empty_is_zero_not_an_error(self):
        self.assertEqual(x.median([]), 0.0)


if __name__ == "__main__":
    unittest.main()
