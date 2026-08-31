from __future__ import annotations

import unittest

from nolane_plan.multiwriter import (
    CommitDecisionStatus,
    MultiWriterCoordinator,
    WriteIntent,
    WriterIdentity,
)
from nolane_plan.production_store import (
    InMemoryProductionStore,
    StorageCapabilityProfile,
    StorageConflict,
    UnsupportedStorageCapability,
)


class Wave9MultiWriterTests(unittest.TestCase):
    def strong_store(self) -> InMemoryProductionStore:
        return InMemoryProductionStore(
            StorageCapabilityProfile.create(
                backend_id="wave9-multiwriter",
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

    def writer(self, writer_id: str) -> WriterIdentity:
        return WriterIdentity.create(
            writer_id=writer_id,
            principal_ref=f"principal:{writer_id}",
            process_instance_ref=f"process:{writer_id}:1",
        )

    def intent(
        self,
        writer_id: str,
        intent_id: str,
        value: int,
        *,
        idempotent: bool = True,
        idempotency_key: str | None = None,
        conflict_scope: str = "canonical:mission",
        external_effect_possible: bool = False,
    ) -> WriteIntent:
        return WriteIntent.create(
            intent_id=intent_id,
            writer_id=writer_id,
            operation_kind="canonical_update",
            payload={"value": value},
            idempotent=idempotent,
            idempotency_key=idempotency_key,
            conflict_scope=conflict_scope,
            external_effect_possible=external_effect_possible,
        )

    def test_epoch_acquisition_is_monotonic_writer_bound_and_old_lease_is_fenced(self) -> None:
        store = self.strong_store()
        coordinator = MultiWriterCoordinator(store)
        w1 = self.writer("w1")
        w2 = self.writer("w2")
        lease1 = coordinator.acquire(w1, expected_epoch=None)
        self.assertEqual(lease1.epoch.epoch, 1)
        self.assertEqual(lease1.writer.canonical_digest, w1.canonical_digest)
        lease2 = coordinator.acquire(w2, expected_epoch=1)
        self.assertEqual(lease2.epoch.epoch, 2)
        with self.assertRaises(StorageConflict):
            coordinator.commit(self.intent("w1", "i:stale", 1), lease1, expected_revision=0)

    def test_same_predecessor_epoch_cannot_be_acquired_twice(self) -> None:
        store = self.strong_store()
        first = MultiWriterCoordinator(store)
        second = MultiWriterCoordinator(store)
        first.acquire(self.writer("w1"), expected_epoch=None)
        with self.assertRaises(StorageConflict):
            second.acquire(self.writer("w2"), expected_epoch=None)
        self.assertEqual(store.current_epoch().writer_id, "w1")

    def test_exact_revision_cas_allows_at_most_one_canonical_successor(self) -> None:
        store = self.strong_store()
        coordinator = MultiWriterCoordinator(store)
        lease = coordinator.acquire(self.writer("w1"), expected_epoch=None)
        first = coordinator.commit(self.intent("w1", "i:1", 1), lease, expected_revision=0)
        self.assertEqual(first.status, CommitDecisionStatus.COMMITTED)
        with self.assertRaises(StorageConflict):
            coordinator.commit(self.intent("w1", "i:2", 2), lease, expected_revision=0)
        self.assertEqual(store.current_revision(), 1)

    def test_duplicate_idempotent_key_converges_across_epoch_transition_without_second_commit(self) -> None:
        store = self.strong_store()
        coordinator = MultiWriterCoordinator(store)
        lease1 = coordinator.acquire(self.writer("w1"), expected_epoch=None)
        first = coordinator.commit(
            self.intent("w1", "i:1", 7, idempotency_key="dedupe:7"),
            lease1,
            expected_revision=0,
        )
        revision = store.current_revision()
        lease2 = coordinator.acquire(self.writer("w2"), expected_epoch=1)
        duplicate = coordinator.commit(
            self.intent("w2", "i:2", 7, idempotency_key="dedupe:7"),
            lease2,
            expected_revision=revision,
        )
        self.assertEqual(duplicate.status, CommitDecisionStatus.DUPLICATE_CONVERGED)
        self.assertEqual(duplicate.authoritative_intent_digest, first.authoritative_intent_digest)
        self.assertEqual(store.current_revision(), revision)

    def test_same_idempotency_key_with_different_semantics_is_explicit_conflict(self) -> None:
        store = self.strong_store()
        coordinator = MultiWriterCoordinator(store)
        lease1 = coordinator.acquire(self.writer("w1"), expected_epoch=None)
        coordinator.commit(self.intent("w1", "i:1", 7, idempotency_key="dedupe:k"), lease1, expected_revision=0)
        lease2 = coordinator.acquire(self.writer("w2"), expected_epoch=1)
        decision = coordinator.commit(
            self.intent("w2", "i:2", 8, idempotency_key="dedupe:k"),
            lease2,
            expected_revision=1,
        )
        self.assertEqual(decision.status, CommitDecisionStatus.CONFLICT_RECONCILIATION_REQUIRED)
        self.assertTrue(decision.conflict.reconciliation_required)
        self.assertEqual(store.current_revision(), 2)

    def test_conflicting_non_idempotent_intents_never_auto_overwrite(self) -> None:
        store = self.strong_store()
        coordinator = MultiWriterCoordinator(store)
        lease1 = coordinator.acquire(self.writer("w1"), expected_epoch=None)
        first = coordinator.commit(
            self.intent("w1", "effect:1", 1, idempotent=False, conflict_scope="remote:deploy", external_effect_possible=True),
            lease1,
            expected_revision=0,
        )
        self.assertEqual(first.status, CommitDecisionStatus.COMMITTED)
        lease2 = coordinator.acquire(self.writer("w2"), expected_epoch=1)
        second = coordinator.commit(
            self.intent("w2", "effect:2", 2, idempotent=False, conflict_scope="remote:deploy", external_effect_possible=True),
            lease2,
            expected_revision=1,
        )
        self.assertEqual(second.status, CommitDecisionStatus.CONFLICT_RECONCILIATION_REQUIRED)
        self.assertTrue(second.conflict.external_effect_ambiguity)

    def test_lease_expiry_does_not_claim_external_effect_absent(self) -> None:
        store = self.strong_store()
        coordinator = MultiWriterCoordinator(store)
        lease = coordinator.acquire(self.writer("w1"), expected_epoch=None, valid_until=10)
        coordinator.commit(
            self.intent("w1", "effect:1", 1, idempotent=False, conflict_scope="remote:deploy", external_effect_possible=True),
            lease,
            expected_revision=0,
            now=5,
        )
        assessment = coordinator.assess_expired_lease(lease, now=11)
        self.assertFalse(assessment.external_effect_absence_proven)
        self.assertTrue(assessment.reconciliation_required)

    def test_reconstruction_from_store_is_deterministic_and_preserves_conflicts(self) -> None:
        store = self.strong_store()
        coordinator = MultiWriterCoordinator(store)
        lease1 = coordinator.acquire(self.writer("w1"), expected_epoch=None)
        coordinator.commit(
            self.intent("w1", "effect:1", 1, idempotent=False, conflict_scope="remote:deploy", external_effect_possible=True),
            lease1,
            expected_revision=0,
        )
        lease2 = coordinator.acquire(self.writer("w2"), expected_epoch=1)
        coordinator.commit(
            self.intent("w2", "effect:2", 2, idempotent=False, conflict_scope="remote:deploy", external_effect_possible=True),
            lease2,
            expected_revision=1,
        )
        first = coordinator.reconstruct()
        second = MultiWriterCoordinator(store).reconstruct()
        self.assertEqual(first, second)
        self.assertEqual(first.canonical_digest, second.canonical_digest)
        self.assertEqual(len(first.conflicts), 1)

    def test_unsupported_backend_is_never_promoted_to_strong_multiwriter(self) -> None:
        weak = InMemoryProductionStore(
            StorageCapabilityProfile.create(
                backend_id="weak",
                revision=1,
                atomic_replace=True,
                durable_acknowledgement=True,
                compare_and_swap=False,
                fencing_tokens=False,
                transactional_batch=True,
                destructive_delete=False,
                crash_recovery_durable=True,
            )
        )
        with self.assertRaises(UnsupportedStorageCapability):
            MultiWriterCoordinator(weak)

    def test_writer_and_commit_receipts_are_digest_deterministic(self) -> None:
        first = self.writer("w")
        second = self.writer("w")
        self.assertEqual(first.canonical_digest, second.canonical_digest)
        intent_a = self.intent("w", "i", 3, idempotency_key="k")
        intent_b = self.intent("w", "i", 3, idempotency_key="k")
        self.assertEqual(intent_a.canonical_digest, intent_b.canonical_digest)


if __name__ == "__main__":
    unittest.main()
