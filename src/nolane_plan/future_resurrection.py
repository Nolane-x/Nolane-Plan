from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable

from .hashing import digest


class FutureResurrectionError(ValueError):
    pass


def _required(name: str, value: object) -> str:
    text = str(value).strip()
    if not text:
        raise FutureResurrectionError(f"{name} must be non-empty")
    return text


def _canon(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(sorted({str(value).strip() for value in values if str(value).strip()}))


@dataclass(frozen=True, slots=True)
class DormantBranchRevision:
    branch_id: str
    revision_id: str
    branch_digest: str
    mission_revision: str
    assumption_revision_refs: tuple[str, ...]
    evidence_revision_refs: tuple[str, ...]
    transition_model_revision: str
    temporal_feasibility_revision: str
    resource_revision_refs: tuple[str, ...]
    capability_revision_refs: tuple[str, ...]
    authority_revision_refs: tuple[str, ...]
    risk_classification: str
    resurrection_dependency_refs: tuple[str, ...]
    dormant_reason: str
    dormant_generation: int
    catastrophic_exposure: bool
    sole_hard_route: bool
    unique_hedge: bool
    information_value: float
    canonical_digest: str

    @classmethod
    def create(
        cls,
        *,
        branch_id: str,
        revision_id: str,
        branch_digest: str,
        mission_revision: str,
        assumption_revision_refs: Iterable[str],
        evidence_revision_refs: Iterable[str],
        transition_model_revision: str,
        temporal_feasibility_revision: str,
        resource_revision_refs: Iterable[str],
        capability_revision_refs: Iterable[str],
        authority_revision_refs: Iterable[str],
        risk_classification: str,
        resurrection_dependency_refs: Iterable[str],
        dormant_reason: str,
        dormant_generation: int,
        catastrophic_exposure: bool,
        sole_hard_route: bool,
        unique_hedge: bool,
        information_value: int | float,
    ) -> "DormantBranchRevision":
        generation = int(dormant_generation)
        if generation < 0:
            raise FutureResurrectionError("dormant_generation cannot be negative")
        information = float(information_value)
        if information < 0:
            raise FutureResurrectionError("information_value cannot be negative")
        dependencies = _canon(resurrection_dependency_refs)
        if not dependencies:
            raise FutureResurrectionError("dormant branch requires resurrection dependencies")
        body = {
            "branch_id": _required("branch_id", branch_id),
            "revision_id": _required("revision_id", revision_id),
            "branch_digest": _required("branch_digest", branch_digest),
            "mission_revision": _required("mission_revision", mission_revision),
            "assumption_revision_refs": _canon(assumption_revision_refs),
            "evidence_revision_refs": _canon(evidence_revision_refs),
            "transition_model_revision": _required("transition_model_revision", transition_model_revision),
            "temporal_feasibility_revision": _required("temporal_feasibility_revision", temporal_feasibility_revision),
            "resource_revision_refs": _canon(resource_revision_refs),
            "capability_revision_refs": _canon(capability_revision_refs),
            "authority_revision_refs": _canon(authority_revision_refs),
            "risk_classification": _required("risk_classification", risk_classification),
            "resurrection_dependency_refs": dependencies,
            "dormant_reason": _required("dormant_reason", dormant_reason),
            "dormant_generation": generation,
            "catastrophic_exposure": bool(catastrophic_exposure),
            "sole_hard_route": bool(sole_hard_route),
            "unique_hedge": bool(unique_hedge),
            "information_value": information,
        }
        return cls(**body, canonical_digest=digest(body))

    @property
    def probability_prunable(self) -> bool:
        return not (
            self.catastrophic_exposure
            or self.sole_hard_route
            or self.unique_hedge
            or self.information_value > 0
        )


class ResurrectionStatus(str, Enum):
    READY = "READY"
    STALE = "STALE"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class BranchResurrectionAssessment:
    dormant_branch_digest: str
    status: ResurrectionStatus
    stale_dimensions: tuple[str, ...]
    blocker_refs: tuple[str, ...]
    canonical_digest: str

    @property
    def can_resurrect(self) -> bool:
        return self.status is ResurrectionStatus.READY


class BranchResurrectionEvaluator:
    @staticmethod
    def evaluate(
        *,
        dormant_branch: DormantBranchRevision,
        current_mission_revision: str,
        current_assumption_revision_refs: Iterable[str],
        current_evidence_revision_refs: Iterable[str],
        current_transition_model_revision: str,
        current_temporal_feasibility_revision: str,
        current_resource_revision_refs: Iterable[str],
        current_capability_revision_refs: Iterable[str],
        current_authority_revision_refs: Iterable[str],
        current_risk_classification: str,
        trigger_dependency_refs: Iterable[str],
        dependencies_observable: bool,
    ) -> BranchResurrectionAssessment:
        if not dependencies_observable:
            body = {
                "dormant_branch_digest": dormant_branch.canonical_digest,
                "status": ResurrectionStatus.UNKNOWN.value,
                "stale_dimensions": (),
                "blocker_refs": ("resurrection_dependencies_not_observable",),
            }
            return BranchResurrectionAssessment(
                dormant_branch_digest=body["dormant_branch_digest"],
                status=ResurrectionStatus.UNKNOWN,
                stale_dimensions=(),
                blocker_refs=body["blocker_refs"],
                canonical_digest=digest(body),
            )

        stale: list[str] = []
        if _required("current_mission_revision", current_mission_revision) != dormant_branch.mission_revision:
            stale.append("mission_revision")
        if _canon(current_assumption_revision_refs) != dormant_branch.assumption_revision_refs:
            stale.append("assumption_revisions")
        if _canon(current_evidence_revision_refs) != dormant_branch.evidence_revision_refs:
            stale.append("evidence_revisions")
        if _required("current_transition_model_revision", current_transition_model_revision) != dormant_branch.transition_model_revision:
            stale.append("transition_model_revision")
        if _required("current_temporal_feasibility_revision", current_temporal_feasibility_revision) != dormant_branch.temporal_feasibility_revision:
            stale.append("temporal_feasibility_revision")
        if _canon(current_resource_revision_refs) != dormant_branch.resource_revision_refs:
            stale.append("resource_revisions")
        if _canon(current_capability_revision_refs) != dormant_branch.capability_revision_refs:
            stale.append("capability_revisions")
        if _canon(current_authority_revision_refs) != dormant_branch.authority_revision_refs:
            stale.append("authority_revisions")
        if _required("current_risk_classification", current_risk_classification) != dormant_branch.risk_classification:
            stale.append("risk_classification")
        if _canon(trigger_dependency_refs) != dormant_branch.resurrection_dependency_refs:
            stale.append("resurrection_dependencies")

        status = ResurrectionStatus.STALE if stale else ResurrectionStatus.READY
        blockers = tuple(f"stale:{dimension}" for dimension in stale)
        body = {
            "dormant_branch_digest": dormant_branch.canonical_digest,
            "status": status.value,
            "stale_dimensions": tuple(stale),
            "blocker_refs": blockers,
        }
        return BranchResurrectionAssessment(
            dormant_branch_digest=body["dormant_branch_digest"],
            status=status,
            stale_dimensions=body["stale_dimensions"],
            blocker_refs=blockers,
            canonical_digest=digest(body),
        )
