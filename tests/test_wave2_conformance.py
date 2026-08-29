from __future__ import annotations

import unittest

from nolane_plan.wave2_conformance import run_wave2_conformance


class Wave2ConformanceTests(unittest.TestCase):
    def test_all_adversarial_cases_are_defended(self):
        report = run_wave2_conformance()
        self.assertTrue(report["ok"], report)
        self.assertEqual(report["total"], 10)
        self.assertEqual(report["passed"], 10)
        self.assertEqual(report["failed"], [])

    def test_case_names_are_unique(self):
        report = run_wave2_conformance()
        names = [row["name"] for row in report["cases"]]
        self.assertEqual(len(names), len(set(names)))


if __name__ == "__main__":
    unittest.main()
