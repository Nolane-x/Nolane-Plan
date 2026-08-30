from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from nolane_plan import PlanKernel
from nolane_plan.semantic_barrier import MutationImpactProfileRevision
from nolane_plan.types import AuthorizationError

from wave7_authority_fixture import AuthorityFixture, CountingAdapter


class Wave7AuthorityLineageTests(unittest.TestCase):
    def make_fixture(self) -> AuthorityFixture:
        return AuthorityFixture(Path(tempfile.mkdtemp()))

    def test_decision_epoch_exact_sidecar_binds_current_semantic_revisions(self):
        fixture = self.make_fixture()
        kernel = fixture.kernel
        epoch = fixture.policy["epoch"]
        self.assertTrue(hasattr(kernel, "decision_epoch_lineage_bindings"))
        binding = kernel.decision_epoch_lineage_bindings[epoch.epoch_id]
        self.assertEqual(
            binding["mission_lineage_revision"],
            kernel.lineage.current("MissionRevision", "mission").revision_id,
        )
        self.assertEqual(
            binding["canonical_state_lineage_revision"],
            kernel.lineage.current("CanonicalState", "canonical-state").revision_id,
        )
        self.assertEqual(binding["strategic_location_revision"], str(kernel._location_revision))
        self.assertEqual(binding["information_partition_revision"], fixture.policy["partition"].revision_id)
        self.assertEqual(binding["observation_frontier_revision"], fixture.policy["frontier"].revision_id)
        self.assertEqual(
            binding["decision_epoch_lineage_revision"],
            kernel.lineage.current("DecisionEpoch", epoch.epoch_id).revision_id,
        )
        self.assertEqual(
            binding["regime_lineage_digest"],
            kernel.current_semantic_regime_lineage_digest(),
        )

    def test_proof_policy_and_schedulability_authority_bind_exact_lineage_revisions(self):
        fixture = self.make_fixture()
        kernel = fixture.kernel
        authorization = fixture.authorize()
        proof = kernel.proof_authorization_bindings[authorization.id]
        policy = kernel.policy_authorization_bindings[authorization.id]
        sched = kernel.schedulability_authorization_bindings[authorization.id]

        for key in ("proof_lineage_revision", "proof_manifest_lineage_revision", "proof_support_lineage_revision"):
            self.assertIn(key, proof)
            kernel.lineage.get(proof[key])
        for key in (
            "decision_epoch_lineage_revision",
            "partition_lineage_revision",
            "frontier_lineage_revision",
            "policy_node_lineage_revision",
            "selection_lineage_revision",
            "sufficiency_lineage_revision",
            "seal_lineage_revision",
            "executability_lineage_revision",
        ):
            self.assertIn(key, policy)
            kernel.lineage.get(policy[key])
        for key in (
            "schedulability_lineage_revision",
            "coverage_lineage_revision",
            "reaction_job_lineage_digest",
            "control_resource_lineage_digest",
        ):
            self.assertIn(key, sched)

    def test_bound_semantic_revision_drift_blocks_dispatch_before_adapter_call(self):
        fixture = self.make_fixture()
        kernel = fixture.kernel
        authorization = fixture.authorize()
        kernel.mutate_semantic_source(
            "proof-source",
            new_revision_id="proof-source@2",
            new_value={"safe": False},
            impact_profile=MutationImpactProfileRevision(
                revision_id="impact@2",
                source_id="proof-source",
                affected_domains=("source:proof-source",),
                coverage_complete=True,
                conservative_fallback_domains=(),
            ),
        )
        adapter = CountingAdapter()
        with self.assertRaises(AuthorizationError):
            kernel.dispatch(authorization.id, "agent:a", adapter, 60)
        self.assertEqual(adapter.calls, 0)

    def test_representation_only_compaction_preserves_authorization_lineage_result(self):
        fixture = self.make_fixture()
        kernel = fixture.kernel
        authorization = fixture.authorize()
        policy_binding = dict(kernel.policy_authorization_bindings[authorization.id])
        self.assertIn("decision_epoch_lineage_revision", policy_binding)
        kernel._assert_authorization_lineage_current(authorization.id)
        kernel.compact_lineage("compaction:authority-equivalence")
        kernel._assert_authorization_lineage_current(authorization.id)
        self.assertEqual(kernel.policy_authorization_bindings[authorization.id], policy_binding)

    def test_migration_mapping_alone_never_restores_invalidated_authority(self):
        fixture = self.make_fixture()
        kernel = fixture.kernel
        authorization = fixture.authorize()
        self.assertIn(
            "decision_epoch_lineage_revision",
            kernel.policy_authorization_bindings[authorization.id],
        )
        kernel.apply_semantic_migration(fixture.migration_manifest(), now=60)
        self.assertIn(authorization.id, kernel.authorizations)
        self.assertIn(authorization.id, kernel.migration_recheck_required_authorizations)
        with self.assertRaises(AuthorizationError):
            kernel._assert_authorization_lineage_current(authorization.id)

    def test_authority_history_survives_restart_but_current_usability_is_recalculated(self):
        fixture = self.make_fixture()
        kernel = fixture.kernel
        authorization = fixture.authorize()
        kernel.save_snapshot()
        kernel.mutate_semantic_source(
            "proof-source",
            new_revision_id="proof-source@2",
            new_value={"safe": False},
            impact_profile=MutationImpactProfileRevision(
                revision_id="impact@restart",
                source_id="proof-source",
                affected_domains=("source:proof-source",),
                coverage_complete=True,
                conservative_fallback_domains=(),
            ),
        )

        reopened = PlanKernel.open(fixture.root)
        self.assertIn(authorization.id, reopened.authorizations)
        self.assertIn(authorization.id, reopened.proof_authorization_bindings)
        self.assertIn(authorization.id, reopened.policy_authorization_bindings)
        self.assertIn(authorization.id, reopened.schedulability_authorization_bindings)
        with self.assertRaises(AuthorizationError):
            reopened._assert_authorization_lineage_current(authorization.id)


if __name__ == "__main__":
    unittest.main()
