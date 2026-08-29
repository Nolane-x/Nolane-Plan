from __future__ import annotations

import unittest

from nolane_plan.wave3_conformance import run_wave3_conformance


class Wave3ConformanceTests(unittest.TestCase):
    def test_all_wave3_trust_cases_are_defended(self):
        report = run_wave3_conformance()
        self.assertTrue(report["ok"], report)
        self.assertEqual(report["total"], 12)
        self.assertEqual(report["passed"], 12)
        self.assertEqual(report["failed"], [])

    def test_case_names_are_unique(self):
        report = run_wave3_conformance()
        names = [row["name"] for row in report["cases"]]
        self.assertEqual(len(names), len(set(names)))


if __name__ == "__main__":
    unittest.main()
