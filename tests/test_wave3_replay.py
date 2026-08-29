from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from nolane_plan import PlanKernel
from nolane_plan.actions import ActionIntent, AuthorityGrant
from nolane_plan.execution import AdapterProfile, DispatchAttestation, ReconciliationEvidence, TransactionState
from nolane_plan.identity import IdentityError, PrincipalAttestation
from nolane_plan.principals import InformationItem
from nolane_plan.types import RiskClass


class _TimeoutAdapter:
    adapter_id = "adapter-1"
    adapter_revision = 1

    def execute(self, action, principal_ref):
        raise RuntimeError("timeout after possible side effect")


class Wave3ReplayTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def _attestation(self, principal: str, subject: str, attestation_id: str, revision: int = 1):
        return PrincipalAttestation.create(
            attestation_id=attestation_id,
            canonical_principal_ref=principal,
            source="host-runtime",
            source_subject=subject,
            revision=revision,
            issued_at=1,
            valid_until=1000,
            assurance=0.95,
            session_ref=f"session-{revision}",
        )

    def _kernel_with_two_principals(self):
        k = PlanKernel.create(self.root, "replay trust")
        k.bind_principal(self._attestation("agent:a", "subject-a", "identity-a"), allowed_tags={"shared"}, now=10)
        k.bind_principal(self._attestation("agent:b", "subject-b", "identity-b"), allowed_tags={"shared"}, now=10)
        return k

    def test_snapshot_round_trip_preserves_identity_and_observed_delivery_provenance(self):
        k = self._kernel_with_two_principals()
        k.publish_information(InformationItem("info-1", {"ok": True}, frozenset({"shared"})))
        k.transfer_information(
            receipt_id="msg-1",
            source_principal_ref="agent:a",
            recipient_principal_ref="agent:b",
            item_id="info-1",
            sent_at=20,
            delivered_at=21,
            observed_at=22,
            delivery_evidence_ref="provider:delivery-1",
            observation_evidence_ref="host:observe-1",
        )
        k.save_snapshot()

        reopened = PlanKernel.open(self.root)
        binding = reopened.identities.current("agent:b", now=30, minimum_assurance=0.8)
        self.assertEqual(binding.attestation_id, "identity-b")
        receipt = reopened.communications.get("msg-1")
        self.assertEqual(receipt.delivery_evidence_ref, "provider:delivery-1")
        self.assertEqual(receipt.observation_evidence_ref, "host:observe-1")
        self.assertTrue(reopened.communications.decision_usable("msg-1", "agent:b", decision_time=30))
        self.assertFalse(reopened.communications.decision_usable("msg-1", "agent:a", decision_time=30))

    def test_snapshot_round_trip_preserves_revoked_identity(self):
        k = PlanKernel.create(self.root, "replay revoked identity")
        k.bind_principal(self._attestation("agent:a", "subject-a", "identity-a"), allowed_tags={"shared"}, now=10)
        k.revoke_principal_attestation("identity-a", revoked_at=20)
        k.save_snapshot()

        reopened = PlanKernel.open(self.root)
        with self.assertRaises(IdentityError):
            reopened.identities.current("agent:a", now=30, minimum_assurance=0.8)

    def test_post_snapshot_identity_binding_replays_exact_host_provenance(self):
        k = PlanKernel.create(self.root, "suffix identity")
        k.save_snapshot()
        k.bind_principal(self._attestation("agent:a", "subject-a", "identity-a"), allowed_tags={"shared"}, now=20)

        reopened = PlanKernel.open(self.root)
        binding = reopened.identities.current("agent:a", now=30, minimum_assurance=0.8)
        attestation = reopened.identities.attestation(binding.attestation_id)
        self.assertEqual(attestation.source, "host-runtime")
        self.assertEqual(attestation.source_subject, "subject-a")
        self.assertEqual(attestation.session_ref, "session-1")
        self.assertEqual(binding.created_at, 20)

    def test_post_snapshot_sent_message_replays_as_sent_not_known(self):
        k = self._kernel_with_two_principals()
        k.publish_information(InformationItem("info-1", "payload", frozenset({"shared"})))
        k.save_snapshot()
        k.transfer_information(
            receipt_id="msg-sent",
            source_principal_ref="agent:a",
            recipient_principal_ref="agent:b",
            item_id="info-1",
            sent_at=20,
        )

        reopened = PlanKernel.open(self.root)
        receipt = reopened.communications.get("msg-sent")
        self.assertEqual(receipt.state.value, "sent")
        self.assertFalse(reopened.communications.decision_usable("msg-sent", "agent:b", decision_time=30))
        self.assertNotIn("info-1", reopened.compile_strong_capsule("agent:b", 30, ()).item_ids)

    def test_post_snapshot_observation_replays_without_retroactive_knowledge(self):
        k = self._kernel_with_two_principals()
        k.publish_information(InformationItem("info-1", "payload", frozenset({"shared"})))
        k.save_snapshot()
        k.transfer_information(
            receipt_id="msg-observed",
            source_principal_ref="agent:a",
            recipient_principal_ref="agent:b",
            item_id="info-1",
            sent_at=20,
            delivered_at=21,
            observed_at=25,
            delivery_evidence_ref="provider:delivery",
            observation_evidence_ref="host:observe",
        )

        reopened = PlanKernel.open(self.root)
        self.assertFalse(reopened.communications.decision_usable("msg-observed", "agent:b", decision_time=24))
        self.assertTrue(reopened.communications.decision_usable("msg-observed", "agent:b", decision_time=25))
        self.assertNotIn("info-1", reopened.compile_strong_capsule("agent:b", 24, ()).item_ids)
        self.assertIn("info-1", reopened.compile_strong_capsule("agent:b", 25, ()).item_ids)

    def test_snapshot_preserves_dispatch_and_reconciliation_evidence_binding(self):
        k = PlanKernel.create(self.root, "execution evidence replay")
        k.bind_principal(self._attestation("agent:a", "subject-a", "identity-a"), allowed_tags=set(), now=10)
        k.propose_action(ActionIntent("action-1", "deploy", RiskClass.CONSEQUENTIAL, idempotent=False, executor_sensitive=True))
        k.add_grant(AuthorityGrant("grant-1", "agent:a", frozenset({"deploy"})))
        k.register_adapter(AdapterProfile("adapter-1", 1, True, True, 0.95))
        authorization = k.authorize_strong("action-1", "agent:a", ("grant-1",), now=20, adapter_id="adapter-1")
        tx = k.transaction_for_authorization(authorization.id)
        dispatch = DispatchAttestation.create(
            attestation_id="dispatch-1",
            authorization_id=authorization.id,
            transaction_id=tx.id,
            action_id="action-1",
            adapter_id="adapter-1",
            adapter_revision=1,
            canonical_principal_ref="agent:a",
            principal_attestation_id="identity-a",
            observed_at=25,
            assurance=0.95,
            provenance="adapter:fence",
        )
        with self.assertRaises(RuntimeError):
            k.dispatch_strong(authorization.id, "agent:a", _TimeoutAdapter(), dispatch, now=25)
        tx = k.transaction_for_authorization(authorization.id)
        self.assertEqual(tx.state, TransactionState.RECONCILIATION_REQUIRED)
        evidence = ReconciliationEvidence.create(
            evidence_id="rec-1",
            transaction_id=tx.id,
            action_id="action-1",
            authorization_id=authorization.id,
            canonical_principal_ref="agent:a",
            adapter_id="adapter-1",
            adapter_revision=1,
            outcome_applied=False,
            source="provider-status",
            observed_at=30,
            assurance=0.95,
        )
        k.reconcile_strong(authorization.id, evidence)
        k.save_snapshot()

        reopened = PlanKernel.open(self.root)
        self.assertEqual(reopened.dispatch_attestations[authorization.id].transaction_id, tx.id)
        self.assertEqual(reopened.reconciliation_evidence["rec-1"].transaction_id, tx.id)
        self.assertEqual(reopened.transaction_for_authorization(authorization.id).state, TransactionState.RECONCILED_NOT_APPLIED)


if __name__ == "__main__":
    unittest.main()
