"""Roadmap 6c: the freshness loop's one silent data-loss path.

Staleness compared `lastmod > harvested_at`, and both are date-only. An
update PORDATA published on the same day a page was harvested therefore
never re-fetched — and never would, because every later run compares the
same two equal dates. The record stays wrong for ever.

The fix compares against the lastmod stored *at harvest*, so any change
to the value re-fetches exactly once. These tests pin all three branches:
the stored-lastmod path, the legacy fallback, and the case that used to
be lost.
"""

import unittest

from helpers import PT, RepoCase, load_script, record

h = load_script("harvest_catalogue")

URL = f"{PT}/portugal/taxa-1"


class IsStaleTest(unittest.TestCase):
    @staticmethod
    def rec(harvested, stored=None):
        r = {"harvested_at": harvested}
        if stored is not None:
            r["sitemap_lastmod"] = stored
        return r

    # --- the bug -------------------------------------------------------
    def test_a_same_day_update_is_now_caught(self):
        # harvested on the 22nd when the sitemap said the 20th; PORDATA
        # then republished on the 22nd. The old `>` test compared
        # "2026-08-22" > "2026-08-22" and skipped it for ever.
        self.assertTrue(h.is_stale(
            URL, self.rec("2026-08-22", "2026-08-20"),
            {URL: "2026-08-22"}))

    def test_and_stops_after_one_re_fetch(self):
        # a `>=` fix would re-fetch this on every run, for ever
        self.assertFalse(h.is_stale(
            URL, self.rec("2026-08-22", "2026-08-22"),
            {URL: "2026-08-22"}))

    # --- the stored-lastmod path ---------------------------------------
    def test_a_changed_lastmod_is_stale(self):
        self.assertTrue(h.is_stale(
            URL, self.rec("2026-08-22", "2026-08-20"),
            {URL: "2026-08-25"}))

    def test_an_unchanged_lastmod_is_fresh(self):
        self.assertFalse(h.is_stale(
            URL, self.rec("2026-08-22", "2026-08-20"),
            {URL: "2026-08-20"}))

    def test_a_lastmod_moving_backwards_still_counts_as_changed(self):
        # PORDATA correcting a date is a change like any other
        self.assertTrue(h.is_stale(
            URL, self.rec("2026-08-22", "2026-08-20"),
            {URL: "2026-08-10"}))

    # --- the legacy fallback -------------------------------------------
    def test_records_without_the_field_use_the_old_comparison(self):
        self.assertTrue(h.is_stale(
            URL, self.rec("2026-08-22"), {URL: "2026-08-25"}))
        self.assertFalse(h.is_stale(
            URL, self.rec("2026-08-22"), {URL: "2026-08-20"}))

    def test_the_fallback_keeps_the_old_same_day_behaviour(self):
        # deliberately unchanged: making equality stale for legacy records
        # would call all 2,195 of them stale at once and fire a full
        # re-harvest, which is roadmap 21 and not a bug fix's business
        self.assertFalse(h.is_stale(
            URL, self.rec("2026-08-22"), {URL: "2026-08-22"}))

    def test_an_empty_stored_value_falls_back_rather_than_matching(self):
        self.assertTrue(h.is_stale(
            URL, self.rec("2026-08-22", ""), {URL: "2026-08-25"}))

    # --- absent data ---------------------------------------------------
    def test_a_url_with_no_lastmod_is_never_stale(self):
        self.assertFalse(h.is_stale(URL, self.rec("2026-08-22"), {}))
        self.assertFalse(h.is_stale(URL, self.rec("2026-08-22"), {URL: ""}))

    def test_a_record_with_no_harvest_date_is_not_stale_under_fallback(self):
        self.assertFalse(h.is_stale(URL, {}, {URL: "2026-08-25"}))


class PlanUsesIsStaleTest(RepoCase):
    def setUp(self):
        super().setUp()
        self.url = f"{PT}/portugal/taxa+de+natalidade-99"

    def lastmods(self, value):
        import pathlib
        pathlib.Path("data/sitemap-lastmod.tsv").write_text(
            f"{self.url}\t{value}\n", encoding="utf-8")

    def test_a_same_day_republish_reaches_the_stale_bucket(self):
        self.write_records([record(
            "portugal/taxa+de+natalidade-99", 99, "portugal", "Taxa",
            harvested_at="2026-08-22", sitemap_lastmod="2026-08-20")])
        self.lastmods("2026-08-22")
        got = h.plan([self.url], __import__(
            "scripts.pordata_lib", fromlist=["x"]).load_records())
        self.assertEqual(got["stale"], [self.url])

    def test_an_unchanged_page_stays_out_of_every_bucket(self):
        self.write_records([record(
            "portugal/taxa+de+natalidade-99", 99, "portugal", "Taxa",
            harvested_at="2026-08-22", sitemap_lastmod="2026-08-20")])
        self.lastmods("2026-08-20")
        got = h.plan([self.url], __import__(
            "scripts.pordata_lib", fromlist=["x"]).load_records())
        self.assertEqual(got, {"missing": [], "errored": [], "stale": []})

    def test_an_abandoned_url_is_never_planned_however_stale(self):
        import pathlib
        pathlib.Path("data/catalogue/abandoned.txt").write_text(
            self.url + "\n", encoding="utf-8")
        self.write_records([record(
            "portugal/taxa+de+natalidade-99", 99, "portugal", "Taxa",
            harvested_at="2026-08-22", sitemap_lastmod="2026-08-20")])
        self.lastmods("2026-09-01")
        got = h.plan([self.url], __import__(
            "scripts.pordata_lib", fromlist=["x"]).load_records())
        self.assertEqual(got["stale"], [])
