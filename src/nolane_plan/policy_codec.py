from __future__ import annotations

from typing import Any

from .hashing import digest
from .policy_certificates import RecallLevel, TotalityMode
from .policy_executability import ExecutabilityClosureManifest, ExecutabilityStatus, PolicyExecutabilityAssessment
from .policy_information import DecisionEpoch, InformationPartitionRevision, ObservationFrontierRevision
from .policy_ir import PolicyNodeRevision, PolicySuccessorRoute
from .policy_readiness import ReactionControllabilityClass
from .seals import ArtifactAssurance, CompositionStatus, DecisionSufficiencyCertificate, PlanSeal, SealStatus
from .selection import SelectionRecord, SelectionStatus
from .types import ReplayError


def _verify(recorded: str, actual: str, label: str) -> None:
    if actual != recorded:
        raise ReplayError(f"{label} canonical digest mismatch")


def frontier_doc(value: ObservationFrontierRevision) -> dict[str, Any]:
    return {
        "frontier_id": value.frontier_id,
        "revision_id": value.revision_id,
        "principal_scope_ref": value.principal_scope_ref,
        "information_access_profile_revision": value.information_access_profile_revision,
        "currently_available_observations": list(value.currently_available_observations),
        "pending_observations": list(value.pending_observations),
        "reveal_event_refs": list(value.reveal_event_refs),
        "latest_safe_observation_times": [list(row) for row in value.latest_safe_observation_times],
        "observation_costs": [list(row) for row in value.observation_costs],
        "observation_side_effects": list(value.observation_side_effects),
        "observation_dependencies": list(value.observation_dependencies),
        "unobservable_predicates": list(value.unobservable_predicates),
        "conditionally_observable_predicates": list(value.conditionally_observable_predicates),
        "frontier_debt_refs": list(value.frontier_debt_refs),
        "validity_regime": value.validity_regime,
        "canonical_digest": value.canonical_digest,
    }


def frontier_from_doc(row: dict[str, Any]) -> ObservationFrontierRevision:
    value = ObservationFrontierRevision.create(
        frontier_id=str(row["frontier_id"]),
        revision_id=str(row["revision_id"]),
        principal_scope_ref=str(row["principal_scope_ref"]),
        information_access_profile_revision=str(row["information_access_profile_revision"]),
        currently_available_observations=tuple(row.get("currently_available_observations", ())),
        pending_observations=tuple(row.get("pending_observations", ())),
        reveal_event_refs=tuple(row.get("reveal_event_refs", ())),
        latest_safe_observation_times={str(x[0]): x[1] for x in row.get("latest_safe_observation_times", ())},
        observation_costs={str(x[0]): float(x[1]) for x in row.get("observation_costs", ())},
        observation_side_effects=tuple(row.get("observation_side_effects", ())),
        observation_dependencies=tuple(row.get("observation_dependencies", ())),
        unobservable_predicates=tuple(row.get("unobservable_predicates", ())),
        conditionally_observable_predicates=tuple(row.get("conditionally_observable_predicates", ())),
        frontier_debt_refs=tuple(row.get("frontier_debt_refs", ())),
        validity_regime=str(row["validity_regime"]),
    )
    _verify(str(row["canonical_digest"]), value.canonical_digest, "observation frontier")
    return value


def partition_doc(value: InformationPartitionRevision) -> dict[str, Any]:
    return {
        "logical_id": value.logical_id,
        "revision_id": value.revision_id,
        "mission_revision": value.mission_revision,
        "decision_epoch_ref": value.decision_epoch_ref,
        "principal_scope_ref": value.principal_scope_ref,
        "information_access_profile_revision": value.information_access_profile_revision,
        "principal_observation_history_digest": value.principal_observation_history_digest,
        "principal_delivery_frontier_refs": list(value.principal_delivery_frontier_refs),
        "canonical_state_version": value.canonical_state_version,
        "observation_history_digest": value.observation_history_digest,
        "observable_predicate_set": list(value.observable_predicate_set),
        "hidden_or_unrevealed_predicate_set": list(value.hidden_or_unrevealed_predicate_set),
        "information_equivalence_classes": [[key, list(histories)] for key, histories in value.information_equivalence_classes],
        "reveal_event_refs": list(value.reveal_event_refs),
        "observation_model_refs": list(value.observation_model_refs),
        "perfect_recall_basis_ref": value.perfect_recall_basis_ref,
        "abstraction_certificate_refs": list(value.abstraction_certificate_refs),
        "debt_refs": list(value.debt_refs),
        "validity_regime": value.validity_regime,
        "canonical_digest": value.canonical_digest,
    }


def partition_from_doc(row: dict[str, Any]) -> InformationPartitionRevision:
    value = InformationPartitionRevision.create(
        logical_id=str(row["logical_id"]),
        revision_id=str(row["revision_id"]),
        mission_revision=int(row["mission_revision"]),
        decision_epoch_ref=str(row["decision_epoch_ref"]),
        principal_scope_ref=str(row["principal_scope_ref"]),
        information_access_profile_revision=str(row["information_access_profile_revision"]),
        principal_observation_history_digest=str(row["principal_observation_history_digest"]),
        principal_delivery_frontier_refs=tuple(row.get("principal_delivery_frontier_refs", ())),
        canonical_state_version=int(row["canonical_state_version"]),
        observation_history_digest=str(row["observation_history_digest"]),
        observable_predicate_set=tuple(row.get("observable_predicate_set", ())),
        hidden_or_unrevealed_predicate_set=tuple(row.get("hidden_or_unrevealed_predicate_set", ())),
        information_equivalence_classes={str(x[0]): tuple(x[1]) for x in row.get("information_equivalence_classes", ())},
        reveal_event_refs=tuple(row.get("reveal_event_refs", ())),
        observation_model_refs=tuple(row.get("observation_model_refs", ())),
        perfect_recall_basis_ref=str(row["perfect_recall_basis_ref"]),
        abstraction_certificate_refs=tuple(row.get("abstraction_certificate_refs", ())),
        debt_refs=tuple(row.get("debt_refs", ())),
        validity_regime=str(row["validity_regime"]),
    )
    _verify(str(row["canonical_digest"]), value.canonical_digest, "information partition")
    return value


def epoch_doc(value: DecisionEpoch) -> dict[str, Any]:
    return {
        "epoch_id": value.epoch_id,
        "plan_snapshot_version": value.plan_snapshot_version,
        "mission_revision": value.mission_revision,
        "decision_principal_ref": value.decision_principal_ref,
        "strategic_location_revision": value.strategic_location_revision,
        "information_partition_revision": value.information_partition_revision,
        "principal_information_access_profile_revision": value.principal_information_access_profile_revision,
        "available_action_space_revision": value.available_action_space_revision,
        "active_authority_profile": value.active_authority_profile,
        "active_obligation_basis": value.active_obligation_basis,
        "risk_policy_revision": value.risk_policy_revision,
        "observation_frontier_revision": value.observation_frontier_revision,
        "temporal_window": list(value.temporal_window),
        "bound_principal_scope_ref": value.bound_principal_scope_ref,
        "canonical_digest": value.canonical_digest,
    }


def epoch_from_doc(row: dict[str, Any]) -> DecisionEpoch:
    value = DecisionEpoch.create(
        epoch_id=str(row["epoch_id"]),
        plan_snapshot_version=int(row["plan_snapshot_version"]),
        mission_revision=int(row["mission_revision"]),
        decision_principal_ref=str(row["decision_principal_ref"]),
        strategic_location_revision=int(row["strategic_location_revision"]),
        information_partition_revision=str(row["information_partition_revision"]),
        principal_information_access_profile_revision=str(row["principal_information_access_profile_revision"]),
        available_action_space_revision=str(row["available_action_space_revision"]),
        active_authority_profile=str(row["active_authority_profile"]),
        active_obligation_basis=str(row["active_obligation_basis"]),
        risk_policy_revision=str(row["risk_policy_revision"]),
        observation_frontier_revision=str(row["observation_frontier_revision"]),
        temporal_window=(row["temporal_window"][0], row["temporal_window"][1]),
        bound_principal_scope_ref=str(row["bound_principal_scope_ref"]),
    )
    _verify(str(row["canonical_digest"]), value.canonical_digest, "decision epoch")
    return value


def node_doc(value: PolicyNodeRevision) -> dict[str, Any]:
    return {
        "policy_node_id": value.policy_node_id,
        "revision_id": value.revision_id,
        "mission_revision": value.mission_revision,
        "decision_principal_ref": value.decision_principal_ref,
        "plan_snapshot_version": value.plan_snapshot_version,
        "strategic_location_revision": value.strategic_location_revision,
        "information_partition_revision": value.information_partition_revision,
        "decision_epoch_ref": value.decision_epoch_ref,
        "action_space_revision": value.action_space_revision,
        "candidate_action_contracts": list(value.candidate_action_contracts),
        "execution_principal_requirement_or_set": list(value.execution_principal_requirement_or_set),
        "selected_action_contract_or_policy_set": list(value.selected_action_contract_or_policy_set),
        "runtime_guard_refs": list(value.runtime_guard_refs),
        "observation_frontier_revision": value.observation_frontier_revision,
        "successor_policy_mapping": [
            [route.guard_ref, route.reveal_event_ref, route.child_policy_node_revision]
            for route in value.successor_policy_mapping
        ],
        "shared_commitment_refs": list(value.shared_commitment_refs),
        "resource_reservation_refs": list(value.resource_reservation_refs),
        "obligation_basis_ref": value.obligation_basis_ref,
        "risk_policy_revision": value.risk_policy_revision,
        "authority_profile_requirement": value.authority_profile_requirement,
        "route_guarantee_requirement": value.route_guarantee_requirement,
        "preparedness_level": value.preparedness_level,
        "proof_context_ref": value.proof_context_ref,
        "assurance_profile": value.assurance_profile,
        "debt_refs": list(value.debt_refs),
        "sealed": value.sealed,
        "canonical_digest": value.canonical_digest,
    }


def node_from_doc(row: dict[str, Any]) -> PolicyNodeRevision:
    value = PolicyNodeRevision.create(
        policy_node_id=str(row["policy_node_id"]),
        revision_id=str(row["revision_id"]),
        mission_revision=int(row["mission_revision"]),
        decision_principal_ref=str(row["decision_principal_ref"]),
        plan_snapshot_version=int(row["plan_snapshot_version"]),
        strategic_location_revision=int(row["strategic_location_revision"]),
        information_partition_revision=str(row["information_partition_revision"]),
        decision_epoch_ref=str(row["decision_epoch_ref"]),
        action_space_revision=str(row["action_space_revision"]),
        candidate_action_contracts=tuple(row.get("candidate_action_contracts", ())),
        execution_principal_requirement_or_set=tuple(row.get("execution_principal_requirement_or_set", ())),
        selected_action_contract_or_policy_set=tuple(row.get("selected_action_contract_or_policy_set", ())),
        runtime_guard_refs=tuple(row.get("runtime_guard_refs", ())),
        observation_frontier_revision=str(row["observation_frontier_revision"]),
        successor_policy_mapping=tuple(
            PolicySuccessorRoute(str(x[0]), str(x[1]), str(x[2])) for x in row.get("successor_policy_mapping", ())
        ),
        shared_commitment_refs=tuple(row.get("shared_commitment_refs", ())),
        resource_reservation_refs=tuple(row.get("resource_reservation_refs", ())),
        obligation_basis_ref=str(row["obligation_basis_ref"]),
        risk_policy_revision=str(row["risk_policy_revision"]),
        authority_profile_requirement=str(row["authority_profile_requirement"]),
        route_guarantee_requirement=str(row["route_guarantee_requirement"]),
        preparedness_level=str(row["preparedness_level"]),
        proof_context_ref=str(row["proof_context_ref"]),
        assurance_profile=str(row["assurance_profile"]),
        debt_refs=tuple(row.get("debt_refs", ())),
        sealed=bool(row["sealed"]),
    )
    _verify(str(row["canonical_digest"]), value.canonical_digest, "policy node")
    return value


def selection_doc(value: SelectionRecord) -> dict[str, Any]:
    return {
        "record_id": value.record_id,
        "transaction_id": value.transaction_id,
        "transaction_digest": value.transaction_digest,
        "candidate_set_digest": value.candidate_set_digest,
        "decision_principal_ref": value.decision_principal_ref,
        "information_partition_revision": value.information_partition_revision,
        "action_space_revision": value.action_space_revision,
        "chosen_action_ref": value.chosen_action_ref,
        "hard_admissibility_digest": value.hard_admissibility_digest,
        "pareto_front": list(value.pareto_front),
        "score_digest": value.score_digest,
        "tie_break_reason": value.tie_break_reason,
        "dependency_generations": [list(x) for x in value.dependency_generations],
        "status": value.status.value,
        "superseded_by": value.superseded_by,
        "canonical_digest": value.canonical_digest,
    }


def selection_from_doc(row: dict[str, Any]) -> SelectionRecord:
    status = SelectionStatus(str(row["status"]))
    body = {
        "record_id": str(row["record_id"]),
        "transaction_id": str(row["transaction_id"]),
        "transaction_digest": str(row["transaction_digest"]),
        "candidate_set_digest": str(row["candidate_set_digest"]),
        "decision_principal_ref": str(row["decision_principal_ref"]),
        "information_partition_revision": str(row["information_partition_revision"]),
        "action_space_revision": str(row["action_space_revision"]),
        "chosen_action_ref": str(row["chosen_action_ref"]),
        "hard_admissibility_digest": str(row["hard_admissibility_digest"]),
        "pareto_front": tuple(str(x) for x in row.get("pareto_front", ())),
        "score_digest": str(row["score_digest"]),
        "tie_break_reason": str(row["tie_break_reason"]),
        "dependency_generations": tuple((str(x[0]), int(x[1])) for x in row.get("dependency_generations", ())),
        "status": status.value,
        "superseded_by": row.get("superseded_by"),
    }
    recorded = str(row["canonical_digest"])
    _verify(recorded, digest(body), "selection record")
    return SelectionRecord(
        record_id=body["record_id"],
        transaction_id=body["transaction_id"],
        transaction_digest=body["transaction_digest"],
        candidate_set_digest=body["candidate_set_digest"],
        decision_principal_ref=body["decision_principal_ref"],
        information_partition_revision=body["information_partition_revision"],
        action_space_revision=body["action_space_revision"],
        chosen_action_ref=body["chosen_action_ref"],
        hard_admissibility_digest=body["hard_admissibility_digest"],
        pareto_front=body["pareto_front"],
        score_digest=body["score_digest"],
        tie_break_reason=body["tie_break_reason"],
        dependency_generations=body["dependency_generations"],
        status=status,
        superseded_by=body["superseded_by"],
        canonical_digest=recorded,
    )


def sufficiency_doc(value: DecisionSufficiencyCertificate) -> dict[str, Any]:
    return {
        "certificate_id": value.certificate_id,
        "revision_id": value.revision_id,
        "scope_ref": value.scope_ref,
        "action_ref": value.action_ref,
        "decision_epoch_ref": value.decision_epoch_ref,
        "decision_principal_ref": value.decision_principal_ref,
        "information_partition_revision": value.information_partition_revision,
        "exact_object_revisions": [list(x) for x in value.exact_object_revisions],
        "included_object_refs": list(value.included_object_refs),
        "excluded_known_object_refs": list(value.excluded_known_object_refs),
        "compiler_profile_ref": value.compiler_profile_ref,
        "adequacy_limits": list(value.adequacy_limits),
        "debt_refs": list(value.debt_refs),
        "complete": value.complete,
        "created_sequence": value.created_sequence,
        "validity_regime": value.validity_regime,
        "canonical_digest": value.canonical_digest,
    }


def sufficiency_from_doc(row: dict[str, Any]) -> DecisionSufficiencyCertificate:
    value = DecisionSufficiencyCertificate.create(
        certificate_id=str(row["certificate_id"]),
        revision_id=str(row["revision_id"]),
        scope_ref=str(row["scope_ref"]),
        action_ref=str(row["action_ref"]),
        decision_epoch_ref=str(row["decision_epoch_ref"]),
        decision_principal_ref=str(row["decision_principal_ref"]),
        information_partition_revision=str(row["information_partition_revision"]),
        exact_object_revisions={str(x[0]): str(x[1]) for x in row.get("exact_object_revisions", ())},
        included_object_refs=tuple(row.get("included_object_refs", ())),
        excluded_known_object_refs=tuple(row.get("excluded_known_object_refs", ())),
        compiler_profile_ref=str(row["compiler_profile_ref"]),
        adequacy_limits=tuple(row.get("adequacy_limits", ())),
        debt_refs=tuple(row.get("debt_refs", ())),
        complete=bool(row["complete"]),
        created_sequence=int(row["created_sequence"]),
        validity_regime=str(row["validity_regime"]),
    )
    _verify(str(row["canonical_digest"]), value.canonical_digest, "decision sufficiency")
    return value


def seal_doc(value: PlanSeal) -> dict[str, Any]:
    return {
        "seal_id": value.seal_id,
        "revision_id": value.revision_id,
        "plan_root_revision": value.plan_root_revision,
        "mission_revision": value.mission_revision,
        "canonical_state_version": value.canonical_state_version,
        "action_closure_refs": list(value.action_closure_refs),
        "sufficiency_certificate_revision": value.sufficiency_certificate_revision,
        "sufficiency_certificate_digest": value.sufficiency_certificate_digest,
        "proof_context_digests": list(value.proof_context_digests),
        "composition_digest": value.composition_digest,
        "required_assurance": value.required_assurance.value,
        "assurance_floor": value.assurance_floor.value,
        "accepted_debt_refs": list(value.accepted_debt_refs),
        "compiler_pass_manifest": list(value.compiler_pass_manifest),
        "invariant_digest": value.invariant_digest,
        "created_sequence": value.created_sequence,
        "validity_regime": value.validity_regime,
        "status": value.status.value,
        "canonical_digest": value.canonical_digest,
    }


def seal_from_doc(row: dict[str, Any]) -> PlanSeal:
    required = ArtifactAssurance(str(row["required_assurance"]))
    floor = ArtifactAssurance(str(row["assurance_floor"]))
    status = SealStatus(str(row["status"]))
    body = {
        "seal_id": str(row["seal_id"]),
        "revision_id": str(row["revision_id"]),
        "plan_root_revision": str(row["plan_root_revision"]),
        "mission_revision": int(row["mission_revision"]),
        "canonical_state_version": int(row["canonical_state_version"]),
        "action_closure_refs": tuple(str(x) for x in row.get("action_closure_refs", ())),
        "sufficiency_certificate_revision": str(row["sufficiency_certificate_revision"]),
        "sufficiency_certificate_digest": str(row["sufficiency_certificate_digest"]),
        "proof_context_digests": tuple(str(x) for x in row.get("proof_context_digests", ())),
        "composition_digest": str(row["composition_digest"]),
        "required_assurance": required.value,
        "assurance_floor": floor.value,
        "accepted_debt_refs": tuple(str(x) for x in row.get("accepted_debt_refs", ())),
        "compiler_pass_manifest": tuple(str(x) for x in row.get("compiler_pass_manifest", ())),
        "invariant_digest": str(row["invariant_digest"]),
        "created_sequence": int(row["created_sequence"]),
        "validity_regime": str(row["validity_regime"]),
        "status": status.value,
    }
    recorded = str(row["canonical_digest"])
    _verify(recorded, digest(body), "PlanSeal")
    return PlanSeal(
        seal_id=body["seal_id"],
        revision_id=body["revision_id"],
        plan_root_revision=body["plan_root_revision"],
        mission_revision=body["mission_revision"],
        canonical_state_version=body["canonical_state_version"],
        action_closure_refs=body["action_closure_refs"],
        sufficiency_certificate_revision=body["sufficiency_certificate_revision"],
        sufficiency_certificate_digest=body["sufficiency_certificate_digest"],
        proof_context_digests=body["proof_context_digests"],
        composition_digest=body["composition_digest"],
        required_assurance=required,
        assurance_floor=floor,
        accepted_debt_refs=body["accepted_debt_refs"],
        compiler_pass_manifest=body["compiler_pass_manifest"],
        invariant_digest=body["invariant_digest"],
        created_sequence=body["created_sequence"],
        validity_regime=body["validity_regime"],
        status=status,
        canonical_digest=recorded,
    )


def executability_doc(value: PolicyExecutabilityAssessment) -> dict[str, Any]:
    manifest = value.closure_manifest
    return {
        "assessment_id": value.assessment_id,
        "revision_id": value.revision_id,
        "scope_ref": value.scope_ref,
        "closure_manifest": {
            "scope_ref": manifest.scope_ref,
            "mission_revision": manifest.mission_revision,
            "plan_snapshot_version": manifest.plan_snapshot_version,
            "policy_revision": manifest.policy_revision,
            "information_partition_revision": manifest.information_partition_revision,
            "action_space_revision": manifest.action_space_revision,
            "bound_snapshot_revisions": [list(x) for x in manifest.bound_snapshot_revisions],
            "nonanticipativity_valid": manifest.nonanticipativity_valid,
            "recall_level": manifest.recall_level.value,
            "totality_mode": manifest.totality_mode.value,
            "edge_certificates_valid": manifest.edge_certificates_valid,
            "shared_resource_commitments_feasible": manifest.shared_resource_commitments_feasible,
            "information_capability_preserved": manifest.information_capability_preserved,
            "reaction_class": manifest.reaction_class.value,
            "required_reaction_class": manifest.required_reaction_class.value,
            "preparedness_level": manifest.preparedness_level,
            "required_preparedness_level": manifest.required_preparedness_level,
            "composition_status": manifest.composition_status.value,
            "route_guarantee_met": manifest.route_guarantee_met,
            "continuation_revision": manifest.continuation_revision,
            "continuation_terminal_semantics": manifest.continuation_terminal_semantics,
            "requested_horizon": manifest.requested_horizon,
            "seal_status": manifest.seal_status.value,
            "canonical_digest": manifest.canonical_digest,
        },
        "status": value.status.value,
        "blockers": list(value.blockers),
        "unknowns": list(value.unknowns),
        "accepted_debt_refs": list(value.accepted_debt_refs),
        "unaccepted_debt_refs": list(value.unaccepted_debt_refs),
        "canonical_digest": value.canonical_digest,
    }


def executability_from_doc(row: dict[str, Any]) -> PolicyExecutabilityAssessment:
    source = dict(row["closure_manifest"])
    recall = RecallLevel(str(source["recall_level"]))
    totality = TotalityMode(str(source["totality_mode"]))
    reaction = ReactionControllabilityClass(str(source["reaction_class"]))
    required_reaction = ReactionControllabilityClass(str(source["required_reaction_class"]))
    composition = CompositionStatus(str(source["composition_status"]))
    seal_status = SealStatus(str(source["seal_status"]))
    manifest_body = {
        "scope_ref": str(source["scope_ref"]),
        "mission_revision": int(source["mission_revision"]),
        "plan_snapshot_version": int(source["plan_snapshot_version"]),
        "policy_revision": str(source["policy_revision"]),
        "information_partition_revision": str(source["information_partition_revision"]),
        "action_space_revision": str(source["action_space_revision"]),
        "bound_snapshot_revisions": tuple((str(x[0]), str(x[1])) for x in source.get("bound_snapshot_revisions", ())),
        "nonanticipativity_valid": bool(source["nonanticipativity_valid"]),
        "recall_level": recall.value,
        "totality_mode": totality.value,
        "edge_certificates_valid": bool(source["edge_certificates_valid"]),
        "shared_resource_commitments_feasible": bool(source["shared_resource_commitments_feasible"]),
        "information_capability_preserved": bool(source["information_capability_preserved"]),
        "reaction_class": reaction.value,
        "required_reaction_class": required_reaction.value,
        "preparedness_level": int(source["preparedness_level"]),
        "required_preparedness_level": int(source["required_preparedness_level"]),
        "composition_status": composition.value,
        "route_guarantee_met": bool(source["route_guarantee_met"]),
        "continuation_revision": str(source["continuation_revision"]),
        "continuation_terminal_semantics": str(source["continuation_terminal_semantics"]),
        "requested_horizon": float(source["requested_horizon"]),
        "seal_status": seal_status.value,
    }
    manifest_recorded = str(source["canonical_digest"])
    _verify(manifest_recorded, digest(manifest_body), "executability closure manifest")
    manifest = ExecutabilityClosureManifest(
        scope_ref=manifest_body["scope_ref"],
        mission_revision=manifest_body["mission_revision"],
        plan_snapshot_version=manifest_body["plan_snapshot_version"],
        policy_revision=manifest_body["policy_revision"],
        information_partition_revision=manifest_body["information_partition_revision"],
        action_space_revision=manifest_body["action_space_revision"],
        bound_snapshot_revisions=manifest_body["bound_snapshot_revisions"],
        nonanticipativity_valid=manifest_body["nonanticipativity_valid"],
        recall_level=recall,
        totality_mode=totality,
        edge_certificates_valid=manifest_body["edge_certificates_valid"],
        shared_resource_commitments_feasible=manifest_body["shared_resource_commitments_feasible"],
        information_capability_preserved=manifest_body["information_capability_preserved"],
        reaction_class=reaction,
        required_reaction_class=required_reaction,
        preparedness_level=manifest_body["preparedness_level"],
        required_preparedness_level=manifest_body["required_preparedness_level"],
        composition_status=composition,
        route_guarantee_met=manifest_body["route_guarantee_met"],
        continuation_revision=manifest_body["continuation_revision"],
        continuation_terminal_semantics=manifest_body["continuation_terminal_semantics"],
        requested_horizon=manifest_body["requested_horizon"],
        seal_status=seal_status,
        canonical_digest=manifest_recorded,
    )
    status = ExecutabilityStatus(str(row["status"]))
    assessment_body = {
        "assessment_id": str(row["assessment_id"]),
        "revision_id": str(row["revision_id"]),
        "scope_ref": str(row["scope_ref"]),
        "closure_manifest_digest": manifest.canonical_digest,
        "status": status.value,
        "blockers": tuple(str(x) for x in row.get("blockers", ())),
        "unknowns": tuple(str(x) for x in row.get("unknowns", ())),
        "accepted_debt_refs": tuple(str(x) for x in row.get("accepted_debt_refs", ())),
        "unaccepted_debt_refs": tuple(str(x) for x in row.get("unaccepted_debt_refs", ())),
    }
    recorded = str(row["canonical_digest"])
    _verify(recorded, digest(assessment_body), "policy executability assessment")
    return PolicyExecutabilityAssessment(
        assessment_id=assessment_body["assessment_id"],
        revision_id=assessment_body["revision_id"],
        scope_ref=assessment_body["scope_ref"],
        closure_manifest=manifest,
        status=status,
        blockers=assessment_body["blockers"],
        unknowns=assessment_body["unknowns"],
        accepted_debt_refs=assessment_body["accepted_debt_refs"],
        unaccepted_debt_refs=assessment_body["unaccepted_debt_refs"],
        canonical_digest=recorded,
    )
