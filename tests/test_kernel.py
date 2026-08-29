import tempfile
import unittest
from pathlib import Path

from nolane_plan.actions import ActionIntent, AuthorityGrant
from nolane_plan.future import FutureFamily
from nolane_plan.kernel import PlanKernel
from nolane_plan.obligations import StrategicObligation
from nolane_plan.principals import InformationItem
from nolane_plan.types import CapsuleError, RiskClass


class Adapter:
    def execute(self, action, principal_ref):
        return {"ok": True, "postconditions_verified": True, "state_patch": {"deployed": True}, "executing_principal_ref": principal_ref}


class KernelTests(unittest.TestCase):
    def test_end_to_end_lifecycle(self):
        with tempfile.TemporaryDirectory() as td:
            k = PlanKernel.create(Path(td), objective="deploy safely", success_conditions=("deployed",))
            k.register_principal("agent:deploy", {"public"})
            info = InformationItem("build", {"verified": True}, frozenset({"public"}), 0)
            k.publish_information(info)
            k.observe_information("agent:deploy", "build", 0)
            k.add_future_family(FutureFamily("api-up", "api available", probability=0.8))
            k.add_obligation(StrategicObligation("verify", "build verified before deployment"))
            action = ActionIntent("deploy-1", "deploy", risk_class=RiskClass.CONSEQUENTIAL)
            k.propose_action(action)
            grant = AuthorityGrant("grant-1", "agent:deploy", frozenset({"deploy"}), expires_at=100)
            k.add_grant(grant)
            capsule = k.compile_capsule("agent:deploy", decision_time=1, action_ids=("deploy-1",))
            auth = k.authorize("deploy-1", "agent:deploy", grant_ids=("grant-1",), now=1)
            receipt = k.dispatch(auth.id, presented_principal_ref="agent:deploy", adapter=Adapter(), now=2)
            self.assertTrue(receipt.postconditions_verified)
            self.assertTrue(k.canonical_state["deployed"])
            self.assertGreater(k.canonical_version, 1)
            self.assertTrue(k.journal.verify())

    def test_mission_revision_stales_old_capsule(self):
        with tempfile.TemporaryDirectory() as td:
            k = PlanKernel.create(Path(td), objective="one")
            k.register_principal("agent:a", {"public"})
            cap = k.compile_capsule("agent:a", decision_time=0, action_ids=())
            k.revise_mission(objective="two")
            with self.assertRaises(CapsuleError):
                k.validate_capsule(cap.id, "agent:a")

    def test_model_proposal_does_not_mutate_canonical_state(self):
        with tempfile.TemporaryDirectory() as td:
            k = PlanKernel.create(Path(td), objective="x")
            before = dict(k.canonical_state)
            proposal_id = k.submit_model_proposal({"claim": "deployed=true"})
            self.assertIn(proposal_id, k.model_proposals)
            self.assertEqual(k.canonical_state, before)

    def test_unknown_world_blocks_irreversible_dispatch(self):
        with tempfile.TemporaryDirectory() as td:
            k = PlanKernel.create(Path(td), objective="x")
            k.register_principal("agent:a", {"public"})
            action = ActionIntent("destroy", "destroy", risk_class=RiskClass.IRREVERSIBLE)
            k.propose_action(action)
            k.add_grant(AuthorityGrant("g", "agent:a", frozenset({"destroy"}), expires_at=100))
            auth = k.authorize("destroy", "agent:a", ("g",), now=1)
            k.report_model_class_anomaly("unexpected schema", 0.8)
            with self.assertRaises(Exception):
                k.dispatch(auth.id, "agent:a", Adapter(), now=2)


if __name__ == "__main__": unittest.main()
