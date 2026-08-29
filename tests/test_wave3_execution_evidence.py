from __future__ import annotations

import unittest

from nolane_plan.execution import (
    ActionTransactionLedger,
    DispatchAttestation,
    ReconciliationEvidence,
    TransactionState,
    verify_dispatch_attestation,
)
from nolane_plan.identity import PrincipalAttestation, PrincipalIdentityLedger
from nolane_plan.types import AuthorizationError


class Wave3ExecutionEvidenceTests(unittest.TestCase):
    def _identity_binding(self):
        identities = PrincipalIdentityLedger()
        attestation = PrincipalAttestation.create(
            attestation_id="identity-a",
            canonical_principal_ref="agent:a",
            source="host-runtime",
            source_subject="subject-a",
            revision=1,
            issued_at=1,
            valid_until=100,
            assurance=0.95,
            session_ref="session-1",
        )
        binding = identities.accept(attestation, now=5)
        return identities, binding

    def _transaction(self):
        ledger = ActionTransactionLedger()
        ledger.authorized("tx-1", "action-1", "auth-1", "agent:a", idempotent=False)
        ledger.record_dispatch("tx-1", "adapter-1", 3)
        ledger.record_unknown_outcome("tx-1", "transport timeout after dispatch")
        return ledger

    def test_dispatch_attestation_binds_exact_principal_and_adapter_revision(self):
        identities, binding = self._identity_binding()
        good = DispatchAttestation.create(
            attestation_id="dispatch-1",
            authorization_id="auth-1",
            transaction_id="tx-1",
            action_id="action-1",
            adapter_id="adapter-1",
            adapter_revision=3,
            canonical_principal_ref="agent:a",
            principal_attestation_id="identity-a",
            observed_at=20,
            assurance=0.95,
            provenance="adapter:fence",
        )
        self.assertTrue(
            verify_dispatch_attestation(
                good,
                authorization_id="auth-1",
                transaction_id="tx-1",
                action_id="action-1",
                expected_principal_ref="agent:a",
                adapter_id="adapter-1",
                adapter_revision=3,
                principal_binding=binding,
                minimum_assurance=0.8,
            )
        )

        wrong_principal = DispatchAttestation.create(
            attestation_id="dispatch-wrong-principal",
            authorization_id="auth-1",
            transaction_id="tx-1",
            action_id="action-1",
            adapter_id="adapter-1",
            adapter_revision=3,
            canonical_principal_ref="agent:b",
            principal_attestation_id="identity-a",
            observed_at=20,
            assurance=0.95,
            provenance="adapter:fence",
        )
        with self.assertRaises(AuthorizationError):
            verify_dispatch_attestation(
                wrong_principal,
                authorization_id="auth-1",
                transaction_id="tx-1",
                action_id="action-1",
                expected_principal_ref="agent:a",
                adapter_id="adapter-1",
                adapter_revision=3,
                principal_binding=binding,
                minimum_assurance=0.8,
            )

        wrong_revision = DispatchAttestation.create(
            attestation_id="dispatch-wrong-revision",
            authorization_id="auth-1",
            transaction_id="tx-1",
            action_id="action-1",
            adapter_id="adapter-1",
            adapter_revision=4,
            canonical_principal_ref="agent:a",
            principal_attestation_id="identity-a",
            observed_at=20,
            assurance=0.95,
            provenance="adapter:fence",
        )
        with self.assertRaises(AuthorizationError):
            verify_dispatch_attestation(
                wrong_revision,
                authorization_id="auth-1",
                transaction_id="tx-1",
                action_id="action-1",
                expected_principal_ref="agent:a",
                adapter_id="adapter-1",
                adapter_revision=3,
                principal_binding=binding,
                minimum_assurance=0.8,
            )

    def test_dispatch_attestation_requires_current_identity_attestation_binding(self):
        _identities, binding = self._identity_binding()
        wrong_identity = DispatchAttestation.create(
            attestation_id="dispatch-2",
            authorization_id="auth-1",
            transaction_id="tx-1",
            action_id="action-1",
            adapter_id="adapter-1",
            adapter_revision=3,
            canonical_principal_ref="agent:a",
            principal_attestation_id="identity-other",
            observed_at=20,
            assurance=0.95,
            provenance="adapter:fence",
        )
        with self.assertRaises(AuthorizationError):
            verify_dispatch_attestation(
                wrong_identity,
                authorization_id="auth-1",
                transaction_id="tx-1",
                action_id="action-1",
                expected_principal_ref="agent:a",
                adapter_id="adapter-1",
                adapter_revision=3,
                principal_binding=binding,
                minimum_assurance=0.8,
            )

    def test_dispatch_attestation_low_assurance_fails_closed(self):
        _identities, binding = self._identity_binding()
        low = DispatchAttestation.create(
            attestation_id="dispatch-low",
            authorization_id="auth-1",
            transaction_id="tx-1",
            action_id="action-1",
            adapter_id="adapter-1",
            adapter_revision=3,
            canonical_principal_ref="agent:a",
            principal_attestation_id="identity-a",
            observed_at=20,
            assurance=0.2,
            provenance="adapter:fence",
        )
        with self.assertRaises(AuthorizationError):
            verify_dispatch_attestation(
                low,
                authorization_id="auth-1",
                transaction_id="tx-1",
                action_id="action-1",
                expected_principal_ref="agent:a",
                adapter_id="adapter-1",
                adapter_revision=3,
                principal_binding=binding,
                minimum_assurance=0.8,
            )

    def test_reconciliation_evidence_is_exact_transaction_principal_and_adapter_bound(self):
        ledger = self._transaction()
        evidence = ReconciliationEvidence.create(
            evidence_id="rec-1",
            transaction_id="tx-1",
            action_id="action-1",
            authorization_id="auth-1",
            canonical_principal_ref="agent:a",
            adapter_id="adapter-1",
            adapter_revision=3,
            outcome_applied=True,
            source="provider-status",
            observed_at=30,
            assurance=0.95,
        )
        result = ledger.reconcile_with_evidence("tx-1", evidence, minimum_assurance=0.8)
        self.assertEqual(result.state, TransactionState.RECONCILED_APPLIED)

    def test_wrong_transaction_reconciliation_evidence_is_rejected(self):
        ledger = self._transaction()
        evidence = ReconciliationEvidence.create(
            evidence_id="rec-wrong",
            transaction_id="tx-other",
            action_id="action-1",
            authorization_id="auth-1",
            canonical_principal_ref="agent:a",
            adapter_id="adapter-1",
            adapter_revision=3,
            outcome_applied=True,
            source="provider-status",
            observed_at=30,
            assurance=0.95,
        )
        with self.assertRaises(AuthorizationError):
            ledger.reconcile_with_evidence("tx-1", evidence, minimum_assurance=0.8)

    def test_wrong_principal_or_adapter_reconciliation_evidence_is_rejected(self):
        for principal_ref, adapter_revision in (("agent:b", 3), ("agent:a", 4)):
            ledger = self._transaction()
            evidence = ReconciliationEvidence.create(
                evidence_id=f"rec-{principal_ref}-{adapter_revision}",
                transaction_id="tx-1",
                action_id="action-1",
                authorization_id="auth-1",
                canonical_principal_ref=principal_ref,
                adapter_id="adapter-1",
                adapter_revision=adapter_revision,
                outcome_applied=False,
                source="provider-status",
                observed_at=30,
                assurance=0.95,
            )
            with self.assertRaises(AuthorizationError):
                ledger.reconcile_with_evidence("tx-1", evidence, minimum_assurance=0.8)

    def test_low_assurance_reconciliation_evidence_is_rejected(self):
        ledger = self._transaction()
        evidence = ReconciliationEvidence.create(
            evidence_id="rec-low",
            transaction_id="tx-1",
            action_id="action-1",
            authorization_id="auth-1",
            canonical_principal_ref="agent:a",
            adapter_id="adapter-1",
            adapter_revision=3,
            outcome_applied=True,
            source="provider-status",
            observed_at=30,
            assurance=0.2,
        )
        with self.assertRaises(AuthorizationError):
            ledger.reconcile_with_evidence("tx-1", evidence, minimum_assurance=0.8)


if __name__ == "__main__":
    unittest.main()
