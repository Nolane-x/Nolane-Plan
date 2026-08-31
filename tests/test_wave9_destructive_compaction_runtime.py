from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from nolane_plan import PlanKernel
from nolane_plan.actions import ActionIntent, AuthorityGrant
from nolane_plan.destructive_compaction import (
    DestructiveCompactionPhase,
    InjectedCompactionFault,
)
from nolane_plan.production_store import InMemoryProductionStore, StorageCapabilityProfile, StorageConflict
from nolane_plan.replay_registry import DEFAULT_REPLAY_REGISTRY
from nolane_plan.types import ReplayError


class Wave9DestructiveCompactionRuntimeTests(unittest.TestCase):
    def store(self) -> InMemoryProductionStore:
        return InMemoryProductionStore(
            StorageCapabilityProfile.create(
                backend_id="wave9-runtime-store",
                revision=1,
                atomic_replace=True,
                durable_acknowledgement=True,
                compare_and_swap=True,
                fencing_tokens=True,
                transactional_batch=True,
                destructive_delete=True,
                crash_recovery_durable=True,
            ),
            require_strong_multiwriter=True,
        )

    def kernel(self, root: Path | None = None) -> PlanKernel:
        root = Path(tempfile.mkdtemp()) if root is None else root
        kernel = PlanKernel.create(root, "runtime destructive compaction")
        kernel.propose_action(ActionIntent("deploy", "deploy"))
        kernel.add_grant(AuthorityGrant("grant", "agent:a", frozenset({"deploy"})))
        kernel.authorize("deploy", "agent:a", ("grant",), 1)
        return kernel

    def prepare(self, kernel: PlanKernel, store: InMemoryProductionStore, epoch, **kwargs):
        return kernel.prepare_destructive_compaction(
            store,
            epoch,
            compaction_id="dc:runtime",
            source_representation_id="source:r1",
            target_representation_id="target:r1",
            **kwargs,
        )

    def test_kernel_exposes_exact_bounded_destructive_compaction_surface(self) -> None:
        for name in (
            "prepare_destructive_compaction",
            "verify_compaction_shadow",
            "commit_compaction_switch",
            "retire_compaction_source",
            "verify_destructive_compaction",
        ):
            self.assertTrue(hasattr(PlanKernel, name), name)

    def test_all_destructive_compaction_events_are_registered_in_existing_replay_registry(self) -> None:
        expected = {
            "compaction.destructive_prepared",
            "compaction.shadow_verified",
            "compaction.production_switched",
            "compaction.source_retired",
            "compaction.destructive_verified",
        }
        self.assertTrue(expected.issubset(DEFAULT_REPLAY_REGISTRY.event_types))

    def test_kernel_pipeline_records_monotonic_observations_without_minting_storage_authority(self) -> None:
        kernel = self.kernel()
        store = self.store()
        epoch = store.acquire_epoch("kernel-writer", expected_epoch=None)
        prepared = self.prepare(kernel, store, epoch)
        self.assertEqual(prepared.phase, DestructiveCompactionPhase.PREPARED)
        shadow = kernel.verify_compaction_shadow(store, epoch, "dc:runtime")
        switched = kernel.commit_compaction_switch(store, epoch, "dc:runtime")
        retired = kernel.retire_compaction_source(store, epoch, "dc:runtime")
        verified = kernel.verify_destructive_compaction(store, epoch, "dc:runtime")
        self.assertEqual(
            [prepared.phase, shadow.phase, switched.phase, retired.phase, verified.phase],
            list(DestructiveCompactionPhase),
        )
        observation = kernel.destructive_compaction_observations["dc:runtime"]
        self.assertEqual(observation.phase, DestructiveCompactionPhase.VERIFIED)
        self.assertEqual(observation.storage_revision, store.current_revision())
        self.assertEqual(observation.authority_epoch_digest, epoch.canonical_digest)
        self.assertEqual(observation.production_pointer, "target:r1")
        self.assertEqual(observation.representation_ids, ("target:r1",))

    def test_post_snapshot_phase_observation_replays_but_does_not_replay_physical_storage(self) -> None:
        root = Path(tempfile.mkdtemp())
        kernel = self.kernel(root)
        store = self.store()
        epoch = store.acquire_epoch("kernel-writer", expected_epoch=None)
        kernel.save_snapshot()
        self.prepare(kernel, store, epoch)
        expected = kernel.destructive_compaction_observations["dc:runtime"]

        reopened = PlanKernel.open(root)
        self.assertEqual(reopened.destructive_compaction_observations["dc:runtime"], expected)
        self.assertFalse(hasattr(reopened, "production_store"))
        self.assertEqual(store.read_payload()["production_pointer"], "source:r1")

    def test_crash_after_durable_switch_is_reconciled_by_idempotent_retry_before_next_journal_observation(self) -> None:
        kernel = self.kernel()
        store = self.store()
        epoch = store.acquire_epoch("kernel-writer", expected_epoch=None)
        self.prepare(kernel, store, epoch)
        kernel.verify_compaction_shadow(store, epoch, "dc:runtime")
        with self.assertRaises(InjectedCompactionFault):
            kernel.commit_compaction_switch(
                store,
                epoch,
                "dc:runtime",
                fault_after=DestructiveCompactionPhase.SWITCH_COMMITTED,
            )
        self.assertEqual(store.read_payload()["production_pointer"], "target:r1")
        self.assertEqual(
            kernel.destructive_compaction_observations["dc:runtime"].phase,
            DestructiveCompactionPhase.SHADOW_WRITTEN,
        )
        recovered = kernel.commit_compaction_switch(store, epoch, "dc:runtime")
        self.assertEqual(recovered.phase, DestructiveCompactionPhase.SWITCH_COMMITTED)
        self.assertEqual(
            kernel.destructive_compaction_observations["dc:runtime"].phase,
            DestructiveCompactionPhase.SWITCH_COMMITTED,
        )
        self.assertEqual(set(store.read_payload()["representations"]), {"source:r1", "target:r1"})

    def test_stale_epoch_is_rejected_before_kernel_can_record_a_new_observation(self) -> None:
        kernel = self.kernel()
        store = self.store()
        old_epoch = store.acquire_epoch("writer-a", expected_epoch=None)
        self.prepare(kernel, store, old_epoch)
        kernel.verify_compaction_shadow(store, old_epoch, "dc:runtime")
        store.acquire_epoch("writer-b", expected_epoch=old_epoch.epoch)
        before = kernel.destructive_compaction_observations["dc:runtime"]
        with self.assertRaises(StorageConflict):
            kernel.commit_compaction_switch(store, old_epoch, "dc:runtime")
        self.assertEqual(kernel.destructive_compaction_observations["dc:runtime"], before)
        self.assertEqual(store.read_payload()["production_pointer"], "source:r1")

    def test_tampered_observation_suffix_fails_closed_even_when_hash_journal_is_valid(self) -> None:
        root = Path(tempfile.mkdtemp())
        kernel = self.kernel(root)
        kernel.save_snapshot()
        kernel.journal.append(
            "compaction.production_switched",
            {
                "observation": {
                    "compaction_id": "dc:tampered",
                    "phase": "switch_committed",
                    "state_digest": "state",
                    "storage_revision": 3,
                    "authority_epoch_digest": "epoch",
                    "production_pointer": "target:r1",
                    "representation_ids": ["source:r1", "target:r1"],
                    "canonical_digest": "tampered",
                }
            },
        )
        with self.assertRaises(ReplayError):
            PlanKernel.open(root)


if __name__ == "__main__":
    unittest.main()
