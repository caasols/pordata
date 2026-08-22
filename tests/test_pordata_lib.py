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
