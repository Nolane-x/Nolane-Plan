from __future__ import annotations

from typing import Any

from .control_plane import ControlPlaneResourceRevision, ReactionJobContract, ReactionResourceDemand
from .handoff_liveness import HandoffLivenessCertificate, HandoffProgressStatus
from .handoff_stability import EdgeActivationAssessment, EdgeActivationStatus, HandoffStabilityContract
from .hashing import digest
from .option_independence import OptionIndependenceCertificate, OptionIndependenceStatus, RobustPreparednessAssessment
from .policy_certificates import TotalityMode
from .policy_coverage import ExecutablePolicyCoverageAssessment, ModelAdequacyLevel, ResidualOpenWorldStatus
from .policy_readiness import PreparednessStructure
from .schedulability import (
    OverloadWitness,
    ReactionSchedulabilityCertificate,
    ReactionSchedulabilityLevel,
    SchedulabilityAnalysisMode,
)
from .types import ReplayError


def _tuple_rows(value):
    return tuple(tuple(item) if isinstance(item, (list, tuple)) else item for item in value)


def _check(expected: str, actual: str, what: str) -> None:
    if str(expected) != str(actual):
        raise ReplayError(f"{what} canonical digest mismatch")


def resource_doc(value: ControlPlaneResourceRevision) -> dict[str, Any]:
    return {
        "resource_id": value.resource_id,
        "revision_id": value.revision_id,
        "resource_kind": value.resource_kind.value,
        "capacity_units": value.capacity_units,
        "concurrency_limit": value.concurrency_limit,
        "service_rate_per_second": value.service_rate_per_second,
        "rate_window_seconds": value.rate_window_seconds,
        "availability_interval": value.availability_interval,
        "priority_policy_ref": value.priority_policy_ref,
        "reservation_policy_ref": value.reservation_policy_ref,
        "regime_ref": value.regime_ref,
        "assurance_profile": value.assurance_profile,
        "opaque_dimensions": value.opaque_dimensions,
        "conservative_capacity_bound": value.conservative_capacity_bound,
        "validity_regime": value.validity_regime,
        "canonical_digest": value.canonical_digest,
    }


def resource_from_doc(row: dict[str, Any]) -> ControlPlaneResourceRevision:
    value = ControlPlaneResourceRevision.create(
        resource_id=row["resource_id"], revision_id=row["revision_id"], resource_kind=row["resource_kind"],
        capacity_units=row["capacity_units"], concurrency_limit=row["concurrency_limit"],
        service_rate_per_second=row["service_rate_per_second"], rate_window_seconds=row["rate_window_seconds"],
        availability_interval=row["availability_interval"], priority_policy_ref=row["priority_policy_ref"],
        reservation_policy_ref=row["reservation_policy_ref"], regime_ref=row["regime_ref"],
        assurance_profile=row["assurance_profile"], opaque_dimensions=row.get("opaque_dimensions", ()),
        conservative_capacity_bound=row.get("conservative_capacity_bound"), validity_regime=row["validity_regime"],
    )
    _check(row["canonical_digest"], value.canonical_digest, "control-plane resource")
    return value


def demand_doc(value: ReactionResourceDemand) -> dict[str, Any]:
    return {
        "resource_ref": value.resource_ref,
        "required_service": value.required_service,
        "required_concurrency_units": value.required_concurrency_units,
        "release_offset_interval": value.release_offset_interval,
        "demand_window": value.demand_window,
        "mandatory": value.mandatory,
        "canonical_digest": value.canonical_digest,
    }


def demand_from_doc(row: dict[str, Any]) -> ReactionResourceDemand:
    value = ReactionResourceDemand.create(
        resource_ref=row["resource_ref"], required_service=row["required_service"],
        required_concurrency_units=row["required_concurrency_units"], release_offset_interval=row["release_offset_interval"],
        demand_window=row["demand_window"], mandatory=row["mandatory"],
    )
    _check(row["canonical_digest"], value.canonical_digest, "reaction resource demand")
    return value


def job_doc(value: ReactionJobContract) -> dict[str, Any]:
    return {
        "reaction_job_id": value.reaction_job_id,
        "revision_id": value.revision_id,
        "policy_scope": value.policy_scope,
        "mission_revision": value.mission_revision,
        "information_partition_revision": value.information_partition_revision,
        "reaction_envelope_ref": value.reaction_envelope_ref,
        "release_window": value.release_window,
        "deadline": value.deadline,
        "resource_demands": [demand_doc(item) for item in value.resource_demands],
        "coexistence_tags": value.coexistence_tags,
        "correlation_refs": value.correlation_refs,
        "priority_class": value.priority_class,
        "reservation_refs": value.reservation_refs,
        "risk_class": value.risk_class,
        "model_adequacy_debt_refs": value.model_adequacy_debt_refs,
        "validity_regime": value.validity_regime,
        "canonical_digest": value.canonical_digest,
    }


def job_from_doc(row: dict[str, Any]) -> ReactionJobContract:
    value = ReactionJobContract.create(
        reaction_job_id=row["reaction_job_id"], revision_id=row["revision_id"], policy_scope=row["policy_scope"],
        mission_revision=row["mission_revision"], information_partition_revision=row["information_partition_revision"],
        reaction_envelope_ref=row["reaction_envelope_ref"], release_window=row["release_window"], deadline=row["deadline"],
        resource_demands=tuple(demand_from_doc(dict(item)) for item in row.get("resource_demands", ())),
        coexistence_tags=row.get("coexistence_tags", ()), correlation_refs=row.get("correlation_refs", ()),
        priority_class=row["priority_class"], reservation_refs=row.get("reservation_refs", ()), risk_class=row["risk_class"],
        model_adequacy_debt_refs=row.get("model_adequacy_debt_refs", ()), validity_regime=row["validity_regime"],
    )
    _check(row["canonical_digest"], value.canonical_digest, "reaction job")
    return value


def schedulability_doc(value: ReactionSchedulabilityCertificate) -> dict[str, Any]:
    return {
        "certificate_id": value.certificate_id,
        "revision_id": value.revision_id,
        "policy_scope": value.policy_scope,
        "mission_revision": value.mission_revision,
        "information_partition_revision": value.information_partition_revision,
        "reaction_job_digests": value.reaction_job_digests,
        "control_resource_digests": value.control_resource_digests,
        "coexistence_constraint_refs": value.coexistence_constraint_refs,
        "resource_reservation_refs": value.resource_reservation_refs,
        "scheduling_model_id": value.scheduling_model_id,
        "scheduling_model_version": value.scheduling_model_version,
        "analysis_mode": value.analysis_mode.value,
        "worst_case_or_interval_assumptions": value.worst_case_or_interval_assumptions,
        "proof_or_solver_ref": value.proof_or_solver_ref,
        "overload_witnesses": [
            {
                "resource_ref": item.resource_ref, "window_start": item.window_start, "window_end": item.window_end,
                "available_service": item.available_service, "required_service": item.required_service,
                "available_concurrency_units": item.available_concurrency_units,
                "required_concurrency_units": item.required_concurrency_units,
                "job_refs": item.job_refs, "reason": item.reason,
            }
            for item in value.overload_witnesses
        ],
        "assurance_profile": value.assurance_profile,
        "model_adequacy_debt_refs": value.model_adequacy_debt_refs,
        "validity_regime": value.validity_regime,
        "level": value.level.value,
        "closed_subdomain_proof_ref": value.closed_subdomain_proof_ref,
        "canonical_digest": value.canonical_digest,
    }


def schedulability_from_doc(row: dict[str, Any]) -> ReactionSchedulabilityCertificate:
    witnesses = tuple(
        OverloadWitness(
            resource_ref=str(item["resource_ref"]), window_start=float(item["window_start"]), window_end=float(item["window_end"]),
            available_service=float(item["available_service"]), required_service=float(item["required_service"]),
            available_concurrency_units=int(item["available_concurrency_units"]),
            required_concurrency_units=int(item["required_concurrency_units"]),
            job_refs=tuple(str(x) for x in item.get("job_refs", ())), reason=str(item["reason"]),
        )
        for item in row.get("overload_witnesses", ())
    )
    mode = SchedulabilityAnalysisMode(str(row["analysis_mode"]))
    level = ReactionSchedulabilityLevel(str(row["level"]))
    body = {
        "certificate_id": str(row["certificate_id"]), "revision_id": str(row["revision_id"]),
        "policy_scope": str(row["policy_scope"]), "mission_revision": str(row["mission_revision"]),
        "information_partition_revision": str(row["information_partition_revision"]),
        "reaction_job_digests": _tuple_rows(row.get("reaction_job_digests", ())),
        "control_resource_digests": _tuple_rows(row.get("control_resource_digests", ())),
        "coexistence_constraint_refs": tuple(row.get("coexistence_constraint_refs", ())),
        "resource_reservation_refs": tuple(row.get("resource_reservation_refs", ())),
        "scheduling_model_id": str(row["scheduling_model_id"]), "scheduling_model_version": str(row["scheduling_model_version"]),
        "analysis_mode": mode.value,
        "worst_case_or_interval_assumptions": tuple(row.get("worst_case_or_interval_assumptions", ())),
        "proof_or_solver_ref": str(row["proof_or_solver_ref"]),
        "overload_witnesses": tuple(
            (w.resource_ref, w.window_start, w.window_end, w.available_service, w.required_service,
             w.available_concurrency_units, w.required_concurrency_units, w.job_refs, w.reason)
            for w in witnesses
        ),
        "assurance_profile": str(row["assurance_profile"]),
        "model_adequacy_debt_refs": tuple(row.get("model_adequacy_debt_refs", ())),
        "validity_regime": str(row["validity_regime"]), "level": level.value,
        "closed_subdomain_proof_ref": row.get("closed_subdomain_proof_ref"),
    }
    actual = digest(body)
    _check(row["canonical_digest"], actual, "schedulability certificate")
    return ReactionSchedulabilityCertificate(
        certificate_id=body["certificate_id"], revision_id=body["revision_id"], policy_scope=body["policy_scope"],
        mission_revision=body["mission_revision"], information_partition_revision=body["information_partition_revision"],
        reaction_job_digests=body["reaction_job_digests"], control_resource_digests=body["control_resource_digests"],
        coexistence_constraint_refs=body["coexistence_constraint_refs"], resource_reservation_refs=body["resource_reservation_refs"],
        scheduling_model_id=body["scheduling_model_id"], scheduling_model_version=body["scheduling_model_version"],
        analysis_mode=mode, worst_case_or_interval_assumptions=body["worst_case_or_interval_assumptions"],
        proof_or_solver_ref=body["proof_or_solver_ref"], overload_witnesses=witnesses,
        assurance_profile=body["assurance_profile"], model_adequacy_debt_refs=body["model_adequacy_debt_refs"],
        validity_regime=body["validity_regime"], level=level,
        closed_subdomain_proof_ref=body["closed_subdomain_proof_ref"], canonical_digest=actual,
    )


def coverage_doc(value: ExecutablePolicyCoverageAssessment) -> dict[str, Any]:
    return {
        "assessment_id": value.assessment_id, "revision_id": value.revision_id, "policy_scope": value.policy_scope,
        "policy_totality_certificate_ref": value.policy_totality_certificate_ref,
        "policy_totality_certificate_digest": value.policy_totality_certificate_digest,
        "policy_totality_mode": value.policy_totality_mode.value,
        "transition_observation_model_adequacy": value.transition_observation_model_adequacy.value,
        "residual_open_world_status": value.residual_open_world_status.value,
        "residual_debt_refs": value.residual_debt_refs, "closed_domain_proof_ref": value.closed_domain_proof_ref,
        "created_sequence": value.created_sequence, "validity_regime": value.validity_regime,
        "qualifier_refs": value.qualifier_refs, "canonical_digest": value.canonical_digest,
    }


def coverage_from_doc(row: dict[str, Any]) -> ExecutablePolicyCoverageAssessment:
    totality = TotalityMode(str(row["policy_totality_mode"]))
    adequacy = ModelAdequacyLevel(str(row["transition_observation_model_adequacy"]))
    residual = ResidualOpenWorldStatus(str(row["residual_open_world_status"]))
    body = {
        "assessment_id": str(row["assessment_id"]), "revision_id": str(row["revision_id"]),
        "policy_scope": str(row["policy_scope"]),
        "policy_totality_certificate_ref": str(row["policy_totality_certificate_ref"]),
        "policy_totality_certificate_digest": str(row["policy_totality_certificate_digest"]),
        "policy_totality_mode": totality.value, "transition_observation_model_adequacy": adequacy.value,
        "residual_open_world_status": residual.value, "residual_debt_refs": tuple(row.get("residual_debt_refs", ())),
        "closed_domain_proof_ref": row.get("closed_domain_proof_ref"), "created_sequence": int(row["created_sequence"]),
        "validity_regime": str(row["validity_regime"]), "qualifier_refs": tuple(row.get("qualifier_refs", ())),
    }
    actual = digest(body)
    _check(row["canonical_digest"], actual, "policy coverage assessment")
    return ExecutablePolicyCoverageAssessment(
        assessment_id=body["assessment_id"], revision_id=body["revision_id"], policy_scope=body["policy_scope"],
        policy_totality_certificate_ref=body["policy_totality_certificate_ref"],
        policy_totality_certificate_digest=body["policy_totality_certificate_digest"], policy_totality_mode=totality,
        transition_observation_model_adequacy=adequacy, residual_open_world_status=residual,
        residual_debt_refs=body["residual_debt_refs"], closed_domain_proof_ref=body["closed_domain_proof_ref"],
        created_sequence=body["created_sequence"], validity_regime=body["validity_regime"],
        qualifier_refs=body["qualifier_refs"], canonical_digest=actual,
    )


def independence_doc(value: OptionIndependenceCertificate) -> dict[str, Any]:
    return {
        "certificate_id": value.certificate_id, "revision_id": value.revision_id, "route_refs": value.route_refs,
        "failure_uncertainty_set_ref": value.failure_uncertainty_set_ref,
        "shared_dependency_graph_ref": value.shared_dependency_graph_ref,
        "route_dependency_refs": value.route_dependency_refs, "resource_overlap_refs": value.resource_overlap_refs,
        "observation_lineage_overlap_refs": value.observation_lineage_overlap_refs,
        "control_plane_overlap_refs": value.control_plane_overlap_refs, "common_mode_failure_refs": value.common_mode_failure_refs,
        "shared_dependency_refs": value.shared_dependency_refs, "coactivation_feasible": value.coactivation_feasible,
        "assurance_profile": value.assurance_profile, "analysis_supported": value.analysis_supported,
        "status": value.status.value, "blocker_refs": value.blocker_refs, "canonical_digest": value.canonical_digest,
    }


def independence_from_doc(row: dict[str, Any]) -> OptionIndependenceCertificate:
    status = OptionIndependenceStatus(str(row["status"]))
    route_deps = tuple((str(route), tuple(str(x) for x in refs)) for route, refs in row.get("route_dependency_refs", ()))
    body = {
        "certificate_id": str(row["certificate_id"]), "revision_id": str(row["revision_id"]),
        "route_refs": tuple(row.get("route_refs", ())), "failure_uncertainty_set_ref": str(row["failure_uncertainty_set_ref"]),
        "shared_dependency_graph_ref": str(row["shared_dependency_graph_ref"]), "route_dependency_refs": route_deps,
        "resource_overlap_refs": tuple(row.get("resource_overlap_refs", ())),
        "observation_lineage_overlap_refs": tuple(row.get("observation_lineage_overlap_refs", ())),
        "control_plane_overlap_refs": tuple(row.get("control_plane_overlap_refs", ())),
        "common_mode_failure_refs": tuple(row.get("common_mode_failure_refs", ())),
        "shared_dependency_refs": tuple(row.get("shared_dependency_refs", ())),
        "coactivation_feasible": row.get("coactivation_feasible"), "assurance_profile": str(row["assurance_profile"]),
        "analysis_supported": bool(row["analysis_supported"]), "status": status.value,
        "blocker_refs": tuple(row.get("blocker_refs", ())),
    }
    actual = digest(body)
    _check(row["canonical_digest"], actual, "option independence certificate")
    return OptionIndependenceCertificate(
        certificate_id=body["certificate_id"], revision_id=body["revision_id"], route_refs=body["route_refs"],
        failure_uncertainty_set_ref=body["failure_uncertainty_set_ref"], shared_dependency_graph_ref=body["shared_dependency_graph_ref"],
        route_dependency_refs=route_deps, resource_overlap_refs=body["resource_overlap_refs"],
        observation_lineage_overlap_refs=body["observation_lineage_overlap_refs"], control_plane_overlap_refs=body["control_plane_overlap_refs"],
        common_mode_failure_refs=body["common_mode_failure_refs"], shared_dependency_refs=body["shared_dependency_refs"],
        coactivation_feasible=body["coactivation_feasible"], assurance_profile=body["assurance_profile"],
        analysis_supported=body["analysis_supported"], status=status, blocker_refs=body["blocker_refs"], canonical_digest=actual,
    )


def robust_preparedness_doc(value: RobustPreparednessAssessment) -> dict[str, Any]:
    return {
        "structure": value.structure.value, "required_count": value.required_count, "profile_digests": value.profile_digests,
        "independence_certificate_digest": value.independence_certificate_digest,
        "nominal_alternative_preparedness": value.nominal_alternative_preparedness,
        "robust_independent_preparedness": value.robust_independent_preparedness,
        "robust_uplift_applied": value.robust_uplift_applied, "blocker_refs": value.blocker_refs,
        "canonical_digest": value.canonical_digest,
    }


def robust_preparedness_from_doc(row: dict[str, Any]) -> RobustPreparednessAssessment:
    structure = PreparednessStructure(str(row["structure"]))
    body = {
        "structure": structure.value, "required_count": int(row["required_count"]),
        "profile_digests": tuple(row.get("profile_digests", ())),
        "independence_certificate_digest": str(row["independence_certificate_digest"]),
        "nominal_alternative_preparedness": int(row["nominal_alternative_preparedness"]),
        "robust_independent_preparedness": int(row["robust_independent_preparedness"]),
        "robust_uplift_applied": bool(row["robust_uplift_applied"]), "blocker_refs": tuple(row.get("blocker_refs", ())),
    }
    actual = digest(body)
    _check(row["canonical_digest"], actual, "robust preparedness assessment")
    return RobustPreparednessAssessment(structure=structure, canonical_digest=actual, **{k: v for k, v in body.items() if k != "structure"})


def liveness_doc(value: HandoffLivenessCertificate) -> dict[str, Any]:
    return {
        "certificate_id": value.certificate_id, "revision_id": value.revision_id,
        "source_continuation_ref": value.source_continuation_ref, "successor_continuation_ref": value.successor_continuation_ref,
        "old_rank_digest": value.old_rank_digest, "new_rank_digest": value.new_rank_digest,
        "progress_policy_digest": value.progress_policy_digest, "handoff_count": value.handoff_count,
        "ordinary_stutter_count": value.ordinary_stutter_count, "recovery_stutter_count": value.recovery_stutter_count,
        "total_deferral_time": value.total_deferral_time, "recursive_feasibility": value.recursive_feasibility,
        "information_available_by_deadline": value.information_available_by_deadline, "recovery_mode": value.recovery_mode,
        "temporal_authority_revision_ref": value.temporal_authority_revision_ref, "current_time": value.current_time,
        "debt_lineage_equivalent": value.debt_lineage_equivalent, "progress_dimensions": value.progress_dimensions,
        "blocker_refs": value.blocker_refs, "status": value.status.value, "canonical_digest": value.canonical_digest,
    }


def liveness_from_doc(row: dict[str, Any]) -> HandoffLivenessCertificate:
    status = HandoffProgressStatus(str(row["status"]))
    body = {
        "certificate_id": str(row["certificate_id"]), "revision_id": str(row["revision_id"]),
        "source_continuation_ref": str(row["source_continuation_ref"]), "successor_continuation_ref": str(row["successor_continuation_ref"]),
        "old_rank_digest": str(row["old_rank_digest"]), "new_rank_digest": str(row["new_rank_digest"]),
        "progress_policy_digest": str(row["progress_policy_digest"]), "handoff_count": int(row["handoff_count"]),
        "ordinary_stutter_count": int(row["ordinary_stutter_count"]), "recovery_stutter_count": int(row["recovery_stutter_count"]),
        "total_deferral_time": float(row["total_deferral_time"]), "recursive_feasibility": row.get("recursive_feasibility"),
        "information_available_by_deadline": bool(row["information_available_by_deadline"]), "recovery_mode": bool(row["recovery_mode"]),
        "temporal_authority_revision_ref": str(row["temporal_authority_revision_ref"]), "current_time": float(row["current_time"]),
        "debt_lineage_equivalent": bool(row["debt_lineage_equivalent"]), "progress_dimensions": tuple(row.get("progress_dimensions", ())),
        "blocker_refs": tuple(row.get("blocker_refs", ())), "status": status.value,
    }
    actual = digest(body)
    _check(row["canonical_digest"], actual, "handoff liveness certificate")
    return HandoffLivenessCertificate(status=status, canonical_digest=actual, **{k: v for k, v in body.items() if k != "status"})


def stability_doc(value: HandoffStabilityContract) -> dict[str, Any]:
    return {
        "contract_id": value.contract_id, "revision_id": value.revision_id, "policy_edge_ref": value.policy_edge_ref,
        "protected_predicate_refs": value.protected_predicate_refs,
        "protected_generation_bindings": value.protected_generation_bindings,
        "lock_or_reservation_refs": value.lock_or_reservation_refs, "stability_start": value.stability_start,
        "stability_end": value.stability_end, "external_writer_assumption_refs": value.external_writer_assumption_refs,
        "refresh_required_predicate_refs": value.refresh_required_predicate_refs,
        "authorization_time_precondition_refs": value.authorization_time_precondition_refs,
        "invalidating_event_refs": value.invalidating_event_refs, "open_side_effect_refs": value.open_side_effect_refs,
        "fallback_on_instability": value.fallback_on_instability, "opacity_debt_refs": value.opacity_debt_refs,
        "validity_regime": value.validity_regime, "canonical_digest": value.canonical_digest,
    }


def stability_from_doc(row: dict[str, Any]) -> HandoffStabilityContract:
    value = HandoffStabilityContract.create(
        contract_id=row["contract_id"], revision_id=row["revision_id"], policy_edge_ref=row["policy_edge_ref"],
        protected_predicate_refs=row.get("protected_predicate_refs", ()),
        protected_generation_bindings=row.get("protected_generation_bindings", ()),
        lock_or_reservation_refs=row.get("lock_or_reservation_refs", ()), stability_start=row["stability_start"],
        stability_end=row["stability_end"], external_writer_assumption_refs=row.get("external_writer_assumption_refs", ()),
        refresh_required_predicate_refs=row.get("refresh_required_predicate_refs", ()),
        authorization_time_precondition_refs=row.get("authorization_time_precondition_refs", ()),
        invalidating_event_refs=row.get("invalidating_event_refs", ()), open_side_effect_refs=row.get("open_side_effect_refs", ()),
        fallback_on_instability=row["fallback_on_instability"], opacity_debt_refs=row.get("opacity_debt_refs", ()),
        validity_regime=row["validity_regime"],
    )
    _check(row["canonical_digest"], value.canonical_digest, "handoff stability contract")
    return value


def activation_doc(value: EdgeActivationAssessment) -> dict[str, Any]:
    return {
        "contract_digest": value.contract_digest, "status": value.status.value,
        "required_refresh_predicates": value.required_refresh_predicates, "blocker_refs": value.blocker_refs,
        "refreshed_predicates": value.refreshed_predicates, "fallback_ref": value.fallback_ref,
        "assessed_at": value.assessed_at, "canonical_digest": value.canonical_digest,
    }


def activation_from_doc(row: dict[str, Any]) -> EdgeActivationAssessment:
    status = EdgeActivationStatus(str(row["status"]))
    body = {
        "contract_digest": str(row["contract_digest"]), "status": status.value,
        "required_refresh_predicates": tuple(row.get("required_refresh_predicates", ())),
        "blocker_refs": tuple(row.get("blocker_refs", ())), "refreshed_predicates": tuple(row.get("refreshed_predicates", ())),
        "fallback_ref": str(row["fallback_ref"]), "assessed_at": float(row["assessed_at"]),
    }
    actual = digest(body)
    _check(row["canonical_digest"], actual, "edge activation assessment")
    return EdgeActivationAssessment(status=status, canonical_digest=actual, **{k: v for k, v in body.items() if k != "status"})
