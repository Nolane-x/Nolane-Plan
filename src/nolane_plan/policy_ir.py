from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

from .hashing import digest
from .policy_information import NonAnticipativityAssessment
from .resources import SharedCommitment


def _canon(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(sorted({str(value).strip() for value in values if str(value).strip()}))


def _required(name: str, value: object) -> str:
    text = str(value).strip()
    if not text:
        raise ValueError(f"{name} must be non-empty")
    return text


@dataclass(frozen=True, slots=True)
class PolicySuccessorRoute:
    guard_ref: str
    reveal_event_ref: str
    child_policy_node_revision: str

    def __post_init__(self) -> None:
        _required("guard_ref", self.guard_ref)
        _required("reveal_event_ref", self.reveal_event_ref)
        _required("child_policy_node_revision", self.child_policy_node_revision)


@dataclass(frozen=True, slots=True)
class PolicyNodeRevision:
    policy_node_id: str
    revision_id: str
    mission_revision: int
    decision_principal_ref: str
    plan_snapshot_version: int
    strategic_location_revision: int
    information_partition_revision: str
    decision_epoch_ref: str
    action_space_revision: str
    candidate_action_contracts: tuple[str, ...]
    execution_principal_requirement_or_set: tuple[str, ...]
    selected_action_contract_or_policy_set: tuple[str, ...]
    runtime_guard_refs: tuple[str, ...]
    observation_frontier_revision: str
    successor_policy_mapping: tuple[PolicySuccessorRoute, ...]
    shared_commitment_refs: tuple[str, ...]
    resource_reservation_refs: tuple[str, ...]
    obligation_basis_ref: str
    risk_policy_revision: str
    authority_profile_requirement: str
    route_guarantee_requirement: str
    preparedness_level: str
    proof_context_ref: str
    assurance_profile: str
    debt_refs: tuple[str, ...]
    sealed: bool
    canonical_digest: str

    @classmethod
    def create(
        cls,
        *,
        policy_node_id: str,
        revision_id: str,
        mission_revision: int,
        decision_principal_ref: str,
        plan_snapshot_version: int,
        strategic_location_revision: int,
        information_partition_revision: str,
        decision_epoch_ref: str,
        action_space_revision: str,
        candidate_action_contracts: Iterable[str],
        execution_principal_requirement_or_set: Iterable[str],
        selected_action_contract_or_policy_set: Iterable[str],
        runtime_guard_refs: Iterable[str],
        observation_frontier_revision: str,
        successor_policy_mapping: Iterable[PolicySuccessorRoute],
        shared_commitment_refs: Iterable[str],
        resource_reservation_refs: Iterable[str],
        obligation_basis_ref: str,
        risk_policy_revision: str,
        authority_profile_requirement: str,
        route_guarantee_requirement: str,
        preparedness_level: str,
        proof_context_ref: str,
        assurance_profile: str,
        debt_refs: Iterable[str],
        sealed: bool,
    ) -> "PolicyNodeRevision":
        if int(mission_revision) < 1 or int(plan_snapshot_version) < 1 or int(strategic_location_revision) < 1:
            raise ValueError("policy node version fields must be positive")
        candidates = _canon(candidate_action_contracts)
        selected = _canon(selected_action_contract_or_policy_set)
        principals = _canon(execution_principal_requirement_or_set)
        if not candidates:
            raise ValueError("policy node requires at least one candidate action contract")
        if not selected:
            raise ValueError("policy node requires a selected action contract or policy set")
        unknown_selected = set(selected).difference(candidates)
        if unknown_selected:
            raise ValueError(f"selected action is outside candidate contracts: {sorted(unknown_selected)!r}")
        if not principals:
            raise ValueError("policy node requires an execution-principal requirement")

        routes = tuple(sorted(tuple(successor_policy_mapping), key=lambda item: item.guard_ref))
        guard_refs = tuple(route.guard_ref for route in routes)
        if len(guard_refs) != len(set(guard_refs)):
            raise ValueError("successor policy guards must be unique")

        body = {
            "policy_node_id": _required("policy_node_id", policy_node_id),
            "revision_id": _required("revision_id", revision_id),
            "mission_revision": int(mission_revision),
            "decision_principal_ref": _required("decision_principal_ref", decision_principal_ref),
            "plan_snapshot_version": int(plan_snapshot_version),
            "strategic_location_revision": int(strategic_location_revision),
            "information_partition_revision": _required("information_partition_revision", information_partition_revision),
            "decision_epoch_ref": _required("decision_epoch_ref", decision_epoch_ref),
            "action_space_revision": _required("action_space_revision", action_space_revision),
            "candidate_action_contracts": candidates,
            "execution_principal_requirement_or_set": principals,
            "selected_action_contract_or_policy_set": selected,
            "runtime_guard_refs": _canon(runtime_guard_refs),
            "observation_frontier_revision": _required("observation_frontier_revision", observation_frontier_revision),
            "successor_policy_mapping": tuple(
                (route.guard_ref, route.reveal_event_ref, route.child_policy_node_revision) for route in routes
            ),
            "shared_commitment_refs": _canon(shared_commitment_refs),
            "resource_reservation_refs": _canon(resource_reservation_refs),
            "obligation_basis_ref": _required("obligation_basis_ref", obligation_basis_ref),
            "risk_policy_revision": _required("risk_policy_revision", risk_policy_revision),
            "authority_profile_requirement": _required("authority_profile_requirement", authority_profile_requirement),
            "route_guarantee_requirement": _required("route_guarantee_requirement", route_guarantee_requirement),
            "preparedness_level": _required("preparedness_level", preparedness_level),
            "proof_context_ref": _required("proof_context_ref", proof_context_ref),
            "assurance_profile": _required("assurance_profile", assurance_profile),
            "debt_refs": _canon(debt_refs),
            "sealed": bool(sealed),
        }
        digest_value = digest(body)
        return cls(
            policy_node_id=body["policy_node_id"],
            revision_id=body["revision_id"],
            mission_revision=body["mission_revision"],
            decision_principal_ref=body["decision_principal_ref"],
            plan_snapshot_version=body["plan_snapshot_version"],
            strategic_location_revision=body["strategic_location_revision"],
            information_partition_revision=body["information_partition_revision"],
            decision_epoch_ref=body["decision_epoch_ref"],
            action_space_revision=body["action_space_revision"],
            candidate_action_contracts=candidates,
            execution_principal_requirement_or_set=principals,
            selected_action_contract_or_policy_set=selected,
            runtime_guard_refs=body["runtime_guard_refs"],
            observation_frontier_revision=body["observation_frontier_revision"],
            successor_policy_mapping=routes,
            shared_commitment_refs=body["shared_commitment_refs"],
            resource_reservation_refs=body["resource_reservation_refs"],
            obligation_basis_ref=body["obligation_basis_ref"],
            risk_policy_revision=body["risk_policy_revision"],
            authority_profile_requirement=body["authority_profile_requirement"],
            route_guarantee_requirement=body["route_guarantee_requirement"],
            preparedness_level=body["preparedness_level"],
            proof_context_ref=body["proof_context_ref"],
            assurance_profile=body["assurance_profile"],
            debt_refs=body["debt_refs"],
            sealed=body["sealed"],
            canonical_digest=digest_value,
        )


@dataclass(frozen=True, slots=True)
class PolicyCoherenceAssessment:
    valid: bool
    policy_node_revisions: tuple[str, ...]
    required_policy_scope: tuple[str, ...]
    branch_route_viability: tuple[tuple[str, bool], ...]
    nonanticipativity_assessment_digest: str
    blockers: tuple[str, ...]
    assessment_digest: str


class PolicyCoherenceEvaluator:
    @staticmethod
    def _exclusive_conflict(left: SharedCommitment, right: SharedCommitment) -> bool:
        return (
            left.resource_id == right.resource_id
            and left.overlaps(right)
            and (left.exclusive or right.exclusive)
        )

    @staticmethod
    def _mutually_exclusive(
        left_branch: str,
        right_branch: str,
        groups: tuple[frozenset[str], ...],
    ) -> bool:
        if left_branch == right_branch:
            return False
        return any(left_branch in group and right_branch in group for group in groups)

    @classmethod
    def evaluate(
        cls,
        *,
        policy_nodes: Iterable[PolicyNodeRevision],
        nonanticipativity: NonAnticipativityAssessment,
        branch_route_viability: Mapping[str, bool],
        pre_reveal_commitments: Mapping[str, Iterable[SharedCommitment]],
        required_policy_scope: Iterable[str],
        post_reveal_commitments: Mapping[str, Iterable[SharedCommitment]] | None = None,
        mutually_exclusive_branches: Iterable[frozenset[str]] = (),
    ) -> PolicyCoherenceAssessment:
        nodes = tuple(policy_nodes)
        if not nodes:
            raise ValueError("policy coherence requires at least one policy node")
        scope = _canon(required_policy_scope)
        if not scope:
            raise ValueError("policy coherence requires a non-empty policy scope")
        blockers: set[str] = set()

        node_principals = {node.decision_principal_ref for node in nodes}
        node_partitions = {node.information_partition_revision for node in nodes}
        if node_principals != {nonanticipativity.decision_principal_ref}:
            blockers.add("POLICY_PRINCIPAL_SCOPE_MISMATCH")
        if node_partitions != {nonanticipativity.partition_revision}:
            blockers.add("POLICY_INFORMATION_PARTITION_MISMATCH")
        if not nonanticipativity.valid:
            blockers.add("NONANTICIPATIVE_POLICY_REQUIRED")

        viability = tuple(sorted((branch, bool(branch_route_viability.get(branch, False))) for branch in scope))
        if any(not is_viable for _, is_viable in viability):
            blockers.add("POLICY_SCOPE_ROUTE_GAP")

        pre_rows: list[tuple[str, SharedCommitment]] = []
        for branch in scope:
            pre_rows.extend((branch, commitment) for commitment in pre_reveal_commitments.get(branch, ()))
        for index, (left_branch, left) in enumerate(pre_rows):
            for right_branch, right in pre_rows[index + 1 :]:
                if cls._exclusive_conflict(left, right):
                    blockers.add("SHARED_COMMITMENT_CONFLICT")

        groups = tuple(frozenset(group) for group in mutually_exclusive_branches)
        post_rows: list[tuple[str, SharedCommitment]] = []
        for branch, commitments in (post_reveal_commitments or {}).items():
            if branch not in scope:
                continue
            post_rows.extend((branch, commitment) for commitment in commitments)
        for index, (left_branch, left) in enumerate(post_rows):
            for right_branch, right in post_rows[index + 1 :]:
                if cls._mutually_exclusive(left_branch, right_branch, groups):
                    continue
                if cls._exclusive_conflict(left, right):
                    blockers.add("SHARED_COMMITMENT_CONFLICT")

        node_revisions = tuple(sorted(node.revision_id for node in nodes))
        blocker_tuple = tuple(sorted(blockers))
        body = {
            "policy_node_revisions": node_revisions,
            "required_policy_scope": scope,
            "branch_route_viability": viability,
            "nonanticipativity_assessment_digest": nonanticipativity.assessment_digest,
            "blockers": blocker_tuple,
        }
        return PolicyCoherenceAssessment(
            valid=not blocker_tuple,
            policy_node_revisions=node_revisions,
            required_policy_scope=scope,
            branch_route_viability=viability,
            nonanticipativity_assessment_digest=nonanticipativity.assessment_digest,
            blockers=blocker_tuple,
            assessment_digest=digest(body),
        )


@dataclass(frozen=True, slots=True)
class ContingentPolicyCertificate:
    certificate_id: str
    revision_id: str
    policy_node_revisions: tuple[str, ...]
    mission_revision: int
    information_partition_revision: str
    action_space_revision: str
    proof_context_ref: str
    route_guarantee: str
    preparedness_floor: str
    coherence_assessment_digest: str
    created_sequence: int
    validity_regime: str
    status: str
    canonical_digest: str

    @classmethod
    def issue(
        cls,
        *,
        certificate_id: str,
        revision_id: str,
        policy_node_revisions: Iterable[str],
        mission_revision: int,
        information_partition_revision: str,
        action_space_revision: str,
        proof_context_ref: str,
        route_guarantee: str,
        preparedness_floor: str,
        coherence: PolicyCoherenceAssessment,
        created_sequence: int,
        validity_regime: str,
    ) -> "ContingentPolicyCertificate":
        if not coherence.valid:
            raise ValueError("contingent policy certificate requires a valid policy coherence assessment")
        if int(mission_revision) < 1 or int(created_sequence) < 0:
            raise ValueError("certificate mission revision must be positive and sequence non-negative")
        nodes = _canon(policy_node_revisions)
        if not nodes:
            raise ValueError("contingent policy certificate requires policy nodes")
        if set(nodes) != set(coherence.policy_node_revisions):
            raise ValueError("certificate policy nodes do not match coherence assessment")
        body = {
            "certificate_id": _required("certificate_id", certificate_id),
            "revision_id": _required("revision_id", revision_id),
            "policy_node_revisions": nodes,
            "mission_revision": int(mission_revision),
            "information_partition_revision": _required("information_partition_revision", information_partition_revision),
            "action_space_revision": _required("action_space_revision", action_space_revision),
            "proof_context_ref": _required("proof_context_ref", proof_context_ref),
            "route_guarantee": _required("route_guarantee", route_guarantee),
            "preparedness_floor": _required("preparedness_floor", preparedness_floor),
            "coherence_assessment_digest": coherence.assessment_digest,
            "created_sequence": int(created_sequence),
            "validity_regime": _required("validity_regime", validity_regime),
            "status": "VALID",
        }
        return cls(**body, canonical_digest=digest(body))
