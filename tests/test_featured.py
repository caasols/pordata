import json
import pathlib
import unittest

from helpers import RepoCase, load_script, record

f = load_script("fetch_featured_sets")
b = load_script("build_catalogue")


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


class GoldenPairsTest(RepoCase):
    """Every pair here was an observed mis-match before the 2026-08-23
    audit, or a match the rewrite must keep. A matcher change that
    breaks one is a regression, not a tuning choice."""

    CATALOGUE = [
        ("municipios", 305, "Alunos matriculados no ensino superior: total e por sexo"),
        ("municipios", 213, "Estabelecimentos nos ensinos pré-escolar, básico e secundário: por nível"),
        ("municipios", 91, "Casamentos dissolvidos por morte"),
        ("municipios", 915, "Empresas não financeiras: total e por dimensão"),
        ("municipios", 990, "Densidade das empresas não financeiras"),
        ("europa", 1801, "Taxa de risco de pobreza após transferências sociais: total e por sexo"),
        ("europa", 1775, "Taxa de desemprego de longa duração: total e por sexo"),
        ("europa", 1928, "Índice de dependência de jovens"),
        ("europa", 1950, "Esperança de vida à nascença: total e por sexo"),
        ("europa", 1951, "Índice de envelhecimento"),
    ]

    def resolve(self, group, area, names):
        self.write_records([
            record(f"{a}/slug-{i}", i, a, n) for a, i, n in self.CATALOGUE])
        pathlib.Path("data/catalogue/featured.json").write_text(
            json.dumps({group: {"indicator_names": names}}), encoding="utf-8")
        flags, stats = b.resolve_featured(
            {r["url"]: r for r in [
                record(f"{a}/slug-{i}", i, a, n) for a, i, n in self.CATALOGUE]})
        return flags, stats[group]

    def test_negation_never_matches_its_opposite(self):
        flags, st = self.resolve("quadro_resumo_municipios", "municipios",
                                 ["Alunos do ensino não superior"])
        self.assertEqual(flags, {})
        self.assertEqual(st["matched"], 0)

    def test_antes_never_matches_apos(self):
        flags, st = self.resolve(
            "quadro_resumo_europa", "europa",
            ["Taxa de risco de pobreza antes de transferências sociais (%)"])
        self.assertEqual(flags, {})

    def test_short_name_does_not_absorb_a_longer_different_indicator(self):
        # "Casamentos" must not match "Casamentos dissolvidos por morte",
        # nor "Jovens" the dependency ratio
        flags, _ = self.resolve("quadro_resumo_municipios", "municipios",
                                ["Casamentos"])
        self.assertEqual(flags, {})
        flags, _ = self.resolve("quadro_resumo_europa", "europa",
                                ["Jovens (%) — indivíduos entre os 0 e os 14 anos"])
        self.assertEqual(flags, {})

    def test_count_indicator_beats_derived_density(self):
        flags, _ = self.resolve("quadro_resumo_municipios", "municipios",
                                ["Empresas não financeiras"])
        self.assertEqual(flags, {("municipios", 915): ["quadro_resumo"]})

    def test_qualifier_suffix_still_matches(self):
        flags, _ = self.resolve("quadro_resumo_europa", "europa",
                                ["Esperança de vida à nascença"])
        self.assertEqual(flags, {("europa", 1950): ["quadro_resumo"]})

    def test_definition_after_a_dash_is_split_off(self):
        flags, _ = self.resolve(
            "quadro_resumo_europa", "europa",
            ["Índice de envelhecimento — número de idosos por cada 100 jovens"])
        self.assertEqual(flags, {("europa", 1951): ["quadro_resumo"]})

    def test_five_similar_names_cannot_all_claim_one_id(self):
        names = [f"Estabelecimentos do {n} ciclo do ensino básico"
                 for n in ("1.º", "2.º", "3.º")]
        flags, st = self.resolve("quadro_resumo_municipios", "municipios", names)
        self.assertLessEqual(len(flags), 1)          # injective
        self.assertEqual(st["matched"], st["distinct_rows"])

    def test_overrides_pin_a_name_the_matcher_will_not_guess(self):
        self.write_records([
            record(f"{a}/slug-{i}", i, a, n) for a, i, n in self.CATALOGUE])
        pathlib.Path("data/catalogue/featured.json").write_text(json.dumps({
            "quadro_resumo_municipios": {"indicator_names": ["Casamentos"]},
            "overrides": {"quadro_resumo_municipios": {"Casamentos": 91}},
        }), encoding="utf-8")
        flags, _ = b.resolve_featured({r["url"]: r for r in [
            record(f"{a}/slug-{i}", i, a, n) for a, i, n in self.CATALOGUE]})
        self.assertEqual(flags, {("municipios", 91): ["quadro_resumo"]})
