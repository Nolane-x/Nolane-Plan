from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from nolane_plan import PlanKernel
from nolane_plan.actions import ActionIntent, AuthorityGrant
from nolane_plan.execution import AdapterProfile, TransactionState
from nolane_plan.execution_contract import (
    CancellationClass,
    CompensationRecord,
    CompensationStatus,
    DispatchAcknowledgementClass,
    ExecutionContract,
    IdempotencyGuaranteeClass,
    OutcomeFinalityClass,
    RemoteCancellationAcknowledgement,
)
from nolane_plan.types import AuthorizationError, RiskClass


class Wave9ExecutionContractTests(unittest.TestCase):
    def contract(
        self,
        *,
        cancellation: CancellationClass = CancellationClass.REMOTE_ACKNOWLEDGED,
        remote_fencing_tokens: bool = False,
        compensation_supported: bool = True,
    ) -> ExecutionContract:
        return ExecutionContract.create(
            adapter_id="remote",
            adapter_revision=1,
            dispatch_acknowledgement=DispatchAcknowledgementClass.DURABLE_REMOTE,
            idempotency_guarantee=IdempotencyGuaranteeClass.REMOTE_DEDUPLICATED,
            deduplication_keys=True,
            remote_fencing_tokens=remote_fencing_tokens,
            cancellation_class=cancellation,
            cancellation_ack_assurance=0.9 if cancellation in {CancellationClass.REMOTE_ACKNOWLEDGED, CancellationClass.FENCED_EFFECT} else 0.0,
            compensation_supported=compensation_supported,
            reconciliation_observable=True,
            outcome_finality=OutcomeFinalityClass.OBSERVABLE,
        )

    def kernel_with_authorization(self, contract: ExecutionContract):
        temp = tempfile.TemporaryDirectory()
        kernel = PlanKernel.create(Path(temp.name), "exercise execution contract")
        kernel.register_adapter(AdapterProfile("remote", 1, False, False, 1.0))
        kernel.register_execution_contract(contract)
        action = ActionIntent("effect", "effect", RiskClass.REVERSIBLE, idempotent=False)
        kernel.propose_action(action)
        kernel.add_grant(AuthorityGrant("grant", "agent", frozenset({"effect"})))
        authorization = kernel.authorize("effect", "agent", ("grant",), 1, adapter_id="remote")
        kernel.bind_authorization_execution_contract(authorization.id)
        return temp, kernel, authorization

    def acknowledgement(
        self,
        kernel: PlanKernel,
        authorization_id: str,
        *,
        authority_epoch: int = 7,
        effect_prevented: bool = True,
        fence_excludes_stale_effect: bool = False,
    ) -> RemoteCancellationAcknowledgement:
        tx = kernel.transaction_for_authorization(authorization_id)
        return RemoteCancellationAcknowledgement.create(
            acknowledgement_id=f"ack-{authority_epoch}-{int(fence_excludes_stale_effect)}",
            transaction_id=tx.id,
            action_id=tx.action_id,
            authorization_id=authorization_id,
            canonical_principal_ref=tx.principal_ref,
            adapter_id="remote",
            adapter_revision=1,
            authority_epoch=authority_epoch,
            effect_prevented=effect_prevented,
            fence_excludes_stale_effect=fence_excludes_stale_effect,
            observed_at=2,
            assurance=0.95,
            provenance="remote-control-plane",
        )

    def make_pending(self, kernel: PlanKernel, authorization_id: str) -> None:
        tx = kernel.transaction_for_authorization(authorization_id)
        kernel.transactions.record_dispatch(tx.id, "remote", 1)
        pending = kernel.cancel_authorized_action(authorization_id, detail="operator cancellation")
        self.assertEqual(pending.state, TransactionState.CANCELLATION_PENDING)

    def test_execution_contract_is_exact_adapter_revision_bound_and_non_rebindable(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            kernel = PlanKernel.create(Path(root), "contract binding")
            kernel.register_adapter(AdapterProfile("remote", 1, False, False, 1.0))
            first = kernel.register_execution_contract(self.contract())
            self.assertEqual(first.adapter_revision, 1)

            changed = ExecutionContract.create(
                adapter_id="remote",
                adapter_revision=1,
                dispatch_acknowledgement=DispatchAcknowledgementClass.DURABLE_REMOTE,
                idempotency_guarantee=IdempotencyGuaranteeClass.REMOTE_DEDUPLICATED,
                deduplication_keys=True,
                remote_fencing_tokens=False,
                cancellation_class=CancellationClass.REMOTE_ACKNOWLEDGED,
                cancellation_ack_assurance=1.0,
                compensation_supported=False,
                reconciliation_observable=True,
                outcome_finality=OutcomeFinalityClass.FINAL,
            )
            with self.assertRaises(AuthorizationError):
                kernel.register_execution_contract(changed)

    def test_adapter_revision_drift_invalidates_bound_execution_contract(self) -> None:
        temp, kernel, authorization = self.kernel_with_authorization(self.contract())
        self.addCleanup(temp.cleanup)
        self.assertEqual(
            kernel.assert_authorization_execution_contract_current(authorization.id).canonical_digest,
            self.contract().canonical_digest,
        )
        kernel.register_adapter(AdapterProfile("remote", 2, False, False, 1.0))
        with self.assertRaises(AuthorizationError):
            kernel.assert_authorization_execution_contract_current(authorization.id)

    def test_acknowledged_remote_cancellation_closes_only_exact_pending_transaction(self) -> None:
        temp, kernel, authorization = self.kernel_with_authorization(self.contract())
        self.addCleanup(temp.cleanup)
        self.make_pending(kernel, authorization.id)
        acknowledgement = self.acknowledgement(kernel, authorization.id, authority_epoch=7)
        result = kernel.record_remote_cancellation_acknowledgement(
            authorization.id,
            acknowledgement,
            authority_epoch=7,
        )
        self.assertEqual(result.state, TransactionState.RECONCILED_NOT_APPLIED)

    def test_wrong_epoch_cancellation_acknowledgement_fails_closed_and_keeps_ambiguity(self) -> None:
        temp, kernel, authorization = self.kernel_with_authorization(self.contract())
        self.addCleanup(temp.cleanup)
        self.make_pending(kernel, authorization.id)
        acknowledgement = self.acknowledgement(kernel, authorization.id, authority_epoch=6)
        with self.assertRaises(AuthorizationError):
            kernel.record_remote_cancellation_acknowledgement(
                authorization.id,
                acknowledgement,
                authority_epoch=7,
            )
        self.assertEqual(
            kernel.transaction_for_authorization(authorization.id).state,
            TransactionState.CANCELLATION_PENDING,
        )

    def test_best_effort_remote_cancellation_never_becomes_clean(self) -> None:
        contract = self.contract(cancellation=CancellationClass.REMOTE_BEST_EFFORT)
        temp, kernel, authorization = self.kernel_with_authorization(contract)
        self.addCleanup(temp.cleanup)
        self.make_pending(kernel, authorization.id)
        acknowledgement = self.acknowledgement(kernel, authorization.id)
        with self.assertRaises(AuthorizationError):
            kernel.record_remote_cancellation_acknowledgement(
                authorization.id,
                acknowledgement,
                authority_epoch=7,
            )
        self.assertEqual(
            kernel.transaction_for_authorization(authorization.id).state,
            TransactionState.CANCELLATION_PENDING,
        )

    def test_fenced_effect_requires_stale_effect_exclusion_evidence(self) -> None:
        contract = self.contract(
            cancellation=CancellationClass.FENCED_EFFECT,
            remote_fencing_tokens=True,
        )
        temp, kernel, authorization = self.kernel_with_authorization(contract)
        self.addCleanup(temp.cleanup)
        self.make_pending(kernel, authorization.id)
        weak_ack = self.acknowledgement(kernel, authorization.id, fence_excludes_stale_effect=False)
        with self.assertRaises(AuthorizationError):
            kernel.record_remote_cancellation_acknowledgement(
                authorization.id,
                weak_ack,
                authority_epoch=7,
            )
        strong_ack = self.acknowledgement(kernel, authorization.id, fence_excludes_stale_effect=True)
        result = kernel.record_remote_cancellation_acknowledgement(
            authorization.id,
            strong_ack,
            authority_epoch=7,
        )
        self.assertEqual(result.state, TransactionState.RECONCILED_NOT_APPLIED)

    def test_compensation_is_a_distinct_effect_and_never_rewrites_original_outcome(self) -> None:
        record = CompensationRecord.create(
            record_id="comp-1",
            original_transaction_id="tx-original",
            compensation_transaction_id="tx-compensation",
            compensation_authorization_id="auth-compensation",
            original_outcome_applied=True,
        )
        unknown = record.transition(CompensationStatus.UNKNOWN, evidence_ref="evidence-unknown")
        applied = unknown.transition(CompensationStatus.APPLIED, evidence_ref="evidence-applied")
        self.assertTrue(applied.original_outcome_applied)
        self.assertEqual(applied.original_transaction_id, "tx-original")
        self.assertEqual(applied.compensation_transaction_id, "tx-compensation")
        with self.assertRaises(AuthorizationError):
            applied.transition(CompensationStatus.FAILED, evidence_ref="late-conflict")

    def test_unsupported_cancellation_capability_is_explicit(self) -> None:
        contract = self.contract(cancellation=CancellationClass.UNSUPPORTED)
        self.assertEqual(contract.cancellation_class, CancellationClass.UNSUPPORTED)
        self.assertTrue(contract.require_for_strong_dispatch(action_idempotent=False))


if __name__ == "__main__":
    unittest.main()
