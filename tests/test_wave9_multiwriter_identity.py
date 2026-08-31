from __future__ import annotations

import unittest

from nolane_plan.multiwriter import MultiWriterCoordinator, WriterIdentity, WriterLease
from nolane_plan.production_store import InMemoryProductionStore, StorageCapabilityProfile


class Wave9MultiWriterIdentityTests(unittest.TestCase):
    def test_epoch_and_lease_bind_full_writer_identity_not_only_writer_id(self) -> None:
        store = InMemoryProductionStore(
            StorageCapabilityProfile.create(
                backend_id="wave9-identity-binding",
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
        coordinator = MultiWriterCoordinator(store)
        original = WriterIdentity.create(
            writer_id="w1",
            principal_ref="principal:one",
            process_instance_ref="process:one",
        )
        impersonator = WriterIdentity.create(
            writer_id="w1",
            principal_ref="principal:two",
            process_instance_ref="process:two",
        )
        lease = coordinator.acquire(original, expected_epoch=None)
        self.assertEqual(lease.epoch.writer_identity_digest, original.canonical_digest)
        with self.assertRaises(ValueError):
            WriterLease.create(writer=impersonator, epoch=lease.epoch)


if __name__ == "__main__":
    unittest.main()
