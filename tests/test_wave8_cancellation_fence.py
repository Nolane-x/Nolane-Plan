from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from nolane_plan import PlanKernel
from nolane_plan.actions import ActionIntent, AuthorityGrant
from nolane_plan.execution import (
    ActionTransactionLedger,
    ReconciliationEvidence,
    TransactionState,
)
from nolane_plan.types import AuthorizationError, ReplayError


class CountingAdapter:
    def __init__(self) -> None:
        self.calls = 0

    def execute(self, action, principal_ref):
        self.calls += 1
        return {
            "executing_principal_ref": principal_ref,
            "ok": True,
            "postconditions_verified": True,
            "state_patch": {},
            "outcome_known": True,
        }


class Wave8CancellationFenceTests(unittest.TestCase):
    def make_kernel(self, *, idempotent: bool = False):
        root = Path(tempfile.mkdtemp())
        kernel = PlanKernel.create(root, "ship")
        kernel.propose_action(ActionIntent("action:deploy", "deploy", idempotent=idempotent))
        kernel.add_grant(AuthorityGrant("grant:deploy", "agent:a", frozenset({"deploy"})))
        authorization = kernel.authorize(
            "action:deploy",
            "agent:a",
            ("grant:deploy",),
            1,
        )
        return kernel, authorization

    @staticmethod
    def reconciliation_evidence(
        transaction_id: str,
        *,
        outcome_applied: bool,
        evidence_id: str,
    ) -> ReconciliationEvidence:
        return ReconciliationEvidence.create(
            evidence_id=evidence_id,
            transaction_id=transaction_id,
            action_id="action:deploy",
            authorization_id="auth:deploy",
            canonical_principal_ref="agent:a",
            adapter_id="adapter:deploy",
            adapter_revision=1,
            outcome_applied=outcome_applied,
            source="provider-status",
            observed_at=10,
            assurance=0.95,
        )

    def test_cancel_before_dispatch_is_terminal_and_adapter_is_never_called(self):
        kernel, authorization = self.make_kernel()
        adapter = CountingAdapter()

        cancelled = kernel.cancel_authorized_action(
            authorization.id,
            detail="operator cancelled before side effect",
        )

        self.assertEqual(cancelled.state, TransactionState.CANCELLED_PRE_DISPATCH)
        self.assertEqual(cancelled.detail, "operator cancelled before side effect")
        with self.assertRaises(AuthorizationError):
            kernel.dispatch(authorization.id, "agent:a", adapter, 2)
        self.assertEqual(adapter.calls, 0)

    def test_cancel_after_durable_dispatch_is_pending_not_clean_cancelled(self):
        kernel, authorization = self.make_kernel()
        tx = kernel.transaction_for_authorization(authorization.id)
        kernel.transactions.record_dispatch(tx.id, "adapter:deploy", 1)

        pending = kernel.cancel_authorized_action(
            authorization.id,
            detail="cancel raced with durable dispatch",
        )

        self.assertEqual(pending.state, TransactionState.CANCELLATION_PENDING)
        self.assertNotEqual(pending.state, TransactionState.CANCELLED_PRE_DISPATCH)

    def test_non_idempotent_cancellation_pending_blocks_retry(self):
        ledger = ActionTransactionLedger()
        ledger.authorized("tx:deploy", "action:deploy", "auth:deploy", "agent:a", idempotent=False)
        ledger.record_dispatch("tx:deploy", "adapter:deploy", 1)
        ledger.request_cancellation_after_dispatch("tx:deploy", "operator requested stop")

        with self.assertRaises(AuthorizationError):
            ledger.assert_retry_allowed("tx:deploy")

    def test_cancellation_pending_reconciles_not_applied_with_exact_evidence(self):
        ledger = ActionTransactionLedger()
        ledger.authorized("tx:deploy", "action:deploy", "auth:deploy", "agent:a", idempotent=False)
        ledger.record_dispatch("tx:deploy", "adapter:deploy", 1)
        ledger.request_cancellation_after_dispatch("tx:deploy", "operator requested stop")
        evidence = self.reconciliation_evidence(
            "tx:deploy",
            outcome_applied=False,
            evidence_id="evidence:not-applied",
        )

        result = ledger.reconcile_with_evidence("tx:deploy", evidence)

        self.assertEqual(result.state, TransactionState.RECONCILED_NOT_APPLIED)

    def test_cancellation_pending_reconciles_applied_with_exact_evidence(self):
        ledger = ActionTransactionLedger()
        ledger.authorized("tx:deploy", "action:deploy", "auth:deploy", "agent:a", idempotent=False)
        ledger.record_dispatch("tx:deploy", "adapter:deploy", 1)
        ledger.request_cancellation_after_dispatch("tx:deploy", "operator requested stop")
        evidence = self.reconciliation_evidence(
            "tx:deploy",
            outcome_applied=True,
            evidence_id="evidence:applied",
        )

        result = ledger.reconcile_with_evidence("tx:deploy", evidence)

        self.assertEqual(result.state, TransactionState.RECONCILED_APPLIED)

    def test_snapshot_restart_preserves_pending_cancellation(self):
        kernel, authorization = self.make_kernel()
        tx = kernel.transaction_for_authorization(authorization.id)
        kernel.transactions.record_dispatch(tx.id, "adapter:deploy", 1)
        kernel.cancel_authorized_action(authorization.id, detail="pending at snapshot")
        kernel.save_snapshot()

        restored = PlanKernel.open(kernel.root)

        self.assertEqual(
            restored.transaction_for_authorization(authorization.id).state,
            TransactionState.CANCELLATION_PENDING,
        )
        self.assertEqual(
            restored.transaction_for_authorization(authorization.id).detail,
            "pending at snapshot",
        )

    def test_post_snapshot_cancellation_event_replays_exactly(self):
        kernel, authorization = self.make_kernel()
        kernel.save_snapshot()
        expected = kernel.cancel_authorized_action(
            authorization.id,
            detail="cancelled in suffix",
        )

        restored = PlanKernel.open(kernel.root)
        actual = restored.transaction_for_authorization(authorization.id)

        self.assertEqual(actual.state, expected.state)
        self.assertEqual(actual.detail, expected.detail)

    def test_tampered_cancellation_resulting_state_fails_closed(self):
        kernel, authorization = self.make_kernel()
        tx = kernel.transaction_for_authorization(authorization.id)
        kernel.save_snapshot()
        kernel._record(
            "action.cancellation_recorded",
            {
                "transaction_id": tx.id,
                "authorization_id": authorization.id,
                "resulting_state": TransactionState.COMMITTED.value,
                "detail": "tampered cancellation",
            },
        )

        with self.assertRaises(ReplayError):
            PlanKernel.open(kernel.root)


if __name__ == "__main__":
    unittest.main()
