"""Gates and data-integrity guards added after the 2026-08-23 mega-audit.

Each test pins one silent-failure mode the audit found: a failed
re-fetch erasing a live indicator, a corrupt JSONL shrinking the
catalogue unnoticed, and QA reporting instead of gating.
"""

import json
import pathlib
import unittest
from unittest import mock

from helpers import PT, RepoCase, load_script, record

lib = load_script("pordata_lib")
harvest = load_script("harvest_catalogue")
qa = load_script("qa_catalogue")
fs = load_script("fetch_sitemap")


class LoadRecordsTest(RepoCase):
    def test_counts_unparseable_lines_instead_of_hiding_them(self):
        good = record("portugal/taxa+de+natalidade-99", 99, "portugal", "Taxa")
        path = pathlib.Path("data/catalogue/pages.jsonl")
        path.write_text(
            json.dumps(good, ensure_ascii=False) + "\n"
            + '{"url": "https://x", "trunc\n'          # malformed JSON
            + "null\n"                                  # valid JSON, not a dict
            + '{"no_url": 1}\n',                        # missing the key
            encoding="utf-8")
        records = lib.load_records()
        self.assertEqual(list(records), [good["url"]])
        self.assertEqual(lib.SKIPPED_LINES, 3)

    def test_blank_lines_are_not_counted_as_corruption(self):
        good = record("portugal/taxa+de+natalidade-99", 99, "portugal", "Taxa")
        pathlib.Path("data/catalogue/pages.jsonl").write_text(
            json.dumps(good, ensure_ascii=False) + "\n\n\n", encoding="utf-8")
        lib.load_records()
        self.assertEqual(lib.SKIPPED_LINES, 0)

    def test_write_records_is_atomic(self):
        rec = record("portugal/taxa+de+natalidade-99", 99, "portugal", "Taxa")
        lib.write_records({rec["url"]: rec})
        path = pathlib.Path("data/catalogue/pages.jsonl")
        self.assertEqual(len(path.read_text(encoding="utf-8").splitlines()), 1)
        self.assertFalse(path.with_suffix(".jsonl.tmp").exists())


class RefetchPreservationTest(RepoCase):
    """A failed *re-fetch* must never erase a good record: the build
    skips error records, so overwriting would drop a live indicator from
    the published site over one transient 500."""

    def setUp(self):
        super().setUp()
        good = record("portugal/taxa+de+natalidade-99", 99, "portugal",
                      "Taxa de natalidade", harvested_at="2026-01-01")
        self.url = good["url"]
        self.write_records([good])
        # lastmod newer than harvested_at -> the page is stale, so the
        # harvester re-fetches it on the next run
        pathlib.Path("data/sitemap-lastmod.tsv").write_text(
            f"{self.url}\t2026-08-01\n", encoding="utf-8")

    def run_harvest_with_failure(self):
        with mock.patch.object(harvest.urllib.request, "urlopen",
                               side_effect=OSError("boom")), \
             mock.patch.object(harvest.time, "sleep"):
            harvest.main()
        return lib.load_records()[self.url]

    def test_failed_refetch_keeps_the_good_record(self):
        rec = self.run_harvest_with_failure()
        self.assertNotIn("error", rec)
        self.assertEqual(rec["name"], "Taxa de natalidade")
        self.assertIn("boom", rec["refetch_error"])
        self.assertTrue(rec["refetch_failed_at"])

    def test_indicator_stays_published_after_a_failed_refetch(self):
        self.run_harvest_with_failure()
        build = load_script("build_catalogue")
        build.main()
        rows = json.loads(
            pathlib.Path("docs/data/catalogue.json").read_text(encoding="utf-8"))
        self.assertEqual([r["name"] for r in rows], ["Taxa de natalidade"])

    def test_never_harvested_page_still_becomes_an_error_record(self):
        pathlib.Path("data/catalogue/pages.jsonl").write_text("", encoding="utf-8")
        rec = self.run_harvest_with_failure()
        self.assertIn("error", rec)


class AbandonedUrlTest(RepoCase):
    """A URL PORDATA lists but never serves must stop being retried and
    stop making the catalogue look incomplete (roadmap 1 planned this
    with no code path behind it until the audit said so)."""

    URL = f"{PT}/portugal/taxa+de+natalidade-99"

    def mark_abandoned(self):
        pathlib.Path("data/catalogue/abandoned.txt").write_text(
            f"# dead upstream\n{self.URL}\n", encoding="utf-8")

    def test_abandoned_urls_are_not_planned_for_harvest(self):
        self.write_records([])
        targets = lib.targets()
        self.assertIn(self.URL, harvest.plan(targets, {})["missing"])
        self.mark_abandoned()
        self.assertNotIn(self.URL, harvest.plan(targets, {})["missing"])

    def test_abandoned_url_does_not_block_completeness(self):
        build = load_script("build_catalogue")
        self.write_records([
            record("municipios/medicos+por+habitante-200", 200,
                   "municipios", "Médicos"),
            record("europa/indice+de+gini-300", 300, "europa", "Gini"),
        ])
        self.mark_abandoned()
        build.main()
        stats = json.loads(
            pathlib.Path("docs/data/stats.json").read_text(encoding="utf-8"))
        self.assertTrue(stats["complete"])

    def test_comments_and_blanks_are_ignored(self):
        pathlib.Path("data/catalogue/abandoned.txt").write_text(
            "# a comment\n\n" + self.URL + "\n", encoding="utf-8")
        self.assertEqual(lib.abandoned(), {self.URL})

    def test_missing_file_means_nothing_abandoned(self):
        self.assertEqual(lib.abandoned(), set())


class SitemapFloorTest(RepoCase):
    def test_target_count_matches_the_harvester_definition(self):
        urls = lib.URLS_FILE.read_text(encoding="utf-8").split()
        self.assertEqual(sorted(fs.count_targets(urls)),
                         sorted(lib.targets()))

    def test_index_shaped_snapshot_yields_no_targets(self):
        # a <sitemapindex> would leave only sub-sitemap URLs, which must
        # not pass as a corpus (the floor then refuses the overwrite)
        self.assertEqual(
            fs.count_targets([f"{PT}/sitemap-1.xml", f"{PT}/sitemap-2.xml"]),
            [])


class QaGateTest(RepoCase):
    def write_ok(self, n):
        self.write_records([
            record(f"portugal/indicador-{i}", i, "portugal", f"Indicador {i}")
            for i in range(n)])

    def test_gate_passes_on_healthy_fixture(self):
        self.write_ok(4)
        self.assertEqual(qa.gate({
            "jsonl_skipped_lines": 0, "ok_records_ratio": 1.0,
            "name_coverage": 1.0, "description_coverage": 1.0,
            "fontes_coverage": 1.0, "date_iso_ratio": 1.0,
            "duplicate_area_id": 0, "published_rows_ratio": 1.0}), [])

    def test_gate_flags_each_breach(self):
        breaches = qa.gate({
            "jsonl_skipped_lines": 2, "ok_records_ratio": 0.5,
            "name_coverage": 0.10, "duplicate_area_id": 3})
        joined = " ".join(breaches)
        self.assertEqual(len(breaches), 4)
        self.assertIn("jsonl_skipped_lines", joined)
        self.assertIn("ok_records_ratio", joined)
        self.assertIn("duplicate_area_id", joined)

    def test_main_exits_nonzero_on_mass_empty_names(self):
        self.write_records([
            record(f"portugal/indicador-{i}", i, "portugal", "")
            for i in range(4)])
        with self.assertRaises(SystemExit) as caught:
            qa.main_strict()
        self.assertEqual(caught.exception.code, 1)
        report = pathlib.Path("data/catalogue/QA.md").read_text(encoding="utf-8")
        self.assertIn("BREACH", report)

    def test_main_without_strict_reports_but_does_not_exit(self):
        self.write_records([
            record(f"portugal/indicador-{i}", i, "portugal", "")
            for i in range(4)])
        qa.main()  # must not raise
        report = pathlib.Path("data/catalogue/QA.md").read_text(encoding="utf-8")
        self.assertIn("BREACH", report)

    def test_duplicate_area_id_detected_but_cross_area_ids_are_fine(self):
        self.write_records([
            record("portugal/a-5", 5, "portugal", "A"),
            record("municipios/b-5", 5, "municipios", "B"),   # fine
            record("portugal/c-5", 5, "portugal", "C"),       # real collision
        ])
        qa.main()
        report = pathlib.Path("data/catalogue/QA.md").read_text(encoding="utf-8")
        self.assertIn("duplicate (area, id) keys: [('portugal', 5)]", report)


if __name__ == "__main__":
    unittest.main()


class ShapeAssertionTest(RepoCase):
    """Roadmap 6a: the gate catches a field going empty, never a field
    filled with something well-formed but wrong. These pin the three
    ways PORDATA could feed us junk that looks fine."""

    def parse(self, html):
        return harvest.parse(f"{PT}/portugal/taxa-99", 200, html.encode())

    def page(self, title="Portugal: Taxa | Pordata", fontes="INE, PORDATA",
             ultima="2026-03-02"):
        return (f"<html><head><title>{title}</title></head><body>"
                f"Fontes/Entidades: {fontes} Última atualização: {ultima}"
                f"</body></html>")

    def test_healthy_page_has_no_warnings(self):
        rec = self.parse(self.page())
        self.assertNotIn("parse_warnings", rec)
        self.assertEqual(rec["name"], "Taxa")
        self.assertEqual(rec["fontes"], "INE, PORDATA")
        self.assertEqual(rec["ultima_atualizacao"], "2026-03-02")

    def test_changed_title_template_yields_no_name(self):
        rec = self.parse(self.page(title="Taxa de natalidade — PORDATA 2026"))
        self.assertEqual(rec["name"], "")
        self.assertIn("title_template", rec["parse_warnings"])

    def test_page_prose_is_not_published_as_a_source(self):
        # deliberately free of every FONTES_BOUNDARY word: the point of a
        # shape assertion is catching UI text the vocabulary never learnt
        prose = ("Estes dados foram compilados a partir de diversas "
                 "entidades nacionais e internacionais durante o processo "
                 "de revisao anual das series estatisticas")
        rec = self.parse(self.page(fontes=prose))
        self.assertEqual(rec["fontes"], "")
        self.assertIn("fontes_shape", rec["parse_warnings"])

    def test_garbage_date_is_dropped_not_sorted_on(self):
        rec = self.parse(self.page(ultima="Consulte aqui a nota metodologica"))
        self.assertEqual(rec["ultima_atualizacao"], "")
        self.assertIn("date_shape", rec["parse_warnings"])

    def test_impossible_and_far_future_dates_rejected(self):
        self.assertEqual(self.parse(self.page(ultima="2026-02-31"))
                         ["ultima_atualizacao"], "")
        self.assertEqual(self.parse(self.page(ultima="2099-01-01"))
                         ["ultima_atualizacao"], "")

    def test_gate_trips_on_parse_warnings(self):
        self.assertIn("parse_warnings",
                      " ".join(qa.gate({"parse_warnings": 4})))
