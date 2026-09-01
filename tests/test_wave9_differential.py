from __future__ import annotations

import unittest

from nolane_plan.wave9_differential import WAVE9_DIFFERENTIAL_CASE_IDS, run_wave9_differential


class Wave9DifferentialTests(unittest.TestCase):
    def test_relations_are_deterministic(self) -> None:
        first = run_wave9_differential()
        second = run_wave9_differential()
        self.assertEqual(first.canonical_digest, second.canonical_digest)
        self.assertEqual(tuple(row.case_id for row in first.results), WAVE9_DIFFERENTIAL_CASE_IDS)
        self.assertEqual(first.case_count, len(WAVE9_DIFFERENTIAL_CASE_IDS))
        self.assertEqual(first.passed_count, first.case_count)
        self.assertEqual(first.failed_count, 0)

    def test_required_projection_relations_are_covered(self) -> None:
        report = run_wave9_differential()
        self.assertEqual(
            {row.relation for row in report.results},
            {
                "live_vs_reopen",
                "live_vs_suffix_replay",
                "single_writer_vs_strong_multiwriter_projection",
                "pre_vs_post_destructive_compaction",
            },
        )
        self.assertTrue(all(row.passed for row in report.results))
        self.assertTrue(all(row.left_digest == row.right_digest for row in report.results))


if __name__ == "__main__":
    unittest.main()
