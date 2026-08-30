from __future__ import annotations

import unittest

from nolane_plan.control_plane import (
    ControlPlaneResourceRevision,
    ReactionJobContract,
    ReactionResourceDemand,
)
from nolane_plan.schedulability import (
    ReactionSchedulabilityEvaluator,
    ReactionSchedulabilityLevel,
    SchedulabilityAnalysisMode,
)


class Wave6SchedulabilityTests(unittest.TestCase):
    def resource(self, **overrides):
        kwargs = dict(
            resource_id="verifier",
            revision_id="verifier-r1",
            resource_kind="CONCURRENCY",
            capacity_units=1.0,
            concurrency_limit=1,
            service_rate_per_second=1.0,
            rate_window_seconds=1.0,
            availability_interval=(0.0, 10.0),
            priority_policy_ref="priority-v1",
            reservation_policy_ref="reservation-v1",
            regime_ref="regime-v1",
            assurance_profile="bounded-worst-case",
            opaque_dimensions=(),
            conservative_capacity_bound=None,
            validity_regime="mission-1",
        )
        kwargs.update(overrides)
        return ControlPlaneResourceRevision.create(**kwargs)

    def job(self, job_id: str, **overrides):
        demand = ReactionResourceDemand.create(
            resource_ref=overrides.pop("resource_ref", "verifier"),
            required_service=overrides.pop("required_service", 1.0),
            required_concurrency_units=overrides.pop("required_concurrency_units", 1),
            release_offset_interval=(0.0, 0.0),
            demand_window=(0.0, 1.0),
            mandatory=True,
        )
        kwargs = dict(
            reaction_job_id=job_id,
            revision_id=f"{job_id}-r1",
            policy_scope="policy-1",
            mission_revision="mission-1",
            information_partition_revision="partition-1",
            reaction_envelope_ref=f"reaction-{job_id}",
            release_window=(0.0, 0.0),
            deadline=1.0,
            resource_demands=(demand,),
            coexistence_tags=("cohort:primary",),
            correlation_refs=("corr-r1",),
            priority_class="deadline-critical",
            reservation_refs=(),
            risk_class="high",
            model_adequacy_debt_refs=(),
            validity_regime="mission-1",
        )
        kwargs.update(overrides)
        return ReactionJobContract.create(**kwargs)

    def evaluate(self, *, jobs, resources=None, mutually_exclusive_pairs=(), coexistence_known=True, mode=SchedulabilityAnalysisMode.EXACT_BOUNDED, closed_subdomain_proof_ref=None):
        return ReactionSchedulabilityEvaluator.evaluate(
            certificate_id="sched-1",
            revision_id="sched-r1",
            policy_scope="policy-1",
            mission_revision="mission-1",
            information_partition_revision="partition-1",
            jobs=tuple(jobs),
            resources=tuple(resources or (self.resource(),)),
            mutually_exclusive_pairs=tuple(mutually_exclusive_pairs),
            coexistence_known=coexistence_known,
            resource_reservation_refs=(),
            scheduling_model_id="bounded-demand-v1",
            scheduling_model_version="1",
            analysis_mode=mode,
            worst_case_or_interval_assumptions=("bounded-release",),
            proof_or_solver_ref="deterministic-bounded-evaluator",
            assurance_profile="bounded-worst-case",
            model_adequacy_debt_refs=(),
            validity_regime="mission-1",
            closed_subdomain_proof_ref=closed_subdomain_proof_ref,
        )

    def test_each_job_can_fit_while_joint_cohort_overloads_shared_resource(self):
        cert = self.evaluate(jobs=(self.job("a"), self.job("b")))
        self.assertEqual(cert.level, ReactionSchedulabilityLevel.RS1_EACH_JOB_INDIVIDUALLY_FEASIBLE)
        self.assertFalse(cert.supports_strong_joint_guarantee)
        self.assertEqual(len(cert.overload_witnesses), 1)
        self.assertEqual(cert.overload_witnesses[0].resource_ref, "verifier")
        self.assertEqual(set(cert.overload_witnesses[0].job_refs), {"a", "b"})

    def test_mutually_exclusive_jobs_do_not_create_simultaneous_demand(self):
        cert = self.evaluate(
            jobs=(self.job("a"), self.job("b")),
            mutually_exclusive_pairs=(("a", "b"),),
        )
        self.assertEqual(cert.level, ReactionSchedulabilityLevel.RS2_DECLARED_COHORT_FEASIBLE)
        self.assertTrue(cert.supports_strong_joint_guarantee)
        self.assertEqual(cert.overload_witnesses, ())

    def test_unknown_coexistence_never_becomes_optimistic_exclusivity(self):
        cert = self.evaluate(
            jobs=(self.job("a"), self.job("b")),
            mutually_exclusive_pairs=(("a", "b"),),
            coexistence_known=False,
        )
        self.assertEqual(cert.level, ReactionSchedulabilityLevel.RS1_EACH_JOB_INDIVIDUALLY_FEASIBLE)
        self.assertTrue(cert.model_adequacy_debt_refs)

    def test_rate_limit_and_kernel_writer_can_bind_joint_feasibility(self):
        rate = self.resource(
            resource_id="api-rate",
            resource_kind="RATE_LIMIT",
            capacity_units=1.0,
            concurrency_limit=100,
            service_rate_per_second=100.0,
            rate_window_seconds=1.0,
        )
        a = self.job("a", resource_ref="api-rate", required_service=1.0, required_concurrency_units=0)
        b = self.job("b", resource_ref="api-rate", required_service=1.0, required_concurrency_units=0)
        self.assertEqual(
            self.evaluate(jobs=(a, b), resources=(rate,)).level,
            ReactionSchedulabilityLevel.RS1_EACH_JOB_INDIVIDUALLY_FEASIBLE,
        )

        writer = self.resource(
            resource_id="writer",
            resource_kind="KERNEL_WRITER",
            capacity_units=1.0,
            concurrency_limit=1,
            service_rate_per_second=1.0,
        )
        wa = self.job("wa", resource_ref="writer", required_service=1.0)
        wb = self.job("wb", resource_ref="writer", required_service=1.0)
        self.assertEqual(
            self.evaluate(jobs=(wa, wb), resources=(writer,)).level,
            ReactionSchedulabilityLevel.RS1_EACH_JOB_INDIVIDUALLY_FEASIBLE,
        )

    def test_scenario_stress_cannot_be_rendered_as_exact_strong_proof(self):
        roomy = self.resource(capacity_units=3.0, concurrency_limit=3, service_rate_per_second=3.0)
        cert = self.evaluate(
            jobs=(self.job("a"), self.job("b")),
            resources=(roomy,),
            mode=SchedulabilityAnalysisMode.SCENARIO_STRESS,
        )
        self.assertEqual(cert.level, ReactionSchedulabilityLevel.RS1_EACH_JOB_INDIVIDUALLY_FEASIBLE)
        self.assertFalse(cert.supports_strong_joint_guarantee)

    def test_unsupported_analysis_fails_closed_as_rs0(self):
        cert = self.evaluate(
            jobs=(self.job("a"),),
            mode=SchedulabilityAnalysisMode.UNSUPPORTED,
        )
        self.assertEqual(cert.level, ReactionSchedulabilityLevel.RS0_UNANALYZED)
        self.assertFalse(cert.supports_strong_joint_guarantee)
        self.assertTrue(cert.model_adequacy_debt_refs)

    def test_rs4_requires_explicit_closed_subdomain_proof(self):
        robust = self.resource(capacity_units=4.0, concurrency_limit=4, service_rate_per_second=4.0)
        without = self.evaluate(
            jobs=(self.job("a"), self.job("b")),
            resources=(robust,),
            mode=SchedulabilityAnalysisMode.INTERVAL_ROBUST,
        )
        self.assertEqual(without.level, ReactionSchedulabilityLevel.RS3_ROBUST_COHORT_SCHEDULABLE)
        with_proof = self.evaluate(
            jobs=(self.job("a"), self.job("b")),
            resources=(robust,),
            mode=SchedulabilityAnalysisMode.INTERVAL_ROBUST,
            closed_subdomain_proof_ref="closed-proof-1",
        )
        self.assertEqual(with_proof.level, ReactionSchedulabilityLevel.RS4_CLOSED_SUBDOMAIN_PROVEN)

    def test_certificate_reuse_binds_exact_job_and_resource_digests(self):
        resource = self.resource(capacity_units=4.0, concurrency_limit=4, service_rate_per_second=4.0)
        job = self.job("a")
        cert = self.evaluate(jobs=(job,), resources=(resource,))
        self.assertTrue(cert.is_current(jobs=(job,), resources=(resource,)))
        resource_r2 = self.resource(
            revision_id="verifier-r2",
            regime_ref="regime-v2",
            capacity_units=4.0,
            concurrency_limit=4,
            service_rate_per_second=4.0,
        )
        self.assertFalse(cert.is_current(jobs=(job,), resources=(resource_r2,)))
        job_r2 = self.job("a", revision_id="a-r2")
        self.assertFalse(cert.is_current(jobs=(job_r2,), resources=(resource,)))


if __name__ == "__main__":
    unittest.main()
