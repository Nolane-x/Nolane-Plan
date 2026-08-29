import unittest

from nolane_plan.action_lifecycle import ActionLifecycle, ActionPhase
from nolane_plan.dependency import DependencyManifest, DerivedArtifact
from nolane_plan.freshness import FreshnessDomainLedger
from nolane_plan.preparedness import PreparednessLevel, PreparednessProfile, required_preparedness
from nolane_plan.pruning import BranchRecord, BranchState, PruningEngine, UnsafePrune
from nolane_plan.query import QuerySnapshotCompletenessReceipt, strong_universal_current


class ClosureLayerTests(unittest.TestCase):
    def test_derived_artifact_stales_when_causal_dependency_changes(self):
        domains = FreshnessDomainLedger()
        domains.ensure("source:evidence")
        manifest = DependencyManifest.capture(domains, ("source:evidence",), assurance="full-envelope")
        artifact = DerivedArtifact("proof-1", manifest)
        self.assertTrue(artifact.current(domains))
        domains.bump("source:evidence")
        self.assertFalse(artifact.current(domains))

    def test_universal_query_requires_complete_current_snapshot(self):
        domains = FreshnessDomainLedger()
        domains.ensure("repo-membership")
        receipt = QuerySnapshotCompletenessReceipt.capture(domains, "repo-membership", "snap-1", complete=True, visibility_assurance=1.0)
        self.assertTrue(strong_universal_current(receipt, domains, minimum_assurance=0.9))
        domains.bump("repo-membership")
        self.assertFalse(strong_universal_current(receipt, domains, minimum_assurance=0.9))

    def test_incomplete_enumeration_never_proves_absence(self):
        domains = FreshnessDomainLedger()
        receipt = QuerySnapshotCompletenessReceipt.capture(domains, "repo-membership", "snap-1", complete=False, visibility_assurance=1.0)
        self.assertFalse(strong_universal_current(receipt, domains, minimum_assurance=0.9))

    def test_safe_pruning_refuses_unique_hedge(self):
        engine = PruningEngine()
        branch = BranchRecord("b", support=0.001, catastrophic_exposure=False, sole_hard_route=False, unique_hedge=True, information_value=0.0)
        with self.assertRaises(UnsafePrune):
            engine.prune(branch)

    def test_pruned_branch_is_dormant_and_resurrectable(self):
        engine = PruningEngine()
        branch = BranchRecord("b", support=0.001, catastrophic_exposure=False, sole_hard_route=False, unique_hedge=False, information_value=0.0)
        dormant = engine.prune(branch)
        self.assertEqual(dormant.state, BranchState.DORMANT)
        active = engine.resurrect(dormant, dependencies_current=True)
        self.assertEqual(active.state, BranchState.ACTIVE)

    def test_irreversible_near_horizon_requires_executable_preparedness(self):
        level = required_preparedness(distance=1, irreversible=True, observation_lead_time=2, synthesis_latency=4)
        self.assertEqual(level, PreparednessLevel.EXECUTABLE)
        profile = PreparednessProfile(level=PreparednessLevel.SCHEMA, dependencies_current=True, schedulable=True)
        self.assertFalse(profile.satisfies(level))

    def test_action_lifecycle_rejects_transport_success_as_commit(self):
        life = ActionLifecycle()
        life.transition(ActionPhase.RISK_CLASSIFIED)
        life.transition(ActionPhase.AUTHORIZED)
        life.transition(ActionPhase.PRECONDITIONS_VERIFIED)
        life.transition(ActionPhase.EXECUTION_STARTED)
        life.transition(ActionPhase.OUTCOME_OBSERVED)
        self.assertFalse(life.committed)
        with self.assertRaises(ValueError):
            life.transition(ActionPhase.COMMITTED)
        life.transition(ActionPhase.POSTCONDITIONS_VERIFIED)
        life.transition(ActionPhase.COMMITTED)
        self.assertTrue(life.committed)


if __name__ == "__main__": unittest.main()
