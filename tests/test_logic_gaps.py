"""Targeted tests for the logic functions mutation testing found thinnest.

Not every survivor is worth killing: `parse()`'s are almost all
equivalent mutants — `decode("utf-8")` versus `decode()`, `"UTF-8"`
versus `"utf-8"`, `split(x, 1)` versus `rsplit(x, 1)` on a string
containing one occurrence, `[-1]` versus `[+1]` on a two-element list.
Chasing those means asserting behaviour nothing depends on. These are the
ones where a surviving mutant means a real hole.
"""

import pathlib
import unittest
import unittest.mock

from helpers import PT, RepoCase, load_script, record

lib = load_script("pordata_lib")
build = load_script("build_catalogue")
featured = load_script("fetch_featured_sets")
diff = load_script("diff_sitemap")


class ExtractNamesTest(unittest.TestCase):
    """A quadro name is a line repeated within the next two lines. The
    length floor is the part mutants kept slipping past."""

    @staticmethod
    def page(*lines):
        return "".join(f"<div>{l}</div>" for l in lines)

    def test_a_repeated_name_is_picked_up(self):
        html = self.page("Taxa de natalidade bruta", "Taxa de natalidade bruta")
        self.assertIn("Taxa de natalidade bruta", featured.extract_names(html))

    def test_a_name_at_the_length_floor_is_kept(self):
        # norm() length exactly 10 passes; the check is `< 10`
        name = "Abcdefghij"
        self.assertEqual(len(featured.norm(name)), 10)
        self.assertIn(name, featured.extract_names(self.page(name, name)))

    def test_one_character_under_the_floor_is_dropped(self):
        name = "Abcdefghi"
        self.assertEqual(len(featured.norm(name)), 9)
        self.assertEqual(featured.extract_names(self.page(name, name)), [])

    def test_a_lowercase_line_is_not_a_name(self):
        line = "taxa de natalidade bruta"
        self.assertEqual(featured.extract_names(self.page(line, line)), [])

    def test_a_line_that_never_repeats_is_not_a_name(self):
        html = self.page("Taxa de natalidade bruta", "Outra coisa qualquer",
                         "Mais uma linha diferente")
        self.assertEqual(featured.extract_names(html), [])

    def test_a_repeat_three_lines_later_is_too_far(self):
        html = self.page("Taxa de natalidade bruta", "a", "b",
                         "Taxa de natalidade bruta")
        self.assertEqual(featured.extract_names(html), [])

    def test_a_rejected_line_does_not_stop_the_scan(self):
        # `continue` mutated to `break` would lose everything after a
        # short line, which is why a rejected line comes first here
        html = self.page("curto", "Taxa de natalidade bruta",
                         "Taxa de natalidade bruta")
        self.assertIn("Taxa de natalidade bruta", featured.extract_names(html))

    def test_the_same_name_in_two_places_is_reported_once(self):
        # four identical lines would trigger the subtitle-absorption path
        # instead, so the repeats are separated by another pair
        html = self.page("Taxa de natalidade bruta", "Taxa de natalidade bruta",
                         "Outra linha diferente", "Outra linha diferente",
                         "Taxa de natalidade bruta", "Taxa de natalidade bruta")
        self.assertEqual(
            featured.extract_names(html).count("Taxa de natalidade bruta"), 1)

    def test_a_name_repeated_as_the_final_lines_does_not_crash(self):
        # regression: the length guard sat after norm(lines[i + 2]), which
        # Python evaluates before it can short-circuit, so a page ending on
        # a repeated name raised IndexError and took the whole extraction
        # down rather than yielding one fewer name
        html = self.page("Primeira linha qualquer",
                         "Taxa de natalidade bruta", "Taxa de natalidade bruta")
        self.assertIn("Taxa de natalidade bruta", featured.extract_names(html))

    def test_the_subtitle_line_is_absorbed_when_the_pattern_repeats(self):
        html = self.page("Energias renovaveis totais", "Consumo final bruto",
                         "Energias renovaveis totais", "Consumo final bruto")
        self.assertEqual(featured.extract_names(html),
                         ["Energias renovaveis totais — Consumo final bruto"])

    def test_a_footnote_marker_is_not_absorbed_as_a_subtitle(self):
        html = self.page("Taxa de natalidade bruta", "(1)",
                         "Taxa de natalidade bruta", "(1)")
        self.assertEqual(featured.extract_names(html),
                         ["Taxa de natalidade bruta"])

    def test_a_trailing_footnote_marker_is_trimmed(self):
        html = self.page("Taxa de natalidade bruta (1)",
                         "Taxa de natalidade bruta (1)")
        self.assertIn("Taxa de natalidade bruta", featured.extract_names(html))


class TargetsTest(RepoCase):
    """Which sitemap URLs count as indicator pages."""

    def write(self, *urls):
        path = pathlib.Path("data/sitemap-urls.txt")
        path.write_text("\n".join(urls) + "\n", encoding="utf-8")
        return lib.targets(path)

    def test_each_statistical_area_is_included(self):
        got = self.write(f"{PT}/portugal/a-1", f"{PT}/municipios/b-2",
                         f"{PT}/europa/c-3")
        self.assertEqual(len(got), 3)

    def test_a_non_area_path_is_excluded(self):
        self.assertEqual(
            self.write(f"{PT}/tema/portugal/populacao-1",
                       f"{PT}/glossario", f"{PT}/"), [])

    def test_the_english_tree_is_excluded(self):
        self.assertEqual(self.write(f"{PT}/en/portugal/birth+rate-99"), [])

    def test_summary_tables_are_excluded(self):
        self.assertEqual(
            self.write(f"{PT}/municipios/quadro+resumo/abrantes-828209"), [])

    def test_a_url_without_a_numeric_id_is_excluded(self):
        self.assertEqual(self.write(f"{PT}/portugal/sem+id"), [])

    def test_the_id_must_end_the_url(self):
        self.assertEqual(self.write(f"{PT}/portugal/a-1/extra"), [])


class ShortTest(unittest.TestCase):
    def test_drops_the_host(self):
        self.assertEqual(diff.short(f"{PT}/portugal/taxa-1"),
                         "portugal/taxa-1")

    def test_a_url_without_the_host_is_returned_whole(self):
        self.assertEqual(diff.short("portugal/taxa-1"), "portugal/taxa-1")

    def test_only_the_first_occurrence_splits(self):
        self.assertEqual(diff.short(f"{PT}/x/www.pordata.pt/y"),
                         "x/www.pordata.pt/y")


class ResolveFeaturedEdgeTest(RepoCase):
    """The matcher reads a committed featured.json; these are the shapes
    that file can take when something upstream went wrong."""

    def write_featured(self, payload):
        pathlib.Path("data/catalogue").mkdir(parents=True, exist_ok=True)
        import json
        pathlib.Path("data/catalogue/featured.json").write_text(
            json.dumps(payload), encoding="utf-8")

    def test_a_group_with_no_names_key_yields_nothing(self):
        self.write_featured({"quadro_resumo_europa": {}})
        self.write_records([record("europa/a-1", 1, "europa", "Alfa")])
        flags, stats = build.resolve_featured(lib.load_records())
        self.assertEqual(flags, {})

    def test_an_absent_featured_file_is_not_an_error(self):
        self.write_records([record("europa/a-1", 1, "europa", "Alfa")])
        flags, stats = build.resolve_featured(lib.load_records())
        self.assertEqual(flags, {})

    def test_error_records_are_never_matched(self):
        self.write_featured({"quadro_resumo_europa": {
            "indicator_names": ["Indice de Gini"]}})
        self.write_records([
            record("europa/gini-300", 300, "europa", "Indice de Gini",
                   error="HTTP 500")])
        flags, _ = build.resolve_featured(lib.load_records())
        self.assertEqual(flags, {})

    def test_a_record_without_a_name_is_never_matched(self):
        self.write_featured({"quadro_resumo_europa": {
            "indicator_names": ["Indice de Gini"]}})
        self.write_records([record("europa/gini-300", 300, "europa", "")])
        flags, _ = build.resolve_featured(lib.load_records())
        self.assertEqual(flags, {})

    def test_a_record_in_another_area_is_never_matched(self):
        self.write_featured({"quadro_resumo_europa": {
            "indicator_names": ["Indice de Gini"]}})
        self.write_records([
            record("portugal/gini-300", 300, "portugal", "Indice de Gini")])
        flags, _ = build.resolve_featured(lib.load_records())
        self.assertEqual(flags, {})

    def test_an_exact_name_match_flags_the_row(self):
        self.write_featured({"quadro_resumo_europa": {
            "indicator_names": ["Indice de Gini"]}})
        self.write_records([
            record("europa/gini-300", 300, "europa", "Indice de Gini")])
        flags, stats = build.resolve_featured(lib.load_records())
        self.assertEqual(flags, {("europa", 300): ["quadro_resumo"]})
        self.assertEqual(stats["quadro_resumo_europa"]["matched"], 1)


class IndicatorUrlTest(unittest.TestCase):
    """One definition, shared by the harvester and the sitemap diff.

    diff_sitemap used to carry a looser copy — a numeric id and nothing
    else — which counted 3,661 non-indicator URLs as indicator updates.
    """

    def test_each_statistical_area_qualifies(self):
        for area in ("portugal", "municipios", "europa"):
            self.assertTrue(lib.is_indicator_url(f"{PT}/{area}/nome-123"), area)

    def test_the_english_tree_never_qualifies(self):
        self.assertFalse(lib.is_indicator_url(f"{PT}/en/portugal/name-123"))

    def test_summary_tables_never_qualify(self):
        self.assertFalse(
            lib.is_indicator_url(f"{PT}/municipios/quadro+resumo/abrantes-8282"))

    def test_a_non_area_path_never_qualifies(self):
        for url in (f"{PT}/tema/portugal/populacao-1", f"{PT}/academia/x-1",
                    f"{PT}/glossario-1"):
            self.assertFalse(lib.is_indicator_url(url), url)

    def test_the_numeric_id_must_end_the_url(self):
        self.assertFalse(lib.is_indicator_url(f"{PT}/portugal/nome-123/extra"))
        self.assertFalse(lib.is_indicator_url(f"{PT}/portugal/nome"))

    def test_targets_and_the_predicate_cannot_disagree(self):
        # the drift this consolidation exists to prevent
        import pathlib
        urls = [f"{PT}/portugal/a-1", f"{PT}/en/portugal/a-1",
                f"{PT}/municipios/quadro+resumo/x-2", f"{PT}/tema/x-3",
                f"{PT}/europa/b-4", f"{PT}/municipios/c-5"]
        with unittest.mock.patch.object(
                lib.pathlib.Path, "read_text",
                return_value="\n".join(urls)):
            picked = lib.targets(pathlib.Path("anything"))
        self.assertEqual(picked, [u for u in urls if lib.is_indicator_url(u)])


class WorksheetKeyTest(RepoCase):
    def test_a_stats_dict_missing_keys_skips_rather_than_crashes(self):
        self.write_records([record("europa/a-1", 1, "europa", "Alfa")])
        build.write_unmatched_worksheet(
            lib.load_records(), {"quadro_resumo_europa": {}})
        self.assertTrue(
            pathlib.Path("data/catalogue/FEATURED-UNMATCHED.md").exists())

    def test_an_unknown_total_is_shown_rather_than_raised(self):
        self.write_records([record("europa/a-1", 1, "europa", "Alfa")])
        build.write_unmatched_worksheet(lib.load_records(), {
            "quadro_resumo_europa": {"unmatched": ["Sem par"]}})
        text = pathlib.Path(
            "data/catalogue/FEATURED-UNMATCHED.md").read_text(encoding="utf-8")
        self.assertIn("Sem par", text)
