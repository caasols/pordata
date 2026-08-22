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
