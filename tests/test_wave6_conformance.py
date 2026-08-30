from __future__ import annotations

import unittest

from nolane_plan.wave6_conformance import WAVE6_CASES, run_wave6_conformance


EXPECTED_TAXONOMY_IDS = tuple(
    [f"CP{i:02d}" for i in range(1, 13)]
    + [f"HL{i:02d}" for i in range(1, 13)]
    + [f"EF{i:02d}" for i in range(1, 9)]
    + [f"TM{i:02d}" for i in range(1, 6)]
    + [f"OI{i:02d}" for i in range(1, 7)]
)


class Wave6ConformanceTests(unittest.TestCase):
    def test_registry_covers_exact_v06_failure_taxonomy_once(self):
        ids = tuple(case_id for case_id, _name, _fn in WAVE6_CASES)
        self.assertEqual(len(ids), 43)
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(set(ids), set(EXPECTED_TAXONOMY_IDS))

    def test_case_names_are_unique(self):
        names = tuple(name for _case_id, name, _fn in WAVE6_CASES)
        self.assertEqual(len(names), len(set(names)))

    def test_all_wave6_taxonomy_cases_are_defended(self):
        result = run_wave6_conformance()
        self.assertEqual(result["total"], 43)
        self.assertEqual(result["passed"], 43, result["cases"])
        self.assertEqual(result["failed"], 0)


if __name__ == "__main__":
    unittest.main()
