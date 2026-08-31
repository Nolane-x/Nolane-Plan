from __future__ import annotations

import unittest

from nolane_plan.production_store import (
    AuthorityEpoch,
    InMemoryProductionStore,
    StorageCapabilityProfile,
    StorageConflict,
    StorageSupport,
    UnsupportedStorageCapability,
)


class Wave9ProductionStoreTests(unittest.TestCase):
    def strong_profile(self) -> StorageCapabilityProfile:
        return StorageCapabilityProfile.create(
            backend_id="memory-strong",
            revision=1,
            atomic_replace=True,
            durable_acknowledgement=True,
            compare_and_swap=True,
            fencing_tokens=True,
            transactional_batch=True,
            destructive_delete=True,
            crash_recovery_durable=True,
        )

    def test_strong_multiwriter_requires_cas_fencing_and_durable_ack(self) -> None:
        profile = self.strong_profile()
        self.assertEqual(profile.support, StorageSupport.STRONG_MULTI_WRITER)
        self.assertTrue(profile.require_strong_multiwriter())

        for field in ("compare_and_swap", "fencing_tokens", "durable_acknowledgement"):
            values = dict(
                backend_id=f"missing-{field}",
                revision=1,
                atomic_replace=True,
                durable_acknowledgement=True,
                compare_and_swap=True,
                fencing_tokens=True,
                transactional_batch=True,
                destructive_delete=True,
                crash_recovery_durable=True,
            )
            values[field] = False
            weak = StorageCapabilityProfile.create(**values)
            self.assertNotEqual(weak.support, StorageSupport.STRONG_MULTI_WRITER)
            with self.assertRaises(UnsupportedStorageCapability):
                weak.require_strong_multiwriter()

    def test_single_writer_profile_is_explicit_not_promoted_to_strong(self) -> None:
        profile = StorageCapabilityProfile.create(
            backend_id="filesystem-reference",
            revision=1,
            atomic_replace=True,
            durable_acknowledgement=True,
            compare_and_swap=False,
            fencing_tokens=False,
            transactional_batch=False,
            destructive_delete=True,
            crash_recovery_durable=True,
        )
        self.assertEqual(profile.support, StorageSupport.SINGLE_WRITER)
        with self.assertRaises(UnsupportedStorageCapability):
            InMemoryProductionStore(profile, require_strong_multiwriter=True)

    def test_epoch_acquisition_is_monotonic_and_writer_bound(self) -> None:
        store = InMemoryProductionStore(self.strong_profile(), require_strong_multiwriter=True)
        first = store.acquire_epoch("writer-a", expected_epoch=None)
        second = store.acquire_epoch("writer-b", expected_epoch=first.epoch)

        self.assertEqual(first.epoch, 1)
        self.assertEqual(first.predecessor_epoch, None)
        self.assertEqual(second.epoch, 2)
        self.assertEqual(second.predecessor_epoch, 1)
        self.assertEqual(second.writer_id, "writer-b")
        self.assertNotEqual(first.canonical_digest, second.canonical_digest)

        with self.assertRaises(StorageConflict):
            store.acquire_epoch("writer-c", expected_epoch=1)

    def test_stale_epoch_cannot_commit(self) -> None:
        store = InMemoryProductionStore(self.strong_profile(), require_strong_multiwriter=True)
        first = store.acquire_epoch("writer-a", expected_epoch=None)
        store.acquire_epoch("writer-b", expected_epoch=first.epoch)

        with self.assertRaises(StorageConflict):
            store.conditional_commit(first, expected_revision=0, payload={"value": "stale"})
        self.assertEqual(store.current_revision(), 0)
        self.assertEqual(store.read_payload(), {})

    def test_conditional_commit_is_exact_revision_bound(self) -> None:
        store = InMemoryProductionStore(self.strong_profile(), require_strong_multiwriter=True)
        epoch = store.acquire_epoch("writer-a", expected_epoch=None)
        receipt = store.conditional_commit(epoch, expected_revision=0, payload={"value": 1})

        self.assertEqual(receipt.expected_revision, 0)
        self.assertEqual(receipt.committed_revision, 1)
        self.assertEqual(receipt.epoch, epoch.epoch)
        self.assertEqual(receipt.writer_id, "writer-a")
        self.assertTrue(receipt.durable_acknowledged)
        self.assertEqual(store.current_revision(), 1)
        self.assertEqual(store.read_payload(), {"value": 1})

        with self.assertRaises(StorageConflict):
            store.conditional_commit(epoch, expected_revision=0, payload={"value": 2})
        self.assertEqual(store.read_payload(), {"value": 1})

    def test_epoch_and_receipt_digests_are_deterministic_and_semantic(self) -> None:
        profile = self.strong_profile()
        store_a = InMemoryProductionStore(profile, require_strong_multiwriter=True)
        store_b = InMemoryProductionStore(profile, require_strong_multiwriter=True)
        epoch_a = store_a.acquire_epoch("writer-a", expected_epoch=None)
        epoch_b = store_b.acquire_epoch("writer-a", expected_epoch=None)
        receipt_a = store_a.conditional_commit(epoch_a, expected_revision=0, payload={"b": 2, "a": 1})
        receipt_b = store_b.conditional_commit(epoch_b, expected_revision=0, payload={"a": 1, "b": 2})

        self.assertEqual(epoch_a.canonical_digest, epoch_b.canonical_digest)
        self.assertEqual(receipt_a.canonical_digest, receipt_b.canonical_digest)
        self.assertEqual(receipt_a.payload_digest, receipt_b.payload_digest)

        store_c = InMemoryProductionStore(profile, require_strong_multiwriter=True)
        epoch_c = store_c.acquire_epoch("writer-c", expected_epoch=None)
        self.assertNotEqual(epoch_a.canonical_digest, epoch_c.canonical_digest)

    def test_invalid_epoch_shape_fails_closed(self) -> None:
        with self.assertRaises(ValueError):
            AuthorityEpoch.create(
                backend_id="memory-strong",
                backend_revision=1,
                epoch=0,
                predecessor_epoch=None,
                writer_id="writer-a",
                acquisition_revision=0,
            )
        with self.assertRaises(ValueError):
            AuthorityEpoch.create(
                backend_id="memory-strong",
                backend_revision=1,
                epoch=2,
                predecessor_epoch=0,
                writer_id="writer-a",
                acquisition_revision=0,
            )


if __name__ == "__main__":
    unittest.main()
