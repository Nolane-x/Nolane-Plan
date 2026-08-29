from __future__ import annotations

import unittest

from nolane_plan.execution import (
    ActionTransactionLedger,
    AdapterProfile,
    TransactionState,
)
from nolane_plan.types import AuthorizationError, RiskClass


class ExecutionRecoveryWave2Tests(unittest.TestCase):
    def test_non_idempotent_ambiguous_outcome_requires_reconciliation(self):
        ledger = ActionTransactionLedger()
        tx = ledger.authorized(
            transaction_id="tx1",
            action_id="charge",
            authorization_id="auth1",
            principal_ref="agent:p0",
            idempotent=False,
        )
        ledger.record_dispatch(tx.id, adapter_id="payments", adapter_revision=1)
        ledger.record_unknown_outcome(tx.id, "transport disconnected after dispatch")

        self.assertEqual(ledger.get(tx.id).state, TransactionState.RECONCILIATION_REQUIRED)
        with self.assertRaises(AuthorizationError):
            ledger.assert_retry_allowed(tx.id)

    def test_trusted_reconciliation_can_close_unknown_outcome(self):
        ledger = ActionTransactionLedger()
        tx = ledger.authorized("tx2", "deploy", "auth2", "agent:p0", idempotent=False)
        ledger.record_dispatch(tx.id, "deploy-api", 1)
        ledger.record_unknown_outcome(tx.id, "timeout")
        ledger.reconcile(tx.id, outcome_applied=True, trusted=True)
        self.assertEqual(ledger.get(tx.id).state, TransactionState.RECONCILED_APPLIED)

    def test_executor_sensitive_action_requires_principal_attestation(self):
        opaque = AdapterProfile(
            adapter_id="opaque",
            revision=1,
            principal_attestation=False,
            dispatch_fence=False,
            postcondition_assurance=1.0,
        )
        with self.assertRaises(AuthorizationError):
            opaque.require_for(RiskClass.CONSEQUENTIAL, executor_sensitive=True)

    def test_adapter_revision_is_part_of_capability_identity(self):
        a = AdapterProfile("tool", 1, True, True, 1.0)
        b = AdapterProfile("tool", 2, True, True, 1.0)
        self.assertNotEqual(a.capability_digest, b.capability_digest)


if __name__ == "__main__":
    unittest.main()
