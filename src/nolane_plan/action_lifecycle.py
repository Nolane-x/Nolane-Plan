from __future__ import annotations

from enum import Enum


class ActionPhase(str, Enum):
    PROPOSED = "proposed"
    RISK_CLASSIFIED = "risk_classified"
    AUTHORIZED = "authorized"
    PRECONDITIONS_VERIFIED = "preconditions_verified"
    EXECUTION_STARTED = "execution_started"
    OUTCOME_OBSERVED = "outcome_observed"
    POSTCONDITIONS_VERIFIED = "postconditions_verified"
    COMMITTED = "committed"
    ROLLBACK = "rollback"
    COMPENSATION = "compensation"
    DEGRADED_STATE = "degraded_state"
    UNKNOWN_OUTCOME = "unknown_outcome"
    MANUAL_AUTHORITY_REQUIRED = "manual_authority_required"


_ALLOWED = {
    ActionPhase.PROPOSED: {ActionPhase.RISK_CLASSIFIED},
    ActionPhase.RISK_CLASSIFIED: {ActionPhase.AUTHORIZED, ActionPhase.MANUAL_AUTHORITY_REQUIRED},
    ActionPhase.AUTHORIZED: {ActionPhase.PRECONDITIONS_VERIFIED, ActionPhase.MANUAL_AUTHORITY_REQUIRED},
    ActionPhase.PRECONDITIONS_VERIFIED: {ActionPhase.EXECUTION_STARTED},
    ActionPhase.EXECUTION_STARTED: {ActionPhase.OUTCOME_OBSERVED, ActionPhase.UNKNOWN_OUTCOME},
    ActionPhase.OUTCOME_OBSERVED: {ActionPhase.POSTCONDITIONS_VERIFIED, ActionPhase.ROLLBACK, ActionPhase.COMPENSATION, ActionPhase.DEGRADED_STATE},
    ActionPhase.POSTCONDITIONS_VERIFIED: {ActionPhase.COMMITTED},
    ActionPhase.UNKNOWN_OUTCOME: {ActionPhase.COMPENSATION, ActionPhase.DEGRADED_STATE, ActionPhase.MANUAL_AUTHORITY_REQUIRED},
    ActionPhase.COMPENSATION: {ActionPhase.DEGRADED_STATE, ActionPhase.COMMITTED},
    ActionPhase.ROLLBACK: {ActionPhase.COMMITTED, ActionPhase.DEGRADED_STATE},
    ActionPhase.DEGRADED_STATE: set(),
    ActionPhase.MANUAL_AUTHORITY_REQUIRED: set(),
    ActionPhase.COMMITTED: set(),
}


class ActionLifecycle:
    def __init__(self) -> None:
        self.phase = ActionPhase.PROPOSED
        self.history = [self.phase]

    @property
    def committed(self) -> bool:
        return self.phase == ActionPhase.COMMITTED

    def transition(self, phase: ActionPhase) -> ActionPhase:
        if phase not in _ALLOWED[self.phase]:
            raise ValueError(f"illegal action lifecycle transition: {self.phase.value} -> {phase.value}")
        self.phase = phase
        self.history.append(phase)
        return phase
