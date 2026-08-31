from __future__ import annotations

import unittest

from nolane_plan.control_plane import (
    ControlPlaneResourceRevision,
    ReactionJobContract,
    ReactionResourceDemand,
)
from nolane_plan.global_exclusion import GlobalExclusionAssessment, GlobalExclusionStatus
from nolane_plan.schedulability import ReactionSchedulabilityEvaluator, ReactionSchedulabilityLevel
from nolane_plan.seals import ArtifactAssurance, CompositionStatus, ProofContextComponent, SealCompiler


class Wave8RemainingClosureTests(unittest.TestCase):
    def test_action_local_sufficiency_never_implies_global_exclusion(self):
        assessment = GlobalExclusionAssessment.create(
            candidate_universe_revision="candidate-universe@local",
            candidate_refs=("action:a", "action:b"),
            surviving_refs=(),
            completeness_assurance="ACTION_LOCAL_ONLY",
        )
        self.assertEqual(GlobalExclusionStatus.UNKNOWN, assessment.status)

    def test_finite_complete_candidate_universe_supports_bounded_exclusion(self):
        excluded = GlobalExclusionAssessment.create(
            candidate_universe_revision="candidate-universe@1",
            candidate_refs=("action:a", "action:b", "action:c"),
            surviving_refs=(),
            completeness_assurance="COMPLETE_BOUNDED",
        )
        surviving = GlobalExclusionAssessment.create(
            candidate_universe_revision="candidate-universe@1",
            candidate_refs=("action:a", "action:b", "action:c"),
            surviving_refs=("action:b",),
            completeness_assurance="COMPLETE_BOUNDED",
        )
        self.assertEqual(GlobalExclusionStatus.EXCLUDED, excluded.status)
        self.assertEqual(GlobalExclusionStatus.NOT_EXCLUDED, surviving.status)
        self.assertEqual(("action:a", "action:b", "action:c"), excluded.candidate_refs)
        self.assertEqual(("action:b",), surviving.surviving_refs)

    def test_missing_or_opaque_candidate_universe_is_unknown(self):
        for assurance in ("INCOMPLETE", "OPAQUE", "ACTION_LOCAL_ONLY"):
            with self.subTest(assurance=assurance):
                assessment = GlobalExclusionAssessment.create(
                    candidate_universe_revision="candidate-universe@opaque",
                    candidate_refs=("action:a",),
                    surviving_refs=(),
                    completeness_assurance=assurance,
                )
                self.assertEqual(GlobalExclusionStatus.UNKNOWN, assessment.status)

    @staticmethod
    def context(ref: str, worlds, *, theory: str = "finite-world-set") -> ProofContextComponent:
        return ProofContextComponent.create(
            component_ref=ref,
            assurance=ArtifactAssurance.CHECKED,
            assumptions=(),
            scope="mission",
            guarantee="G2",
            debt_refs=(),
            risk_refs=(),
            authority_refs=(),
            resource_refs=(),
            external_regime_refs=(),
            validity_horizon=(0, 100),
            constraint_theory=theory,
            allowed_worlds=worlds,
        )

    def test_pairwise_compatible_but_globally_inconsistent_contexts_never_compose(self):
        rows = (
            self.context("ctx:a", ("w1", "w2")),
            self.context("ctx:b", ("w2", "w3")),
            self.context("ctx:c", ("w1", "w3")),
        )
        for left, right in ((rows[0], rows[1]), (rows[0], rows[2]), (rows[1], rows[2])):
            pair = SealCompiler.compose_contexts((left, right), accepted_debt_refs=())
            self.assertEqual(CompositionStatus.COMPOSABLE, pair.status)
            self.assertTrue(pair.surviving_worlds)

        global_result = SealCompiler.compose_contexts(rows, accepted_debt_refs=())
        self.assertEqual(CompositionStatus.NONCOMPOSABLE_CONFLICT, global_result.status)
        self.assertEqual((), global_result.surviving_worlds)

    def test_unsupported_context_theory_is_explicit_fail_closed_not_composable(self):
        result = SealCompiler.compose_contexts(
            (self.context("ctx:unsupported", (), theory="opaque-theory"),),
            accepted_debt_refs=(),
        )
        self.assertEqual(CompositionStatus.UNSUPPORTED_CONSTRAINT_THEORY, result.status)
        self.assertNotEqual(CompositionStatus.COMPOSABLE, result.status)

    @staticmethod
    def resource(capacity: int) -> ControlPlaneResourceRevision:
        return ControlPlaneResourceRevision.create(
            resource_id="worker",
            revision_id=f"worker@{capacity}",
            resource_kind="CONCURRENCY",
            capacity_units=float(capacity),
            concurrency_limit=capacity,
            service_rate_per_second=100.0,
            rate_window_seconds=1.0,
            availability_interval=(0.0, 20.0),
            priority_policy_ref="priority@1",
            reservation_policy_ref="reservation@1",
            regime_ref="resource-regime@1",
            assurance_profile="BOUNDED",
            opaque_dimensions=(),
            conservative_capacity_bound=None,
            validity_regime="ACTIVE",
        )

    @staticmethod
    def jobs(count: int):
        rows = []
        for index in range(count):
            demand = ReactionResourceDemand.create(
                resource_ref="worker",
                required_service=1.0,
                required_concurrency_units=1,
                release_offset_interval=(0.0, 0.0),
                demand_window=(0.0, 10.0),
                mandatory=True,
            )
            rows.append(
                ReactionJobContract.create(
                    reaction_job_id=f"job:{index}",
                    revision_id=f"job:{index}@1",
                    policy_scope="policy:wave8",
                    mission_revision="mission@1",
                    information_partition_revision="partition@1",
                    reaction_envelope_ref="reaction@1",
                    release_window=(0.0, 0.0),
                    deadline=10.0,
                    resource_demands=(demand,),
                    coexistence_tags=("same-window",),
                    correlation_refs=(),
                    priority_class="critical",
                    reservation_refs=(),
                    risk_class="consequential",
                    model_adequacy_debt_refs=(),
                    validity_regime="ACTIVE",
                )
            )
        return tuple(rows)

    @staticmethod
    def evaluate(jobs, resource, suffix: str):
        return ReactionSchedulabilityEvaluator.evaluate(
            certificate_id=f"sched:{suffix}",
            revision_id=f"sched:{suffix}@1",
            policy_scope="policy:wave8",
            mission_revision="mission@1",
            information_partition_revision="partition@1",
            jobs=jobs,
            resources=(resource,),
            mutually_exclusive_pairs=(),
            coexistence_known=True,
            resource_reservation_refs=(),
            scheduling_model_id="wave8-monotonicity",
            scheduling_model_version="1",
            analysis_mode="EXACT_BOUNDED",
            worst_case_or_interval_assumptions=(),
            proof_or_solver_ref="enumeration:wave8",
            assurance_profile="BOUNDED",
            model_adequacy_debt_refs=(),
            validity_regime="ACTIVE",
        )

    def test_capacity_decrease_and_load_increase_never_improve_strong_schedulability(self):
        rank = {
            ReactionSchedulabilityLevel.RS0_UNANALYZED: 0,
            ReactionSchedulabilityLevel.RS1_EACH_JOB_INDIVIDUALLY_FEASIBLE: 1,
            ReactionSchedulabilityLevel.RS2_DECLARED_COHORT_FEASIBLE: 2,
            ReactionSchedulabilityLevel.RS3_ROBUST_COHORT_SCHEDULABLE: 3,
            ReactionSchedulabilityLevel.RS4_CLOSED_SUBDOMAIN_PROVEN: 4,
        }
        cases = 0
        for job_count in range(1, 6):
            for capacity in range(2, 7):
                base_jobs = self.jobs(job_count)
                base = self.evaluate(base_jobs, self.resource(capacity), f"base:{job_count}:{capacity}")
                less_capacity = self.evaluate(
                    base_jobs,
                    self.resource(capacity - 1),
                    f"capacity-down:{job_count}:{capacity}",
                )
                more_load = self.evaluate(
                    self.jobs(job_count + 1),
                    self.resource(capacity),
                    f"load-up:{job_count}:{capacity}",
                )
                self.assertLessEqual(rank[less_capacity.level], rank[base.level])
                self.assertLessEqual(rank[more_load.level], rank[base.level])
                cases += 1
        self.assertEqual(25, cases)


if __name__ == "__main__":
    unittest.main()
