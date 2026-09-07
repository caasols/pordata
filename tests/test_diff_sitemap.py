import contextlib
import io
import json
import os
import pathlib
import subprocess
import unittest

from helpers import RepoCase, load_script

d = load_script("diff_sitemap")

PT = "https://www.pordata.pt"
URLS = [f"{PT}/portugal/a-1", f"{PT}/portugal/b-2", f"{PT}/europa/c-3"]


class DiffCase(RepoCase):
    """RepoCase plus a real git repo, since diff_sitemap reads HEAD."""

    def setUp(self):
        super().setUp()
        subprocess.run(["git", "init", "-q"], check=True)
        subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t",
                        "commit", "-q", "--allow-empty", "-m", "root"],
                       check=True)
        self.write_snapshot(URLS, {u: "2026-08-01" for u in URLS})

    def write_snapshot(self, urls, mods):
        pathlib.Path("data/sitemap-urls.txt").write_text(
            "\n".join(urls) + "\n", encoding="utf-8")
        pathlib.Path("data/sitemap-lastmod.tsv").write_text(
            "".join(f"{u}\t{mods.get(u, '')}\n" for u in urls),
            encoding="utf-8")

    def commit_all(self):
        subprocess.run(["git", "add", "-A"], check=True)
        subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t",
                        "commit", "-q", "-m", "snap"], check=True)

    def run_diff(self, *argv):
        outputs, _ = self.run_diff_body(*argv)
        return outputs

    def run_diff_body(self, *argv):
        """Like run_diff, but also returns the printed markdown summary —
        the exact string that becomes the GitHub issue body."""
        out = pathlib.Path("gh_output")
        out.write_text("", encoding="utf-8")
        os.environ["GITHUB_OUTPUT"] = str(out.resolve())
        self.addCleanup(os.environ.pop, "GITHUB_OUTPUT", None)
        import sys
        old_argv = sys.argv
        sys.argv = ["diff_sitemap.py", *argv]
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                d.main()
        finally:
            sys.argv = old_argv
        outputs = dict(line.split("=", 1)
                       for line in out.read_text().splitlines())
        return outputs, buf.getvalue()


class BaselineTest(DiffCase):
    def test_first_run_is_baseline_and_changed(self):
        got = self.run_diff()
        self.assertEqual(got["changed"], "true")
        self.assertEqual(got["notify"], "false")


class ChangesTest(DiffCase):
    def test_add_remove_update_detected(self):
        self.commit_all()
        urls = [f"{PT}/portugal/a-1", f"{PT}/europa/c-3",
                f"{PT}/portugal/novo-9"]
        mods = {f"{PT}/portugal/a-1": "2026-08-20",   # updated
                f"{PT}/europa/c-3": "2026-08-01",     # unchanged
                f"{PT}/portugal/novo-9": "2026-08-20"}
        self.write_snapshot(urls, mods)
        got = self.run_diff("--changelog")
        self.assertEqual(got["changed"], "true")
        self.assertEqual(got["notify"], "true")   # add + remove present
        self.assertEqual(got["added"], "1")
        self.assertEqual(got["removed"], "1")
        self.assertEqual(got["updated"], "1")
        changelog = pathlib.Path("data/CHANGELOG.md").read_text(
            encoding="utf-8")
        self.assertIn("portugal/novo-9", changelog)
        self.assertIn("portugal/b-2", changelog)

    def test_landing_page_churn_not_reported_as_update(self):
        self.commit_all()
        mods = {u: "2026-08-01" for u in URLS}
        mods[f"{PT}/portugal/a-1"] = "2026-08-20"
        urls = URLS + [f"{PT}/"]
        mods[f"{PT}/"] = "2026-08-22"  # landing page, no -id suffix
        self.write_snapshot(urls, mods)
        got = self.run_diff()
        self.assertEqual(got["updated"], "1")  # only the -id page counts

    def test_no_changes(self):
        self.commit_all()
        got = self.run_diff("--changelog")
        self.assertEqual(got["changed"], "false")
        self.assertEqual(got["notify"], "false")
        self.assertFalse(pathlib.Path("data/CHANGELOG.md").exists())

    def test_mass_churn_summarized(self):
        self.commit_all()
        old = d.MASS_CHURN_THRESHOLD
        d.MASS_CHURN_THRESHOLD = 2
        self.addCleanup(setattr, d, "MASS_CHURN_THRESHOLD", old)
        self.write_snapshot(URLS, {u: "2026-08-21" for u in URLS})
        got = self.run_diff("--changelog")
        self.assertEqual(got["updated"], "3")
        changelog = pathlib.Path("data/CHANGELOG.md").read_text(
            encoding="utf-8")
        self.assertIn("wholesale lastmod churn", changelog)


class BodySizeTest(DiffCase):
    """The printed summary becomes the GitHub issue body, which the API
    rejects above 65,536 chars. A frozen snapshot let added/removed grow
    to +724/-623 and every run failed on `gh issue create`."""

    # a slug about as long as PORDATA's real ones, so the byte budget is
    # exercised, not a toy
    STEM = ("populacao-residente-estimativas-a-31-de-dezembro-total-e-por"
            "-sexo")

    def big_urls(self, n, tag):
        return [f"{PT}/portugal/{self.STEM}-{tag}{i}-{i}" for i in range(n)]

    def test_large_add_remove_body_within_github_limit(self):
        old = self.big_urls(800, "old")
        self.write_snapshot(old, {u: "2026-08-01" for u in old})
        self.commit_all()
        new = self.big_urls(800, "new")
        self.write_snapshot(new, {u: "2026-08-01" for u in new})
        outputs, body = self.run_diff_body("--changelog")
        self.assertEqual(outputs["added"], "800")
        self.assertEqual(outputs["removed"], "800")
        self.assertLess(len(body), 65536)

    def test_added_list_truncated_but_count_complete(self):
        self.commit_all()
        new = list(URLS) + self.big_urls(120, "new")
        self.write_snapshot(new, {u: "2026-08-01" for u in new})
        outputs, body = self.run_diff_body("--changelog")
        # the count reported to the workflow is the full total ...
        self.assertEqual(outputs["added"], "120")
        # ... but the rendered list is capped and says how many it omits
        self.assertIn(f"and {120 - d.MAX_LISTED_UPDATES} more", body)

    def test_body_hard_clamped_as_last_resort(self):
        old = d.MAX_BODY_CHARS
        d.MAX_BODY_CHARS = 500
        self.addCleanup(setattr, d, "MAX_BODY_CHARS", old)
        self.commit_all()
        new = list(URLS) + self.big_urls(60, "new")
        self.write_snapshot(new, {u: "2026-08-01" for u in new})
        _, body = self.run_diff_body("--changelog")
        self.assertLessEqual(len(body), d.MAX_BODY_CHARS)
        self.assertIn("truncated", body)


if __name__ == "__main__":
    unittest.main()
