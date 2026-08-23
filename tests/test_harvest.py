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
