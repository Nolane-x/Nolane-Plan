from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from nolane_plan.actions import ActionIntent, AuthorityGrant
from nolane_plan.execution import AdapterProfile, TransactionState
from nolane_plan.kernel import PlanKernel
from nolane_plan.preparedness import PreparednessLevel, PreparednessProfile
from nolane_plan.principals import InformationItem
from nolane_plan.query import QuerySnapshotCompletenessReceipt
from nolane_plan.relocation import CandidateRegion
from nolane_plan.temporal import ReactionWindow
from nolane_plan.types import AuthorizationError, CapsuleError, RiskClass


class _StrongAdapter:
    adapter_id = "deploy-api"
    adapter_revision = 1

    def execute(self, action, principal_ref):
        return {
            "ok": True,
            "postconditions_verified": True,
            "state_patch": {"deployed": True},
            "executing_principal_ref": principal_ref,
        }


class _AmbiguousAdapter:
    adapter_id = "payments"
    adapter_revision = 1

    def execute(self, action, principal_ref):
        raise TimeoutError("connection lost after dispatch may have applied effect")


class Wave2KernelIntegrationTests(unittest.TestCase):
    def make_kernel(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        k = PlanKernel.create(Path(td.name), "ship verified artifact", success_conditions=("deployed",))
        k.register_principal("agent:p0", {"public"})
        item = InformationItem("proof", {"ok": True}, frozenset({"public"}), provenance="verifier")
        k.publish_information(item)
        k.observe_information("agent:p0", item.id, 0)
        return k

    def add_action_and_grant(self, k, action):
        k.propose_action(action)
        k.add_grant(AuthorityGrant("g1", "agent:p0", frozenset({action.family}), expires_at=100))

    def test_capsule_is_decision_cut_bound_and_freshness_sensitive(self):
        k = self.make_kernel()
        self.add_action_and_grant(k, ActionIntent("deploy", "deploy"))
        capsule = k.compile_capsule("agent:p0", 1, ("deploy",))
        self.assertTrue(capsule.decision_cut_id)
        self.assertTrue(k.validate_capsule(capsule.id, "agent:p0"))

        k.bump_freshness("canonical")
        with self.assertRaises(CapsuleError):
            k.validate_capsule(capsule.id, "agent:p0")

    def test_executor_sensitive_authorization_requires_strong_adapter(self):
        k = self.make_kernel()
        action = ActionIntent("deploy", "deploy", risk_class=RiskClass.CONSEQUENTIAL, executor_sensitive=True)
        self.add_action_and_grant(k, action)
        capsule = k.compile_capsule("agent:p0", 1, ("deploy",))
        k.register_adapter(AdapterProfile("opaque", 1, False, False, 1.0))

        with self.assertRaises(AuthorizationError):
            k.authorize("deploy", "agent:p0", ("g1",), 1, capsule_id=capsule.id, adapter_id="opaque")

    def test_policy_gate_blocks_incomplete_universal_query(self):
        k = self.make_kernel()
        action = ActionIntent("deploy", "deploy", risk_class=RiskClass.CONSEQUENTIAL)
        self.add_action_and_grant(k, action)
        capsule = k.compile_capsule("agent:p0", 1, ("deploy",))
        k.register_adapter(AdapterProfile("deploy-api", 1, True, True, 1.0))
        k.freshness.ensure("inventory")
        receipt = QuerySnapshotCompletenessReceipt.capture(k.freshness, "inventory", "snap1", False, 1.0)

        with self.assertRaises(AuthorizationError):
            k.authorize(
                "deploy", "agent:p0", ("g1",), 1,
                capsule_id=capsule.id,
                adapter_id="deploy-api",
                query_receipts=(receipt,),
            )

    def test_policy_gate_blocks_unschedulable_reaction_window(self):
        k = self.make_kernel()
        action = ActionIntent("deploy", "deploy", risk_class=RiskClass.CONSEQUENTIAL)
        self.add_action_and_grant(k, action)
        capsule = k.compile_capsule("agent:p0", 1, ("deploy",))
        k.register_adapter(AdapterProfile("deploy-api", 1, True, True, 1.0))
        window = ReactionWindow(0, 3, 2, 2, 1)
        preparedness = PreparednessProfile(PreparednessLevel.EXECUTABLE, True, True)

        with self.assertRaises(AuthorizationError):
            k.authorize(
                "deploy", "agent:p0", ("g1",), 1,
                capsule_id=capsule.id,
                adapter_id="deploy-api",
                preparedness=preparedness,
                reaction_window=window,
            )

    def test_non_idempotent_unknown_outcome_requires_reconciliation(self):
        k = self.make_kernel()
        action = ActionIntent(
            "charge", "charge", risk_class=RiskClass.CONSEQUENTIAL,
            idempotent=False, executor_sensitive=True,
        )
        self.add_action_and_grant(k, action)
        capsule = k.compile_capsule("agent:p0", 1, ("charge",))
        k.register_adapter(AdapterProfile("payments", 1, True, True, 1.0))
        auth = k.authorize("charge", "agent:p0", ("g1",), 1, capsule_id=capsule.id, adapter_id="payments")

        with self.assertRaises(TimeoutError):
            k.dispatch(auth.id, "agent:p0", _AmbiguousAdapter(), now=2)
        tx = k.transaction_for_authorization(auth.id)
        self.assertEqual(tx.state, TransactionState.RECONCILIATION_REQUIRED)
        with self.assertRaises(AuthorizationError):
            k.authorize("charge", "agent:p0", ("g1",), 3, capsule_id=capsule.id, adapter_id="payments")

        k.reconcile_action(auth.id, outcome_applied=True, state_patch={"charged": True}, trusted=True)
        self.assertTrue(k.canonical_state["charged"])

    def test_relocation_unlocated_after_commit_enters_unknown_world(self):
        k = self.make_kernel()
        k.register_region(CandidateRegion("before", {"deployed": False}, "stay"))
        action = ActionIntent("deploy", "deploy", risk_class=RiskClass.CONSEQUENTIAL)
        self.add_action_and_grant(k, action)
        capsule = k.compile_capsule("agent:p0", 1, ("deploy",))
        k.register_adapter(AdapterProfile("deploy-api", 1, True, True, 1.0))
        auth = k.authorize("deploy", "agent:p0", ("g1",), 1, capsule_id=capsule.id, adapter_id="deploy-api")
        k.dispatch(auth.id, "agent:p0", _StrongAdapter(), now=2)
        self.assertEqual(k.strategic_location.status.value, "unlocated")
        self.assertEqual(k.recovery.state.mode.value, "model_class_uncertain")

    def test_completion_proof_stales_after_mission_revision(self):
        k = self.make_kernel()
        k.canonical_state["deployed"] = True
        report = k.verify_completion(())
        self.assertTrue(report.complete)
        self.assertTrue(k.artifacts.current(report.artifact_id))

        k.revise_mission(objective="ship verified artifact v2")
        self.assertFalse(k.artifacts.current(report.artifact_id))


if __name__ == "__main__":
    unittest.main()
