"""The mutation gate is itself gated: a scoring bug would either hide a
regression or block every push, and both are worse than no gate."""

import pathlib
import sys
import unittest
from unittest import mock

from helpers import RepoCase, load_script

gate = load_script("mutation_gate")


LINE = "⠹ 2981/2981  🎉 1834 🫥 121  ⏰ 0  🤔 0  🙁 1026  🔇 0  🧙 0"


class TallyTest(unittest.TestCase):
    def test_reads_the_tallies_from_a_progress_line(self):
        self.assertEqual(
            gate.tally(LINE),
            {"killed": 1834, "no_tests": 121, "timeout": 0,
             "suspicious": 0, "survived": 1026, "skipped": 0})

    def test_takes_the_last_progress_line_not_the_first(self):
        early = "⠋ 10/2981  🎉 5 🫥 0  ⏰ 0  🤔 0  🙁 5  🔇 0"
        counts = gate.tally(early + "\n" + LINE)
        self.assertEqual(counts["killed"], 1834)

    def test_carriage_returns_are_line_breaks(self):
        # mutmut redraws its progress line with \r, not \n
        counts = gate.tally("⠋ 1/2  🎉 1 🙁 0\r" + LINE)
        self.assertEqual(counts["killed"], 1834)

    def test_trailing_noise_after_the_line_is_ignored(self):
        self.assertEqual(
            gate.tally(LINE + "\n24.66 mutations/second\n")["survived"], 1026)

    def test_a_line_without_both_tallies_is_not_used(self):
        self.assertEqual(gate.tally("🎉 5 only killed here"), {})
        self.assertEqual(gate.tally(""), {})

    def test_output_with_no_progress_line_yields_nothing(self):
        self.assertEqual(gate.tally("mutmut failed to start\n"), {})


class KillRateTest(unittest.TestCase):
    def test_killed_over_killable(self):
        self.assertAlmostEqual(
            gate.kill_rate({"killed": 3, "survived": 1}), 0.75)

    def test_timeouts_count_as_killed(self):
        # a mutant that hangs the suite is caught, not missed
        self.assertEqual(gate.kill_rate({"killed": 1, "timeout": 1}), 1.0)

    def test_suspicious_counts_against_the_rate(self):
        self.assertAlmostEqual(
            gate.kill_rate({"killed": 1, "suspicious": 1}), 0.5)

    def test_skipped_mutants_are_in_neither_half(self):
        # mutmut declined to test them, so counting them as failures would
        # penalise code the tool chose not to mutate
        self.assertEqual(gate.kill_rate({"killed": 2, "skipped": 98}), 1.0)

    def test_nothing_killable_is_not_a_divide_by_zero(self):
        self.assertEqual(gate.kill_rate({}), 1.0)
        self.assertEqual(gate.kill_rate({"skipped": 5}), 1.0)

    def test_all_survived_is_zero_not_an_error(self):
        self.assertEqual(gate.kill_rate({"survived": 4}), 0.0)

    def test_a_timeout_counts_as_a_kill(self):
        """The docstring says a timeout means the mutant broke the suite,
        and every run so far has reported zero of them - so the branch
        that implements it had never been executed by anything. Mutation
        testing on the mutation gate is what surfaced that."""
        self.assertEqual(gate.kill_rate({"killed": 1, "timeout": 1,
                                         "survived": 2}), 0.5)

    def test_timeouts_alone_are_a_perfect_score(self):
        self.assertEqual(gate.kill_rate({"timeout": 3}), 1.0)

    def test_a_timeout_is_not_subtracted(self):
        """Pinning the sign: with `-` in place of `+` this reads 0.0 and
        the gate would fail a tree that killed everything."""
        self.assertEqual(gate.kill_rate({"killed": 4, "timeout": 4}), 1.0)


class FloorTest(unittest.TestCase):
    def test_the_floor_leaves_margin_below_the_lowest_measurement(self):
        # two runs of the same tree scored 64.1% and 62.5%: mutmut is not
        # perfectly deterministic, and a gate that flakes gets disabled
        self.assertLess(gate.FLOOR, 0.625 - 0.03)
        self.assertGreater(gate.FLOOR, 0.5)

    def test_a_rate_at_the_floor_passes(self):
        counts = {"killed": 58, "survived": 42}
        self.assertAlmostEqual(gate.kill_rate(counts), gate.FLOOR)
        self.assertGreaterEqual(gate.kill_rate(counts), gate.FLOOR)

    def test_a_rate_below_the_floor_fails(self):
        self.assertLess(gate.kill_rate({"killed": 57, "survived": 43}),
                        gate.FLOOR)


class VolumeFloorTest(RepoCase):
    """A run where mutmut exercised nothing scores 1.0 by construction —
    killed over killable with killable at zero — and printed "100.0%
    killed … passes". That is exactly the state a missing `also_copy`
    entry or a trigger that never fires produces, so the gate reported
    perfect health for the failure it exists to catch. `mutmut run`'s own
    exit status is discarded upstream by `|| true`, so this is the only
    place that can notice."""

    def run_gate(self, line):
        log = pathlib.Path("run.log")
        log.write_text(line, encoding="utf-8")
        with mock.patch("builtins.print"), \
                mock.patch.object(sys, "argv", ["x", str(log)]):
            try:
                gate.main()
            except SystemExit as exit_info:
                return exit_info.code or 0
        return 0

    def test_a_run_that_tested_nothing_fails(self):
        self.assertEqual(
            self.run_gate("x 🎉 0 🫥 250 ⏰ 0 🤔 0 🙁 0 🔇 0 🧙 0\n"), 1)

    def test_a_handful_of_mutants_is_not_a_run(self):
        self.assertEqual(
            self.run_gate("x 🎉 9 🫥 0 ⏰ 0 🤔 0 🙁 1 🔇 0 🧙 0\n"), 1)

    def test_a_real_run_above_the_floor_passes(self):
        self.assertEqual(
            self.run_gate("x 🎉 3595 🫥 186 ⏰ 0 🤔 0 🙁 1901 🔇 0 🧙 0\n"), 0)

    def test_a_real_run_below_the_kill_floor_still_fails(self):
        self.assertEqual(
            self.run_gate("x 🎉 100 🫥 0 ⏰ 0 🤔 0 🙁 5000 🔇 0 🧙 0\n"), 1)

    def test_the_volume_floor_sits_far_under_the_measured_run(self):
        """It only has to separate "ran" from "did not run", so it never
        needs re-baselining as the corpus grows."""
        self.assertLess(gate.MIN_KILLABLE, 5000)
