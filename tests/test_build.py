import json
import pathlib
import unittest

from helpers import PT, RepoCase, load_script, record

b = load_script("build_catalogue")


class NormTest(unittest.TestCase):
    def test_norm_name_accents_hyphens(self):
        self.assertEqual(b.norm_name("Auto-Estradas: vém!"),
                         "autoestradas vem")

    def test_content_tokens(self):
        tokens = b.content_tokens("Limites de velocidade nas auto-estradas")
        self.assertIn("limite", tokens)        # plural stripped
        self.assertIn("autoestrada", tokens)   # hyphen joined
        self.assertNotIn("de", tokens)         # stopword
        self.assertNotIn("nas", tokens)

    def test_single_char_tokens_dropped(self):
        self.assertEqual(b.content_tokens("Pessoal em I&D"), {"pessoal"})


class NameFromSlugTest(unittest.TestCase):
    def test_slug_becomes_readable_fallback(self):
        self.assertEqual(
            b.name_from_slug("financiamento+da+uniao+europeia-3597"),
            "Financiamento da uniao europeia")


class SplitFontesTest(unittest.TestCase):
    def test_split_dedupe_and_trim(self):
        out = b.split_fontes(
            "Eurostat | OCDE, PORDATA Carregue aqui Fontes/Entidades: Eurostat")
        self.assertEqual(out, ["Eurostat", "OCDE", "PORDATA"])


class EnNamesTest(unittest.TestCase):
    def test_maps_ids_excludes_summary_tables(self):
        text = "\n".join([
            f"{PT}/en/portugal/birth+rate-99",
            f"{PT}/en/municipalities/summary+table/abrantes-828209",
            f"{PT}/en/europe/gini+index-300",
            f"{PT}/en/theme/portugal/population-1",
            f"{PT}/portugal/taxa+de+natalidade-99",
        ])
        names = b.build_en_names(text)
        self.assertEqual(names[99], "Birth rate")
        self.assertEqual(names[300], "Gini index")
        self.assertNotIn(828209, names)
        self.assertNotIn(1, names)  # theme pages are not indicators


class ResolveFeaturedTest(RepoCase):
    def make_records(self):
        return {r["url"]: r for r in [
            record("europa/evolucao+do+indice+de+gini-300", 300, "europa",
                   "Evolução do Índice de Gini (%) por Países"),
            record("europa/taxa+de+poupanca-301", 301, "europa",
                   "Taxa de poupança das famílias"),
            record("municipios/medicos-200", 200, "municipios",
                   "Médicos por mil habitantes"),
        ]}

    def write_featured(self, names, group="quadro_resumo_europa"):
        pathlib.Path("data/catalogue/featured.json").write_text(
            json.dumps({group: {"indicator_names": names}}), encoding="utf-8")

    def test_exact_and_containment_matches(self):
        self.write_featured(["Taxa de poupança das famílias",
                             "Índice de Gini (%)"])
        flags, stats = b.resolve_featured(self.make_records())
        self.assertEqual(sorted(flags), [300, 301])
        self.assertEqual(stats["quadro_resumo_europa"]["matched"], 2)

    def test_ambiguous_short_name_unmatched(self):
        self.write_featured(["Pessoal em I&D"])
        flags, stats = b.resolve_featured(self.make_records())
        self.assertEqual(flags, {})
        self.assertEqual(stats["quadro_resumo_europa"]["unmatched"],
                         ["Pessoal em I&D"])

    def test_wrong_area_not_matched(self):
        self.write_featured(["Médicos por mil habitantes"])  # europa group
        flags, _ = b.resolve_featured(self.make_records())
        self.assertEqual(flags, {})

    def test_no_featured_file(self):
        flags, stats = b.resolve_featured(self.make_records())
        self.assertEqual((flags, stats), ({}, {}))


class BuildEndToEndTest(RepoCase):
    def test_main_builds_catalogue_with_tombstone(self):
        gone = record("portugal/indicador+extinto-777", 777, "portugal",
                      "Indicador extinto")  # not in the sitemap fixture
        self.write_records([
            record("portugal/taxa+de+natalidade-99", 99, "portugal",
                   "Taxa de natalidade"),
            gone,
            {"url": f"{PT}/europa/falhado-888", "error": "timeout",
             "harvested_at": "2026-08-22"},
        ])
        b.main()
        rows = json.loads(pathlib.Path("docs/data/catalogue.json").read_text(
            encoding="utf-8"))
        by_id = {r["id"]: r for r in rows}
        self.assertEqual(len(rows), 2)          # error record excluded
        self.assertNotIn(888, by_id)
        self.assertTrue(by_id[777]["removed"])  # tombstoned, not deleted
        self.assertNotIn("removed", by_id[99])
        self.assertEqual(by_id[99]["name_en"], "Birth rate")
        stats = json.loads(pathlib.Path("docs/data/stats.json").read_text(
            encoding="utf-8"))
        self.assertEqual(stats["indicators"], 2)
        self.assertEqual(stats["targets"], 3)
        self.assertFalse(stats["complete"])
        csv_text = pathlib.Path("docs/data/catalogue.csv").read_text(
            encoding="utf-8")
        self.assertIn("Taxa de natalidade", csv_text)
        names_map = pathlib.Path("docs/data/names-map.csv").read_text(
            encoding="utf-8")
        self.assertIn("99,portugal,Taxa de natalidade,Birth rate,ok",
                      names_map)
        # 777 is absent from the /en sitemap fixture -> flagged
        self.assertIn("777,portugal,Indicador extinto,,missing_en", names_map)
        self.assertEqual(stats["names"],
                         {"ok": 1, "missing_en": 1})


if __name__ == "__main__":
    unittest.main()
