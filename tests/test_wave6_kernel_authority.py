from __future__ import annotations

import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path

from nolane_plan import PlanKernel
from nolane_plan.control_plane import ControlPlaneResourceRevision, ReactionJobContract, ReactionResourceDemand
from nolane_plan.handoff_liveness import (
    ContinuationProgressRank,
    HandoffLivenessEvaluator,
    HandoffProgressPolicy,
)
from nolane_plan.handoff_stability import HandoffStabilityContract, HandoffStabilityEvaluator
from nolane_plan.option_independence import OptionIndependenceCertificate
from nolane_plan.policy_certificates import OutcomeSupport, PolicyTotalityCertificate, SuccessorHandler
from nolane_plan.policy_coverage import ExecutablePolicyCoverageAssessment
from nolane_plan.schedulability import ReactionSchedulabilityEvaluator, ReactionSchedulabilityLevel
from nolane_plan.schedulability_runtime import install_schedulability_runtime
from nolane_plan.types import AuthorizationError


@dataclass(frozen=True)
class _Authorization:
    id: str


class Wave6KernelAuthorityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.kernel = PlanKernel.create(Path(self.tmp.name), "wave6 authority")
        install_schedulability_runtime(PlanKernel)
        # Existing instances predate explicit installer calls in some harnesses.
        if not hasattr(self.kernel, "schedulability_certificates"):
            self.kernel = PlanKernel.create(Path(self.tmp.name) / "fresh", "wave6 authority fresh")
        self.delegate_calls = 0

        def delegate(**kwargs):
            self.delegate_calls += 1
            auth = _Authorization(f"auth-{self.delegate_calls}")
            self.kernel.authorization_identity_bindings[auth.id] = "identity-binding"
            self.kernel.proof_authorization_bindings[auth.id] = {"proof": kwargs["proof_artifact_revision"]}
            self.kernel.policy_authorization_bindings[auth.id] = {"policy_node_revision": kwargs["policy_node_revision"]}
            return auth

        self.kernel.authorize_sealed_policy = delegate

    def tearDown(self):
        self.tmp.cleanup()

    def _resource(self, revision_id="verifier@1", capacity=2.0):
        return ControlPlaneResourceRevision.create(
            resource_id="verifier",
            revision_id=revision_id,
            resource_kind="CONCURRENCY",
            capacity_units=capacity,
            concurrency_limit=int(capacity),
            service_rate_per_second=10.0,
            rate_window_seconds=1.0,
            availability_interval=(0.0, 100.0),
            priority_policy_ref="priority@1",
            reservation_policy_ref="reservation@1",
            regime_ref="runtime@1",
            assurance_profile="bounded-worst-case",
            opaque_dimensions=(),
            conservative_capacity_bound=None,
            validity_regime="runtime@1",
        )

    def _job(self, job_id="reaction-a", service=1.0):
        demand = ReactionResourceDemand.create(
            resource_ref="verifier",
            required_service=service,
            required_concurrency_units=1,
            release_offset_interval=(0.0, 0.0),
            demand_window=(0.0, 1.0),
            mandatory=True,
        )
        return ReactionJobContract.create(
            reaction_job_id=job_id,
            revision_id=f"{job_id}@1",
            policy_scope="action:act",
            mission_revision=str(self.kernel.mission.current.version),
            information_partition_revision="partition@1",
            reaction_envelope_ref=f"envelope:{job_id}",
            release_window=(0.0, 0.0),
            deadline=1.0,
            resource_demands=(demand,),
            coexistence_tags=("same-window",),
            correlation_refs=(),
            priority_class="critical",
            reservation_refs=(),
            risk_class="consequential",
            model_adequacy_debt_refs=(),
            validity_regime="runtime@1",
        )

    def _sched(self, *, jobs=None, resource=None, coexistence_known=True):
        jobs = tuple(jobs or (self._job(),))
        resource = resource or self._resource()
        return ReactionSchedulabilityEvaluator.evaluate(
            certificate_id="sched",
            revision_id="sched@1",
            policy_scope="action:act",
            mission_revision=str(self.kernel.mission.current.version),
            information_partition_revision="partition@1",
            jobs=jobs,
            resources=(resource,),
            mutually_exclusive_pairs=(),
            coexistence_known=coexistence_known,
            resource_reservation_refs=(),
            scheduling_model_id="bounded-window",
            scheduling_model_version="1",
            analysis_mode="EXACT_BOUNDED",
            worst_case_or_interval_assumptions=("bounded-service",),
            proof_or_solver_ref="evaluator@1",
            assurance_profile="bounded-worst-case",
            model_adequacy_debt_refs=(),
            validity_regime="runtime@1",
        )

    def _totality(self):
        return PolicyTotalityCertificate.evaluate(
            certificate_id="totality",
            revision_id="totality@1",
            policy_revision="policy@1",
            action_node_revision="policy@1",
            outcomes=(OutcomeSupport("ok", "modeled", True, False),),
            handlers=(SuccessorHandler("ok", "done", "successor", False),),
            solver_status="PROVED",
            created_sequence=0,
            validity_regime="runtime@1",
        )

    def _coverage(self, *, strong=True):
        return ExecutablePolicyCoverageAssessment.create(
            assessment_id="coverage",
            revision_id="coverage@1" if strong else "coverage@degraded",
            policy_scope="action:act",
            policy_totality_certificate=self._totality(),
            transition_observation_model_adequacy="STRONG" if strong else "DEGRADED",
            residual_open_world_status="CLOSED" if strong else "ACTIVE",
            residual_debt_refs=() if strong else ("unknown-transition",),
            closed_domain_proof_ref="closed-domain@1" if strong else None,
            created_sequence=0,
            validity_regime="runtime@1",
        )

    def _independence(self, *, robust=True):
        deps = {"route-a": ("provider:a",), "route-b": ("provider:b",)}
        if not robust:
            deps = {"route-a": ("credential:prod",), "route-b": ("credential:prod",)}
        return OptionIndependenceCertificate.evaluate(
            certificate_id="independence",
            revision_id="independence@1" if robust else "independence@nominal",
            route_refs=("route-a", "route-b"),
            failure_uncertainty_set_ref="failure-set@1",
            shared_dependency_graph_ref="dependency-graph@1",
            route_dependency_refs=deps,
            resource_overlap_refs=(),
            observation_lineage_overlap_refs=(),
            control_plane_overlap_refs=(),
            common_mode_failure_refs=(),
            coactivation_feasible=True,
            assurance_profile="strong",
            analysis_supported=True,
        )

    def _liveness(self, *, exhausted=False):
        old = ContinuationProgressRank.create(
            rank_id="rank-old", revision_id="rank-old@1", continuation_scope="boundary@1",
            mission_revision=str(self.kernel.mission.current.version), unresolved_critical_debt_count=1,
            remaining_unprepared_boundaries=1, absolute_executable_horizon=50,
            minimum_preparedness_at_next_boundary=3, remaining_synthesis_workload=5,
            reaction_refinement_slack=10, mission_distance_measure=5,
            semantic_continuation_digest="same", created_at=10,
        )
        new = ContinuationProgressRank.create(
            rank_id="rank-new", revision_id="rank-new@1", continuation_scope="boundary@1",
            mission_revision=str(self.kernel.mission.current.version), unresolved_critical_debt_count=1,
            remaining_unprepared_boundaries=1, absolute_executable_horizon=50,
            minimum_preparedness_at_next_boundary=3, remaining_synthesis_workload=5,
            reaction_refinement_slack=9, mission_distance_measure=5,
            semantic_continuation_digest="same", created_at=11,
        )
        policy = HandoffProgressPolicy.create(
            policy_id="handoff-policy", revision_id="handoff-policy@1", max_handoff_count=8,
            max_total_deferral_time=100, minimum_horizon_advance=10, minimum_debt_reduction_rate=1,
            mandatory_preparedness_floor_by_time=((0, 2),), bounded_stutter_allowance=1,
            recovery_stutter_allowance=1, absolute_latest_safe_refinement_time=100,
            temporal_authority_ref="temporal@1",
        )
        return HandoffLivenessEvaluator.evaluate(
            certificate_id="liveness", revision_id="liveness@1", source_continuation_ref="source",
            successor_continuation_ref="successor", old_rank=old, new_rank=new, progress_policy=policy,
            handoff_count=1, ordinary_stutter_count=1 if exhausted else 0, recovery_stutter_count=0,
            total_deferral_time=1, recursive_feasibility=True, information_available_by_deadline=True,
            recovery_mode=False, temporal_authority_revision_ref="temporal@1", current_time=20,
            debt_lineage_equivalent=True,
        )

    def _stability(self, *, current=True):
        contract = HandoffStabilityContract.create(
            contract_id="edge", revision_id="edge@1", policy_edge_ref="parent->child",
            protected_predicate_refs=("inventory",), protected_generation_bindings=(("inventory", 1),),
            lock_or_reservation_refs=(), stability_start=0, stability_end=100,
            external_writer_assumption_refs=(), refresh_required_predicate_refs=("inventory",),
            authorization_time_precondition_refs=("inventory",), invalidating_event_refs=(),
            open_side_effect_refs=(), fallback_on_instability="fallback@1", opacity_debt_refs=(),
            validity_regime="runtime@1",
        )
        assessment = HandoffStabilityEvaluator.assess(
            contract=contract, current_generations={"inventory": 1 if current else 2},
            refreshed_predicates=(), active_lock_or_reservation_refs=(), observed_invalidating_events=(),
            resolved_side_effect_refs=(), current_external_writer_assumption_refs=(), now=20,
        )
        return contract, assessment

    def _register_valid_bundle(self):
        resource = self._resource()
        job = self._job()
        sched = self._sched(jobs=(job,), resource=resource)
        coverage = self._coverage(strong=True)
        independence = self._independence(robust=True)
        liveness = self._liveness(exhausted=False)
        contract, activation = self._stability(current=True)
        self.kernel.register_control_plane_resource(resource)
        self.kernel.register_reaction_job(job)
        self.kernel.register_schedulability_certificate(sched)
        self.kernel.register_policy_coverage_assessment(coverage)
        self.kernel.register_option_independence_certificate(independence)
        self.kernel.register_handoff_liveness_certificate(liveness)
        self.kernel.register_handoff_stability_contract(contract)
        self.kernel.register_edge_activation_assessment(activation)
        return resource, job, sched, coverage, independence, liveness, contract, activation

    def _authorize(self, bundle, **changes):
        _, _, sched, coverage, independence, liveness, contract, activation = bundle
        args = dict(
            action_id="act", acting_principal_ref="agent:a", grant_ids=("grant",), now=20,
            proof_artifact_revision="proof@1", active_context={"prod"}, policy_node_revision="policy@1",
            selection_record_id="selection@1", sufficiency_revision="sufficiency@1",
            seal_revision="seal@1", executability_revision="exec@1",
            schedulability_revision=sched.revision_id, coverage_revision=coverage.revision_id,
            liveness_revision=liveness.revision_id, stability_contract_revision=contract.revision_id,
            edge_activation_digest=activation.canonical_digest,
            independence_revision=independence.revision_id,
            require_safe_handoff=True, require_closed_world=True, require_robust_redundancy=True,
        )
        args.update(changes)
        return self.kernel.authorize_schedulable_policy(**args)

    def test_runtime_uses_exact_kernel_writer_lock(self):
        self.assertIs(self.kernel.schedulability_writer_lock, self.kernel._writer_lock)

    def test_valid_path_preserves_existing_authority_bindings_and_adds_wave6_binding(self):
        bundle = self._register_valid_bundle()
        auth = self._authorize(bundle)
        self.assertIn(auth.id, self.kernel.authorization_identity_bindings)
        self.assertIn(auth.id, self.kernel.proof_authorization_bindings)
        self.assertIn(auth.id, self.kernel.policy_authorization_bindings)
        binding = self.kernel.schedulability_authorization_bindings[auth.id]
        self.assertEqual(binding["schedulability_revision"], bundle[2].revision_id)
        self.assertEqual(binding["coverage_revision"], bundle[3].revision_id)
        self.assertEqual(self.delegate_calls, 1)

    def test_rs1_cannot_authorize_when_concurrent_reactions_are_possible(self):
        resource = self._resource(capacity=1.0)
        jobs = (self._job("reaction-a"), self._job("reaction-b"))
        cert = self._sched(jobs=jobs, resource=resource)
        self.assertEqual(cert.level, ReactionSchedulabilityLevel.RS1_EACH_JOB_INDIVIDUALLY_FEASIBLE)
        self.kernel.register_control_plane_resource(resource)
        for job in jobs:
            self.kernel.register_reaction_job(job)
        self.kernel.register_schedulability_certificate(cert)
        self.kernel.register_policy_coverage_assessment(self._coverage())
        with self.assertRaises(AuthorizationError):
            self.kernel.authorize_schedulable_policy(
                action_id="act", acting_principal_ref="agent:a", grant_ids=("grant",), now=20,
                proof_artifact_revision="proof@1", active_context={"prod"}, policy_node_revision="policy@1",
                selection_record_id="selection@1", sufficiency_revision="sufficiency@1", seal_revision="seal@1",
                executability_revision="exec@1", schedulability_revision=cert.revision_id,
                coverage_revision="coverage@1",
            )
        self.assertEqual(self.delegate_calls, 0)

    def test_resource_revision_drift_blocks_before_delegate(self):
        bundle = self._register_valid_bundle()
        self.kernel.register_control_plane_resource(self._resource(revision_id="verifier@2", capacity=2.0))
        with self.assertRaises(AuthorizationError):
            self._authorize(bundle)
        self.assertEqual(self.delegate_calls, 0)

    def test_exhausted_handoff_liveness_blocks_safe_handoff_authority(self):
        bundle = list(self._register_valid_bundle())
        exhausted = self._liveness(exhausted=True)
        self.kernel.register_handoff_liveness_certificate(exhausted)
        bundle[5] = exhausted
        with self.assertRaises(AuthorizationError):
            self._authorize(tuple(bundle))
        self.assertEqual(self.delegate_calls, 0)

    def test_stale_edge_activation_blocks_child_authorization_until_refreshed(self):
        bundle = list(self._register_valid_bundle())
        contract, stale = self._stability(current=False)
        self.kernel.register_edge_activation_assessment(stale)
        bundle[6], bundle[7] = contract, stale
        with self.assertRaises(AuthorizationError):
            self._authorize(tuple(bundle), edge_activation_digest=stale.canonical_digest)
        self.assertEqual(self.delegate_calls, 0)

    def test_degraded_open_residual_cannot_be_laundered_into_closed_world_claim(self):
        bundle = list(self._register_valid_bundle())
        degraded = self._coverage(strong=False)
        self.kernel.register_policy_coverage_assessment(degraded)
        bundle[3] = degraded
        with self.assertRaises(AuthorizationError):
            self._authorize(tuple(bundle))
        self.assertEqual(self.delegate_calls, 0)

    def test_nominal_only_independence_blocks_robust_redundancy_claim(self):
        bundle = list(self._register_valid_bundle())
        nominal = self._independence(robust=False)
        self.kernel.register_option_independence_certificate(nominal)
        bundle[4] = nominal
        with self.assertRaises(AuthorizationError):
            self._authorize(tuple(bundle))
        self.assertEqual(self.delegate_calls, 0)

    def test_wave6_objects_do_not_mint_authority_or_dispatch(self):
        bundle = self._register_valid_bundle()
        for obj in bundle[2:]:
            self.assertFalse(hasattr(obj, "authorize"))
            self.assertFalse(hasattr(obj, "dispatch"))


if __name__ == "__main__":
    unittest.main()
