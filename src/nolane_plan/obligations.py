from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum


class ObligationStatus(str, Enum):
    OPEN = "open"
    SATISFIED = "satisfied"
    VIOLATED = "violated"
    INFEASIBLE = "infeasible"


@dataclass(frozen=True, slots=True)
class StrategicObligation:
    id: str
    condition: str
    deadline: int | float | None = None
    required_capability: str | None = None
    hard: bool = True
    status: ObligationStatus = ObligationStatus.OPEN
    lineage: tuple[str, ...] = ()


class ObligationLedger:
    def __init__(self) -> None:
        self._items: dict[str, StrategicObligation] = {}
        self.unavailable_principals: set[str] = set()

    def add(self, obligation: StrategicObligation) -> StrategicObligation:
        if obligation.id in self._items:
            raise ValueError(obligation.id)
        self._items[obligation.id] = obligation
        return obligation

    def get(self, obligation_id: str) -> StrategicObligation:
        return self._items[obligation_id]

    def set_status(self, obligation_id: str, status: ObligationStatus) -> StrategicObligation:
        updated = replace(self.get(obligation_id), status=status)
        self._items[obligation_id] = updated
        return updated

    def principal_unavailable(self, principal_ref: str) -> None:
        self.unavailable_principals.add(principal_ref)
        # Obligations are normative conditions, not assignee-owned tasks.

    def open(self) -> tuple[StrategicObligation, ...]:
        return tuple(o for o in self._items.values() if o.status == ObligationStatus.OPEN)
