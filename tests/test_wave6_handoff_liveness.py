from __future__ import annotations

import unittest

from nolane_plan.handoff_liveness import (
    ContinuationProgressRank,
    HandoffLivenessEvaluator,
    HandoffProgressPolicy,
    HandoffProgressStatus,
)


class Wave6HandoffLivenessTests(unittest.TestCase):
    def rank(self, **overrides):
        kwargs = dict(
            rank_id="rank-a",
            revision_id="rank-a-r1",
            continuation_scope="policy-1",
            mission_revision="mission-1",
            unresolved_critical_debt_count=3,
            remaining_unprepared_boundaries=2,
            absolute_executable_horizon=100.0,
            minimum_preparedness_at_next_boundary=3,
            remaining_synthesis_workload=5.0,
            reaction_refinement_slack=20.0,
            mission_distance_measure=5.0,
            semantic_continuation_digest="semantic-a",
            debt_equivalence_refs=("debt-class-a", "debt-class-b", "debt-class-c"),
            created_at=0.0,
        )
        kwargs.update(overrides)
        return ContinuationProgressRank.create(**kwargs)

    def policy(self, **overrides):
        kwargs = dict(
            policy_id="handoff-policy-1",
            revision_id="handoff-policy-r1",
            max_handoff_count=8,
            max_total_deferral_time=30.0,
            minimum_horizon_advance=5.0,
            minimum_debt_reduction_rate=1,
            mandatory_preparedness_floor_by_time=((10.0, 2), (20.0, 3)),
            bounded_stutter_allowance=2,
            recovery_stutter_allowance=1,
            absolute_latest_safe_refinement_time=50.0,
            temporal_authority_ref="temporal-authority-r1",
        )
        kwargs.update(overrides)
        return HandoffProgressPolicy.create(**kwargs)

    def evaluate(self, old, new, **overrides):
        kwargs = dict(
            certificate_id="live-1",
            revision_id="live-r1",
            source_continuation_ref="cont-a",
            successor_continuation_ref="cont-b",
            old_rank=old,
            new_rank=new,
            progress_policy=self.policy(),
            handoff_count=1,
            ordinary_stutter_count=0,
            recovery_stutter_count=0,
            total_deferral_time=1.0,
            recursive_feasibility=True,
            information_available_by_deadline=True,
            recovery_mode=False,
            temporal_authority_revision_ref="temporal-authority-r1",
            current_time=1.0,
            debt_lineage_equivalent=True,
        )
        kwargs.update(overrides)
        return HandoffLivenessEvaluator.evaluate(**kwargs)

    def test_debt_reduction_is_strict_progress(self):
        old = self.rank()
        new = self.rank(
            rank_id="rank-b",
            revision_id="rank-b-r1",
            unresolved_critical_debt_count=2,
            debt_equivalence_refs=("debt-class-a", "debt-class-b"),
            semantic_continuation_digest="semantic-b",
            created_at=2.0,
        )
        cert = self.evaluate(old, new)
        self.assertEqual(cert.status, HandoffProgressStatus.STRICT_PROGRESS)
        self.assertTrue(cert.supports_safe_handoff)

    def test_semantically_identical_handoffs_consume_bounded_stutter(self):
        old = self.rank()
        new = self.rank(rank_id="rank-b", revision_id="rank-b-r1", created_at=2.0)
        cert = self.evaluate(old, new, ordinary_stutter_count=1)
        self.assertEqual(cert.status, HandoffProgressStatus.BOUNDED_STUTTER)
        exhausted = self.evaluate(old, new, ordinary_stutter_count=2)
        self.assertEqual(exhausted.status, HandoffProgressStatus.NO_PROGRESS)
        self.assertFalse(exhausted.supports_safe_handoff)

    def test_renaming_equivalent_debt_does_not_fake_progress(self):
        old = self.rank(debt_equivalence_refs=("root-a", "root-b", "root-c"))
        new = self.rank(
            rank_id="rank-b",
            revision_id="rank-b-r1",
            semantic_continuation_digest="semantic-b",
            debt_equivalence_refs=("root-a", "root-b", "root-c"),
            created_at=2.0,
        )
        cert = self.evaluate(old, new, debt_lineage_equivalent=True)
        self.assertEqual(cert.status, HandoffProgressStatus.BOUNDED_STUTTER)

    def test_absolute_horizon_advance_can_count_as_progress_but_rebase_cannot(self):
        old = self.rank(absolute_executable_horizon=100.0)
        advanced = self.rank(
            rank_id="rank-b",
            revision_id="rank-b-r1",
            absolute_executable_horizon=106.0,
            semantic_continuation_digest="semantic-b",
            created_at=2.0,
        )
        self.assertEqual(self.evaluate(old, advanced).status, HandoffProgressStatus.STRICT_PROGRESS)

        rebased = self.rank(
            rank_id="rank-c",
            revision_id="rank-c-r1",
            absolute_executable_horizon=90.0,
            semantic_continuation_digest="semantic-c",
            created_at=2.0,
        )
        self.assertNotEqual(self.evaluate(old, rebased).status, HandoffProgressStatus.STRICT_PROGRESS)

    def test_recovery_stutter_is_separate_and_bounded(self):
        old = self.rank()
        new = self.rank(rank_id="rank-b", revision_id="rank-b-r1", created_at=2.0)
        cert = self.evaluate(old, new, recovery_mode=True, recovery_stutter_count=0)
        self.assertEqual(cert.status, HandoffProgressStatus.RECOVERY_STUTTER)
        exhausted = self.evaluate(old, new, recovery_mode=True, recovery_stutter_count=1)
        self.assertEqual(exhausted.status, HandoffProgressStatus.NO_PROGRESS)

    def test_plan_cannot_self_extend_absolute_refinement_deadline(self):
        old_policy = self.policy(absolute_latest_safe_refinement_time=50.0)
        extended = self.policy(
            revision_id="handoff-policy-r2",
            absolute_latest_safe_refinement_time=70.0,
            temporal_authority_ref="temporal-authority-r1",
        )
        self.assertFalse(
            HandoffLivenessEvaluator.deadline_revision_is_grounded(
                old_policy=old_policy,
                new_policy=extended,
                temporal_authority_revision_ref="temporal-authority-r1",
            )
        )
        grounded = self.policy(
            revision_id="handoff-policy-r3",
            absolute_latest_safe_refinement_time=70.0,
            temporal_authority_ref="temporal-authority-r2",
        )
        self.assertTrue(
            HandoffLivenessEvaluator.deadline_revision_is_grounded(
                old_policy=old_policy,
                new_policy=grounded,
                temporal_authority_revision_ref="temporal-authority-r2",
            )
        )

    def test_recursive_feasibility_unknown_or_false_blocks_safe_handoff(self):
        old = self.rank()
        new = self.rank(rank_id="rank-b", revision_id="rank-b-r1", unresolved_critical_debt_count=2, created_at=2.0)
        for value in (False, None):
            cert = self.evaluate(old, new, recursive_feasibility=value)
            self.assertEqual(cert.status, HandoffProgressStatus.UNKNOWN)
            self.assertFalse(cert.supports_safe_handoff)

    def test_handoff_count_and_total_deferral_budget_are_hard_limits(self):
        old = self.rank()
        new = self.rank(rank_id="rank-b", revision_id="rank-b-r1", unresolved_critical_debt_count=2, created_at=2.0)
        too_many = self.evaluate(old, new, handoff_count=9)
        self.assertEqual(too_many.status, HandoffProgressStatus.NO_PROGRESS)
        too_late = self.evaluate(old, new, total_deferral_time=31.0)
        self.assertEqual(too_late.status, HandoffProgressStatus.NO_PROGRESS)

    def test_information_available_only_after_deadline_is_not_live(self):
        old = self.rank()
        new = self.rank(rank_id="rank-b", revision_id="rank-b-r1", unresolved_critical_debt_count=2, created_at=2.0)
        cert = self.evaluate(old, new, information_available_by_deadline=False)
        self.assertEqual(cert.status, HandoffProgressStatus.UNKNOWN)
        self.assertFalse(cert.supports_safe_handoff)

    def test_policy_and_rank_validation_fail_closed(self):
        with self.assertRaises(ValueError):
            self.rank(unresolved_critical_debt_count=-1)
        with self.assertRaises(ValueError):
            self.policy(max_handoff_count=-1)
        with self.assertRaises(ValueError):
            self.policy(bounded_stutter_allowance=-1)
        with self.assertRaises(ValueError):
            self.policy(mandatory_preparedness_floor_by_time=((20.0, 3), (10.0, 2)))


if __name__ == "__main__":
    unittest.main()
