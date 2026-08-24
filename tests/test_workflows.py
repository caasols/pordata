"""The CI configuration itself, checked offline (roadmap 6b).

Eight workflows are the only thing that runs this project: the sandbox
cannot reach pordata.pt, so every fetch, every commit and every gate
happens in Actions. That makes the YAML production code — and until now
nothing tested it. The failures it can hide are the quiet kind: GitHub
does not error on a mistyped `steps.<id>`, it renders the empty string
and takes the `else` branch; a job with no `timeout-minutes` inherits a
six-hour default and holds its concurrency group while queued runs wait;
a data-writing job checked out at the trigger-time sha pushes a stale
tree. None of those announce themselves.

So these are invariants, not a schema check. Each one is a specific way
the pipeline has broken or could break silently, and each is decidable
from the repo with no network.
"""

import pathlib
import re
import unittest

import yaml

from helpers import load_script
from test_diff_sitemap import DiffCase

WF_DIR = pathlib.Path(__file__).resolve().parents[1] / ".github" / "workflows"
WORKFLOWS = sorted(WF_DIR.glob("*.yml"))
BRANCH_HEAD = "${{ github.ref_name }}"


def load(path: pathlib.Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def jobs():
    for path in WORKFLOWS:
        doc = load(path)
        for name, job in doc["jobs"].items():
            yield path, doc, name, job


def step_names(job: dict) -> list[str]:
    return [s.get("name", s.get("uses", "")) for s in job["steps"]]


def index_of(job: dict, fragment: str) -> int:
    for i, name in enumerate(step_names(job)):
        if fragment in name:
            return i
    raise AssertionError(f"no step matching {fragment!r} in {step_names(job)}")


class WorkflowsExistTest(unittest.TestCase):
    def test_every_workflow_parses(self):
        """A guard for the guards: an unparseable file is not skipped by
        the tests below, it makes them all fail loudly."""
        self.assertTrue(WORKFLOWS, "no workflows found - wrong path?")
        for path in WORKFLOWS:
            with self.subTest(path.name):
                self.assertIn("jobs", load(path))


class BoundedRunsTest(unittest.TestCase):
    def test_every_job_has_a_timeout(self):
        """Without one a job inherits GitHub's 6-hour default. Every
        workflow here is in a serial concurrency group, so one stalled
        run does not just waste minutes - it stops the pipeline for the
        rest of the day while the queue sits behind it."""
        for path, _doc, name, job in jobs():
            with self.subTest(f"{path.name}:{name}"):
                self.assertIsInstance(job.get("timeout-minutes"), int)

    def test_pushing_workflows_are_serialised(self):
        """Two concurrent runs of the same committer race on push; the
        loser fails or, worse, rebases over the winner's work."""
        for path in WORKFLOWS:
            raw = path.read_text(encoding="utf-8")
            if "git push" not in raw:
                continue
            with self.subTest(path.name):
                conc = load(path).get("concurrency")
                self.assertTrue(conc, f"{path.name} pushes with no concurrency group")
                self.assertFalse(conc.get("cancel-in-progress"),
                                 "cancelling a pushing run mid-commit")


class CheckoutTest(unittest.TestCase):
    def test_writers_check_out_the_branch_head(self):
        """actions/checkout defaults to the trigger-time sha. A job that
        commits from there pushes a tree that predates anything landed
        since the trigger - and for dispatched harvests that gap is the
        whole point, because the dispatcher just committed a snapshot."""
        for path, doc, name, job in jobs():
            if doc.get("permissions", {}).get("contents") != "write":
                continue
            checkouts = [s for s in job["steps"]
                         if "actions/checkout" in s.get("uses", "")]
            with self.subTest(f"{path.name}:{name}"):
                self.assertEqual(len(checkouts), 1)
                self.assertEqual((checkouts[0].get("with") or {}).get("ref"),
                                 BRANCH_HEAD)


class StepReferenceTest(unittest.TestCase):
    def test_no_dangling_step_ids(self):
        """`steps.ftech.outcome` is not an error in Actions - it is the
        empty string, which silently takes whichever branch treats an
        unset value as false. In harvest.yml that would label every
        commit a partial run."""
        for path in WORKFLOWS:
            declared = {s["id"] for job in load(path)["jobs"].values()
                        for s in job["steps"] if s.get("id")}
            referenced = set(re.findall(
                r"steps\.([A-Za-z0-9_-]+)\.",
                path.read_text(encoding="utf-8")))
            with self.subTest(path.name):
                self.assertEqual(referenced - declared, set())


class SitemapOrderTest(unittest.TestCase):
    """The detector's ordering is load-bearing, not cosmetic."""

    def setUp(self):
        self.job = load(WF_DIR / "sitemap.yml")["jobs"]["watch"]

    def test_notify_before_commit(self):
        """The diff is computed against the *committed* snapshot. Commit
        first and a failed `gh issue create` loses the add/remove notice
        for good: the next run compares against the advanced snapshot and
        sees nothing to report."""
        self.assertLess(index_of(self.job, "Open issue"),
                        index_of(self.job, "Commit snapshot"))

    def test_dispatch_survives_an_earlier_failure(self):
        """Pending pages are worth fetching even when the notice or the
        snapshot commit failed - the harvest job checks out the branch
        head and plans from whatever is committed there."""
        dispatch = self.job["steps"][index_of(self.job, "Dispatch harvest")]
        self.assertIn("always()", dispatch["if"])
        self.assertIn("refs/heads/main", dispatch["if"])

    def test_dispatch_is_pinned_to_main(self):
        """The paths-filtered push trigger also runs this workflow on
        feature branches, and a harvest dispatched from one would commit
        data to that branch."""
        for step in self.job["steps"]:
            if "Dispatch" in step.get("name", ""):
                self.assertIn("github.ref == 'refs/heads/main'", step["if"])


class HarvestSalvageTest(unittest.TestCase):
    def setUp(self):
        self.job = load(WF_DIR / "harvest.yml")["jobs"]["harvest"]
        self.steps = {s.get("name"): s for s in self.job["steps"]}

    def test_progress_is_committed_even_when_the_run_dies(self):
        """The harvester checkpoints every 25 pages so a dead run is not
        a total loss. Without always() the commit is skipped and those
        checkpoints - hours of 20-second-spaced requests - are re-made
        from scratch."""
        self.assertEqual(self.steps["Commit progress"].get("if"), "always()")

    def test_a_partial_run_says_so_in_the_commit(self):
        commit = self.steps["Commit progress"]["run"]
        self.assertIn("steps.fetch.outcome", commit)
        self.assertIn("partial", commit)
        self.assertEqual(self.steps["Harvest chunk"]["id"], "fetch")

    def test_qa_gate_reverts_before_the_commit(self):
        """The revert has to land before the commit or the degraded
        catalogue is what gets committed."""
        self.assertLess(index_of(self.job, "QA gate"),
                        index_of(self.job, "Commit progress"))


class SiteBundleTest(unittest.TestCase):
    def test_freshness_gate_runs_after_the_build(self):
        """The gate is `git diff -- docs/` and means nothing until the
        build has rewritten docs/."""
        job = load(WF_DIR / "site.yml")["jobs"]["build"]
        names = [s.get("name") or s.get("run", "") for s in job["steps"]]
        build = next(i for i, n in enumerate(names) if n == "npm run build")
        gate = next(i for i, n in enumerate(names) if "docs/ bundle" in n)
        self.assertLess(build, gate)


class PagesHealthContractTest(unittest.TestCase):
    """The health workflow branches on strings the script produces.

    Nothing connects the two files, and the failure is silent in the
    worst direction: `status != 'deploy'` is true for every real state,
    so a typo turns a daily health check into a daily issue."""

    def setUp(self):
        self.job = load(WF_DIR / "pages-health.yml")["jobs"]["health"]
        self.raw = (WF_DIR / "pages-health.yml").read_text(encoding="utf-8")

    def test_the_states_it_treats_as_healthy_are_the_scripts(self):
        script = load_script("check_pages_live")
        compared = set(re.findall(r"steps\.check\.outputs\.status "
                                  r"[!=]= '([a-z]+)'", self.raw))
        self.assertEqual(compared, set(script.HEALTHY))

    def test_an_unhealthy_run_still_fails(self):
        """The check step is continue-on-error so the issue gets filed,
        which would otherwise leave every run green."""
        names = [s.get("name", "") for s in self.job["steps"]]
        self.assertIn("Fail the run when the site is unhealthy", names)


class OutputContractTest(DiffCase):
    """The workflow's `if:` keys against the ones the script really writes.

    Renaming an output in diff_sitemap.py cannot break the workflow
    loudly: `steps.diff.outputs.notifi == 'true'` is simply never true,
    so the issue is never opened and the run stays green. This runs the
    script for real and compares.
    """

    def test_every_referenced_output_is_emitted(self):
        emitted = set(self.run_diff())
        raw = (WF_DIR / "sitemap.yml").read_text(encoding="utf-8")
        referenced = set(re.findall(r"steps\.diff\.outputs\.(\w+)", raw))
        self.assertTrue(referenced, "workflow stopped reading the diff outputs")
        self.assertEqual(referenced - emitted, set())


if __name__ == "__main__":
    unittest.main()
