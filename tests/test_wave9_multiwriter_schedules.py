from __future__ import annotations

import unittest

from nolane_plan.multiwriter import CommitDecisionStatus, MultiWriterCoordinator, WriteIntent, WriterIdentity
from nolane_plan.production_store import InMemoryProductionStore, StorageCapabilityProfile, StorageConflict


class Wave9MultiWriterScheduleTests(unittest.TestCase):
    def store(self) -> InMemoryProductionStore:
        return InMemoryProductionStore(
            StorageCapabilityProfile.create(
                backend_id="wave9-schedule-store",
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
        idempotent: bool,
        idempotency_key: str | None,
        scope: str,
        external_effect_possible: bool,
    ) -> WriteIntent:
        return WriteIntent.create(
            intent_id=intent_id,
            writer_id=writer_id,
            operation_kind="scheduled_update",
            payload={"value": value},
            idempotent=idempotent,
            idempotency_key=idempotency_key,
            conflict_scope=scope,
            external_effect_possible=external_effect_possible,
        )

    def run_duplicate_schedule(self, order: tuple[str, str]) -> tuple[str, int, str]:
        store = self.store()
        coordinator = MultiWriterCoordinator(store)
        first_id, second_id = order
        first_lease = coordinator.acquire(self.writer(first_id), expected_epoch=None)
        first_intent = self.intent(
            first_id,
            f"intent:{first_id}",
            7,
            idempotent=True,
            idempotency_key="dedupe:7",
            scope="canonical:shared",
            external_effect_possible=False,
        )
        first = coordinator.commit(first_intent, first_lease, expected_revision=0)
        second_lease = coordinator.acquire(self.writer(second_id), expected_epoch=1)
        second_intent = self.intent(
            second_id,
            f"intent:{second_id}",
            7,
            idempotent=True,
            idempotency_key="dedupe:7",
            scope="canonical:shared",
            external_effect_possible=False,
        )
        second = coordinator.commit(second_intent, second_lease, expected_revision=1)
        self.assertEqual(first.status, CommitDecisionStatus.COMMITTED)
        self.assertEqual(second.status, CommitDecisionStatus.DUPLICATE_CONVERGED)
        projection = coordinator.reconstruct()
        self.assertEqual(len(projection.committed_intents), 1)
        return projection.committed_intents[0].semantic_digest, store.current_revision(), second.status.value

    def run_conflict_schedule(self, order: tuple[str, str]) -> tuple[str, str, int]:
        store = self.store()
        coordinator = MultiWriterCoordinator(store)
        first_id, second_id = order
        values = {"w1": 1, "w2": 2}
        first_lease = coordinator.acquire(self.writer(first_id), expected_epoch=None)
        first = coordinator.commit(
            self.intent(
                first_id,
                f"effect:{first_id}",
                values[first_id],
                idempotent=False,
                idempotency_key=None,
                scope="remote:deploy",
                external_effect_possible=True,
            ),
            first_lease,
            expected_revision=0,
        )
        second_lease = coordinator.acquire(self.writer(second_id), expected_epoch=1)
        second = coordinator.commit(
            self.intent(
                second_id,
                f"effect:{second_id}",
                values[second_id],
                idempotent=False,
                idempotency_key=None,
                scope="remote:deploy",
                external_effect_possible=True,
            ),
            second_lease,
            expected_revision=1,
        )
        self.assertEqual(first.status, CommitDecisionStatus.COMMITTED)
        self.assertEqual(second.status, CommitDecisionStatus.CONFLICT_RECONCILIATION_REQUIRED)
        self.assertTrue(second.conflict.external_effect_ambiguity)
        projection = coordinator.reconstruct()
        self.assertEqual(len(projection.conflicts), 1)
        return second.status.value, projection.conflicts[0].canonical_digest, store.current_revision()

    def run_same_predecessor_schedule(self, order: tuple[str, str]) -> tuple[int, int]:
        store = self.store()
        coordinators = {writer_id: MultiWriterCoordinator(store) for writer_id in order}
        successes = 0
        conflicts = 0
        for writer_id in order:
            try:
                coordinators[writer_id].acquire(self.writer(writer_id), expected_epoch=None)
                successes += 1
            except StorageConflict:
                conflicts += 1
        return successes, conflicts

    def test_forward_reverse_idempotent_schedule_has_same_semantic_result(self) -> None:
        forward = self.run_duplicate_schedule(("w1", "w2"))
        reverse = self.run_duplicate_schedule(("w2", "w1"))
        self.assertEqual(forward, reverse)
        self.assertEqual(forward, self.run_duplicate_schedule(("w1", "w2")))
        self.assertEqual(reverse, self.run_duplicate_schedule(("w2", "w1")))

    def test_forward_reverse_non_idempotent_schedule_has_same_explicit_conflict(self) -> None:
        forward = self.run_conflict_schedule(("w1", "w2"))
        reverse = self.run_conflict_schedule(("w2", "w1"))
        self.assertEqual(forward, reverse)
        self.assertEqual(forward, self.run_conflict_schedule(("w1", "w2")))
        self.assertEqual(reverse, self.run_conflict_schedule(("w2", "w1")))

    def test_forward_reverse_same_predecessor_schedule_has_exactly_one_canonical_epoch_winner(self) -> None:
        forward = self.run_same_predecessor_schedule(("w1", "w2"))
        reverse = self.run_same_predecessor_schedule(("w2", "w1"))
        self.assertEqual(forward, (1, 1))
        self.assertEqual(reverse, (1, 1))
        self.assertEqual(forward, self.run_same_predecessor_schedule(("w1", "w2")))
        self.assertEqual(reverse, self.run_same_predecessor_schedule(("w2", "w1")))


if __name__ == "__main__":
    unittest.main()
