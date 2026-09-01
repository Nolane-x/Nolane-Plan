from __future__ import annotations

import unittest

from nolane_plan.wave9_chaos import WAVE9_CHAOS_CASE_IDS, run_wave9_chaos
from nolane_plan.wave9_registry import WAVE9_CORE_INVARIANT_IDS


class Wave9ChaosTests(unittest.TestCase):
    def test_deterministic_fault_schedule_is_green_and_repeatable(self) -> None:
        first = run_wave9_chaos()
        second = run_wave9_chaos()
        self.assertEqual(first.canonical_digest, second.canonical_digest)
        self.assertEqual(first.case_count, len(WAVE9_CHAOS_CASE_IDS))
        self.assertEqual(first.passed_count, first.case_count)
        self.assertEqual(first.failed_count, 0)
        self.assertEqual(tuple(row.case_id for row in first.results), WAVE9_CHAOS_CASE_IDS)
        self.assertTrue(all(row.passed for row in first.results))
        self.assertTrue(all(row.invariant_id in WAVE9_CORE_INVARIANT_IDS for row in first.results))

    def test_schedule_covers_each_wave9_production_frontier(self) -> None:
        report = run_wave9_chaos()
        covered = {row.invariant_id[:2] for row in report.results}
        self.assertEqual(covered, {"DC", "EX", "MW"})
        self.assertEqual(len({row.case_id for row in report.results}), report.case_count)
        self.assertTrue(all(row.observed_summary for row in report.results))


if __name__ == "__main__":
    unittest.main()
