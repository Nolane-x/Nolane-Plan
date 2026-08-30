from __future__ import annotations

import unittest

from nolane_plan.wave5_conformance import run_wave5_conformance


class Wave5ConformanceTests(unittest.TestCase):
    def test_all_wave5_executable_policy_cases_are_defended(self):
        result = run_wave5_conformance()
        self.assertGreaterEqual(result["total"], 18)
        self.assertEqual(result["passed"], result["total"], result["cases"])

    def test_case_names_are_unique(self):
        result = run_wave5_conformance()
        names = [row["name"] for row in result["cases"]]
        self.assertEqual(len(names), len(set(names)))


if __name__ == "__main__":
    unittest.main()
