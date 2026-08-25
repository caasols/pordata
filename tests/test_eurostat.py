"""Eurostat's catalogue: the parsing, and the refusals around it.

The TOC is a TSV whose *indentation* is the theme tree, which is an
unusual enough format that the parser is the risky part — and it proved
so on the first real run, which parsed 1,436 datasets where the file
inventory lists 7,412 because the tree carries a leaf type the sample
had not shown. Every test below is a shape from the real file or a
failure that actually happened.
"""

import io
import pathlib
import unittest
from unittest import mock

from helpers import RepoCase, load_script

e = load_script("fetch_eurostat_catalogue")

HEADER = ('"title"\t"code"\t"type"\t"last update of data"\t'
          '"last table structure change"\t"data start"\t"data end"\t"values"\n')


def toc(*rows):
    return HEADER + "".join(rows)


def row(title, code, kind, *rest):
    cells = [f'"{title}"', f'"{code}"', f'"{kind}"']
    cells += [f'"{c}"' for c in (rest or ("", "", "", ""))]
    return "\t".join(cells) + "\t\n"


class IndentTest(unittest.TestCase):
    def test_depth_counts_four_space_levels(self):
        self.assertEqual(e.depth("Database by themes"), 0)
        self.assertEqual(e.depth("    General statistics"), 1)
        self.assertEqual(e.depth("        Balance of payments"), 2)


class TocTest(unittest.TestCase):
    def parse(self, text):
        return e.parse_toc(text)

    def test_a_dataset_gets_the_folder_path_above_it(self):
        """The indentation *is* the tree — there is no parent id to join
        on, so the path has to be carried while scanning."""
        rows, _seen = self.parse(toc(
            row("Database by themes", "data", "folder"),
            row("    General and regional statistics", "general", "folder"),
            row("        Balance of payments", "ei_bp", "folder"),
            row("            Current account", "ei_bpm6ca_q", "table",
                "19.08.2026", "19.08.2026", "1991-Q1", "2026-Q2"),
        ))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["code"], "EI_BPM6CA_Q")
        self.assertEqual(rows[0]["theme"],
                         "General and regional statistics / Balance of payments")

    def test_leaving_a_branch_pops_the_stack(self):
        """Rows arrive depth-first, so a sibling branch must not inherit
        the previous one's path."""
        rows, _seen = self.parse(toc(
            row("Database", "data", "folder"),
            row("    Alpha", "a", "folder"),
            row("        One", "one", "table"),
            row("    Beta", "b", "folder"),
            row("        Two", "two", "table"),
        ))
        themes = {r["code"]: r["theme"] for r in rows}
        self.assertEqual(themes["ONE"], "Alpha")
        self.assertEqual(themes["TWO"], "Beta")

    def test_both_leaf_types_are_kept(self):
        """The first real run parsed only `table` and came back with
        1,436 of 7,412. `dataset` is the other one."""
        rows, _seen = self.parse(toc(
            row("Database", "data", "folder"),
            row("    A table", "tbl", "table"),
            row("    A dataset", "ds", "dataset"),
        ))
        self.assertEqual({r["code"] for r in rows}, {"TBL", "DS"})

    def test_an_unknown_type_is_counted_not_kept(self):
        """Counted so a breach can name it; not kept, because guessing
        that an unknown leaf is a dataset is how a catalogue fills with
        things that cannot be fetched."""
        rows, seen = self.parse(toc(
            row("Database", "data", "folder"),
            row("    Odd", "odd", "weird"),
        ))
        self.assertEqual(rows, [])
        self.assertEqual(seen["weird"], 1)

    def test_the_census_covers_every_row(self):
        _rows, seen = self.parse(toc(
            row("Database", "data", "folder"),
            row("    A", "a", "table"),
            row("    B", "b", "table"),
        ))
        self.assertEqual(seen["folder"], 1)
        self.assertEqual(seen["table"], 2)

    def test_codes_are_upper_cased_to_join_with_the_inventory(self):
        """The TOC writes `ei_bpm6ca_q` and the inventory `AACT_ALI01`;
        the merge is on this key, so a case mismatch would silently lose
        every download URL."""
        rows, _seen = self.parse(toc(
            row("Database", "data", "folder"),
            row("    X", "ei_bp_q", "table"),
        ))
        self.assertEqual(rows[0]["code"], "EI_BP_Q")

    def test_a_short_row_is_skipped_rather_than_crashing(self):
        rows, _seen = self.parse(HEADER + '"only"\t"two"\n'
                                 + row("Database", "data", "folder")
                                 + row("    X", "x", "table"))
        self.assertEqual(len(rows), 1)

    def test_an_unexpected_header_fails_the_run(self):
        """Parsing a changed format as if it had not changed is how a
        cache fills with nonsense that every downstream gate then trusts."""
        with self.assertRaises(SystemExit):
            self.parse('"a"\t"b"\t"c"\n"x"\t"y"\t"table"\n')


class InventoryTest(unittest.TestCase):
    INV = ("Code\tType\tSource dataset\tLast data change\t"
           "Last structural change\tData download url (tsv)\t"
           "Data download url (csv)\tData download url (sdmx)\t"
           "Data structure download url\tOpen in Data Browser url\n"
           "AACT_ALI01\tDATASET\t-\t2026-05-13\t2026-03-24\t"
           "https://x/tsv\thttps://x/csv\thttps://x/sdmx\t"
           "https://x/struct\thttps://x/browser\n")

    def test_the_download_urls_are_picked_up(self):
        got = e.parse_inventory(self.INV)
        self.assertEqual(got["AACT_ALI01"]["tsv_url"], "https://x/tsv")
        self.assertEqual(got["AACT_ALI01"]["browser_url"], "https://x/browser")

    def test_a_blank_code_is_skipped(self):
        got = e.parse_inventory(self.INV + "\tDATASET\t-\t\t\t\t\t\t\t\n")
        self.assertEqual(len(got), 1)


class CollapseTest(unittest.TestCase):
    """One row per code. The TOC hangs a dataset off up to eight branches
    and the first version emitted a row per branch, so 10,313 rows stood
    in for 7,572 datasets and every candidate count downstream was
    multiplied by how many themes the dataset happened to be filed
    under."""

    @staticmethod
    def appearance(code, theme, title="T", values="1"):
        return {"code": code, "title": title, "theme": theme,
                "last_update": "", "last_structure_change": "",
                "data_start": "", "data_end": "", "values": values}

    def test_a_dataset_filed_twice_becomes_one_row(self):
        got = e.collapse([self.appearance("A", "Health"),
                          self.appearance("A", "Society")])
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["theme_count"], 2)

    def test_every_theme_is_kept_not_just_the_first(self):
        got = e.collapse([self.appearance("A", "Society"),
                          self.appearance("A", "Health")])
        self.assertEqual(got[0]["themes"],
                         f"Health{e.THEME_SEP}Society")

    def test_the_singular_theme_field_is_gone(self):
        """It named one path where there are up to eight; leaving it
        would let a reader believe the first one is the theme."""
        got = e.collapse([self.appearance("A", "Health")])
        self.assertNotIn("theme", got[0])
        self.assertEqual(got[0]["themes"], "Health")

    def test_a_blank_theme_is_not_stored_as_a_theme(self):
        got = e.collapse([self.appearance("A", ""), self.appearance("A", "H")])
        self.assertEqual(got[0]["themes"], "H")
        self.assertEqual(got[0]["theme_count"], 1)

    def test_distinct_codes_stay_distinct(self):
        """Two codes can carry the same title — SDG_05_20 and TESEM180 are
        both "Gender pay gap in unadjusted form". That is real Eurostat
        redundancy and an honest tie, not a duplicate to fold away."""
        got = e.collapse([self.appearance("SDG_05_20", "T", title="Gender pay gap"),
                          self.appearance("TESEM180", "T", title="Gender pay gap")])
        self.assertEqual([r["code"] for r in got], ["SDG_05_20", "TESEM180"])

    def test_input_order_is_preserved(self):
        got = e.collapse([self.appearance("B", "T"), self.appearance("A", "T")])
        self.assertEqual([r["code"] for r in got], ["B", "A"])

    def test_disagreement_outside_the_theme_refuses_to_collapse(self):
        """Deduping is only lossless while the appearances agree on
        everything else; if Eurostat ever starts varying a field per
        branch, folding them silently would lose it."""
        with self.assertRaises(SystemExit) as caught:
            e.collapse([self.appearance("A", "Health", values="1"),
                        self.appearance("A", "Society", values="2")])
        self.assertIn("values", str(caught.exception))


class MergeTest(unittest.TestCase):
    def test_a_dataset_with_no_inventory_entry_keeps_empty_urls(self):
        """The two endpoints need not agree exactly, and a missing URL is
        a fact about that dataset rather than a reason to drop it."""
        got = e.merge([{"code": "MISSING"}], {})
        self.assertEqual(got[0]["tsv_url"], "")
        self.assertEqual(got[0]["sdmx_url"], "")

    def test_urls_are_joined_on_the_code(self):
        got = e.merge([{"code": "A"}], {"A": {"tsv_url": "u", "sdmx_url": "s",
                                              "browser_url": "b"}})
        self.assertEqual(got[0]["tsv_url"], "u")


class FloorTest(RepoCase):
    """The corpus floor, which caught the leaf-type gap on the first run."""

    def run_main(self, toc_text, inv_text):
        calls = [toc_text, inv_text]
        with mock.patch.object(e, "fetch", side_effect=calls), \
                mock.patch("builtins.print"):
            e.main()

    def test_a_degraded_pull_refuses_to_overwrite_the_cache(self):
        small = toc(row("Database", "data", "folder"),
                    row("    X", "x", "table"))
        with self.assertRaises(SystemExit):
            self.run_main(small, InventoryTest.INV)
        self.assertFalse(pathlib.Path("data/eurostat/datasets.csv").exists())

    def test_a_full_pull_is_written(self):
        rows = "".join(row(f"    D{n}", f"d{n}", "table")
                       for n in range(e.MIN_DATASETS))
        self.run_main(toc(row("Database", "data", "folder"), rows),
                      InventoryTest.INV)
        written = pathlib.Path("data/eurostat/datasets.csv")
        self.assertTrue(written.exists())
        self.assertIn("code,title,themes,theme_count",
                      written.read_text(encoding="utf-8")[:60])

    def test_the_floor_sits_under_the_inventory_count(self):
        """7,412 codes in the inventory; the floor is set under that
        rather than at it, because the two endpoints need not agree."""
        self.assertLess(e.MIN_DATASETS, 7412)
        self.assertGreater(e.MIN_DATASETS, 1436)   # what the bug produced

    def test_the_floor_counts_datasets_not_toc_rows(self):
        """The TOC carries ~1.36 rows per dataset, so a floor applied
        before the collapse would pass on a pull missing a quarter of the
        catalogue."""
        rows = "".join(row(f"    D{n}", f"d{n}", "table")
                       for n in range(e.MIN_DATASETS - 1))
        again = "".join(row(f"    D{n}", f"d{n}", "table")
                        for n in range(e.MIN_DATASETS - 1))
        with self.assertRaises(SystemExit):
            self.run_main(toc(row("Database", "data", "folder"), rows,
                              row("Second", "s", "folder"), again),
                          InventoryTest.INV)


if __name__ == "__main__":
    unittest.main()
