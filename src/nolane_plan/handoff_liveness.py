from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable

from .hashing import digest


class HandoffLivenessError(ValueError):
    pass


def _required(name: str, value: object) -> str:
    text = str(value).strip()
    if not text:
        raise HandoffLivenessError(f"{name} must be non-empty")
    return text


def _nonnegative(name: str, value: int | float) -> float:
    number = float(value)
    if number < 0:
        raise HandoffLivenessError(f"{name} must be non-negative")
    return number


def _nonnegative_int(name: str, value: int) -> int:
    number = int(value)
    if number < 0:
        raise HandoffLivenessError(f"{name} must be non-negative")
    return number


def _canon(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(sorted({str(value).strip() for value in values if str(value).strip()}))


@dataclass(frozen=True, slots=True)
class ContinuationProgressRank:
    rank_id: str
    revision_id: str
    continuation_scope: str
    mission_revision: str
    unresolved_critical_debt_count: int
    remaining_unprepared_boundaries: int
    absolute_executable_horizon: float
    minimum_preparedness_at_next_boundary: int
    remaining_synthesis_workload: float
    reaction_refinement_slack: float
    mission_distance_measure: float
    semantic_continuation_digest: str
    debt_equivalence_refs: tuple[str, ...]
    created_at: float
    canonical_digest: str

    @classmethod
    def create(
        cls,
        *,
        rank_id: str,
        revision_id: str,
        continuation_scope: str,
        mission_revision: str,
        unresolved_critical_debt_count: int,
        remaining_unprepared_boundaries: int,
        absolute_executable_horizon: int | float,
        minimum_preparedness_at_next_boundary: int,
        remaining_synthesis_workload: int | float,
        reaction_refinement_slack: int | float,
        mission_distance_measure: int | float,
        semantic_continuation_digest: str,
        debt_equivalence_refs: Iterable[str] = (),
        created_at: int | float = 0.0,
    ) -> "ContinuationProgressRank":
        debt_count = _nonnegative_int("unresolved_critical_debt_count", unresolved_critical_debt_count)
        boundaries = _nonnegative_int("remaining_unprepared_boundaries", remaining_unprepared_boundaries)
        preparedness = int(minimum_preparedness_at_next_boundary)
        if preparedness < 0 or preparedness > 5:
            raise HandoffLivenessError("minimum preparedness must be within P0..P5")
        body = {
            "rank_id": _required("rank_id", rank_id),
            "revision_id": _required("revision_id", revision_id),
            "continuation_scope": _required("continuation_scope", continuation_scope),
            "mission_revision": _required("mission_revision", mission_revision),
            "unresolved_critical_debt_count": debt_count,
            "remaining_unprepared_boundaries": boundaries,
            "absolute_executable_horizon": _nonnegative("absolute_executable_horizon", absolute_executable_horizon),
            "minimum_preparedness_at_next_boundary": preparedness,
            "remaining_synthesis_workload": _nonnegative("remaining_synthesis_workload", remaining_synthesis_workload),
            "reaction_refinement_slack": float(reaction_refinement_slack),
            "mission_distance_measure": _nonnegative("mission_distance_measure", mission_distance_measure),
            "semantic_continuation_digest": _required("semantic_continuation_digest", semantic_continuation_digest),
            "debt_equivalence_refs": _canon(debt_equivalence_refs),
            "created_at": _nonnegative("created_at", created_at),
        }
        return cls(**body, canonical_digest=digest(body))


@dataclass(frozen=True, slots=True)
class HandoffProgressPolicy:
    policy_id: str
    revision_id: str
    max_handoff_count: int
    max_total_deferral_time: float
    minimum_horizon_advance: float
    minimum_debt_reduction_rate: int
    mandatory_preparedness_floor_by_time: tuple[tuple[float, int], ...]
    bounded_stutter_allowance: int
    recovery_stutter_allowance: int
    absolute_latest_safe_refinement_time: float
    temporal_authority_ref: str
    canonical_digest: str

    @classmethod
    def create(
        cls,
        *,
        policy_id: str,
        revision_id: str,
        max_handoff_count: int,
        max_total_deferral_time: int | float,
        minimum_horizon_advance: int | float,
        minimum_debt_reduction_rate: int,
        mandatory_preparedness_floor_by_time: Iterable[tuple[int | float, int]],
        bounded_stutter_allowance: int,
        recovery_stutter_allowance: int,
        absolute_latest_safe_refinement_time: int | float,
        temporal_authority_ref: str,
    ) -> "HandoffProgressPolicy":
        floors: list[tuple[float, int]] = []
        last_time = -1.0
        for raw_time, raw_level in mandatory_preparedness_floor_by_time:
            at = _nonnegative("preparedness floor time", raw_time)
            level = int(raw_level)
            if level < 0 or level > 5:
                raise HandoffLivenessError("preparedness floor must be within P0..P5")
            if at <= last_time:
                raise HandoffLivenessError("preparedness floor schedule must be strictly increasing")
            floors.append((at, level))
            last_time = at
        body = {
            "policy_id": _required("policy_id", policy_id),
            "revision_id": _required("revision_id", revision_id),
            "max_handoff_count": _nonnegative_int("max_handoff_count", max_handoff_count),
            "max_total_deferral_time": _nonnegative("max_total_deferral_time", max_total_deferral_time),
            "minimum_horizon_advance": _nonnegative("minimum_horizon_advance", minimum_horizon_advance),
            "minimum_debt_reduction_rate": _nonnegative_int("minimum_debt_reduction_rate", minimum_debt_reduction_rate),
            "mandatory_preparedness_floor_by_time": tuple(floors),
            "bounded_stutter_allowance": _nonnegative_int("bounded_stutter_allowance", bounded_stutter_allowance),
            "recovery_stutter_allowance": _nonnegative_int("recovery_stutter_allowance", recovery_stutter_allowance),
            "absolute_latest_safe_refinement_time": _nonnegative(
                "absolute_latest_safe_refinement_time", absolute_latest_safe_refinement_time
            ),
            "temporal_authority_ref": _required("temporal_authority_ref", temporal_authority_ref),
        }
        return cls(**body, canonical_digest=digest(body))

    def preparedness_floor_at(self, instant: int | float) -> int:
        now = float(instant)
        floor = 0
        for at, level in self.mandatory_preparedness_floor_by_time:
            if now >= at:
                floor = max(floor, level)
        return floor


class HandoffProgressStatus(str, Enum):
    STRICT_PROGRESS = "STRICT_PROGRESS"
    BOUNDED_STUTTER = "BOUNDED_STUTTER"
    RECOVERY_STUTTER = "RECOVERY_STUTTER"
    NO_PROGRESS = "NO_PROGRESS"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class HandoffLivenessCertificate:
    certificate_id: str
    revision_id: str
    source_continuation_ref: str
    successor_continuation_ref: str
    old_rank_digest: str
    new_rank_digest: str
    progress_policy_digest: str
    handoff_count: int
    ordinary_stutter_count: int
    recovery_stutter_count: int
    total_deferral_time: float
    recursive_feasibility: bool | None
    information_available_by_deadline: bool
    recovery_mode: bool
    temporal_authority_revision_ref: str
    current_time: float
    debt_lineage_equivalent: bool
    progress_dimensions: tuple[str, ...]
    blocker_refs: tuple[str, ...]
    status: HandoffProgressStatus
    canonical_digest: str

    @property
    def supports_safe_handoff(self) -> bool:
        return self.status in {
            HandoffProgressStatus.STRICT_PROGRESS,
            HandoffProgressStatus.BOUNDED_STUTTER,
            HandoffProgressStatus.RECOVERY_STUTTER,
        }


class HandoffLivenessEvaluator:
    @staticmethod
    def deadline_revision_is_grounded(
        *,
        old_policy: HandoffProgressPolicy,
        new_policy: HandoffProgressPolicy,
        temporal_authority_revision_ref: str,
    ) -> bool:
        authority = str(temporal_authority_revision_ref).strip()
        if new_policy.absolute_latest_safe_refinement_time <= old_policy.absolute_latest_safe_refinement_time:
            return True
        return (
            bool(authority)
            and authority == new_policy.temporal_authority_ref
            and authority != old_policy.temporal_authority_ref
        )

    @staticmethod
    def _progress_dimensions(
        old: ContinuationProgressRank,
        new: ContinuationProgressRank,
        policy: HandoffProgressPolicy,
        *,
        debt_lineage_equivalent: bool,
    ) -> tuple[str, ...]:
        progress: list[str] = []
        debt_reduction = old.unresolved_critical_debt_count - new.unresolved_critical_debt_count
        if debt_lineage_equivalent and debt_reduction >= policy.minimum_debt_reduction_rate and debt_reduction > 0:
            progress.append("critical_debt_reduced")
        if new.remaining_unprepared_boundaries < old.remaining_unprepared_boundaries:
            progress.append("unprepared_boundaries_reduced")
        horizon_advance = new.absolute_executable_horizon - old.absolute_executable_horizon
        if horizon_advance >= policy.minimum_horizon_advance and horizon_advance > 0:
            progress.append("absolute_executable_horizon_advanced")
        if new.minimum_preparedness_at_next_boundary > old.minimum_preparedness_at_next_boundary:
            progress.append("next_boundary_preparedness_improved")
        if new.remaining_synthesis_workload < old.remaining_synthesis_workload:
            progress.append("remaining_synthesis_workload_reduced")
        if new.mission_distance_measure < old.mission_distance_measure:
            progress.append("mission_distance_reduced")
        return tuple(progress)

    @classmethod
    def evaluate(
        cls,
        *,
        certificate_id: str,
        revision_id: str,
        source_continuation_ref: str,
        successor_continuation_ref: str,
        old_rank: ContinuationProgressRank,
        new_rank: ContinuationProgressRank,
        progress_policy: HandoffProgressPolicy,
        handoff_count: int,
        ordinary_stutter_count: int,
        recovery_stutter_count: int,
        total_deferral_time: int | float,
        recursive_feasibility: bool | None,
        information_available_by_deadline: bool,
        recovery_mode: bool,
        temporal_authority_revision_ref: str,
        current_time: int | float,
        debt_lineage_equivalent: bool,
    ) -> HandoffLivenessCertificate:
        if old_rank.continuation_scope != new_rank.continuation_scope:
            raise HandoffLivenessError("handoff ranks must share continuation scope")
        if old_rank.mission_revision != new_rank.mission_revision:
            raise HandoffLivenessError("handoff ranks must share mission revision")
        handoffs = _nonnegative_int("handoff_count", handoff_count)
        ordinary_stutters = _nonnegative_int("ordinary_stutter_count", ordinary_stutter_count)
        recovery_stutters = _nonnegative_int("recovery_stutter_count", recovery_stutter_count)
        deferral = _nonnegative("total_deferral_time", total_deferral_time)
        now = _nonnegative("current_time", current_time)
        authority = _required("temporal_authority_revision_ref", temporal_authority_revision_ref)

        blockers: list[str] = []
        progress = cls._progress_dimensions(
            old_rank,
            new_rank,
            progress_policy,
            debt_lineage_equivalent=bool(debt_lineage_equivalent),
        )
        rank_regression_blockers: list[str] = []
        if new_rank.unresolved_critical_debt_count > old_rank.unresolved_critical_debt_count:
            rank_regression_blockers.append("critical_debt_regressed")
        if new_rank.remaining_synthesis_workload > old_rank.remaining_synthesis_workload:
            rank_regression_blockers.append("remaining_synthesis_workload_regressed")

        if recursive_feasibility is not True:
            status = HandoffProgressStatus.UNKNOWN
            blockers.append("recursive_feasibility_not_proven")
        elif not information_available_by_deadline:
            status = HandoffProgressStatus.UNKNOWN
            blockers.append("information_not_available_by_deadline")
        elif authority != progress_policy.temporal_authority_ref:
            status = HandoffProgressStatus.UNKNOWN
            blockers.append("temporal_authority_revision_mismatch")
        elif handoffs > progress_policy.max_handoff_count:
            status = HandoffProgressStatus.NO_PROGRESS
            blockers.append("handoff_budget_exhausted")
        elif deferral > progress_policy.max_total_deferral_time:
            status = HandoffProgressStatus.NO_PROGRESS
            blockers.append("total_deferral_budget_exhausted")
        elif now > progress_policy.absolute_latest_safe_refinement_time:
            status = HandoffProgressStatus.NO_PROGRESS
            blockers.append("absolute_refinement_deadline_missed")
        elif new_rank.minimum_preparedness_at_next_boundary < progress_policy.preparedness_floor_at(now):
            status = HandoffProgressStatus.NO_PROGRESS
            blockers.append("mandatory_preparedness_floor_missed")
        elif rank_regression_blockers:
            status = HandoffProgressStatus.NO_PROGRESS
            blockers.append("progress_rank_regression")
            blockers.extend(rank_regression_blockers)
        elif progress:
            status = HandoffProgressStatus.STRICT_PROGRESS
        elif recovery_mode:
            if recovery_stutters < progress_policy.recovery_stutter_allowance:
                status = HandoffProgressStatus.RECOVERY_STUTTER
            else:
                status = HandoffProgressStatus.NO_PROGRESS
                blockers.append("recovery_stutter_budget_exhausted")
        elif ordinary_stutters < progress_policy.bounded_stutter_allowance:
            status = HandoffProgressStatus.BOUNDED_STUTTER
        else:
            status = HandoffProgressStatus.NO_PROGRESS
            blockers.append("ordinary_stutter_budget_exhausted")

        body = {
            "certificate_id": _required("certificate_id", certificate_id),
            "revision_id": _required("revision_id", revision_id),
            "source_continuation_ref": _required("source_continuation_ref", source_continuation_ref),
            "successor_continuation_ref": _required("successor_continuation_ref", successor_continuation_ref),
            "old_rank_digest": old_rank.canonical_digest,
            "new_rank_digest": new_rank.canonical_digest,
            "progress_policy_digest": progress_policy.canonical_digest,
            "handoff_count": handoffs,
            "ordinary_stutter_count": ordinary_stutters,
            "recovery_stutter_count": recovery_stutters,
            "total_deferral_time": deferral,
            "recursive_feasibility": recursive_feasibility,
            "information_available_by_deadline": bool(information_available_by_deadline),
            "recovery_mode": bool(recovery_mode),
            "temporal_authority_revision_ref": authority,
            "current_time": now,
            "debt_lineage_equivalent": bool(debt_lineage_equivalent),
            "progress_dimensions": progress,
            "blocker_refs": tuple(blockers),
            "status": status.value,
        }
        return HandoffLivenessCertificate(
            certificate_id=body["certificate_id"],
            revision_id=body["revision_id"],
            source_continuation_ref=body["source_continuation_ref"],
            successor_continuation_ref=body["successor_continuation_ref"],
            old_rank_digest=body["old_rank_digest"],
            new_rank_digest=body["new_rank_digest"],
            progress_policy_digest=body["progress_policy_digest"],
            handoff_count=handoffs,
            ordinary_stutter_count=ordinary_stutters,
            recovery_stutter_count=recovery_stutters,
            total_deferral_time=deferral,
            recursive_feasibility=recursive_feasibility,
            information_available_by_deadline=bool(information_available_by_deadline),
            recovery_mode=bool(recovery_mode),
            temporal_authority_revision_ref=authority,
            current_time=now,
            debt_lineage_equivalent=bool(debt_lineage_equivalent),
            progress_dimensions=progress,
            blocker_refs=tuple(blockers),
            status=status,
            canonical_digest=digest(body),
        )
