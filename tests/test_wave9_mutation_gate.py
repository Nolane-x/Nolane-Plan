from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "wave9_mutation_gate.py"


class Wave9MutationGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        spec = importlib.util.spec_from_file_location("wave9_mutation_gate", SCRIPT)
        if spec is None or spec.loader is None:
            raise RuntimeError("cannot load Wave-9 mutation gate")
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        cls.module = module

    def test_catalog_freezes_exact_twelve_constitutional_mutants(self) -> None:
        mutations = self.module.MUTATIONS
        self.assertEqual(tuple(row.mutant_id for row in mutations), tuple(f"X{i:02d}" for i in range(1, 13)))
        self.assertEqual(len({row.name for row in mutations}), 12)
        self.assertTrue(all(row.path for row in mutations))
        self.assertTrue(all(row.replacements for row in mutations))
        self.assertTrue(all(row.target_invariant_id for row in mutations))

    def test_classifier_never_counts_import_error_or_unrelated_failure_as_kill(self) -> None:
        classify = self.module.classify_probe_result
        outcome = self.module.ProbeOutcome
        self.assertEqual(
            classify(1, "TARGET_ASSERTION_REACHED:MW01\nTARGET_ASSERTION_FAILED:MW01\n", "MW01"),
            outcome.KILLED,
        )
        self.assertEqual(
            classify(0, "TARGET_ASSERTION_REACHED:MW01\nTARGET_ASSERTION_PASSED:MW01\n", "MW01"),
            outcome.SURVIVED,
        )
        self.assertEqual(classify(1, "ImportError: broken module", "MW01"), outcome.INVALID)
        self.assertEqual(
            classify(1, "TARGET_ASSERTION_REACHED:MW01\nTARGET_ASSERTION_ERROR:MW01:RuntimeError\n", "MW01"),
            outcome.INVALID,
        )

    def test_mutants_cover_every_declared_wave9_minimum_target(self) -> None:
        expected = {
            "epoch_monotonicity",
            "stale_writer_commit",
            "cas_last_writer_wins",
            "active_lineage_deletion",
            "source_deletion_before_switch_durability",
            "mixed_representation_recovery",
            "best_effort_cancel_clean",
            "wrong_epoch_cancellation_ack",
            "compensation_erases_original_outcome",
            "unsupported_backend_promoted",
            "old_epoch_authorization_resurrection",
            "unknown_wave9_replay_event",
        }
        self.assertEqual({row.name for row in self.module.MUTATIONS}, expected)

    def test_source_deletion_before_switch_durability_mutant_is_a_targeted_kill(self) -> None:
        mutation = next(row for row in self.module.MUTATIONS if row.mutant_id == "X05")
        outcome, detail = self.module.run_mutation(mutation)
        self.assertEqual(outcome, self.module.ProbeOutcome.KILLED, detail)


if __name__ == "__main__":
    unittest.main()
