from __future__ import annotations

import unittest

from nolane_plan.wave4_conformance import run_wave4_conformance


class Wave4ConformanceTests(unittest.TestCase):
    def test_all_wave4_proof_dependency_cases_are_defended(self):
        report = run_wave4_conformance()
        self.assertTrue(report["ok"], report)
        self.assertGreaterEqual(report["total"], 12)
        self.assertEqual(report["passed"], report["total"])

    def test_case_names_are_unique(self):
        report = run_wave4_conformance()
        names = [row["name"] for row in report["cases"]]
        self.assertEqual(len(names), len(set(names)))


if __name__ == "__main__":
    unittest.main()
