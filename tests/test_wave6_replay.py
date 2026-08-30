from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from nolane_plan import PlanKernel
from nolane_plan.control_plane import ControlPlaneResourceRevision, ReactionJobContract, ReactionResourceDemand
from nolane_plan.handoff_liveness import ContinuationProgressRank, HandoffLivenessEvaluator, HandoffProgressPolicy
from nolane_plan.handoff_stability import HandoffStabilityContract, HandoffStabilityEvaluator
from nolane_plan.hashing import digest
from nolane_plan.option_independence import OptionIndependenceCertificate, RobustPreparednessAssessment
from nolane_plan.persistence import SnapshotStore
from nolane_plan.policy_certificates import OutcomeSupport, PolicyTotalityCertificate, SuccessorHandler
from nolane_plan.policy_coverage import ExecutablePolicyCoverageAssessment
from nolane_plan.policy_readiness import PreparednessProfile, PreparednessStructure
from nolane_plan.policy_recovery import POLICY_SNAPSHOT_SCHEMA
from nolane_plan.schedulability import ReactionSchedulabilityEvaluator
from nolane_plan.schedulability_recovery import SCHEDULABILITY_SNAPSHOT_SCHEMA
from nolane_plan.types import AuthorizationError, ReplayError


_AXES = {
    "recognition": 4,
    "trigger": 4,
    "observation": 4,
    "recall": 4,
    "routing": 4,
    "action_contract": 4,
    "authority": 4,
    "resource": 4,
    "temporal_reaction": 4,
    "recovery": 4,
    "policy_coherence": 4,
    "proof_context": 4,
    "continuation": 4,
}


class Wave6ReplayTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.kernel = PlanKernel.create(self.root, "wave6 replay")

    def tearDown(self):
        self.tmp.cleanup()

    def _resource(self, revision_id="verifier@1", capacity=2.0):
        return ControlPlaneResourceRevision.create(
            resource_id="verifier", revision_id=revision_id, resource_kind="CONCURRENCY",
            capacity_units=capacity, concurrency_limit=int(capacity), service_rate_per_second=10,
            rate_window_seconds=1, availability_interval=(0, 100), priority_policy_ref="priority@1",
            reservation_policy_ref="reservation@1", regime_ref="runtime@1",
            assurance_profile="bounded-worst-case", opaque_dimensions=(), conservative_capacity_bound=None,
            validity_regime="runtime@1",
        )

    def _job(self):
        demand = ReactionResourceDemand.create(
            resource_ref="verifier", required_service=1, required_concurrency_units=1,
            release_offset_interval=(0, 0), demand_window=(0, 1), mandatory=True,
        )
        return ReactionJobContract.create(
            reaction_job_id="reaction-a", revision_id="reaction-a@1", policy_scope="action:act",
            mission_revision=str(self.kernel.mission.current.version), information_partition_revision="partition@1",
            reaction_envelope_ref="envelope@1", release_window=(0, 0), deadline=1,
            resource_demands=(demand,), coexistence_tags=("same-window",), correlation_refs=(),
            priority_class="critical", reservation_refs=(), risk_class="consequential",
            model_adequacy_debt_refs=(), validity_regime="runtime@1",
        )

    def _sched(self, resource, job):
        return ReactionSchedulabilityEvaluator.evaluate(
            certificate_id="sched", revision_id="sched@1", policy_scope="action:act",
            mission_revision=str(self.kernel.mission.current.version), information_partition_revision="partition@1",
            jobs=(job,), resources=(resource,), mutually_exclusive_pairs=(), coexistence_known=True,
            resource_reservation_refs=(), scheduling_model_id="bounded-window", scheduling_model_version="1",
            analysis_mode="EXACT_BOUNDED", worst_case_or_interval_assumptions=("bounded-service",),
            proof_or_solver_ref="evaluator@1", assurance_profile="bounded-worst-case",
            model_adequacy_debt_refs=(), validity_regime="runtime@1",
        )

    def _coverage(self):
        totality = PolicyTotalityCertificate.evaluate(
            certificate_id="totality", revision_id="totality@1", policy_revision="policy@1",
            action_node_revision="policy@1", outcomes=(OutcomeSupport("ok", "modeled", True, False),),
            handlers=(SuccessorHandler("ok", "done", "successor", False),), solver_status="PROVED",
            created_sequence=0, validity_regime="runtime@1",
        )
        return ExecutablePolicyCoverageAssessment.create(
            assessment_id="coverage", revision_id="coverage@1", policy_scope="action:act",
            policy_totality_certificate=totality, transition_observation_model_adequacy="STRONG",
            residual_open_world_status="CLOSED", residual_debt_refs=(), closed_domain_proof_ref="closed-domain@1",
            created_sequence=0, validity_regime="runtime@1",
        )

    def _independence(self):
        return OptionIndependenceCertificate.evaluate(
            certificate_id="independence", revision_id="independence@1", route_refs=("route-a", "route-b"),
            failure_uncertainty_set_ref="failure-set@1", shared_dependency_graph_ref="graph@1",
            route_dependency_refs={"route-a": ("provider:a",), "route-b": ("provider:b",)},
            resource_overlap_refs=(), observation_lineage_overlap_refs=(), control_plane_overlap_refs=(),
            common_mode_failure_refs=(), coactivation_feasible=True, assurance_profile="strong", analysis_supported=True,
        )

    def _robust_preparedness(self, independence):
        profiles = tuple(
            PreparednessProfile.create(
                preparedness_profile_id=f"prep-{suffix}", revision_id=f"prep-{suffix}@1",
                future_region_or_policy_scope=f"route-{suffix}", axes=_AXES, model_adequacy_cap=4,
                debt_refs=(), validity_regime="runtime@1",
            )
            for suffix in ("a", "b")
        )
        return RobustPreparednessAssessment.evaluate(
            profiles=profiles, structure=PreparednessStructure.OR, required_count=1,
            independence_certificate=independence,
        )

    def _liveness(self):
        old = ContinuationProgressRank.create(
            rank_id="old", revision_id="old@1", continuation_scope="boundary@1",
            mission_revision=str(self.kernel.mission.current.version), unresolved_critical_debt_count=2,
            remaining_unprepared_boundaries=1, absolute_executable_horizon=50,
            minimum_preparedness_at_next_boundary=3, remaining_synthesis_workload=5,
            reaction_refinement_slack=10, mission_distance_measure=5, semantic_continuation_digest="semantic@1",
            created_at=10,
        )
        new = ContinuationProgressRank.create(
            rank_id="new", revision_id="new@1", continuation_scope="boundary@1",
            mission_revision=str(self.kernel.mission.current.version), unresolved_critical_debt_count=1,
            remaining_unprepared_boundaries=1, absolute_executable_horizon=50,
            minimum_preparedness_at_next_boundary=3, remaining_synthesis_workload=5,
            reaction_refinement_slack=9, mission_distance_measure=5, semantic_continuation_digest="semantic@1",
            created_at=11,
        )
        policy = HandoffProgressPolicy.create(
            policy_id="progress", revision_id="progress@1", max_handoff_count=8, max_total_deferral_time=100,
            minimum_horizon_advance=10, minimum_debt_reduction_rate=1,
            mandatory_preparedness_floor_by_time=((0, 2),), bounded_stutter_allowance=1,
            recovery_stutter_allowance=1, absolute_latest_safe_refinement_time=100,
            temporal_authority_ref="temporal@1",
        )
        return HandoffLivenessEvaluator.evaluate(
            certificate_id="liveness", revision_id="liveness@1", source_continuation_ref="source",
            successor_continuation_ref="successor", old_rank=old, new_rank=new, progress_policy=policy,
            handoff_count=1, ordinary_stutter_count=0, recovery_stutter_count=0, total_deferral_time=1,
            recursive_feasibility=True, information_available_by_deadline=True, recovery_mode=False,
            temporal_authority_revision_ref="temporal@1", current_time=20, debt_lineage_equivalent=True,
        )

    def _stability(self, *, current=True):
        contract = HandoffStabilityContract.create(
            contract_id="edge", revision_id="edge@1", policy_edge_ref="parent->child",
            protected_predicate_refs=("inventory",), protected_generation_bindings=(("inventory", 1),),
            lock_or_reservation_refs=(), stability_start=0, stability_end=100,
            external_writer_assumption_refs=(), refresh_required_predicate_refs=("inventory",),
            authorization_time_precondition_refs=("inventory",), invalidating_event_refs=(), open_side_effect_refs=(),
            fallback_on_instability="fallback@1", opacity_debt_refs=(), validity_regime="runtime@1",
        )
        assessment = HandoffStabilityEvaluator.assess(
            contract=contract, current_generations={"inventory": 1 if current else 2}, refreshed_predicates=(),
            active_lock_or_reservation_refs=(), observed_invalidating_events=(), resolved_side_effect_refs=(),
            current_external_writer_assumption_refs=(), now=20,
        )
        return contract, assessment

    def _register_full_state(self, *, stale_activation=False):
        resource = self._resource()
        job = self._job()
        sched = self._sched(resource, job)
        coverage = self._coverage()
        independence = self._independence()
        robust = self._robust_preparedness(independence)
        liveness = self._liveness()
        contract, activation = self._stability(current=not stale_activation)
        self.kernel.register_control_plane_resource(resource)
        self.kernel.register_reaction_job(job)
        self.kernel.register_schedulability_certificate(sched)
        self.kernel.register_policy_coverage_assessment(coverage)
        self.kernel.register_option_independence_certificate(independence)
        self.kernel.register_robust_preparedness_assessment(robust)
        self.kernel.register_handoff_liveness_certificate(liveness)
        self.kernel.register_handoff_stability_contract(contract)
        self.kernel.register_edge_activation_assessment(activation)
        return resource, job, sched, coverage, independence, robust, liveness, contract, activation

    def test_v6_round_trip_preserves_all_wave6_registries_and_digests(self):
        values = self._register_full_state()
        state = self.kernel.save_snapshot_v6()
        self.assertEqual(state["snapshot_schema"], SCHEDULABILITY_SNAPSHOT_SCHEMA)
        reopened = PlanKernel.open(self.root)
        self.assertEqual(reopened.control_plane_resources["verifier"].canonical_digest, values[0].canonical_digest)
        self.assertEqual(reopened.reaction_jobs["reaction-a"].canonical_digest, values[1].canonical_digest)
        self.assertEqual(reopened.schedulability_certificates["sched@1"].canonical_digest, values[2].canonical_digest)
        self.assertEqual(reopened.policy_coverage_assessments["coverage@1"].canonical_digest, values[3].canonical_digest)
        self.assertEqual(reopened.option_independence_certificates["independence@1"].canonical_digest, values[4].canonical_digest)
        self.assertIn(values[5].canonical_digest, reopened.robust_preparedness_assessments)
        self.assertEqual(reopened.handoff_liveness_certificates["liveness@1"].canonical_digest, values[6].canonical_digest)
        self.assertEqual(reopened.handoff_stability_contracts["edge@1"].canonical_digest, values[7].canonical_digest)
        self.assertIn(values[8].canonical_digest, reopened.edge_activation_assessments)

    def test_v5_snapshot_migrates_to_empty_wave6_state_without_inventing_certificates(self):
        state = self.kernel.save_snapshot()
        state = dict(state)
        state["snapshot_schema"] = POLICY_SNAPSHOT_SCHEMA
        state.pop("schedulability", None)
        SnapshotStore(self.root / "snapshot.json").save(state)
        reopened = PlanKernel.open(self.root)
        self.assertEqual(reopened.schedulability_certificates, {})
        self.assertEqual(reopened.control_plane_resources, {})
        self.assertEqual(reopened.handoff_liveness_certificates, {})

    def test_current_resource_drift_does_not_resurrect_old_certificate_after_restart(self):
        _, _, sched, *_ = self._register_full_state()
        self.kernel.register_control_plane_resource(self._resource(revision_id="verifier@2", capacity=3))
        self.kernel.save_snapshot()
        reopened = PlanKernel.open(self.root)
        self.assertEqual(reopened.control_plane_resources["verifier"].revision_id, "verifier@2")
        with self.assertRaises(AuthorizationError):
            reopened._certificate_current_objects(sched)

    def test_stale_edge_activation_stays_stale_across_restart(self):
        values = self._register_full_state(stale_activation=True)
        self.kernel.save_snapshot()
        reopened = PlanKernel.open(self.root)
        activation = reopened.edge_activation_assessments[values[8].canonical_digest]
        self.assertFalse(activation.supports_activation)
        self.assertEqual(activation.status.value, "REFRESH_REQUIRED")

    def test_post_snapshot_wave6_registration_suffix_replays_exactly(self):
        self.kernel.save_snapshot()
        resource, job, sched, *_ = self._register_full_state()
        reopened = PlanKernel.open(self.root)
        self.assertEqual(reopened.control_plane_resources["verifier"].canonical_digest, resource.canonical_digest)
        self.assertEqual(reopened.reaction_jobs["reaction-a"].canonical_digest, job.canonical_digest)
        self.assertEqual(reopened.schedulability_certificates["sched@1"].canonical_digest, sched.canonical_digest)

    def test_tampered_internal_wave6_digest_fails_even_if_outer_snapshot_digest_is_recomputed(self):
        self._register_full_state()
        self.kernel.save_snapshot()
        raw_path = self.root / "snapshot.json"
        doc = json.loads(raw_path.read_text(encoding="utf-8"))
        doc["state"]["schedulability"]["resource_revisions"][0]["canonical_digest"] = "0" * 64
        doc["digest"] = digest(doc["state"])
        raw_path.write_text(json.dumps(doc, sort_keys=True), encoding="utf-8")
        with self.assertRaises(ReplayError):
            PlanKernel.open(self.root)

    def test_unknown_correctness_significant_wave6_suffix_event_fails_closed(self):
        self.kernel.save_snapshot()
        self.kernel._record("schedulability.unknown_correctness_event", {"ref": "x"})
        with self.assertRaises(ReplayError):
            PlanKernel.open(self.root)


if __name__ == "__main__":
    unittest.main()
