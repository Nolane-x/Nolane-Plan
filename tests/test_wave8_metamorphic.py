from __future__ import annotations

import unittest

from nolane_plan.wave8_metamorphic import (
    METAMORPHIC_IDS,
    run_wave8_metamorphic,
    run_wave8_metamorphic_relation,
)


class Wave8MetamorphicTests(unittest.TestCase):
    def test_exact_metamorphic_taxonomy_runs_seeded_runtime_relations(self) -> None:
        self.assertEqual(tuple(f"M{index:02d}" for index in range(1, 13)), METAMORPHIC_IDS)
        for invariant_id in METAMORPHIC_IDS:
            with self.subTest(invariant_id=invariant_id):
                failures = run_wave8_metamorphic_relation(invariant_id, range(32))
                self.assertEqual((), failures, failures[0] if failures else None)

    def test_aggregate_metamorphic_runner_is_seed_order_independent(self) -> None:
        seeds = tuple(range(16))
        forward = run_wave8_metamorphic(seeds)
        reverse = run_wave8_metamorphic(reversed(seeds))
        self.assertEqual((), forward)
        self.assertEqual(forward, reverse)

    def test_unknown_metamorphic_id_fails_closed(self) -> None:
        with self.assertRaises(ValueError):
            run_wave8_metamorphic_relation("M99", (0,))


if __name__ == "__main__":
    unittest.main()
