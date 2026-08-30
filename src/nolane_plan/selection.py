from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
from math import isfinite
from typing import Iterable, Mapping

from .hashing import digest


def _canon(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(sorted({str(value).strip() for value in values if str(value).strip()}))


def _required(name: str, value: object) -> str:
    text = str(value).strip()
    if not text:
        raise ValueError(f"{name} must be non-empty")
    return text


class SelectionStatus(str, Enum):
    ADVISORY = "advisory"
    STALE = "stale"
    SUPERSEDED = "superseded"


@dataclass(frozen=True, slots=True)
class CandidateAdmissibility:
    action_ref: str
    hard_admissible: bool
    rejection_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        _required("action_ref", self.action_ref)
        if self.hard_admissible and self.rejection_codes:
            raise ValueError("hard-admissible candidate cannot carry hard rejection codes")
        if not self.hard_admissible and not self.rejection_codes:
            raise ValueError("hard-rejected candidate requires an explicit rejection code")


@dataclass(frozen=True, slots=True)
class SelectionTransaction:
    transaction_id: str
    plan_snapshot_version: int
    mission_revision: int
    decision_principal_ref: str
    principal_information_access_profile_revision: str
    information_partition_revision: str
    decision_epoch_ref: str
    action_space_revision: str
    candidate_action_refs: tuple[str, ...]
    candidate_set_digest: str
    route_guarantee_requirement: str
    measure_mode: str
    risk_policy_revision: str
    survival_profile_ref: str
    commitment_pressure_ref: str
    debt_policy_ref: str
    tie_policy: str
    dependency_generations: tuple[tuple[str, int], ...]
    canonical_digest: str

    @classmethod
    def create(
        cls,
        *,
        transaction_id: str,
        plan_snapshot_version: int,
        mission_revision: int,
        decision_principal_ref: str,
        principal_information_access_profile_revision: str,
        information_partition_revision: str,
        decision_epoch_ref: str,
        action_space_revision: str,
        candidate_action_refs: Iterable[str],
        route_guarantee_requirement: str,
        measure_mode: str,
        risk_policy_revision: str,
        survival_profile_ref: str,
        commitment_pressure_ref: str,
        debt_policy_ref: str,
        tie_policy: str,
        dependency_generations: Mapping[str, int],
    ) -> "SelectionTransaction":
        candidates = _canon(candidate_action_refs)
        if not candidates:
            raise ValueError("selection transaction requires a non-empty frozen candidate set")
        if int(plan_snapshot_version) < 1 or int(mission_revision) < 1:
            raise ValueError("selection transaction version fields must be positive")
        generations = tuple(sorted((str(domain), int(generation)) for domain, generation in dependency_generations.items()))
        if any(not domain or generation < 0 for domain, generation in generations):
            raise ValueError("dependency generation entries must be non-empty and non-negative")
        tie = _required("tie_policy", tie_policy)
        if tie != "stable-id":
            raise ValueError("reference runtime supports only deterministic stable-id tie policy")
        candidate_digest = digest({"candidate_action_refs": candidates})
        body = {
            "transaction_id": _required("transaction_id", transaction_id),
            "plan_snapshot_version": int(plan_snapshot_version),
            "mission_revision": int(mission_revision),
            "decision_principal_ref": _required("decision_principal_ref", decision_principal_ref),
            "principal_information_access_profile_revision": _required(
                "principal_information_access_profile_revision", principal_information_access_profile_revision
            ),
            "information_partition_revision": _required("information_partition_revision", information_partition_revision),
            "decision_epoch_ref": _required("decision_epoch_ref", decision_epoch_ref),
            "action_space_revision": _required("action_space_revision", action_space_revision),
            "candidate_action_refs": candidates,
            "candidate_set_digest": candidate_digest,
            "route_guarantee_requirement": _required("route_guarantee_requirement", route_guarantee_requirement),
            "measure_mode": _required("measure_mode", measure_mode),
            "risk_policy_revision": _required("risk_policy_revision", risk_policy_revision),
            "survival_profile_ref": _required("survival_profile_ref", survival_profile_ref),
            "commitment_pressure_ref": _required("commitment_pressure_ref", commitment_pressure_ref),
            "debt_policy_ref": _required("debt_policy_ref", debt_policy_ref),
            "tie_policy": tie,
            "dependency_generations": generations,
        }
        return cls(**body, canonical_digest=digest(body))


@dataclass(frozen=True, slots=True)
class SelectionRecord:
    record_id: str
    transaction_id: str
    transaction_digest: str
    candidate_set_digest: str
    decision_principal_ref: str
    information_partition_revision: str
    action_space_revision: str
    chosen_action_ref: str
    hard_admissibility_digest: str
    pareto_front: tuple[str, ...]
    score_digest: str
    tie_break_reason: str
    dependency_generations: tuple[tuple[str, int], ...]
    status: SelectionStatus
    superseded_by: str | None
    canonical_digest: str

    def status_against(self, current_generations: Mapping[str, int]) -> SelectionStatus:
        if self.status == SelectionStatus.SUPERSEDED or self.superseded_by:
            return SelectionStatus.SUPERSEDED
        for domain, bound in self.dependency_generations:
            if int(current_generations.get(domain, -1)) != bound:
                return SelectionStatus.STALE
        return SelectionStatus.ADVISORY

    def supersede(self, replacement_record_ref: str) -> "SelectionRecord":
        replacement_ref = _required("replacement_record_ref", replacement_record_ref)
        body = {
            "record_id": self.record_id,
            "transaction_id": self.transaction_id,
            "transaction_digest": self.transaction_digest,
            "candidate_set_digest": self.candidate_set_digest,
            "decision_principal_ref": self.decision_principal_ref,
            "information_partition_revision": self.information_partition_revision,
            "action_space_revision": self.action_space_revision,
            "chosen_action_ref": self.chosen_action_ref,
            "hard_admissibility_digest": self.hard_admissibility_digest,
            "pareto_front": self.pareto_front,
            "score_digest": self.score_digest,
            "tie_break_reason": self.tie_break_reason,
            "dependency_generations": self.dependency_generations,
            "status": SelectionStatus.SUPERSEDED.value,
            "superseded_by": replacement_ref,
        }
        return replace(
            self,
            status=SelectionStatus.SUPERSEDED,
            superseded_by=replacement_ref,
            canonical_digest=digest(body),
        )


class SelectionEvaluator:
    @staticmethod
    def select(
        transaction: SelectionTransaction,
        *,
        admissibility: Mapping[str, CandidateAdmissibility],
        scores: Mapping[str, float],
        pareto_front: Iterable[str],
    ) -> SelectionRecord:
        frozen = set(transaction.candidate_action_refs)
        referenced = set(admissibility).union(scores).union(pareto_front)
        outside = referenced.difference(frozen)
        if outside:
            raise ValueError(f"selection input references candidates outside the frozen transaction: {sorted(outside)!r}")

        hard_rows: list[tuple[str, bool, tuple[str, ...]]] = []
        for action_ref in transaction.candidate_action_refs:
            row = admissibility.get(action_ref)
            if row is None:
                hard_rows.append((action_ref, False, ("MISSING_HARD_ADMISSIBILITY",)))
                continue
            if row.action_ref != action_ref:
                raise ValueError("admissibility mapping key and action ref differ")
            hard_rows.append((action_ref, row.hard_admissible, tuple(sorted(row.rejection_codes))))

        admitted = {ref for ref, allowed, _ in hard_rows if allowed}
        pareto = _canon(pareto_front)
        if pareto:
            admitted.intersection_update(pareto)
        if not admitted:
            raise ValueError("no hard-admissible candidate survives the frozen selection pipeline")

        score_rows: list[tuple[str, float]] = []
        for action_ref in sorted(admitted):
            value = float(scores.get(action_ref, float("-inf")))
            if not isfinite(value):
                raise ValueError(f"candidate score must be finite: {action_ref}")
            score_rows.append((action_ref, value))
        best_score = max(score for _, score in score_rows)
        tied = sorted(action for action, score in score_rows if score == best_score)
        chosen = tied[0]
        tie_reason = transaction.tie_policy if len(tied) > 1 else "unique-best"

        hard_digest = digest(tuple(hard_rows))
        score_digest = digest(tuple(score_rows))
        record_body = {
            "transaction_id": transaction.transaction_id,
            "transaction_digest": transaction.canonical_digest,
            "candidate_set_digest": transaction.candidate_set_digest,
            "decision_principal_ref": transaction.decision_principal_ref,
            "information_partition_revision": transaction.information_partition_revision,
            "action_space_revision": transaction.action_space_revision,
            "chosen_action_ref": chosen,
            "hard_admissibility_digest": hard_digest,
            "pareto_front": pareto,
            "score_digest": score_digest,
            "tie_break_reason": tie_reason,
            "dependency_generations": transaction.dependency_generations,
            "status": SelectionStatus.ADVISORY.value,
            "superseded_by": None,
        }
        record_id = f"selection:{digest(record_body)[:24]}"
        body = {"record_id": record_id, **record_body}
        return SelectionRecord(
            record_id=record_id,
            transaction_id=transaction.transaction_id,
            transaction_digest=transaction.canonical_digest,
            candidate_set_digest=transaction.candidate_set_digest,
            decision_principal_ref=transaction.decision_principal_ref,
            information_partition_revision=transaction.information_partition_revision,
            action_space_revision=transaction.action_space_revision,
            chosen_action_ref=chosen,
            hard_admissibility_digest=hard_digest,
            pareto_front=pareto,
            score_digest=score_digest,
            tie_break_reason=tie_reason,
            dependency_generations=transaction.dependency_generations,
            status=SelectionStatus.ADVISORY,
            superseded_by=None,
            canonical_digest=digest(body),
        )
