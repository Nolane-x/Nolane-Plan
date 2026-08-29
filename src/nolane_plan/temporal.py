from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ReactionWindow:
    trigger_time: int | float
    deadline: int | float
    prepare_seconds: float
    verify_seconds: float
    dispatch_seconds: float

    @property
    def total_demand(self) -> float:
        return self.prepare_seconds + self.verify_seconds + self.dispatch_seconds

    def schedulable(self) -> bool:
        return self.trigger_time + self.total_demand <= self.deadline


@dataclass(frozen=True, slots=True)
class HandoffContract:
    from_principal_ref: str
    to_principal_ref: str
    handoff_deadline: int | float
    communication_seconds: float
    refinement_seconds: float
    information_adequate: bool
    authority_adequate: bool

    def live(self, now: int | float) -> bool:
        return (
            self.information_adequate
            and self.authority_adequate
            and now + self.communication_seconds + self.refinement_seconds <= self.handoff_deadline
        )
