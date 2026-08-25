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

REPO = pathlib.Path(__file__).resolve().parents[1]
WF_DIR = REPO / ".github" / "workflows"
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

    def test_the_crosswalk_is_rebuilt_after_the_qa_revert(self):
        """It is built from docs/data/catalogue.json. Rebuilding before
        the revert would derive the routing from a catalogue QA is about
        to withdraw, and commit that instead."""
        self.assertLess(index_of(self.job, "Withhold publish"),
                        index_of(self.job, "Rebuild the INE crosswalk"))
        self.assertEqual(self.steps["Rebuild the INE crosswalk"]["if"],
                         "steps.qa.outputs.status == 'pass'")

    def test_the_crosswalk_is_committed_with_the_harvest(self):
        """A rebuild nothing stages is a rebuild that never happened."""
        run = self.steps["Commit progress"]["run"]
        self.assertIn("data/crosswalk/", run)
        self.assertIn("data/coverage/", run)

    def test_detail_pages_are_built_after_the_crosswalk(self):
        """They render the crosswalk as provenance, so building first
        would show the previous run's routing on this run's pages."""
        self.assertLess(index_of(self.job, "Rebuild the INE crosswalk"),
                        index_of(self.job, "Rebuild the indicator detail"))
        self.assertEqual(
            self.steps["Rebuild the indicator detail pages"]["if"],
            "steps.qa.outputs.status == 'pass'")

    def test_the_detail_pages_are_committed(self):
        """Every card links to them; unstaged pages are 404s."""
        self.assertIn("docs/", self.steps["Commit progress"]["run"])

    def test_the_coverage_gap_is_recomputed_after_the_crosswalk(self):
        """It reads the crosswalk to report its reach; running first
        would state the previous run's."""
        self.assertLess(index_of(self.job, "Rebuild the INE crosswalk"),
                        index_of(self.job, "Recompute the INE coverage gap"))

    def test_qa_gate_reverts_before_the_commit(self):
        """The revert has to land before the commit or the degraded
        catalogue is what gets committed."""
        self.assertLess(index_of(self.job, "QA gate"),
                        index_of(self.job, "Commit progress"))


class PublishGateTest(unittest.TestCase):
    """Every path that publishes must pass the same gate.

    `featured-sets.yml` rebuilt the whole catalogue and pushed `docs/data`
    while running `qa_catalogue.py` without `--strict` — which prints a
    breach and exits 0 — so a second publish path existed with the gate
    disarmed, against a standing decision that nothing publishes past a
    failing gate. Stated as a property over every workflow rather than
    fixed in one, because the next one added would have the same hole."""

    @staticmethod
    def jobs():
        for path in sorted(WF_DIR.glob("*.yml")):
            for name, job in (load(path).get("jobs") or {}).items():
                yield path.name, name, job

    @staticmethod
    def script(job):
        return "\n".join(str(step.get("run", "")) for step in job["steps"])

    def test_a_job_committing_docs_runs_the_gate_strictly(self):
        for wf, name, job in self.jobs():
            body = self.script(job)
            if "git add" not in body or "docs/" not in body:
                continue
            self.assertIn("qa_catalogue.py --strict", body,
                          f"{wf}:{name} commits docs/ without the gate")

    def test_nothing_stages_docs_without_consulting_the_gate(self):
        """Running the gate is not enough — `continue-on-error` keeps the
        job going, so the commit must actually consult the result.

        Consulting it in the step's `if:` and consulting it inside the
        script are both fine, and harvest.yml has to do the second: that
        step is `always()` so a dead run still commits its raw
        checkpoints, and only the `docs/` half is conditional. What is
        not fine is what was there — `git add … docs/` under `always()`
        with the status referenced nowhere in the step at all."""
        for wf, name, job in self.jobs():
            for step in job["steps"]:
                run = str(step.get("run", ""))
                if "git add" not in run or "docs/" not in run:
                    continue
                consulted = " ".join([str(step.get("if", "")), run,
                                      str(step.get("env", ""))])
                self.assertRegex(
                    consulted, r"steps\.qa\.outputs\.status|QA_STATUS",
                    f"{wf}:{name} stages docs/ without consulting the gate")

    def test_a_continue_on_error_step_is_never_the_last_word(self):
        """`continue-on-error: true` keeps a job green, so something
        later must read the outcome and decide."""
        for wf, name, job in self.jobs():
            for step in job["steps"]:
                if not step.get("continue-on-error"):
                    continue
                ident = step.get("id")
                self.assertIsNotNone(
                    ident, f"{wf}:{name} has a continue-on-error step with no id")
                later = "\n".join(str(s.get("if", "")) for s in job["steps"])
                self.assertIn(f"steps.{ident}.outputs", later,
                              f"{wf}:{name} never inspects {ident}")

    def test_a_refreshed_upstream_cache_rebuilds_what_reads_it(self):
        """A catalogue snapshot without its crosswalk leaves the routing
        pointing at the previous snapshot's ids with nothing saying so —
        the rule ine-catalogue.yml states and eurostat-catalogue.yml did
        not follow."""
        pairs = [("fetch_ine_catalogue.py", "build_crosswalk.py"),
                 ("fetch_eurostat_catalogue.py", "build_eurostat_crosswalk.py")]
        for wf, name, job in self.jobs():
            body = self.script(job)
            for producer, consumer in pairs:
                # an invocation, not a mention: `fetch_ine_catalogue.py`
                # also appears inside coverage's --omit list
                if re.search(rf"python3?\s+scripts/{re.escape(producer)}", body):
                    self.assertIn(consumer, body,
                                  f"{wf}:{name} refreshes {producer} without "
                                  f"rebuilding {consumer}")


class TriggerCoverageTest(unittest.TestCase):
    """Whatever the suite reads off disk must also trigger the suite.

    `setup.cfg`'s `also_copy` already enumerates every such path, because
    mutmut runs from a copied tree and dies without them. That list and
    `tests.yml`'s push paths are the same set for the same reason, and
    they had drifted: four of the six `also_copy` entries were not
    triggers, so `DesignSystemTest` — the guard credited with keeping one
    design across the SPA and the 2,195 detail pages — never ran on a
    site-only push. Four real commits changed `site/src/` with this job
    not firing.

    Asserting one against the other makes the coupling self-maintaining:
    a test that starts reading a new directory must add it in both places
    or fail here."""

    @staticmethod
    def also_copy():
        import configparser
        parser = configparser.ConfigParser()
        parser.read(REPO / "setup.cfg")
        raw = parser["mutmut"]["also_copy"]
        return [line.strip().rstrip("/") for line in raw.splitlines()
                if line.strip()]

    @staticmethod
    def push_paths():
        return [p.rstrip("/").removesuffix("/**")
                for p in load(WF_DIR / "tests.yml")[True]["push"]["paths"]]

    def test_every_copied_path_also_triggers_the_suite(self):
        triggers = self.push_paths()
        for path in self.also_copy():
            self.assertTrue(
                any(path == t or path.startswith(t + "/") for t in triggers),
                f"{path!r} is in setup.cfg also_copy but nothing in "
                f"tests.yml push.paths covers it: {triggers}")

    def test_every_copied_path_exists(self):
        """A stale entry copies nothing and covers nothing, while reading
        as though the coupling holds."""
        for path in self.also_copy():
            self.assertTrue((REPO / path).exists(), path)


class SiteBundleTest(unittest.TestCase):
    def test_freshness_gate_runs_after_the_build(self):
        """The gate is `git diff -- docs/` and means nothing until the
        build has rewritten docs/."""
        job = load(WF_DIR / "site.yml")["jobs"]["build"]
        names = [s.get("name") or s.get("run", "") for s in job["steps"]]
        build = next(i for i, n in enumerate(names) if n == "npm run build")
        gate = next(i for i, n in enumerate(names) if "docs/ bundle" in n)
        self.assertLess(build, gate)

    def test_the_bundle_it_gates_can_retrigger_it(self):
        """The gate went red on a push that changed site/src without
        rebuilding, and then nothing could clear it: the fix touches only
        docs/, and docs/ was not a trigger. A gate you cannot clear by
        fixing what it flagged stays red until an unrelated push."""
        paths = load(WF_DIR / "site.yml")[True]["push"]["paths"]
        self.assertIn("docs/index.html", paths)
        self.assertIn("docs/assets/**", paths)

    def test_the_nightly_harvest_does_not_drag_a_site_build_along(self):
        """`docs/**` would have worked and would run this job on every
        harvest — the harvest rewrites docs/data and docs/indicador every
        night and neither is a site build output."""
        paths = load(WF_DIR / "site.yml")[True]["push"]["paths"]
        self.assertNotIn("docs/**", paths)
        self.assertFalse([p for p in paths if p.startswith("docs/data")
                          or p.startswith("docs/indicador")])


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
