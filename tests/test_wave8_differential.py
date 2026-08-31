from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from nolane_plan import PlanKernel
from nolane_plan.wave8_differential import (
    DIFFERENTIAL_IDS,
    run_wave8_differential,
    run_wave8_differential_invariant,
)
from nolane_plan.wave8_proof_fixture import build_proof_authorized_kernel


class Wave8DifferentialTests(unittest.TestCase):
    def test_exact_differential_taxonomy_runs_all_seeded_runtime_relations(self) -> None:
        self.assertEqual(tuple(f"D{index:02d}" for index in range(1, 11)), DIFFERENTIAL_IDS)
        for invariant_id in DIFFERENTIAL_IDS:
            with self.subTest(invariant_id=invariant_id):
                failures = run_wave8_differential_invariant(invariant_id, range(16))
                self.assertEqual((), failures, failures[0] if failures else None)

    def test_aggregate_differential_runner_is_seed_order_independent_and_repeatable(self) -> None:
        seeds = tuple(range(16))
        first = run_wave8_differential(seeds)
        second = run_wave8_differential(reversed(seeds))
        third = run_wave8_differential(seeds)
        self.assertEqual((), first)
        self.assertEqual(first, second)
        self.assertEqual(first, third)

    def test_d08_binding_diagnostics_exposes_exact_live_replay_delta(self) -> None:
        with tempfile.TemporaryDirectory(prefix="nolane-wave8-d08-diagnostic-") as temp:
            root = Path(temp)
            kernel, authorization, _, _ = build_proof_authorized_kernel(0, root)
            live = dict(kernel.proof_authorization_bindings[authorization.id])
            kernel.save_snapshot()
            restored = PlanKernel.open(root)
            replayed = dict(restored.proof_authorization_bindings[authorization.id])
            self.assertEqual(live, replayed, f"live={live!r} replayed={replayed!r}")

    def test_unknown_differential_id_fails_closed(self) -> None:
        with self.assertRaises(ValueError):
            run_wave8_differential_invariant("D99", (0,))


if __name__ == "__main__":
    unittest.main()
