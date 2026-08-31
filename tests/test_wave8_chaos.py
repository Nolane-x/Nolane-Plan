from __future__ import annotations

import unittest

from nolane_plan.wave8_chaos import (
    CHAOS_IDS,
    build_chaos_schedule,
    run_wave8_chaos,
    run_wave8_chaos_invariant,
)


class Wave8ChaosTests(unittest.TestCase):
    def test_exact_chaos_taxonomy_runs_all_seeded_fault_schedules(self) -> None:
        self.assertEqual(tuple(f"C{index:02d}" for index in range(1, 11)), CHAOS_IDS)
        for invariant_id in CHAOS_IDS:
            with self.subTest(invariant_id=invariant_id):
                failures = run_wave8_chaos_invariant(invariant_id, range(16))
                self.assertEqual((), failures, failures[0] if failures else None)

    def test_fault_schedules_are_explicit_seed_deterministic_and_nonempty(self) -> None:
        for invariant_id in CHAOS_IDS:
            for seed in range(16):
                with self.subTest(invariant_id=invariant_id, seed=seed):
                    first = build_chaos_schedule(invariant_id, seed)
                    second = build_chaos_schedule(invariant_id, seed)
                    self.assertEqual(first, second)
                    self.assertEqual(invariant_id, first.invariant_id)
                    self.assertEqual(seed, first.seed)
                    self.assertTrue(first.operations)
                    self.assertTrue(first.canonical_digest)

    def test_aggregate_chaos_runner_is_seed_order_independent_and_repeatable(self) -> None:
        seeds = tuple(range(16))
        first = run_wave8_chaos(seeds)
        second = run_wave8_chaos(reversed(seeds))
        third = run_wave8_chaos(seeds)
        self.assertEqual((), first)
        self.assertEqual(first, second)
        self.assertEqual(first, third)

    def test_unknown_chaos_id_fails_closed(self) -> None:
        with self.assertRaises(ValueError):
            build_chaos_schedule("C99", 0)
        with self.assertRaises(ValueError):
            run_wave8_chaos_invariant("C99", (0,))


if __name__ == "__main__":
    unittest.main()
