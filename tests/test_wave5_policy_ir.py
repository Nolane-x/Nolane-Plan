from __future__ import annotations

import unittest

from nolane_plan.policy_ir import (
    ContingentPolicyCertificate,
    PolicyCoherenceEvaluator,
    PolicyNodeRevision,
    PolicySuccessorRoute,
)
from nolane_plan.policy_information import NonAnticipativityAssessment
from nolane_plan.resources import SharedCommitment


class Wave5PolicyIRTests(unittest.TestCase):
    def _node(self, **changes) -> PolicyNodeRevision:
        fields = dict(
            policy_node_id="node",
            revision_id="node@1",
            mission_revision=1,
            decision_principal_ref="agent:a",
            plan_snapshot_version=7,
            strategic_location_revision=3,
            information_partition_revision="partition@1",
            decision_epoch_ref="epoch@1",
            action_space_revision="actions@1",
            candidate_action_contracts=("deploy:red", "deploy:blue"),
            execution_principal_requirement_or_set=("agent:a",),
            selected_action_contract_or_policy_set=("deploy:red",),
            runtime_guard_refs=("guard:ready@1",),
            observation_frontier_revision="frontier@1",
            successor_policy_mapping=(
                PolicySuccessorRoute("branch:red", "reveal:red@1", "node-red@1"),
            ),
            shared_commitment_refs=("gpu-reservation@1",),
            resource_reservation_refs=("gpu-reservation@1",),
            obligation_basis_ref="obligations@1",
            risk_policy_revision="risk@1",
            authority_profile_requirement="authority@1",
            route_guarantee_requirement="G2",
            preparedness_level="P3",
            proof_context_ref="proof-context@1",
            assurance_profile="CHECKED",
            debt_refs=(),
            sealed=True,
        )
        fields.update(changes)
        return PolicyNodeRevision.create(**fields)

    def _nonanticipativity(self, valid: bool = True) -> NonAnticipativityAssessment:
        return NonAnticipativityAssessment(
            valid=valid,
            partition_revision="partition@1",
            epoch_id="epoch@1",
            decision_principal_ref="agent:a",
            violations=(),
            debt_refs=() if valid else ("NONANTICIPATIVITY_DEBT:TEST",),
            assessment_digest="na@1",
        )

    def test_policy_node_binds_principal_information_and_action_space(self):
        a = self._node()
        b = self._node(
            revision_id="node@2",
            decision_principal_ref="agent:b",
            information_partition_revision="partition-b@1",
        )
        self.assertNotEqual(a.canonical_digest, b.canonical_digest)
        self.assertEqual(a.action_space_revision, "actions@1")

    def test_policy_node_has_no_execution_authorization(self):
        node = self._node()
        self.assertFalse(hasattr(node, "authorization_id"))
        self.assertFalse(hasattr(node, "dispatch"))

    def test_selected_action_must_be_in_candidate_contracts(self):
        with self.assertRaises(ValueError):
            self._node(selected_action_contract_or_policy_set=("deploy:green",))

    def test_successor_guards_are_unique_and_explicit(self):
        duplicate = (
            PolicySuccessorRoute("branch:red", "reveal:red@1", "node-red@1"),
            PolicySuccessorRoute("branch:red", "reveal:blue@1", "node-blue@1"),
        )
        with self.assertRaises(ValueError):
            self._node(successor_policy_mapping=duplicate)

    def test_branchwise_viability_does_not_imply_policy_viability_before_reveal(self):
        assessment = PolicyCoherenceEvaluator.evaluate(
            policy_nodes=(self._node(),),
            nonanticipativity=self._nonanticipativity(False),
            branch_route_viability={"h1": True, "h2": True},
            pre_reveal_commitments={},
            required_policy_scope=("h1", "h2"),
        )
        self.assertFalse(assessment.valid)
        self.assertIn("NONANTICIPATIVE_POLICY_REQUIRED", assessment.blockers)

    def test_hidden_branches_cannot_double_spend_exclusive_shared_resource(self):
        red = SharedCommitment("only-gpu", "agent:a", 10, 20, True)
        blue = SharedCommitment("only-gpu", "agent:a", 10, 20, True)
        assessment = PolicyCoherenceEvaluator.evaluate(
            policy_nodes=(self._node(),),
            nonanticipativity=self._nonanticipativity(True),
            branch_route_viability={"h1": True, "h2": True},
            pre_reveal_commitments={"h1": (red,), "h2": (blue,)},
            required_policy_scope=("h1", "h2"),
        )
        self.assertFalse(assessment.valid)
        self.assertIn("SHARED_COMMITMENT_CONFLICT", assessment.blockers)

    def test_mutually_exclusive_branch_local_commitments_after_reveal_do_not_fake_pre_reveal_conflict(self):
        red = SharedCommitment("only-gpu", "agent:a", 20, 30, True)
        blue = SharedCommitment("only-gpu", "agent:a", 20, 30, True)
        assessment = PolicyCoherenceEvaluator.evaluate(
            policy_nodes=(self._node(),),
            nonanticipativity=self._nonanticipativity(True),
            branch_route_viability={"h1": True, "h2": True},
            pre_reveal_commitments={},
            post_reveal_commitments={"h1": (red,), "h2": (blue,)},
            mutually_exclusive_branches=(frozenset({"h1", "h2"}),),
            required_policy_scope=("h1", "h2"),
        )
        self.assertTrue(assessment.valid, assessment)

    def test_certificate_cannot_be_valid_when_coherence_has_blocker(self):
        assessment = PolicyCoherenceEvaluator.evaluate(
            policy_nodes=(self._node(),),
            nonanticipativity=self._nonanticipativity(False),
            branch_route_viability={"h1": True},
            pre_reveal_commitments={},
            required_policy_scope=("h1",),
        )
        with self.assertRaises(ValueError):
            ContingentPolicyCertificate.issue(
                certificate_id="policy-cert@1",
                revision_id="policy-cert@1",
                policy_node_revisions=("node@1",),
                mission_revision=1,
                information_partition_revision="partition@1",
                action_space_revision="actions@1",
                proof_context_ref="proof-context@1",
                route_guarantee="G2",
                preparedness_floor="P3",
                coherence=assessment,
                created_sequence=10,
                validity_regime="runtime@1",
            )


if __name__ == "__main__":
    unittest.main()
