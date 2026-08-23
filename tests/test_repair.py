import json
import pathlib
import unittest

from helpers import RepoCase, load_script, record

rp = load_script("repair_pages")


class RepairTest(RepoCase):
    def test_trims_overcaptured_fontes_and_rewrites(self):
        dirty = record("portugal/taxa+de+natalidade-99", 99, "portugal",
                       "Taxa de natalidade",
                       fontes="INE, PORDATA Carregue aqui para ver o gráfico")
        clean = record("europa/indice+de+gini-300", 300, "europa",
                       "Índice de Gini", fontes="Eurostat | PORDATA")
        err = {"url": "https://www.pordata.pt/europa/falhado-888",
               "error": "timeout", "harvested_at": "2026-08-22"}
        self.write_records([dirty, clean, err])
        rp.main()
        lines = [json.loads(x) for x in pathlib.Path(
            "data/catalogue/pages.jsonl").read_text(
            encoding="utf-8").splitlines()]
        by_url = {r["url"]: r for r in lines}
        self.assertEqual(by_url[dirty["url"]]["fontes"], "INE, PORDATA")
        self.assertEqual(by_url[clean["url"]]["fontes"],
                         "Eurostat | PORDATA")
        self.assertIn(err["url"], by_url)  # error records pass through

    def test_repair_counts_only_changed(self):
        records = {"a": {"url": "a", "fontes": "INE, PORDATA"},
                   "b": {"url": "b", "fontes": "INE ver tabela completa"},
                   "c": {"url": "c", "error": "x", "fontes": "INE Carregue"}}
        self.assertEqual(rp.repair(records), 1)
        self.assertEqual(records["b"]["fontes"], "INE")
        self.assertEqual(records["c"]["fontes"], "INE Carregue")  # untouched

    def test_no_rewrite_when_clean(self):
        clean = record("portugal/taxa+de+natalidade-99", 99, "portugal",
                       "Taxa de natalidade", fontes="INE, PORDATA")
        self.write_records([clean])
        before = pathlib.Path("data/catalogue/pages.jsonl").read_text(
            encoding="utf-8")
        rp.main()
        after = pathlib.Path("data/catalogue/pages.jsonl").read_text(
            encoding="utf-8")
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
