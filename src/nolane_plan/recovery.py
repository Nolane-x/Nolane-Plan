from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .types import RiskClass


class RecoveryMode(str, Enum):
    NORMAL = "normal"
    MODEL_CLASS_UNCERTAIN = "model_class_uncertain"
    QUARANTINED = "quarantined"


@dataclass(frozen=True, slots=True)
class RecoveryState:
    mode: RecoveryMode = RecoveryMode.NORMAL
    reason: str | None = None
    residual_weight: float = 0.0
    generation: int = 1


class RecoveryController:
    def __init__(self) -> None:
        self.state = RecoveryState()

    def enter_model_class_uncertain(self, reason: str, residual_weight: float) -> RecoveryState:
        self.state = RecoveryState(RecoveryMode.MODEL_CLASS_UNCERTAIN, reason, max(0.0, min(1.0, residual_weight)), self.state.generation + 1)
        return self.state

    def quarantine(self, reason: str) -> RecoveryState:
        self.state = RecoveryState(RecoveryMode.QUARANTINED, reason, max(self.state.residual_weight, 0.5), self.state.generation + 1)
        return self.state

    def restore_normal(self) -> RecoveryState:
        self.state = RecoveryState(RecoveryMode.NORMAL, generation=self.state.generation + 1)
        return self.state

    def can_execute(self, risk_class: RiskClass, emergency_authorized: bool = False) -> bool:
        if self.state.mode == RecoveryMode.NORMAL:
            return True
        if risk_class == RiskClass.REVERSIBLE:
            return True
        return emergency_authorized
