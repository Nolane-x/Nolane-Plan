from __future__ import annotations

import unittest

from nolane_plan.wave8_properties import (
    PROPERTY_IDS,
    run_wave8_properties,
    run_wave8_property,
)


class Wave8PropertyTests(unittest.TestCase):
    def test_exact_property_taxonomy_runs_seeded_runtime_oracles(self) -> None:
        self.assertEqual(tuple(f"P{index:02d}" for index in range(1, 11)), PROPERTY_IDS)
        for invariant_id in PROPERTY_IDS:
            with self.subTest(invariant_id=invariant_id):
                failures = run_wave8_property(invariant_id, range(32))
                self.assertEqual((), failures, failures[0] if failures else None)

    def test_aggregate_property_runner_is_deterministic(self) -> None:
        seeds = tuple(range(16))
        first = run_wave8_properties(seeds)
        second = run_wave8_properties(reversed(seeds))
        self.assertEqual((), first)
        self.assertEqual(first, second)

    def test_unknown_property_id_fails_closed(self) -> None:
        with self.assertRaises(ValueError):
            run_wave8_property("P99", (0,))


if __name__ == "__main__":
    unittest.main()
