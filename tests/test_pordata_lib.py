import json
import pathlib
import unittest

from helpers import RepoCase, load_script, record

lib = load_script("pordata_lib")


class TargetsTest(RepoCase):
    def test_targets_filters_corpus(self):
        urls = lib.targets()
        self.assertEqual(len(urls), 3)
        self.assertTrue(all("/en/" not in u for u in urls))
        self.assertTrue(all("quadro+resumo" not in u for u in urls))
        self.assertTrue(all("/tema/" not in u for u in urls))

    def test_lastmods_parses_tsv(self):
        pathlib.Path("data/sitemap-lastmod.tsv").write_text(
            "https://a\t2026-01-01\nhttps://b\t\n", encoding="utf-8")
        mods = lib.lastmods()
        self.assertEqual(mods["https://a"], "2026-01-01")
        self.assertEqual(mods["https://b"], "")

    def test_lastmods_missing_file(self):
        pathlib.Path("data/sitemap-lastmod.tsv").unlink()
        self.assertEqual(lib.lastmods(), {})


class RecordsTest(RepoCase):
    def test_roundtrip_and_dedupe_keeps_last(self):
        a1 = record("portugal/x-1", 1, "portugal", "Old")
        a2 = record("portugal/x-1", 1, "portugal", "New")
        b = record("europa/y-2", 2, "europa", "B")
        pathlib.Path("data/catalogue/pages.jsonl").write_text(
            json.dumps(a1) + "\nnot json\n" + json.dumps(b) + "\n"
            + json.dumps(a2) + "\n", encoding="utf-8")
        records = lib.load_records()
        self.assertEqual(len(records), 2)
        self.assertEqual(records[a1["url"]]["name"], "New")
        lib.write_records(records)
        again = lib.load_records()
        self.assertEqual(again.keys(), records.keys())

    def test_load_records_missing_file(self):
        self.assertEqual(lib.load_records(), {})


class CleanFontesTest(unittest.TestCase):
    def test_trims_ui_boundaries(self):
        self.assertEqual(
            lib.clean_fontes("INE, PORDATA Carregue aqui para ver"),
            "INE, PORDATA")
        self.assertEqual(
            lib.clean_fontes("Eurostat | OCDE ver tabela completa"),
            "Eurostat | OCDE")
        self.assertEqual(
            lib.clean_fontes("INE, PORDATA Última atualização: 2026"),
            "INE, PORDATA")
        self.assertEqual(lib.clean_fontes("INE, PORDATA"), "INE, PORDATA")
        self.assertEqual(  # municipal toolbar variant
            lib.clean_fontes(
                "II/MTSSS, PORDATA Operações Opções Ver Gráfico Ranking"),
            "II/MTSSS, PORDATA")

    def test_strips_punctuation_edges(self):
        self.assertEqual(lib.clean_fontes(" INE, PORDATA ,"), "INE, PORDATA")


if __name__ == "__main__":
    unittest.main()


class UrlHostTest(unittest.TestCase):
    """`is_indicator_url` looked for "pordata.pt/" as a substring, so the
    host was mentioned rather than checked. A sitemap is precisely an
    input we do not control."""

    def test_a_real_indicator_url_passes(self):
        self.assertTrue(lib.is_indicator_url(
            "https://www.pordata.pt/portugal/taxa+de+natalidade-1"))

    def test_the_apex_domain_passes(self):
        self.assertTrue(lib.is_indicator_url(
            "https://pordata.pt/municipios/casamentos-5"))

    def test_a_foreign_host_mentioning_pordata_is_refused(self):
        self.assertFalse(lib.is_indicator_url(
            "https://evil.example/redir?u=pordata.pt/portugal/x-999"))

    def test_a_javascript_url_is_refused(self):
        self.assertFalse(lib.is_indicator_url(
            "javascript:pordata.pt/portugal/x-1"))

    def test_a_non_https_scheme_is_refused(self):
        self.assertFalse(lib.is_indicator_url(
            "ftp://x/pordata.pt/municipios/y-5"))
        self.assertFalse(lib.is_indicator_url(
            "http://www.pordata.pt/portugal/taxa-1"))

    def test_a_lookalike_domain_is_refused(self):
        self.assertFalse(lib.is_indicator_url(
            "https://pordata.pt.evil.example/portugal/x-1"))

    def test_userinfo_cannot_smuggle_the_host(self):
        self.assertFalse(lib.is_indicator_url(
            "https://pordata.pt@evil.example/portugal/x-1"))


class RecordUrlTest(RepoCase):
    """`jsonl_skipped_lines_max: 0` gates a count that a null url never
    reached: the key existed, so nothing raised, and the record went into
    the dict under `None` — then died much later in `sorted(records)` as
    an unattributed TypeError."""

    def write(self, *lines):
        path = pathlib.Path("data/catalogue/pages.jsonl")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def test_a_null_url_is_counted_as_skipped(self):
        self.write('{"url": null, "id": 1}',
                   '{"url": "https://www.pordata.pt/portugal/a-1"}')
        got = lib.load_records()
        self.assertEqual(len(got), 1)
        self.assertEqual(lib.SKIPPED_LINES, 1)

    def test_a_non_string_url_is_counted_as_skipped(self):
        self.write('{"url": 42}')
        lib.load_records()
        self.assertEqual(lib.SKIPPED_LINES, 1)

    def test_an_empty_url_is_counted_as_skipped(self):
        self.write('{"url": "   "}')
        lib.load_records()
        self.assertEqual(lib.SKIPPED_LINES, 1)


class AreaAndIdTest(unittest.TestCase):
    """Identity from the URL, for the one record that has nothing else:
    an errored fetch carries only url/error/harvested_at, and that is
    exactly the abandoned page the tombstone path exists for."""

    def test_it_reads_the_area_and_the_trailing_id(self):
        self.assertEqual(
            lib.area_and_id("https://www.pordata.pt/portugal/despesas-1221"),
            ("portugal", 1221))

    def test_it_refuses_a_url_that_is_not_an_indicator(self):
        self.assertIsNone(lib.area_and_id("https://www.pordata.pt/portugal/"))
        self.assertIsNone(lib.area_and_id("https://evil.example/portugal/x-1"))
