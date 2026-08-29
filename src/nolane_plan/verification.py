from __future__ import annotations

from dataclasses import dataclass

from .mission import MissionContract
from .obligations import ObligationLedger, ObligationStatus


@dataclass(frozen=True, slots=True)
class CompletionReport:
    complete: bool
    missing_success_conditions: tuple[str, ...]
    open_hard_obligations: tuple[str, ...]
    anti_goal_violations: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class BoundCompletionReport:
    complete: bool
    missing_success_conditions: tuple[str, ...]
    open_hard_obligations: tuple[str, ...]
    anti_goal_violations: tuple[str, ...]
    artifact_id: str
    decision_cut_id: str


class CompletionVerifier:
    def verify(
        self,
        mission: MissionContract,
        canonical_state: dict,
        obligations: ObligationLedger,
        anti_goal_violations: tuple[str, ...],
    ) -> CompletionReport:
        missing = tuple(condition for condition in mission.success_conditions if not bool(canonical_state.get(condition)))
        open_hard = tuple(sorted(o.id for o in obligations.open() if o.hard and o.status == ObligationStatus.OPEN))
        violations = tuple(anti_goal_violations)
        return CompletionReport(not missing and not open_hard and not violations, missing, open_hard, violations)
