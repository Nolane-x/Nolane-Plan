from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Mapping

from .hashing import digest
from .policy_certificates import RecallLevel, TotalityMode
from .policy_readiness import ContinuationContract, ReactionControllabilityClass
from .seals import CompositionStatus, SealStatus


def _canon(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(sorted({str(value).strip() for value in values if str(value).strip()}))


def _required(name: str, value: object) -> str:
    text = str(value).strip()
    if not text:
        raise ValueError(f"{name} must be non-empty")
    return text


class ExecutabilityStatus(str, Enum):
    EXEC_UNANALYZED = "EXEC_UNANALYZED"
    EXEC_PARTIAL = "EXEC_PARTIAL"
    EXEC_BOUNDED = "EXEC_BOUNDED"
    EXEC_BOUNDED_WITH_ACCEPTED_DEBT = "EXEC_BOUNDED_WITH_ACCEPTED_DEBT"
    EXEC_NOT_EXECUTABLE = "EXEC_NOT_EXECUTABLE"
    EXEC_UNKNOWN = "EXEC_UNKNOWN"


_REACTION_RANK = {
    ReactionControllabilityClass.IA0_UNANALYZED: 0,
    ReactionControllabilityClass.IA1_POSSIBLE_TIMELY: 1,
    ReactionControllabilityClass.IA2_BOUNDED_GUARANTEED_TIMELY: 2,
    ReactionControllabilityClass.IA3_DYNAMICALLY_REACTION_CONTROLLABLE: 3,
    ReactionControllabilityClass.IA4_CLOSED_SUBDOMAIN_PROVEN: 4,
}


@dataclass(frozen=True, slots=True)
class ExecutabilityClosureManifest:
    scope_ref: str
    mission_revision: int
    plan_snapshot_version: int
    policy_revision: str
    information_partition_revision: str
    action_space_revision: str
    bound_snapshot_revisions: tuple[tuple[str, str], ...]
    nonanticipativity_valid: bool
    recall_level: RecallLevel
    totality_mode: TotalityMode
    edge_certificates_valid: bool
    shared_resource_commitments_feasible: bool
    information_capability_preserved: bool
    reaction_class: ReactionControllabilityClass
    required_reaction_class: ReactionControllabilityClass
    preparedness_level: int
    required_preparedness_level: int
    composition_status: CompositionStatus
    route_guarantee_met: bool
    continuation_revision: str
    continuation_terminal_semantics: str
    requested_horizon: float
    seal_status: SealStatus
    canonical_digest: str


@dataclass(frozen=True, slots=True)
class PolicyExecutabilityAssessment:
    assessment_id: str
    revision_id: str
    scope_ref: str
    closure_manifest: ExecutabilityClosureManifest
    status: ExecutabilityStatus
    blockers: tuple[str, ...]
    unknowns: tuple[str, ...]
    accepted_debt_refs: tuple[str, ...]
    unaccepted_debt_refs: tuple[str, ...]
    canonical_digest: str


class PolicyExecutabilityEvaluator:
    @staticmethod
    def evaluate(
        *,
        assessment_id: str,
        revision_id: str,
        scope_ref: str,
        mission_revision: int,
        plan_snapshot_version: int,
        policy_revision: str,
        information_partition_revision: str,
        action_space_revision: str,
        bound_snapshot_revisions: Mapping[str, str],
        nonanticipativity_valid: bool,
        recall_level: RecallLevel,
        totality_mode: TotalityMode,
        edge_certificates_valid: bool,
        shared_resource_commitments_feasible: bool,
        information_capability_preserved: bool,
        reaction_class: ReactionControllabilityClass,
        required_reaction_class: ReactionControllabilityClass,
        preparedness_level: int,
        required_preparedness_level: int,
        composition_status: CompositionStatus,
        route_guarantee_met: bool,
        continuation: ContinuationContract,
        requested_horizon: int | float,
        seal_status: SealStatus,
        debt_refs: Iterable[str],
        accepted_debt_refs: Iterable[str],
        model_confidence: float | None = None,
    ) -> PolicyExecutabilityAssessment:
        # Model confidence is diagnostic only. It has no authority-promoting role.
        del model_confidence

        if int(mission_revision) < 1 or int(plan_snapshot_version) < 1:
            raise ValueError("mission and plan snapshot revisions must be positive")
        prep = int(preparedness_level)
        required_prep = int(required_preparedness_level)
        if prep < 0 or required_prep < 0:
            raise ValueError("preparedness levels cannot be negative")
        horizon = float(requested_horizon)
        if horizon < 0:
            raise ValueError("requested horizon cannot be negative")

        scope = _required("scope_ref", scope_ref)
        policy = _required("policy_revision", policy_revision)
        partition = _required("information_partition_revision", information_partition_revision)
        actions = _required("action_space_revision", action_space_revision)
        snapshot = tuple(sorted((str(key), str(value)) for key, value in bound_snapshot_revisions.items()))

        blockers: set[str] = set()
        unknowns: set[str] = set()

        expected_snapshot = {
            "mission": str(int(mission_revision)),
            "plan": str(int(plan_snapshot_version)),
            "policy": policy,
            "partition": partition,
            "actions": actions,
        }
        if dict(snapshot) != expected_snapshot:
            blockers.add("MIXED_SEMANTIC_SNAPSHOT")

        if not nonanticipativity_valid:
            blockers.add("NONANTICIPATIVITY_VIOLATION")

        if recall_level == RecallLevel.RECALL_INSUFFICIENT:
            blockers.add("RECALL_INSUFFICIENT")
        elif recall_level == RecallLevel.RECALL_UNKNOWN:
            unknowns.add("RECALL_UNRESOLVED")

        if totality_mode == TotalityMode.INCOMPLETE:
            blockers.add("POLICY_TOTALITY_HOLE")
        elif totality_mode in {TotalityMode.UNKNOWN, TotalityMode.UNSUPPORTED}:
            unknowns.add("POLICY_TOTALITY_UNRESOLVED")

        if not edge_certificates_valid:
            blockers.add("POLICY_EDGE_STITCH_FAILURE")
        if not shared_resource_commitments_feasible:
            blockers.add("SHARED_RESOURCE_COMMITMENT_CONFLICT")
        if not information_capability_preserved:
            blockers.add("INFORMATION_CAPABILITY_LOSS")

        if _REACTION_RANK[reaction_class] < _REACTION_RANK[required_reaction_class]:
            blockers.add("REACTION_CONTROLLABILITY_BELOW_FLOOR")
        elif reaction_class == ReactionControllabilityClass.IA0_UNANALYZED:
            unknowns.add("REACTION_UNANALYZED")

        if prep < required_prep:
            blockers.add("PREPAREDNESS_BELOW_FLOOR")

        if composition_status == CompositionStatus.NONCOMPOSABLE_CONFLICT:
            blockers.add("PROOF_CONTEXT_NONCOMPOSABLE")
        elif composition_status in {
            CompositionStatus.COMPOSITION_UNKNOWN,
            CompositionStatus.UNSUPPORTED_CONSTRAINT_THEORY,
        }:
            unknowns.add("PROOF_CONTEXT_COMPOSITION_UNRESOLVED")

        if not route_guarantee_met:
            blockers.add("ROUTE_GUARANTEE_NOT_MET")

        if continuation.mission_revision != int(mission_revision):
            blockers.add("CONTINUATION_MISSION_MISMATCH")
        if not continuation.supports_executable_horizon(horizon):
            blockers.add("CONTINUATION_HORIZON_OPEN")

        if seal_status not in {SealStatus.SEALED, SealStatus.SEALED_WITH_ACCEPTED_DEBT}:
            blockers.add("PLAN_SEAL_NOT_CURRENT")

        debts = set(_canon(debt_refs))
        accepted_declared = set(_canon(accepted_debt_refs))
        accepted_present = tuple(sorted(debts.intersection(accepted_declared)))
        unaccepted = tuple(sorted(debts.difference(accepted_declared)))

        manifest_body = {
            "scope_ref": scope,
            "mission_revision": int(mission_revision),
            "plan_snapshot_version": int(plan_snapshot_version),
            "policy_revision": policy,
            "information_partition_revision": partition,
            "action_space_revision": actions,
            "bound_snapshot_revisions": snapshot,
            "nonanticipativity_valid": bool(nonanticipativity_valid),
            "recall_level": recall_level.value,
            "totality_mode": totality_mode.value,
            "edge_certificates_valid": bool(edge_certificates_valid),
            "shared_resource_commitments_feasible": bool(shared_resource_commitments_feasible),
            "information_capability_preserved": bool(information_capability_preserved),
            "reaction_class": reaction_class.value,
            "required_reaction_class": required_reaction_class.value,
            "preparedness_level": prep,
            "required_preparedness_level": required_prep,
            "composition_status": composition_status.value,
            "route_guarantee_met": bool(route_guarantee_met),
            "continuation_revision": continuation.revision_id,
            "continuation_terminal_semantics": continuation.terminal_semantics.value,
            "requested_horizon": horizon,
            "seal_status": seal_status.value,
        }
        manifest = ExecutabilityClosureManifest(
            scope_ref=scope,
            mission_revision=int(mission_revision),
            plan_snapshot_version=int(plan_snapshot_version),
            policy_revision=policy,
            information_partition_revision=partition,
            action_space_revision=actions,
            bound_snapshot_revisions=snapshot,
            nonanticipativity_valid=bool(nonanticipativity_valid),
            recall_level=recall_level,
            totality_mode=totality_mode,
            edge_certificates_valid=bool(edge_certificates_valid),
            shared_resource_commitments_feasible=bool(shared_resource_commitments_feasible),
            information_capability_preserved=bool(information_capability_preserved),
            reaction_class=reaction_class,
            required_reaction_class=required_reaction_class,
            preparedness_level=prep,
            required_preparedness_level=required_prep,
            composition_status=composition_status,
            route_guarantee_met=bool(route_guarantee_met),
            continuation_revision=continuation.revision_id,
            continuation_terminal_semantics=continuation.terminal_semantics.value,
            requested_horizon=horizon,
            seal_status=seal_status,
            canonical_digest=digest(manifest_body),
        )

        blocker_tuple = tuple(sorted(blockers))
        unknown_tuple = tuple(sorted(unknowns))
        if blocker_tuple:
            status = ExecutabilityStatus.EXEC_NOT_EXECUTABLE
        elif unknown_tuple:
            status = ExecutabilityStatus.EXEC_UNKNOWN
        elif unaccepted:
            status = ExecutabilityStatus.EXEC_PARTIAL
        elif accepted_present:
            status = ExecutabilityStatus.EXEC_BOUNDED_WITH_ACCEPTED_DEBT
        else:
            status = ExecutabilityStatus.EXEC_BOUNDED

        assessment_body = {
            "assessment_id": _required("assessment_id", assessment_id),
            "revision_id": _required("revision_id", revision_id),
            "scope_ref": scope,
            "closure_manifest_digest": manifest.canonical_digest,
            "status": status.value,
            "blockers": blocker_tuple,
            "unknowns": unknown_tuple,
            "accepted_debt_refs": accepted_present,
            "unaccepted_debt_refs": unaccepted,
        }
        return PolicyExecutabilityAssessment(
            assessment_id=assessment_body["assessment_id"],
            revision_id=assessment_body["revision_id"],
            scope_ref=scope,
            closure_manifest=manifest,
            status=status,
            blockers=blocker_tuple,
            unknowns=unknown_tuple,
            accepted_debt_refs=accepted_present,
            unaccepted_debt_refs=unaccepted,
            canonical_digest=digest(assessment_body),
        )
