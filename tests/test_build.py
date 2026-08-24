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


class StripMarkupTest(unittest.TestCase):
    def test_em_tags_dropped(self):
        self.assertEqual(b.strip_markup("PIB <em>per capita</em> (UE27=100)"),
                         "PIB per capita (UE27=100)")

    def test_sub_sup_become_unicode(self):
        self.assertEqual(b.strip_markup("Emissão de CO<sub>2</sub> por km"),
                         "Emissão de CO₂ por km")
        self.assertEqual(b.strip_markup("Área em km<sup>2</sup>"),
                         "Área em km²")

    def test_plain_text_untouched(self):
        self.assertEqual(b.strip_markup("Taxa de natalidade"),
                         "Taxa de natalidade")


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
    def test_maps_area_ids_excludes_summary_tables(self):
        text = "\n".join([
            f"{PT}/en/portugal/birth+rate-99",
            f"{PT}/en/municipalities/summary+table/abrantes-828209",
            f"{PT}/en/europe/gini+index-300",
            f"{PT}/en/theme/portugal/population-1",
            f"{PT}/portugal/taxa+de+natalidade-99",
        ])
        names = b.build_en_names(text)
        self.assertEqual(names[("portugal", 99)], "Birth rate")
        self.assertEqual(names[("europa", 300)], "Gini index")
        self.assertNotIn(("municipios", 828209), names)
        # theme pages are not indicators
        self.assertNotIn(("portugal", 1), names)

    def test_percent_encoding_decoded(self):
        text = f"{PT}/en/portugal/master%27s+degrees-5"
        names = b.build_en_names(text)
        self.assertEqual(names[("portugal", 5)], "Master's degrees")

    def test_same_id_in_two_areas_kept_apart(self):
        # ids repeat across areas; each must keep its own EN name
        text = "\n".join([
            f"{PT}/en/portugal/annual+average+resident+population-6",
            f"{PT}/en/municipalities/cinema+facilities-6",
        ])
        names = b.build_en_names(text)
        self.assertEqual(names[("portugal", 6)],
                         "Annual average resident population")
        self.assertEqual(names[("municipios", 6)], "Cinema facilities")


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
        self.assertEqual(sorted(flags), [("europa", 300), ("europa", 301)])
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
            record("municipios/medicos+por+habitante-200", 200, "municipios",
                   "Médicos por habitante"),
            gone,
            {"url": f"{PT}/europa/falhado-888", "error": "timeout",
             "harvested_at": "2026-08-22"},
        ])
        b.main()
        rows = json.loads(pathlib.Path("docs/data/catalogue.json").read_text(
            encoding="utf-8"))
        by_id = {(r["area"], r["id"]): r for r in rows}
        self.assertEqual(len(rows), 3)          # error record excluded
        self.assertNotIn(("europa", 888), by_id)
        # tombstoned, not deleted
        self.assertTrue(by_id[("portugal", 777)]["removed"])
        self.assertNotIn("removed", by_id[("portugal", 99)])
        self.assertEqual(by_id[("portugal", 99)]["name_en"], "Birth rate")
        self.assertEqual(by_id[("municipios", 200)]["name_en"],
                         "Doctors per inhabitant")
        stats = json.loads(pathlib.Path("docs/data/stats.json").read_text(
            encoding="utf-8"))
        self.assertEqual(stats["indicators"], 3)
        self.assertEqual(stats["targets"], 3)
        # tombstones don't count towards completeness (gini-300 unharvested)
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
                         {"ok": 2, "missing_en": 1})


if __name__ == "__main__":
    unittest.main()


class FixSeparatorTest(unittest.TestCase):
    """PORDATA serves a literal '?' where an en dash belongs (37 names).
    The repair must not touch a name that ends in a real question."""

    def test_mid_string_question_mark_becomes_en_dash(self):
        self.assertEqual(
            b.fix_separator("População empregada a tempo parcial ? Homens"),
            "População empregada a tempo parcial – Homens")

    def test_repeated_separators_all_repaired(self):
        self.assertEqual(b.fix_separator("A ? B ? C"), "A – B – C")

    def test_trailing_question_is_a_real_question(self):
        for name in ("Onde existem mais Vilas?",
                     "Quantos somos?",
                     "Onde vivem mais idosos ?"):
            self.assertEqual(b.fix_separator(name), name)

    def test_question_without_flanking_spaces_untouched(self):
        self.assertEqual(b.fix_separator("E agora?Já sei"), "E agora?Já sei")

    def test_clean_name_unchanged(self):
        self.assertEqual(b.fix_separator("PIB per capita"), "PIB per capita")


class SplitBreakdownTest(unittest.TestCase):
    """The tail after a colon is demoted to the coverage line only when
    it reads as a dimension list. Refusing is the safe outcome."""

    def test_dimension_tail_is_split_out(self):
        self.assertEqual(
            b.split_breakdown("Docentes do ensino superior: total e por tipo"),
            ("Docentes do ensino superior", "total e por tipo"))

    def test_comma_form_is_split(self):
        self.assertEqual(
            b.split_breakdown("Eleitores: total, votantes e abstenção"),
            ("Eleitores", "total, votantes e abstenção"))

    def test_bare_por_form_is_split(self):
        self.assertEqual(
            b.split_breakdown("Acidentes: por tipo de acidente"),
            ("Acidentes", "por tipo de acidente"))

    def test_tail_that_is_the_indicator_is_refused(self):
        # the regression this rule exists for: demoting "dívida bruta em
        # % do PIB" would leave the card titled "Administrações Públicas"
        for name in (
                "Administrações Públicas: dívida bruta em % do PIB",
                "Abortos: Interrupções voluntárias de gravidez",
                "Cinema: receitas de bilheteira"):
            self.assertEqual(b.split_breakdown(name), (name, ""))

    def test_rate_phrasing_is_not_a_breakdown(self):
        # "por cem mil" / "por mil habitantes" describe the measure, not
        # a dimension the table is broken down by
        name = "Acidentes: por cem mil habitantes"
        self.assertEqual(b.split_breakdown(name), (name, ""))

    def test_no_colon_or_many_colons_refused(self):
        for name in ("PIB per capita",
                     "Cinema: exibições: total e por país"):
            self.assertEqual(b.split_breakdown(name), (name, ""))

    def test_empty_head_refused(self):
        self.assertEqual(b.split_breakdown(": total e por sexo"),
                         (": total e por sexo", ""))


class PlausibleUnitTest(unittest.TestCase):
    def test_real_units_accepted(self):
        for unit in ("Indivíduo", "Proporção - %", "Euro - Milhões", "Km²",
                     "t (tonelada) - Milhares", "Taxa - ‰",
                     "Euro (a partir de 1/1/1999) / ECU (até 31/12/1998) - Média",
                     "Agregado doméstico privado (até 2010); Alojamento "
                     "(a partir de 2011) - Milhares"):
            self.assertTrue(b.plausible_unit(unit), unit)

    def test_shape_failures_rejected(self):
        cases = {
            "empty": "",
            "too long": "x" * 91,
            "too many words": " ".join(["palavra"] * 13),
            "mostly digits": "210 015 800 1 2 3",
            "pipe": "Euro | Milhões",
            "colon": "Fontes: Eurostat",
            "newline": "Euro\nMilhões",
        }
        for why, value in cases.items():
            self.assertFalse(b.plausible_unit(value), why)


class ExtractUnitTest(unittest.TestCase):
    CAPTION = ("Carregue aqui para ver o gráfico ampliado {} "
               "ver tabela completa Fontes/Entidades: INE, PORDATA")

    def test_unit_read_from_a_marker_slice(self):
        rec = {"marker_windows": {"Fontes": [self.CAPTION.format("Indivíduo")]}}
        self.assertEqual(b.extract_unit(rec), "Indivíduo")

    def test_slices_are_never_concatenated(self):
        # Joining the slices used to splice two truncated fragments into
        # a plausible-looking but corrupt unit. Each slice is truncated
        # here, so the honest answer is no unit at all.
        rec = {"marker_windows": {"Fontes": [
            "para ver o gráfico ampliado Euro (a partir de 1/1",
            "tir de 1/1/1999) / ECU (até 31/12/1998) ver tabela completa"]}}
        self.assertEqual(b.extract_unit(rec), "")

    def test_run_on_into_the_next_slice_is_trimmed(self):
        rec = {"marker_windows": {"Fontes": [
            "ampliado Rácio - % ver tabela comple i para ver o gráfico "
            "ampliado Rácio - % ver tabela completa"]}}
        self.assertEqual(b.extract_unit(rec), "Rácio - %")

    def test_string_window_supported(self):
        rec = {"marker_windows": {"Fontes": self.CAPTION.format("Taxa - %")}}
        self.assertEqual(b.extract_unit(rec), "Taxa - %")

    def test_missing_or_implausible_gives_empty(self):
        self.assertEqual(b.extract_unit({}), "")
        self.assertEqual(b.extract_unit({"marker_windows": {}}), "")
        rec = {"marker_windows": {"Fontes": [
            self.CAPTION.format("Fontes: INE")]}}
        self.assertEqual(b.extract_unit(rec), "")


class ExtractRevisionTest(unittest.TestCase):
    """Decision 5's revision caveat, recovered from `revis` windows the
    harvester has been storing since day one (roadmap 24)."""

    def rec(self, text):
        return {"marker_windows": {"revis": [text]}}

    def test_reads_the_revision_sentence(self):
        self.assertEqual(
            b.extract_revision(self.rec(
                "Fontes/Entidades: INE, PORDATA Última actualização: "
                "2026-08-05 Os valores foram revistos pela entidade "
                "oficial. Mais opções e dados")),
            "Os valores foram revistos pela entidade oficial.")

    def test_strips_a_label_or_date_the_window_sliced_into(self):
        got = b.extract_revision(self.rec(
            "actualização: 2026-07-13 Os valores são revistos anualmente "
            "para a série toda."))
        self.assertEqual(got,
                         "Os valores são revistos anualmente para a série toda.")

    def test_magazines_are_not_revisions(self):
        # "revistas" means magazines: pages about jornais e revistas
        # matched the marker and served their own question as a note
        self.assertEqual(b.extract_revision(self.rec(
            "Onde há mais e menos diários, semanários, revistas ou "
            "outros periódicos?")), "")

    def test_an_unforeseen_expense_is_not_a_revision(self):
        # "imprevista" contains "revis"
        self.assertEqual(b.extract_revision(self.rec(
            "Pessoas sem dinheiro para pagar uma despesa imprevista de "
            "valor próximo ao limiar de pobreza.")), "")

    def test_ui_furniture_is_never_served_as_a_note(self):
        for junk in ("Mais opções e dados. Aprofunde a sua análise.",
                     "Carregue aqui para ver a revisão. ver tabela completa"):
            self.assertEqual(b.extract_revision(self.rec(junk)), "")

    def test_missing_window_gives_empty(self):
        self.assertEqual(b.extract_revision({}), "")
        self.assertEqual(b.extract_revision({"marker_windows": {}}), "")
