from __future__ import annotations

from dataclasses import dataclass, replace


@dataclass(frozen=True, slots=True)
class MissionContract:
    version: int
    objective: str
    success_conditions: tuple[str, ...] = ()
    hard_constraints: tuple[str, ...] = ()
    soft_preferences: tuple[str, ...] = ()
    anti_goals: tuple[str, ...] = ()
    risk_budget: float | None = None


class MissionLedger:
    def __init__(self, current: MissionContract):
        self.current = current
        self.history: list[MissionContract] = []

    @classmethod
    def create(
        cls,
        objective: str,
        success_conditions: tuple[str, ...] = (),
        hard_constraints: tuple[str, ...] = (),
        soft_preferences: tuple[str, ...] = (),
        anti_goals: tuple[str, ...] = (),
        risk_budget: float | None = None,
    ) -> "MissionLedger":
        if not objective.strip():
            raise ValueError("objective must be non-empty")
        return cls(MissionContract(1, objective, tuple(success_conditions), tuple(hard_constraints), tuple(soft_preferences), tuple(anti_goals), risk_budget))

    def revise(self, **changes) -> MissionContract:
        self.history.append(self.current)
        allowed = {"objective", "success_conditions", "hard_constraints", "soft_preferences", "anti_goals", "risk_budget"}
        unknown = set(changes) - allowed
        if unknown:
            raise TypeError(f"unsupported mission fields: {sorted(unknown)}")
        normalized = dict(changes)
        for key in ("success_conditions", "hard_constraints", "soft_preferences", "anti_goals"):
            if key in normalized:
                normalized[key] = tuple(normalized[key])
        self.current = replace(self.current, version=self.current.version + 1, **normalized)
        return self.current
