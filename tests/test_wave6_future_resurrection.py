from __future__ import annotations

import unittest

from nolane_plan.future_resurrection import (
    BranchResurrectionEvaluator,
    DormantBranchRevision,
    ResurrectionStatus,
)


class Wave6FutureResurrectionTests(unittest.TestCase):
    def dormant(self, **overrides):
        kwargs = dict(
            branch_id="branch-a",
            revision_id="branch-a-r1",
            branch_digest="branch-digest-a",
            mission_revision="mission-r1",
            assumption_revision_refs=("assumption:a-r1",),
            evidence_revision_refs=("evidence:a-r1",),
            transition_model_revision="transition-r1",
            temporal_feasibility_revision="temporal-r1",
            resource_revision_refs=("resource:a-r1",),
            capability_revision_refs=("capability:a-r1",),
            authority_revision_refs=("authority:a-r1",),
            risk_classification="high",
            resurrection_dependency_refs=("trigger:a",),
            dormant_reason="low-current-support",
            dormant_generation=3,
            catastrophic_exposure=False,
            sole_hard_route=False,
            unique_hedge=False,
            information_value=0.0,
        )
        kwargs.update(overrides)
        return DormantBranchRevision.create(**kwargs)

    def assess(self, branch=None, **overrides):
        b = branch or self.dormant()
        kwargs = dict(
            dormant_branch=b,
            current_mission_revision="mission-r1",
            current_assumption_revision_refs=("assumption:a-r1",),
            current_evidence_revision_refs=("evidence:a-r1",),
            current_transition_model_revision="transition-r1",
            current_temporal_feasibility_revision="temporal-r1",
            current_resource_revision_refs=("resource:a-r1",),
            current_capability_revision_refs=("capability:a-r1",),
            current_authority_revision_refs=("authority:a-r1",),
            current_risk_classification="high",
            trigger_dependency_refs=("trigger:a",),
            dependencies_observable=True,
        )
        kwargs.update(overrides)
        return BranchResurrectionEvaluator.evaluate(**kwargs)

    def test_current_revalidation_of_every_bound_dimension_allows_resurrection(self):
        result = self.assess()
        self.assertEqual(result.status, ResurrectionStatus.READY)
        self.assertTrue(result.can_resurrect)
        self.assertEqual(result.stale_dimensions, ())

    def test_mission_revision_drift_blocks_resurrection(self):
        result = self.assess(current_mission_revision="mission-r2")
        self.assertEqual(result.status, ResurrectionStatus.STALE)
        self.assertIn("mission_revision", result.stale_dimensions)

    def test_assumption_or_evidence_drift_blocks_resurrection(self):
        assumption = self.assess(current_assumption_revision_refs=("assumption:a-r2",))
        self.assertIn("assumption_revisions", assumption.stale_dimensions)
        evidence = self.assess(current_evidence_revision_refs=("evidence:a-r2",))
        self.assertIn("evidence_revisions", evidence.stale_dimensions)

    def test_transition_or_temporal_drift_blocks_resurrection(self):
        transition = self.assess(current_transition_model_revision="transition-r2")
        self.assertIn("transition_model_revision", transition.stale_dimensions)
        temporal = self.assess(current_temporal_feasibility_revision="temporal-r2")
        self.assertIn("temporal_feasibility_revision", temporal.stale_dimensions)

    def test_resource_capability_or_authority_drift_blocks_resurrection(self):
        resource = self.assess(current_resource_revision_refs=("resource:a-r2",))
        self.assertIn("resource_revisions", resource.stale_dimensions)
        capability = self.assess(current_capability_revision_refs=("capability:a-r2",))
        self.assertIn("capability_revisions", capability.stale_dimensions)
        authority = self.assess(current_authority_revision_refs=("authority:a-r2",))
        self.assertIn("authority_revisions", authority.stale_dimensions)

    def test_risk_reclassification_blocks_old_dormant_contract(self):
        result = self.assess(current_risk_classification="catastrophic")
        self.assertEqual(result.status, ResurrectionStatus.STALE)
        self.assertIn("risk_classification", result.stale_dimensions)

    def test_trigger_becoming_likely_is_not_enough_if_dependency_lineage_changed(self):
        result = self.assess(trigger_dependency_refs=("trigger:a-r2",))
        self.assertEqual(result.status, ResurrectionStatus.STALE)
        self.assertIn("resurrection_dependencies", result.stale_dimensions)

    def test_unobservable_revalidation_is_unknown_not_ready(self):
        result = self.assess(dependencies_observable=False)
        self.assertEqual(result.status, ResurrectionStatus.UNKNOWN)
        self.assertFalse(result.can_resurrect)

    def test_probability_only_pruning_is_forbidden_for_protected_branches(self):
        for branch in (
            self.dormant(catastrophic_exposure=True),
            self.dormant(sole_hard_route=True),
            self.dormant(unique_hedge=True),
            self.dormant(information_value=0.1),
        ):
            self.assertFalse(branch.probability_prunable)
        self.assertTrue(self.dormant().probability_prunable)

    def test_revision_and_generation_participate_in_digest(self):
        base = self.dormant()
        changed = self.dormant(revision_id="branch-a-r2", dormant_generation=4)
        self.assertNotEqual(base.canonical_digest, changed.canonical_digest)

    def test_validation_fails_closed(self):
        with self.assertRaises(ValueError):
            self.dormant(dormant_generation=-1)
        with self.assertRaises(ValueError):
            self.dormant(information_value=-1)
        with self.assertRaises(ValueError):
            self.dormant(resurrection_dependency_refs=())


if __name__ == "__main__":
    unittest.main()
