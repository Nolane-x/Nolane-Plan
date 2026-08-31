from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from nolane_plan import PlanKernel
from nolane_plan.actions import ActionIntent, AuthorityGrant
from nolane_plan.execution import AdapterProfile
from nolane_plan.execution_contract import (
    CancellationClass,
    DispatchAcknowledgementClass,
    ExecutionContract,
    IdempotencyGuaranteeClass,
    OutcomeFinalityClass,
)
from nolane_plan.multiwriter import MultiWriterCoordinator, WriteIntent, WriterIdentity
from nolane_plan.production_store import InMemoryProductionStore, StorageCapabilityProfile
from nolane_plan.replay_registry import DEFAULT_REPLAY_REGISTRY
from nolane_plan.types import AuthorizationError, RiskClass


class Wave9MultiWriterRuntimeTests(unittest.TestCase):
    def strong_store(self) -> InMemoryProductionStore:
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

    def writer(self, writer_id: str, principal_ref: str = "agent") -> WriterIdentity:
        return WriterIdentity.create(
            writer_id=writer_id,
            principal_ref=principal_ref,
            process_instance_ref=f"process:{writer_id}:1",
        )

    def contract(self) -> ExecutionContract:
        return ExecutionContract.create(
            adapter_id="remote",
            adapter_revision=1,
            dispatch_acknowledgement=DispatchAcknowledgementClass.DURABLE_REMOTE,
            idempotency_guarantee=IdempotencyGuaranteeClass.REMOTE_DEDUPLICATED,
            deduplication_keys=True,
            remote_fencing_tokens=True,
            cancellation_class=CancellationClass.FENCED_EFFECT,
            cancellation_ack_assurance=0.9,
            compensation_supported=True,
            reconciliation_observable=True,
            outcome_finality=OutcomeFinalityClass.OBSERVABLE,
        )

    def prepare_authorization(self, kernel: PlanKernel):
        kernel.register_adapter(AdapterProfile("remote", 1, False, False, 1.0))
        kernel.register_execution_contract(self.contract())
        action = ActionIntent("effect", "effect", RiskClass.REVERSIBLE, idempotent=False)
        kernel.propose_action(action)
        kernel.add_grant(AuthorityGrant("grant", "agent", frozenset({"effect"})))
        authorization = kernel.authorize("effect", "agent", ("grant",), 1, adapter_id="remote")
        kernel.bind_authorization_execution_contract(authorization.id)
        return authorization

    def test_kernel_exposes_multiwriter_runtime_surface_and_events(self) -> None:
        for name in (
            "acquire_authority_epoch",
            "conditional_correctness_commit",
            "bind_authorization_authority_epoch",
            "assert_authorization_authority_epoch_current",
            "dispatch_epoch_bound",
        ):
            self.assertTrue(hasattr(PlanKernel, name), name)
        expected = {
            "writer.epoch_acquired",
            "writer.conditional_commit",
            "writer.conflict_recorded",
            "action.authorization_epoch_bound",
        }
        self.assertTrue(expected.issubset(DEFAULT_REPLAY_REGISTRY.event_types))

    def test_epoch_transition_invalidates_old_authorization_until_explicit_rebind(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            kernel = PlanKernel.create(Path(root), "epoch-bound authority")
            authorization = self.prepare_authorization(kernel)
            store = self.strong_store()
            coordinator = MultiWriterCoordinator(store)
            lease1 = kernel.acquire_authority_epoch(coordinator, self.writer("w1"), None)
            first = kernel.bind_authorization_authority_epoch(authorization.id, lease1)
            self.assertEqual(first.epoch_digest, lease1.epoch.canonical_digest)
            self.assertEqual(
                kernel.assert_authorization_authority_epoch_current(authorization.id, store).canonical_digest,
                first.canonical_digest,
            )

            lease2 = kernel.acquire_authority_epoch(coordinator, self.writer("w2"), 1)
            with self.assertRaises(AuthorizationError):
                kernel.assert_authorization_authority_epoch_current(authorization.id, store)

            rebound = kernel.bind_authorization_authority_epoch(authorization.id, lease2)
            self.assertNotEqual(rebound.canonical_digest, first.canonical_digest)
            self.assertEqual(
                kernel.assert_authorization_authority_epoch_current(authorization.id, store).epoch_digest,
                lease2.epoch.canonical_digest,
            )

    def test_authorization_epoch_binding_requires_same_acting_principal(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            kernel = PlanKernel.create(Path(root), "principal bound epoch")
            authorization = self.prepare_authorization(kernel)
            store = self.strong_store()
            coordinator = MultiWriterCoordinator(store)
            lease = kernel.acquire_authority_epoch(coordinator, self.writer("w1", principal_ref="other"), None)
            with self.assertRaises(AuthorizationError):
                kernel.bind_authorization_authority_epoch(authorization.id, lease)

    def test_conditional_correctness_commit_records_store_authority_after_cas(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            kernel = PlanKernel.create(Path(root), "conditional commit")
            store = self.strong_store()
            coordinator = MultiWriterCoordinator(store)
            lease = kernel.acquire_authority_epoch(coordinator, self.writer("w1"), None)
            intent = WriteIntent.create(
                intent_id="intent:1",
                writer_id="w1",
                operation_kind="canonical_update",
                payload={"value": 1},
                idempotent=True,
                idempotency_key="dedupe:1",
                conflict_scope="canonical:mission",
                external_effect_possible=False,
            )
            decision = kernel.conditional_correctness_commit(
                coordinator,
                intent,
                lease,
                expected_revision=0,
            )
            self.assertEqual(store.current_revision(), 1)
            self.assertEqual(decision.storage_revision, 1)
            self.assertEqual(kernel.journal.entries()[-1].event_type, "writer.conditional_commit")

    def test_post_snapshot_epoch_binding_suffix_replays_without_recreating_external_store(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            path = Path(root)
            kernel = PlanKernel.create(path, "replay epoch binding")
            kernel.save_snapshot()
            authorization = self.prepare_authorization(kernel)
            store = self.strong_store()
            coordinator = MultiWriterCoordinator(store)
            lease = kernel.acquire_authority_epoch(coordinator, self.writer("w1"), None)
            binding = kernel.bind_authorization_authority_epoch(authorization.id, lease)

            restored = PlanKernel.open(path)
            self.assertEqual(
                restored.authorization_authority_epoch_bindings[authorization.id].canonical_digest,
                binding.canonical_digest,
            )
            self.assertEqual(
                restored.observed_authority_epochs[lease.epoch.canonical_digest].canonical_digest,
                lease.canonical_digest,
            )


if __name__ == "__main__":
    unittest.main()
