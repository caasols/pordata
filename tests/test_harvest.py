import pathlib
import unittest

from helpers import PT, RepoCase, load_script, record

h = load_script("harvest_catalogue")
lib = load_script("pordata_lib")

PAGE = """<html><head>
<title>Portugal: Taxa de natalidade | Pordata</title>
<meta name="description" content="Nados-vivos por mil habitantes">
<script type="application/ld+json">{"@type":"Dataset","name":"Taxa"}</script>
</head><body>
<div>Fontes/Entidades: INE, PORDATA Carregue aqui para ver o gráfico</div>
<span>&Uacute;ltima atualiza&ccedil;&atilde;o: 2026-06-22</span>
<p>Valores de 2021 a 2024 revistos pelo INE</p>
</body></html>"""


class ParseTest(unittest.TestCase):
    def test_full_page(self):
        rec = h.parse(f"{PT}/portugal/taxa+de+natalidade-99", 200,
                      PAGE.encode())
        self.assertEqual(rec["id"], 99)
        self.assertEqual(rec["area"], "portugal")
        self.assertEqual(rec["name"], "Taxa de natalidade")
        self.assertEqual(rec["description"], "Nados-vivos por mil habitantes")
        self.assertEqual(rec["fontes"], "INE, PORDATA")
        self.assertEqual(rec["ultima_atualizacao"], "2026-06-22")
        self.assertEqual(rec["json_ld"]["@type"], "Dataset")
        self.assertIn("Fontes", rec["marker_windows"])
        self.assertIn("revis", rec["marker_windows"])
        self.assertEqual(rec["http_status"], 200)

    def test_unparseable_json_ld_kept_raw(self):
        page = PAGE.replace('{"@type":"Dataset","name":"Taxa"}', "{oops")
        rec = h.parse(f"{PT}/europa/x-1", 200, page.encode())
        self.assertIn("unparsed", rec["json_ld"])

    def test_marker_windows_caps_spans(self):
        text = "Fontes a " * 10
        windows = h.marker_windows(text)
        self.assertLessEqual(len(windows["Fontes"]), 3)


class PlanTest(RepoCase):
    def test_missing_errored_stale(self):
        targets = lib.targets()  # 3 urls from the fixture sitemap
        fresh = record("portugal/taxa+de+natalidade-99", 99, "portugal",
                       "Taxa", harvested_at="2026-08-20")
        stale = record("municipios/medicos+por+habitante-200", 200,
                       "municipios", "Médicos", harvested_at="2026-08-01")
        errored = {"url": f"{PT}/europa/indice+de+gini-300",
                   "error": "timeout", "harvested_at": "2026-08-20"}
        records = {r["url"]: r for r in (fresh, stale, errored)}
        pathlib.Path("data/sitemap-lastmod.tsv").write_text(
            f"{fresh['url']}\t2026-08-10\n"      # older than harvest: fresh
            f"{stale['url']}\t2026-08-15\n",     # newer than harvest: stale
            encoding="utf-8")
        plan = h.plan(targets, records)
        self.assertEqual(plan["missing"], [])
        self.assertEqual(plan["errored"], [errored["url"]])
        self.assertEqual(plan["stale"], [stale["url"]])

    def test_unharvested_url_is_missing(self):
        plan = h.plan(lib.targets(), {})
        self.assertEqual(len(plan["missing"]), 3)
        self.assertEqual(plan["errored"], [])
        self.assertEqual(plan["stale"], [])


class ReportTest(RepoCase):
    def test_report_written_with_counts(self):
        self.write_records([
            record("portugal/taxa+de+natalidade-99", 99, "portugal", "Taxa"),
            {"url": f"{PT}/europa/indice+de+gini-300", "error": "boom",
             "harvested_at": "2026-08-22"},
        ])
        targets = lib.targets()
        h.write_report(targets, h.plan(targets, lib.load_records()))
        report = pathlib.Path("data/catalogue/REPORT.md").read_text(
            encoding="utf-8")
        self.assertIn("1 / 3", report)
        self.assertIn("1 errored", report)


if __name__ == "__main__":
    unittest.main()


class CaptionMarkerTest(RepoCase):
    """Spike A3 (2026-08-23): the chart caption carrying the unit is in
    all three area templates, but no marker reached it, so portugal units
    were 0% while europa and municipios were 100%."""

    CAPTION = ("Ver Gráfico Ranking Fontes/Entidades: IEFP/MTSSS-ME, "
               "PORDATA Carregue aqui para ver o gráfico ampliado "
               "{} ver tabela completa Fontes/Entidades: IEFP/MTSSS-ME, "
               "PORDATA Última actualização: 2026-03-05")

    def test_caption_is_captured_and_the_unit_survives_the_round_trip(self):
        build = load_script("build_catalogue")
        for unit in ("Indivíduo - Milhares", "Proporção - %", "Km²"):
            windows = h.marker_windows(self.CAPTION.format(unit))
            self.assertIn("ampliado", windows, unit)
            self.assertEqual(
                build.extract_unit({"marker_windows": windows}), unit)

    def test_anchor_sits_ahead_of_the_unit_not_behind_it(self):
        # the leading window is 60 chars and the trailing one 220, so
        # anchoring on "ver tabela completa" would cut a long unit off
        self.assertIn("ampliado", h.MARKER_WORDS)
        long_unit = ("Agregado doméstico privado (até 2010); Alojamento "
                     "(a partir de 2011) - Milhares")
        windows = h.marker_windows(self.CAPTION.format(long_unit))
        self.assertEqual(
            load_script("build_catalogue").extract_unit(
                {"marker_windows": windows}), long_unit)

    def test_page_without_a_caption_yields_no_marker(self):
        self.assertNotIn("ampliado", h.marker_windows(
            "Fontes/Entidades: INE, PORDATA Última actualização: 2026-01-01"))


class QuestionAndPeriodTest(RepoCase):
    """Roadmap 24: fields spike A6 located, captured at harvest time so
    the freshness loop collects them without a dedicated re-fetch."""

    def test_question_is_read_from_h2(self):
        self.assertEqual(
            h.extract_question("<h1>Título</h1><h2>Quantos médicos há?</h2>"),
            "Quantos médicos há?")

    def test_inline_markup_does_not_break_the_question(self):
        self.assertEqual(
            h.extract_question("<h2>Emissões de CO<sub>2</sub>?</h2>"),
            "Emissões de CO₂?")

    def test_a_footnote_marker_does_not_leave_a_gap(self):
        self.assertEqual(
            h.extract_question("<h2>Água da rede pública<sub>1</sub>?</h2>"),
            "Água da rede pública₁?")

    def test_an_h2_that_is_not_a_question_is_ignored(self):
        self.assertEqual(h.extract_question("<h2>Metainformação</h2>"), "")

    def test_period_from_the_portugal_year_elements(self):
        self.assertEqual(
            h.extract_period('<div class="YearCurrentText">2006</div>'
                             '<div class="YearOtherText">1991</div>'),
            ("1991", "2006"))

    def test_period_from_the_municipios_year_picker(self):
        html = "".join(f'<option value="{y}">{y}</option>'
                       for y in (2019, 2020, 2021))
        self.assertEqual(h.extract_period(html), ("2019", "2021"))

    def test_europa_has_neither_mechanism_so_no_period(self):
        self.assertEqual(h.extract_period("<h2>Que países?</h2>"), ("", ""))

    def test_implausible_years_are_refused(self):
        self.assertEqual(
            h.extract_period('<div class="YearCurrentText">1899</div>'
                             '<div class="YearOtherText">1801</div>'),
            ("", ""))

    def test_a_single_year_is_not_a_period(self):
        self.assertEqual(
            h.extract_period('<div class="YearCurrentText">2006</div>'),
            ("", ""))


class EuropaPeriodTest(unittest.TestCase):
    """The third template, which the roadmap had recorded as unhandled.

    Item 20 said europa has "neither the portugal year elements nor the
    municipios picker", inferred from spikes A3 and A4 which had sampled
    the other two areas. Probed directly on 2026-08-25, all three sampled
    europa pages carry **both**: four `YearCurrentText`/`YearOtherText`
    elements and 26-30 `<option value="YYYY">`. So the extractor already
    covers it and `period_ratio[europa]` sits at 0 because no europa page
    has been re-fetched since the parser learned the field — harvest lag,
    not a missing mechanism.

    Pinned here so the premise cannot quietly return.
    """

    EUROPA = ('<div class="YearOtherText">2010</div>'
              '<div class="YearCurrentText">2023</div>'
              '<select><option value="2010">2010</option>'
              '<option value="2023">2023</option></select>')

    def test_a_europa_shaped_page_yields_its_range(self):
        self.assertEqual(h.extract_period(self.EUROPA),
                         ("2010", "2023"))

    def test_both_mechanisms_are_present_on_that_shape(self):
        """The two are asserted separately because either alone would
        make the test pass while the page carried only one."""
        self.assertTrue(h.YEAR_ELEMENT.findall(self.EUROPA))
        self.assertTrue(h.YEAR_OPTION.findall(self.EUROPA))
