from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from nolane_plan import PlanKernel
from nolane_plan.actions import ActionIntent, AuthorityGrant
from nolane_plan.execution import AdapterProfile, DispatchAttestation, ReconciliationEvidence, TransactionState
from nolane_plan.identity import IdentityError, PrincipalAttestation
from nolane_plan.principals import InformationItem
from nolane_plan.types import AuthorizationError, RiskClass


class _GoodAdapter:
    adapter_id = "adapter-1"
    adapter_revision = 1

    def __init__(self, principal_ref: str = "agent:a", *, fail: bool = False):
        self.principal_ref = principal_ref
        self.fail = fail
        self.called = 0

    def execute(self, action, principal_ref):
        self.called += 1
        if self.fail:
            raise RuntimeError("timeout after possible side effect")
        return {
            "executing_principal_ref": self.principal_ref,
            "ok": True,
            "postconditions_verified": True,
            "state_patch": {"applied": action.id},
        }


class Wave3KernelTrustTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.kernel = PlanKernel.create(self.root, "Wave 3 trust test")

    def tearDown(self):
        self.temp.cleanup()

    def _attestation(self, principal_ref: str, subject: str, *, attestation_id: str, revision: int = 1, assurance: float = 0.95):
        return PrincipalAttestation.create(
            attestation_id=attestation_id,
            canonical_principal_ref=principal_ref,
            source="host-runtime",
            source_subject=subject,
            revision=revision,
            issued_at=1,
            valid_until=1000,
            assurance=assurance,
            session_ref=f"session-{revision}",
        )

    def _bind(self, principal_ref: str, subject: str, *, attestation_id: str, revision: int = 1):
        return self.kernel.bind_principal(
            self._attestation(principal_ref, subject, attestation_id=attestation_id, revision=revision),
            allowed_tags={"shared"},
            now=10 + revision,
        )

    def _prepare_action(self, *, action_id: str = "action-1", idempotent: bool = False):
        action = ActionIntent(
            action_id,
            "deploy",
            RiskClass.CONSEQUENTIAL,
            idempotent=idempotent,
            executor_sensitive=True,
        )
        self.kernel.propose_action(action)
        self.kernel.add_grant(AuthorityGrant("grant-1", "agent:a", frozenset({"deploy"})))
        self.kernel.register_adapter(AdapterProfile("adapter-1", 1, True, True, 0.95))
        return action

    def _dispatch_attestation(self, authorization_id: str, *, principal_ref: str = "agent:a", principal_attestation_id: str = "identity-a"):
        tx = self.kernel.transaction_for_authorization(authorization_id)
        return DispatchAttestation.create(
            attestation_id=f"dispatch-{authorization_id}-{principal_ref}",
            authorization_id=authorization_id,
            transaction_id=tx.id,
            action_id=tx.action_id,
            adapter_id="adapter-1",
            adapter_revision=1,
            canonical_principal_ref=principal_ref,
            principal_attestation_id=principal_attestation_id,
            observed_at=30,
            assurance=0.95,
            provenance="adapter:fence",
        )

    def test_strong_authorization_rejects_raw_narrated_principal_without_host_binding(self):
        self.kernel.register_principal("agent:a", {"shared"})
        self._prepare_action()
        with self.assertRaises(IdentityError):
            self.kernel.authorize_strong("action-1", "agent:a", ("grant-1",), now=20, adapter_id="adapter-1")

    def test_identity_rebind_after_authorization_blocks_old_dispatch_before_adapter_call(self):
        self._bind("agent:a", "subject-a", attestation_id="identity-a")
        self._prepare_action()
        authorization = self.kernel.authorize_strong("action-1", "agent:a", ("grant-1",), now=20, adapter_id="adapter-1")

        self._bind("agent:a", "subject-a", attestation_id="identity-a-2", revision=2)
        adapter = _GoodAdapter()
        attestation = self._dispatch_attestation(authorization.id, principal_attestation_id="identity-a-2")
        with self.assertRaises(AuthorizationError):
            self.kernel.dispatch_strong(authorization.id, "agent:a", adapter, attestation, now=30)
        self.assertEqual(adapter.called, 0)

    def test_inter_principal_transfer_requires_observation_and_is_not_retroactive(self):
        self._bind("agent:a", "subject-a", attestation_id="identity-a")
        self._bind("agent:b", "subject-b", attestation_id="identity-b")
        self.kernel.publish_information(InformationItem("info-1", {"result": "green"}, frozenset({"shared"})))

        sent = self.kernel.transfer_information(
            receipt_id="msg-sent",
            source_principal_ref="agent:a",
            recipient_principal_ref="agent:b",
            item_id="info-1",
            sent_at=20,
        )
        self.assertEqual(sent.state.value, "sent")
        self.assertNotIn("info-1", self.kernel.compile_strong_capsule("agent:b", 25, ()).item_ids)

        observed = self.kernel.transfer_information(
            receipt_id="msg-observed",
            source_principal_ref="agent:a",
            recipient_principal_ref="agent:b",
            item_id="info-1",
            sent_at=26,
            delivered_at=28,
            observed_at=30,
            delivery_evidence_ref="provider:delivery",
            observation_evidence_ref="host:observation",
        )
        self.assertEqual(observed.state.value, "observed")
        self.assertNotIn("info-1", self.kernel.compile_strong_capsule("agent:b", 29, ()).item_ids)
        self.assertIn("info-1", self.kernel.compile_strong_capsule("agent:b", 30, ()).item_ids)

    def test_wrong_dispatch_principal_attestation_is_rejected_before_side_effect(self):
        self._bind("agent:a", "subject-a", attestation_id="identity-a")
        self._prepare_action()
        authorization = self.kernel.authorize_strong("action-1", "agent:a", ("grant-1",), now=20, adapter_id="adapter-1")
        adapter = _GoodAdapter()
        bad = self._dispatch_attestation(authorization.id, principal_ref="agent:b")
        with self.assertRaises(AuthorizationError):
            self.kernel.dispatch_strong(authorization.id, "agent:a", adapter, bad, now=30)
        self.assertEqual(adapter.called, 0)

    def test_valid_strong_dispatch_commits_only_after_attested_executor_and_postconditions(self):
        self._bind("agent:a", "subject-a", attestation_id="identity-a")
        self._prepare_action()
        authorization = self.kernel.authorize_strong("action-1", "agent:a", ("grant-1",), now=20, adapter_id="adapter-1")
        adapter = _GoodAdapter()
        receipt = self.kernel.dispatch_strong(
            authorization.id,
            "agent:a",
            adapter,
            self._dispatch_attestation(authorization.id),
            now=30,
        )
        self.assertTrue(receipt.postconditions_verified)
        self.assertEqual(self.kernel.canonical_state["applied"], "action-1")
        self.assertEqual(adapter.called, 1)
        self.assertIn(authorization.id, self.kernel.dispatch_attestations)

    def test_strong_reconciliation_requires_transaction_bound_evidence(self):
        self._bind("agent:a", "subject-a", attestation_id="identity-a")
        self._prepare_action()
        authorization = self.kernel.authorize_strong("action-1", "agent:a", ("grant-1",), now=20, adapter_id="adapter-1")
        adapter = _GoodAdapter(fail=True)
        with self.assertRaises(RuntimeError):
            self.kernel.dispatch_strong(
                authorization.id,
                "agent:a",
                adapter,
                self._dispatch_attestation(authorization.id),
                now=30,
            )
        tx = self.kernel.transaction_for_authorization(authorization.id)
        self.assertEqual(tx.state, TransactionState.RECONCILIATION_REQUIRED)

        wrong = ReconciliationEvidence.create(
            evidence_id="rec-wrong",
            transaction_id="tx-other",
            action_id="action-1",
            authorization_id=authorization.id,
            canonical_principal_ref="agent:a",
            adapter_id="adapter-1",
            adapter_revision=1,
            outcome_applied=True,
            source="provider-status",
            observed_at=40,
            assurance=0.95,
        )
        with self.assertRaises(AuthorizationError):
            self.kernel.reconcile_strong(authorization.id, wrong, state_patch={"reconciled": True})

        good = ReconciliationEvidence.create(
            evidence_id="rec-good",
            transaction_id=tx.id,
            action_id="action-1",
            authorization_id=authorization.id,
            canonical_principal_ref="agent:a",
            adapter_id="adapter-1",
            adapter_revision=1,
            outcome_applied=True,
            source="provider-status",
            observed_at=41,
            assurance=0.95,
        )
        result = self.kernel.reconcile_strong(authorization.id, good, state_patch={"reconciled": True})
        self.assertEqual(result.state, TransactionState.COMMITTED)
        self.assertTrue(self.kernel.canonical_state["reconciled"])
        self.assertIn(good.evidence_id, self.kernel.reconciliation_evidence)


if __name__ == "__main__":
    unittest.main()
