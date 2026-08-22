import unittest

from helpers import load_script

f = load_script("fetch_featured_sets")


def page(rows: list[str]) -> str:
    cells = "".join(f"<tr><td>{r}</td></tr>" for r in rows)
    return f"<html><body><table>{cells}</table></body></html>"


class ExtractNamesTest(unittest.TestCase):
    def test_name_name_pattern(self):
        html = page(["Índice de Gini (%)", "Índice de Gini (%)", "25,0"])
        self.assertEqual(f.extract_names(html), ["Índice de Gini (%)"])

    def test_name_desc_name_desc_absorbs_subtitle(self):
        html = page(["Contribuição das energias renováveis (%)",
                     "no consumo final bruto de energia",
                     "Contribuição das energias renováveis (%)",
                     "no consumo final bruto de energia", "12,5"])
        self.assertEqual(
            f.extract_names(html),
            ["Contribuição das energias renováveis (%) — "
             "no consumo final bruto de energia"])

    def test_footnote_marker_not_absorbed(self):
        html = page(["População residente", "(6)",
                     "População residente", "(6)", "10.343.066"])
        self.assertEqual(f.extract_names(html), ["População residente"])

    def test_stoplist_and_values_skipped(self):
        html = page(["Simbologia", "Simbologia",
                     "Exportar dados", "Exportar dados",
                     "1.234,5", "1.234,5"])
        self.assertEqual(f.extract_names(html), [])

    def test_lowercase_lines_are_not_names(self):
        html = page(["valor médio mensalizado", "valor médio mensalizado"])
        self.assertEqual(f.extract_names(html), [])

    def test_trailing_footnote_stripped_from_name(self):
        html = page(["Limiar de risco de pobreza (PPC) (1)",
                     "Limiar de risco de pobreza (PPC)", "9.492"])
        names = f.extract_names(html)
        self.assertEqual(names, ["Limiar de risco de pobreza (PPC)"])


class NormTest(unittest.TestCase):
    def test_norm_strips_accents_footnotes_case(self):
        self.assertEqual(f.norm("População (1) Résidente"),
                         "populacao residente")


if __name__ == "__main__":
    unittest.main()
