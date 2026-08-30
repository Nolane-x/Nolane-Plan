from __future__ import annotations

import unittest

from nolane_plan.policy_certificates import RecallLevel, TotalityMode
from nolane_plan.policy_executability import (
    ExecutabilityStatus,
    PolicyExecutabilityEvaluator,
)
from nolane_plan.policy_readiness import (
    ReactionControllabilityClass,
    TerminalSemantics,
    ContinuationContract,
)
from nolane_plan.seals import CompositionStatus, SealStatus


class Wave5PolicyExecutabilityTests(unittest.TestCase):
    def _continuation(self, terminal=TerminalSemantics.MISSION_COMPLETE):
        return ContinuationContract.create(
            continuation_contract_id="continuation@1",
            revision_id="continuation@1",
            boundary_region_ref="boundary@1",
            mission_revision=1,
            certified_prefix_horizon=100,
            terminal_semantics=terminal,
            required_next_preparedness_profile="prep@next",
            remaining_subgoal_obligation_refs=(),
            refinement_dependencies=("world-model@1",),
            required_action_space_capability_discovery=("deploy",),
            estimated_refinement_latency=5,
            latest_safe_refinement_time=120,
            fallback_if_refinement_misses_boundary="recovery@1",
            continuation_debt_refs=("debt:suffix",) if terminal == TerminalSemantics.DEFERRED_CONTINUATION else (),
            assurance_profile="CHECKED",
        )

    def _evaluate(self, **changes):
        fields = dict(
            assessment_id="exec@1",
            revision_id="exec@1",
            scope_ref="action:deploy",
            mission_revision=1,
            plan_snapshot_version=7,
            policy_revision="policy@1",
            information_partition_revision="partition@1",
            action_space_revision="actions@1",
            bound_snapshot_revisions={
                "mission": "1",
                "plan": "7",
                "policy": "policy@1",
                "partition": "partition@1",
                "actions": "actions@1",
            },
            nonanticipativity_valid=True,
            recall_level=RecallLevel.RECALL_SUFFICIENT,
            totality_mode=TotalityMode.TOTAL,
            edge_certificates_valid=True,
            shared_resource_commitments_feasible=True,
            information_capability_preserved=True,
            reaction_class=ReactionControllabilityClass.IA2_BOUNDED_GUARANTEED_TIMELY,
            required_reaction_class=ReactionControllabilityClass.IA2_BOUNDED_GUARANTEED_TIMELY,
            preparedness_level=4,
            required_preparedness_level=3,
            composition_status=CompositionStatus.COMPOSABLE,
            route_guarantee_met=True,
            continuation=self._continuation(),
            requested_horizon=100,
            seal_status=SealStatus.SEALED,
            debt_refs=(),
            accepted_debt_refs=(),
            model_confidence=0.0,
        )
        fields.update(changes)
        return PolicyExecutabilityEvaluator.evaluate(**fields)

    def test_status_vocabulary_is_exact(self):
        self.assertEqual(
            {status.value for status in ExecutabilityStatus},
            {
                "EXEC_UNANALYZED",
                "EXEC_PARTIAL",
                "EXEC_BOUNDED",
                "EXEC_BOUNDED_WITH_ACCEPTED_DEBT",
                "EXEC_NOT_EXECUTABLE",
                "EXEC_UNKNOWN",
            },
        )

    def test_complete_coherent_closure_can_be_exec_bounded(self):
        assessment = self._evaluate()
        self.assertEqual(assessment.status, ExecutabilityStatus.EXEC_BOUNDED)
        self.assertFalse(assessment.blockers)

    def test_known_policy_hole_makes_exec_bounded_impossible(self):
        assessment = self._evaluate(totality_mode=TotalityMode.INCOMPLETE, model_confidence=1.0)
        self.assertEqual(assessment.status, ExecutabilityStatus.EXEC_NOT_EXECUTABLE)
        self.assertIn("POLICY_TOTALITY_HOLE", assessment.blockers)

    def test_unresolved_recall_is_exec_unknown_not_bounded(self):
        assessment = self._evaluate(recall_level=RecallLevel.RECALL_UNKNOWN)
        self.assertEqual(assessment.status, ExecutabilityStatus.EXEC_UNKNOWN)
        self.assertIn("RECALL_UNRESOLVED", assessment.unknowns)

    def test_stitch_failure_and_ia1_reaction_both_block_strong_executability(self):
        assessment = self._evaluate(
            edge_certificates_valid=False,
            reaction_class=ReactionControllabilityClass.IA1_POSSIBLE_TIMELY,
            model_confidence=1.0,
        )
        self.assertEqual(assessment.status, ExecutabilityStatus.EXEC_NOT_EXECUTABLE)
        self.assertIn("POLICY_EDGE_STITCH_FAILURE", assessment.blockers)
        self.assertIn("REACTION_CONTROLLABILITY_BELOW_FLOOR", assessment.blockers)

    def test_globally_noncomposable_or_unknown_context_cannot_be_exec_bounded(self):
        conflict = self._evaluate(composition_status=CompositionStatus.NONCOMPOSABLE_CONFLICT)
        unknown = self._evaluate(composition_status=CompositionStatus.COMPOSITION_UNKNOWN)
        self.assertEqual(conflict.status, ExecutabilityStatus.EXEC_NOT_EXECUTABLE)
        self.assertEqual(unknown.status, ExecutabilityStatus.EXEC_UNKNOWN)

    def test_deferred_continuation_cannot_extend_requested_executable_horizon(self):
        assessment = self._evaluate(
            continuation=self._continuation(TerminalSemantics.DEFERRED_CONTINUATION),
            requested_horizon=101,
            debt_refs=("debt:suffix",),
            accepted_debt_refs=("debt:suffix",),
        )
        self.assertEqual(assessment.status, ExecutabilityStatus.EXEC_NOT_EXECUTABLE)
        self.assertIn("CONTINUATION_HORIZON_OPEN", assessment.blockers)

    def test_stale_or_revoked_seal_blocks_executability(self):
        stale = self._evaluate(seal_status=SealStatus.STALE)
        revoked = self._evaluate(seal_status=SealStatus.REVOKED)
        self.assertEqual(stale.status, ExecutabilityStatus.EXEC_NOT_EXECUTABLE)
        self.assertEqual(revoked.status, ExecutabilityStatus.EXEC_NOT_EXECUTABLE)

    def test_explicit_accepted_debt_gets_qualified_status_not_clean_bounded(self):
        assessment = self._evaluate(
            debt_refs=("debt:bounded-model-gap",),
            accepted_debt_refs=("debt:bounded-model-gap",),
        )
        self.assertEqual(assessment.status, ExecutabilityStatus.EXEC_BOUNDED_WITH_ACCEPTED_DEBT)
        self.assertEqual(assessment.accepted_debt_refs, ("debt:bounded-model-gap",))

    def test_unaccepted_debt_is_partial_not_silently_bounded(self):
        assessment = self._evaluate(debt_refs=("debt:open",), accepted_debt_refs=())
        self.assertEqual(assessment.status, ExecutabilityStatus.EXEC_PARTIAL)
        self.assertIn("debt:open", assessment.unaccepted_debt_refs)

    def test_mixed_snapshot_revisions_fail_closed(self):
        assessment = self._evaluate(
            bound_snapshot_revisions={
                "mission": "1",
                "plan": "6",
                "policy": "policy@1",
                "partition": "partition@1",
                "actions": "actions@1",
            }
        )
        self.assertEqual(assessment.status, ExecutabilityStatus.EXEC_NOT_EXECUTABLE)
        self.assertIn("MIXED_SEMANTIC_SNAPSHOT", assessment.blockers)

    def test_information_capability_loss_and_low_preparedness_block(self):
        assessment = self._evaluate(
            information_capability_preserved=False,
            preparedness_level=2,
            required_preparedness_level=3,
        )
        self.assertEqual(assessment.status, ExecutabilityStatus.EXEC_NOT_EXECUTABLE)
        self.assertIn("INFORMATION_CAPABILITY_LOSS", assessment.blockers)
        self.assertIn("PREPAREDNESS_BELOW_FLOOR", assessment.blockers)


if __name__ == "__main__":
    unittest.main()
