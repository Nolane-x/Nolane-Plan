from __future__ import annotations

from enum import Enum


class PlanError(RuntimeError):
    """Base class for correctness-significant runtime failures."""


class InvariantViolation(PlanError):
    pass


class AuthorizationError(PlanError):
    pass


class CapsuleError(PlanError):
    pass


class ReplayError(PlanError):
    pass


class RiskClass(str, Enum):
    REVERSIBLE = "reversible"
    CONSEQUENTIAL = "consequential"
    IRREVERSIBLE = "irreversible"


class DecisionOutcome(str, Enum):
    ALLOW = "allow"
    BLOCK = "block"
    INCONCLUSIVE = "inconclusive"
