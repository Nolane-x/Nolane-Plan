from __future__ import annotations

from typing import Callable

from .budget import PlanningBudgetGovernor, PlanningWorkUnit, ProtectedBudgetDemand
from .control_plane import ControlPlaneResourceRevision, ReactionJobContract, ReactionResourceDemand
from .handoff_liveness import (
    ContinuationProgressRank,
    HandoffLivenessEvaluator,
    HandoffProgressPolicy,
    HandoffProgressStatus,
)
from .handoff_stability import EdgeActivationStatus, HandoffStabilityContract, HandoffStabilityEvaluator
from .option_independence import (
    OptionIndependenceCertificate,
    OptionIndependenceStatus,
    RobustPreparednessAssessment,
)
from .policy_certificates import OutcomeSupport, PolicyTotalityCertificate, SuccessorHandler, TotalityMode
from .policy_coverage import ExecutablePolicyCoverageAssessment, ModelAdequacyLevel, ResidualOpenWorldStatus
from .policy_readiness import DecisionReactionEnvelope, PreparednessProfile, PreparednessStructure, ReactionControllabilityClass
from .schedulability import ReactionSchedulabilityEvaluator, ReactionSchedulabilityLevel, SchedulabilityAnalysisMode
from .types import InvariantViolation


def _raises(exc_type, fn: Callable[[], object]) -> bool:
    try:
        fn()
    except exc_type:
        return True
    return False


def _resource(**overrides) -> ControlPlaneResourceRevision:
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


def _job(job_id: str, **overrides) -> ReactionJobContract:
    demand = ReactionResourceDemand.create(
        resource_ref=overrides.pop("resource_ref", "verifier"),
        required_service=overrides.pop("required_service", 1.0),
        required_concurrency_units=overrides.pop("required_concurrency_units", 1),
        release_offset_interval=overrides.pop("release_offset_interval", (0.0, 0.0)),
        demand_window=overrides.pop("demand_window", (0.0, 1.0)),
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
    ) | overrides
    return ReactionJobContract.create(**kwargs)


def _sched(
    *,
    jobs,
    resources=None,
    mutually_exclusive_pairs=(),
    coexistence_known=True,
    mode=SchedulabilityAnalysisMode.EXACT_BOUNDED,
    closed_subdomain_proof_ref=None,
):
    return ReactionSchedulabilityEvaluator.evaluate(
        certificate_id="sched-1",
        revision_id="sched-r1",
        policy_scope="policy-1",
        mission_revision="mission-1",
        information_partition_revision="partition-1",
        jobs=tuple(jobs),
        resources=tuple(resources or (_resource(),)),
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


def _rank(**overrides) -> ContinuationProgressRank:
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
        debt_equivalence_refs=("debt-a", "debt-b", "debt-c"),
        created_at=0.0,
    )
    kwargs.update(overrides)
    return ContinuationProgressRank.create(**kwargs)


def _progress_policy(**overrides) -> HandoffProgressPolicy:
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


def _live(old=None, new=None, **overrides):
    kwargs = dict(
        certificate_id="live-1",
        revision_id="live-r1",
        source_continuation_ref="cont-a",
        successor_continuation_ref="cont-b",
        old_rank=old or _rank(),
        new_rank=new or _rank(rank_id="rank-b", revision_id="rank-b-r1", created_at=2.0),
        progress_policy=_progress_policy(),
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


def _stability_contract(**overrides) -> HandoffStabilityContract:
    kwargs = dict(
        contract_id="stability-1",
        revision_id="stability-r1",
        policy_edge_ref="edge-a-b",
        protected_predicate_refs=("inventory-ok", "permission-ok"),
        protected_generation_bindings=(("inventory", 7), ("permission", 3)),
        lock_or_reservation_refs=("inventory-lock-r1",),
        stability_start=10.0,
        stability_end=30.0,
        external_writer_assumption_refs=("writer-set-r1",),
        refresh_required_predicate_refs=("inventory-ok", "permission-ok"),
        authorization_time_precondition_refs=("inventory-ok", "permission-ok"),
        invalidating_event_refs=("inventory.external_write", "permission.revoked"),
        open_side_effect_refs=(),
        fallback_on_instability="replan-edge",
        opacity_debt_refs=(),
        validity_regime="mission-1",
    )
    kwargs.update(overrides)
    return HandoffStabilityContract.create(**kwargs)


def _edge(contract=None, **overrides):
    kwargs = dict(
        contract=contract or _stability_contract(),
        current_generations={"inventory": 7, "permission": 3},
        refreshed_predicates=(),
        active_lock_or_reservation_refs=("inventory-lock-r1",),
        observed_invalidating_events=(),
        resolved_side_effect_refs=(),
        current_external_writer_assumption_refs=("writer-set-r1",),
        now=20.0,
    )
    kwargs.update(overrides)
    return HandoffStabilityEvaluator.assess(**kwargs)


def _reaction(*, slow_model=(1, 8), slow_authorize=(1, 4)) -> DecisionReactionEnvelope:
    return DecisionReactionEnvelope.create(
        reaction_envelope_id="reaction@1",
        revision_id="reaction@1",
        policy_node_or_reveal_ref="reveal@1",
        reveal_time_interval=(10, 12),
        ingestion_latency_interval=(1, 2),
        canonical_commit_latency_interval=(1, 2),
        relocation_latency_interval=(0, 1),
        capsule_compile_latency_interval=(1, 2),
        model_or_solver_latency_interval=slow_model,
        verification_latency_interval=(1, 2),
        authorization_latency_interval=slow_authorize,
        dispatch_latency_interval=(1, 2),
        external_effect_start_latency_interval=(0, 2),
        latest_safe_authorization_time=25,
        latest_safe_dispatch_time=28,
        latest_safe_effect_time=30,
        cancellation_or_preemption_window=(20, 29),
        clock_regime_refs=("clock@1", "latency-regime@1"),
        model_adequacy_debt_refs=(),
    )


def _totality(*, include_timeout=False) -> PolicyTotalityCertificate:
    outcomes = [OutcomeSupport("SUCCESS", "modeled", True, False)]
    handlers = [SuccessorHandler("SUCCESS", "next", "successor", False)]
    if include_timeout:
        outcomes.append(OutcomeSupport("TIMEOUT", "modeled", True, False))
    return PolicyTotalityCertificate.evaluate(
        certificate_id="totality-1",
        revision_id="totality-r1",
        policy_revision="policy-r1",
        action_node_revision="node-r1",
        outcomes=tuple(outcomes),
        handlers=tuple(handlers),
        solver_status="PROVED",
        created_sequence=1,
        validity_regime="mission-1",
    )


def _coverage(
    *,
    scope="policy-r1",
    totality=None,
    adequacy=ModelAdequacyLevel.STRONG,
    residual=ResidualOpenWorldStatus.CLOSED,
    debt=(),
    closed_proof="closed-domain-proof-1",
):
    return ExecutablePolicyCoverageAssessment.create(
        assessment_id="coverage-1",
        revision_id="coverage-r1",
        policy_scope=scope,
        policy_totality_certificate=totality or _totality(),
        transition_observation_model_adequacy=adequacy,
        residual_open_world_status=residual,
        residual_debt_refs=tuple(debt),
        closed_domain_proof_ref=closed_proof,
        created_sequence=2,
        validity_regime="mission-1",
    )


def _independence(
    *,
    route_dependencies=None,
    resource_overlap=(),
    observation_overlap=(),
    control_overlap=(),
    common_modes=(),
    coactivation=True,
    assurance="strong",
    supported=True,
    failure_set="provider-loss",
):
    return OptionIndependenceCertificate.evaluate(
        certificate_id="ind-1",
        revision_id="ind-r1",
        route_refs=("route-a", "route-b"),
        failure_uncertainty_set_ref=failure_set,
        shared_dependency_graph_ref="deps-r1",
        route_dependency_refs=route_dependencies
        or {"route-a": ("credential:a", "provider:a"), "route-b": ("credential:b", "provider:b")},
        resource_overlap_refs=tuple(resource_overlap),
        observation_lineage_overlap_refs=tuple(observation_overlap),
        control_plane_overlap_refs=tuple(control_overlap),
        common_mode_failure_refs=tuple(common_modes),
        coactivation_feasible=coactivation,
        assurance_profile=assurance,
        analysis_supported=supported,
    )


def _profile(ref: str, level: int) -> PreparednessProfile:
    axes = {name: level for name in (
        "recognition", "trigger", "observation", "recall", "routing", "action_contract", "authority",
        "resource", "temporal_reaction", "recovery", "policy_coherence", "proof_context", "continuation",
    )}
    return PreparednessProfile.create(
        preparedness_profile_id=ref,
        revision_id=f"{ref}-r1",
        future_region_or_policy_scope="policy-1",
        axes=axes,
        model_adequacy_cap=level,
        debt_refs=(),
        validity_regime="mission-1",
    )


# Control-plane schedulability failures -------------------------------------------------

def _cp01():
    cert = _sched(jobs=(_job("a"), _job("b")))
    return cert.level == ReactionSchedulabilityLevel.RS1_EACH_JOB_INDIVIDUALLY_FEASIBLE and bool(cert.overload_witnesses)


def _cp02():
    verifier = _resource(resource_id="proof-verifier", resource_kind="CONCURRENCY", capacity_units=1, concurrency_limit=1)
    return verifier.supports_strong_bound and verifier.available_service(0, 1) == 1.0 and verifier.concurrency_limit == 1


def _cp03():
    resource = _resource(capacity_units=4, concurrency_limit=4, service_rate_per_second=4)
    job = _job("a")
    cert = _sched(jobs=(job,), resources=(resource,))
    changed = _resource(revision_id="verifier-r2", regime_ref="regime-v2", capacity_units=4, concurrency_limit=4, service_rate_per_second=4)
    return cert.is_current(jobs=(job,), resources=(resource,)) and not cert.is_current(jobs=(job,), resources=(changed,))


def _cp04():
    allocation = PlanningBudgetGovernor(10).allocate(
        [PlanningWorkUnit("mandatory", "core", 3, 100, True), PlanningWorkUnit("background", "search", 4, 1000)],
        protected_demands=(ProtectedBudgetDemand("reaction", 4, 0, 10, 10, "reserve", True),),
        now=1,
    )
    return allocation.selected_ids == ("mandatory",) and allocation.protected == 4


def _cp05():
    cert = _sched(jobs=(_job("a"), _job("b")), mutually_exclusive_pairs=(("a", "b"),))
    return cert.level == ReactionSchedulabilityLevel.RS2_DECLARED_COHORT_FEASIBLE and not cert.overload_witnesses


def _cp06():
    cert = _sched(
        jobs=(_job("a"), _job("b")),
        mutually_exclusive_pairs=(("a", "b"),),
        coexistence_known=False,
    )
    return cert.level == ReactionSchedulabilityLevel.RS1_EACH_JOB_INDIVIDUALLY_FEASIBLE and bool(cert.model_adequacy_debt_refs)


def _cp07():
    human = _resource(resource_id="human-approval", resource_kind="AUTHORITY_HUMAN")
    a = _job("a", resource_ref="human-approval")
    b = _job("b", resource_ref="human-approval")
    cert = _sched(jobs=(a, b), resources=(human,))
    return cert.level == ReactionSchedulabilityLevel.RS1_EACH_JOB_INDIVIDUALLY_FEASIBLE and cert.overload_witnesses[0].resource_ref == "human-approval"


def _cp08():
    writer = _resource(resource_id="kernel-writer", resource_kind="KERNEL_WRITER")
    cert = _sched(
        jobs=(_job("a", resource_ref="kernel-writer"), _job("b", resource_ref="kernel-writer")),
        resources=(writer,),
    )
    return cert.level == ReactionSchedulabilityLevel.RS1_EACH_JOB_INDIVIDUALLY_FEASIBLE and cert.overload_witnesses[0].resource_ref == "kernel-writer"


def _cp09():
    workers = _resource(resource_id="worker-pool", resource_kind="CONCURRENCY")
    normal = _job("normal", resource_ref="worker-pool")
    recovery = _job("recovery", resource_ref="worker-pool", priority_class="recovery-critical")
    cert = _sched(jobs=(normal, recovery), resources=(workers,))
    return cert.level == ReactionSchedulabilityLevel.RS1_EACH_JOB_INDIVIDUALLY_FEASIBLE and set(cert.overload_witnesses[0].job_refs) == {"normal", "recovery"}


def _cp10():
    opaque = _resource(opaque_dimensions=("burst-latency",), conservative_capacity_bound=None)
    stress = _sched(jobs=(_job("a"),), mode=SchedulabilityAnalysisMode.SCENARIO_STRESS)
    return not opaque.supports_strong_bound and not stress.supports_strong_joint_guarantee


def _cp11():
    return _raises(
        InvariantViolation,
        lambda: PlanningBudgetGovernor(5).allocate(
            [],
            protected_demands=(
                ProtectedBudgetDemand("route-a", 3, 0, 10, 10, "reserve-a", True),
                ProtectedBudgetDemand("route-b", 3, 0, 10, 10, "reserve-b", True),
            ),
            now=1,
        ),
    )


def _cp12():
    cert = _sched(jobs=(_job("a"),), mode=SchedulabilityAnalysisMode.UNSUPPORTED)
    return cert.level == ReactionSchedulabilityLevel.RS0_UNANALYZED and bool(cert.model_adequacy_debt_refs)


# Handoff/liveness failures -------------------------------------------------------------

def _hl01():
    cert = _live(ordinary_stutter_count=2)
    return cert.status == HandoffProgressStatus.NO_PROGRESS and not cert.supports_safe_handoff


def _hl02():
    old = _progress_policy(absolute_latest_safe_refinement_time=50)
    rewritten = _progress_policy(revision_id="handoff-policy-r2", absolute_latest_safe_refinement_time=70)
    return not HandoffLivenessEvaluator.deadline_revision_is_grounded(
        old_policy=old, new_policy=rewritten, temporal_authority_revision_ref="temporal-authority-r1"
    )


def _hl03():
    old = _rank(unresolved_critical_debt_count=2, remaining_synthesis_workload=5, absolute_executable_horizon=100)
    new = _rank(
        rank_id="rank-b", revision_id="rank-b-r1", unresolved_critical_debt_count=3,
        remaining_synthesis_workload=20, absolute_executable_horizon=106,
        semantic_continuation_digest="semantic-b", created_at=2,
    )
    cert = _live(old, new, ordinary_stutter_count=2)
    return (
        cert.status == HandoffProgressStatus.NO_PROGRESS
        and "progress_rank_regression" in cert.blocker_refs
        and "absolute_executable_horizon_advanced" not in cert.progress_dimensions
    )


def _hl04():
    cert = _live(progress_policy=_progress_policy(bounded_stutter_allowance=0), ordinary_stutter_count=0)
    return cert.status == HandoffProgressStatus.NO_PROGRESS and "ordinary_stutter_budget_exhausted" in cert.blocker_refs


def _hl05():
    cert = _live(recovery_mode=True, recovery_stutter_count=0)
    return cert.status == HandoffProgressStatus.RECOVERY_STUTTER and "STRICT_PROGRESS" != cert.status.value


def _hl06():
    old = _rank(semantic_continuation_digest="same")
    new = _rank(rank_id="renamed", revision_id="renamed-r1", semantic_continuation_digest="same", created_at=2)
    cert = _live(old, new, ordinary_stutter_count=1)
    return cert.status == HandoffProgressStatus.BOUNDED_STUTTER and not cert.progress_dimensions


def _hl07():
    old = _rank(absolute_executable_horizon=100)
    new = _rank(rank_id="rank-b", revision_id="rank-b-r1", absolute_executable_horizon=90, created_at=2)
    cert = _live(old, new)
    return cert.status != HandoffProgressStatus.STRICT_PROGRESS and "absolute_executable_horizon_advanced" not in cert.progress_dimensions


def _hl08():
    cert = _live(recursive_feasibility=False)
    return cert.status == HandoffProgressStatus.UNKNOWN and "recursive_feasibility_not_proven" in cert.blocker_refs


def _hl09():
    old = _rank(unresolved_critical_debt_count=3)
    new = _rank(rank_id="rank-b", revision_id="rank-b-r1", unresolved_critical_debt_count=2, created_at=2)
    cert = _live(old, new, debt_lineage_equivalent=False)
    return cert.status == HandoffProgressStatus.BOUNDED_STUTTER and "critical_debt_reduced" not in cert.progress_dimensions


def _hl10():
    cert = _live(total_deferral_time=31)
    return cert.status == HandoffProgressStatus.NO_PROGRESS and "total_deferral_budget_exhausted" in cert.blocker_refs


def _hl11():
    cert = _live(information_available_by_deadline=False)
    return cert.status == HandoffProgressStatus.UNKNOWN and "information_not_available_by_deadline" in cert.blocker_refs


def _hl12():
    cert = _live(handoff_count=9)
    return cert.status == HandoffProgressStatus.NO_PROGRESS and "handoff_budget_exhausted" in cert.blocker_refs


# Edge freshness failures ---------------------------------------------------------------

def _ef01():
    result = _edge(current_generations={"inventory": 8, "permission": 3})
    return result.status == EdgeActivationStatus.REFRESH_REQUIRED and "inventory-ok" in result.required_refresh_predicates


def _ef02():
    result = _edge(active_lock_or_reservation_refs=())
    return result.status == EdgeActivationStatus.REFRESH_REQUIRED and "lock_or_reservation_not_current" in result.blocker_refs


def _ef03():
    result = _edge(current_external_writer_assumption_refs=("writer-set-r2",))
    return result.status == EdgeActivationStatus.REFRESH_REQUIRED and "external_writer_assumption_drift" in result.blocker_refs


def _ef04():
    result = _edge(current_generations={"inventory": 7, "permission": 4})
    return result.status == EdgeActivationStatus.REFRESH_REQUIRED and "permission-ok" in result.required_refresh_predicates


def _ef05():
    contract = _stability_contract(open_side_effect_refs=("dispatch-x",))
    blocked = _edge(contract=contract)
    resolved = _edge(contract=contract, resolved_side_effect_refs=("dispatch-x",))
    return blocked.status == EdgeActivationStatus.REFRESH_REQUIRED and resolved.status == EdgeActivationStatus.STABLE


def _ef06():
    result = _edge(contract=_stability_contract(opacity_debt_refs=("adapter-atomicity-opaque",)))
    return result.status == EdgeActivationStatus.UNKNOWN and not result.supports_activation


def _ef07():
    bound = _stability_contract(lock_or_reservation_refs=("shared-lock-r1",))
    changed = _stability_contract(revision_id="stability-r2", lock_or_reservation_refs=("shared-lock-r2",))
    blocked = _edge(contract=bound, active_lock_or_reservation_refs=())
    return bound.canonical_digest != changed.canonical_digest and blocked.status == EdgeActivationStatus.REFRESH_REQUIRED


def _ef08():
    envelope = _reaction(slow_model=(1, 8), slow_authorize=(1, 4))
    return envelope.controllability_class == ReactionControllabilityClass.IA1_POSSIBLE_TIMELY and not envelope.supports_strong_route_guarantee


# Model-totality reporting failures -----------------------------------------------------

def _tm01():
    assessment = _coverage(
        adequacy=ModelAdequacyLevel.DEGRADED,
        residual=ResidualOpenWorldStatus.ACTIVE,
        debt=("unmodeled-timeout",),
        closed_proof=None,
    )
    return assessment.modeled_total and not assessment.open_world_complete and bool(assessment.qualifier_refs)


def _tm02():
    assessment = _coverage(
        adequacy=ModelAdequacyLevel.DEGRADED,
        residual=ResidualOpenWorldStatus.ACTIVE,
        debt=("transition-debt",),
        closed_proof=None,
    )
    return "transition-debt" in assessment.residual_debt_refs and not assessment.open_world_complete


def _tm03():
    return _raises(
        ValueError,
        lambda: _coverage(
            adequacy=ModelAdequacyLevel.DEGRADED,
            residual=ResidualOpenWorldStatus.ACTIVE,
            debt=(),
            closed_proof=None,
        ),
    )


def _tm04():
    before = _totality(include_timeout=False)
    after = _totality(include_timeout=True)
    return before.mode == TotalityMode.TOTAL and after.mode != TotalityMode.TOTAL and before.canonical_digest != after.canonical_digest


def _tm05():
    a = _coverage(scope="policy-scope-a")
    b = _coverage(scope="policy-scope-b")
    return a.policy_scope != b.policy_scope and a.canonical_digest != b.canonical_digest


# Option-independence failures ----------------------------------------------------------

def _oi01():
    cert = _independence(
        route_dependencies={
            "route-a": ("credential:prod", "provider:a"),
            "route-b": ("credential:prod", "provider:b"),
        },
        common_modes=("credential:prod",),
        failure_set="credential-loss",
    )
    return cert.status == OptionIndependenceStatus.NOMINAL_ONLY and not cert.supports_robust_uplift


def _oi02():
    cert = _independence(
        route_dependencies={"route-a": ("network:path-1", "provider:a"), "route-b": ("network:path-1", "provider:b")},
        common_modes=("network:path-1",),
        failure_set="network-loss",
    )
    return cert.status == OptionIndependenceStatus.NOMINAL_ONLY and "network:path-1" in cert.shared_dependency_refs


def _oi03():
    cert = _independence(observation_overlap=("source:stale-cache",), failure_set="observation-corruption")
    return cert.status == OptionIndependenceStatus.NOMINAL_ONLY and any("observation-lineage-overlap" in ref for ref in cert.blocker_refs)


def _oi04():
    cert = _independence(coactivation=False, failure_set="shared-capacity")
    return cert.status == OptionIndependenceStatus.NOMINAL_ONLY and "coactivation-infeasible" in cert.blocker_refs


def _oi05():
    before = _independence(failure_set="provider-loss")
    after = _independence(common_modes=("newly-discovered-common-cause",), failure_set="provider-loss")
    return (
        before.status == OptionIndependenceStatus.ROBUST_INDEPENDENT
        and after.status == OptionIndependenceStatus.NOMINAL_ONLY
        and before.canonical_digest != after.canonical_digest
    )


def _oi06():
    cert = _independence(
        route_dependencies={
            "route-a": ("credential:prod", "provider:a"),
            "route-b": ("credential:prod", "provider:b"),
        },
        common_modes=("credential:prod",),
    )
    result = RobustPreparednessAssessment.evaluate(
        profiles=(_profile("route-a", 5), _profile("route-b", 2)),
        structure=PreparednessStructure.OR,
        required_count=1,
        independence_certificate=cert,
    )
    return (
        result.nominal_alternative_preparedness == 5
        and result.robust_independent_preparedness == 2
        and not result.robust_uplift_applied
    )


WAVE6_CASES: tuple[tuple[str, str, Callable[[], bool]], ...] = (
    ("CP01", "local_reaction_pass_does_not_imply_joint_capacity", _cp01),
    ("CP02", "verifier_is_explicit_finite_control_resource", _cp02),
    ("CP03", "resource_regime_revision_invalidates_certificate", _cp03),
    ("CP04", "background_work_cannot_spend_protected_reaction_capacity", _cp04),
    ("CP05", "mutually_exclusive_jobs_are_not_overreserved", _cp05),
    ("CP06", "unknown_coexistence_is_not_optimistic_exclusivity", _cp06),
    ("CP07", "human_approval_capacity_participates_in_deadline_feasibility", _cp07),
    ("CP08", "kernel_writer_is_modeled_as_serial_bottleneck", _cp08),
    ("CP09", "recovery_and_normal_reactions_share_real_worker_capacity", _cp09),
    ("CP10", "opaque_or_scenario_capacity_cannot_claim_worst_case_guarantee", _cp10),
    ("CP11", "cross_future_protections_fail_on_oversubscription", _cp11),
    ("CP12", "unsupported_scheduler_result_is_explicitly_unanalyzed", _cp12),
    ("HL01", "repeated_handoff_without_progress_exhausts_stutter_budget", _hl01),
    ("HL02", "plan_revision_cannot_self_extend_refinement_deadline", _hl02),
    ("HL03", "horizon_advance_cannot_launder_rank_regression", _hl03),
    ("HL04", "handoff_stutter_policy_has_a_hard_bound", _hl04),
    ("HL05", "recovery_stutter_is_not_reported_as_strategic_progress", _hl05),
    ("HL06", "semantic_rephrasing_is_bounded_stutter_not_progress", _hl06),
    ("HL07", "shrinking_absolute_horizon_never_counts_as_progress", _hl07),
    ("HL08", "safe_handoff_requires_recursive_feasibility", _hl08),
    ("HL09", "equivalent_or_unproven_debt_lineage_cannot_fake_reduction", _hl09),
    ("HL10", "endless_deferral_hits_temporal_liveness_bound", _hl10),
    ("HL11", "post_deadline_information_makes_handoff_unknown", _hl11),
    ("HL12", "handoff_chain_has_a_hard_planning_budget", _hl12),
    ("EF01", "external_generation_drift_requires_child_entry_refresh", _ef01),
    ("EF02", "expired_or_missing_reservation_requires_refresh", _ef02),
    ("EF03", "external_writer_assumption_drift_requires_refresh", _ef03),
    ("EF04", "permission_drift_cannot_be_waived_by_old_edge", _ef04),
    ("EF05", "open_parent_side_effect_blocks_child_activation", _ef05),
    ("EF06", "atomicity_opacity_is_unknown_not_stable", _ef06),
    ("EF07", "edge_lock_identity_is_explicit_shared_resource_lineage", _ef07),
    ("EF08", "refresh_pipeline_must_fit_child_reaction_window", _ef08),
    ("TM01", "modeled_totality_is_not_rendered_as_real_world_totality", _tm01),
    ("TM02", "transition_debt_caps_open_world_adequacy", _tm02),
    ("TM03", "active_residual_cannot_disappear_during_normalization", _tm03),
    ("TM04", "new_timeout_outcome_invalidates_old_totality_identity", _tm04),
    ("TM05", "adequacy_metric_is_policy_scope_bound", _tm05),
    ("OI01", "shared_credential_collapses_redundancy", _oi01),
    ("OI02", "shared_network_path_is_common_mode_dependency", _oi02),
    ("OI03", "copied_observation_lineage_is_not_independent", _oi03),
    ("OI04", "k_of_n_requires_coactivation_feasibility", _oi04),
    ("OI05", "new_common_cause_invalidates_robust_independence", _oi05),
    ("OI06", "nominal_and_robust_preparedness_are_reported_separately", _oi06),
)


def run_wave6_conformance() -> dict:
    rows = []
    for case_id, name, fn in WAVE6_CASES:
        try:
            passed = bool(fn())
            detail = "defense held" if passed else "unsafe shortcut was not rejected"
        except Exception as exc:
            passed = False
            detail = f"unexpected {type(exc).__name__}: {exc}"
        rows.append({"id": case_id, "name": name, "passed": passed, "detail": detail})
    passed = sum(1 for row in rows if row["passed"])
    return {"cases": rows, "total": len(rows), "passed": passed, "failed": len(rows) - passed}


def main() -> int:
    result = run_wave6_conformance()
    for row in result["cases"]:
        print(f"{'PASS' if row['passed'] else 'FAIL'} {row['id']} {row['name']}: {row['detail']}")
    print(f"WAVE6_CONFORMANCE={result['passed']}/{result['total']}")
    return 0 if result["passed"] == result["total"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
