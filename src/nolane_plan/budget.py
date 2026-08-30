from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .types import InvariantViolation


@dataclass(frozen=True, slots=True)
class PlanningWorkUnit:
    id: str
    pool: str
    cost: float
    value: float
    mandatory: bool = False


@dataclass(frozen=True, slots=True)
class ProtectedBudgetDemand:
    id: str
    amount: float
    active_from: float
    active_until: float
    release_after: float
    source_reservation_ref: str
    required_route: bool = True

    def __post_init__(self) -> None:
        identifier = str(self.id).strip()
        source = str(self.source_reservation_ref).strip()
        amount = float(self.amount)
        active_from = float(self.active_from)
        active_until = float(self.active_until)
        release_after = float(self.release_after)
        if not identifier:
            raise ValueError("protected budget demand id must be non-empty")
        if not source:
            raise ValueError("source_reservation_ref must be non-empty")
        if amount < 0:
            raise ValueError("protected budget demand amount must be non-negative")
        if active_from < 0 or active_until < active_from:
            raise ValueError("protected budget demand active interval is invalid")
        if release_after < active_from or release_after > active_until:
            raise ValueError("release_after must lie inside the active interval")
        object.__setattr__(self, "id", identifier)
        object.__setattr__(self, "amount", amount)
        object.__setattr__(self, "active_from", active_from)
        object.__setattr__(self, "active_until", active_until)
        object.__setattr__(self, "release_after", release_after)
        object.__setattr__(self, "source_reservation_ref", source)
        object.__setattr__(self, "required_route", bool(self.required_route))

    def protected_at(self, now: int | float) -> float:
        instant = float(now)
        if self.active_from <= instant < self.release_after:
            return self.amount
        return 0.0


@dataclass(frozen=True, slots=True)
class BudgetAllocation:
    selected_ids: tuple[str, ...]
    spent: float
    remaining: float
    protected: float = 0.0


class PlanningBudgetGovernor:
    def __init__(self, total_budget: float):
        if total_budget < 0:
            raise ValueError("total_budget must be non-negative")
        self.total_budget = float(total_budget)

    def allocate(
        self,
        units: list[PlanningWorkUnit],
        *,
        protected_demands: Iterable[ProtectedBudgetDemand] = (),
        now: int | float = 0.0,
    ) -> BudgetAllocation:
        active_protected = tuple(
            (demand, demand.protected_at(now)) for demand in protected_demands
        )
        protected = sum(amount for _, amount in active_protected)
        if protected > self.total_budget:
            raise InvariantViolation(
                "protected reaction demand exceeds planning budget; cannot silently oversubscribe"
            )

        mandatory = [u for u in units if u.mandatory]
        mandatory_cost = sum(u.cost for u in mandatory)
        if mandatory_cost + protected > self.total_budget:
            raise InvariantViolation(
                "mandatory planning work plus protected reaction demand exceeds budget; cannot silently prune"
            )

        planning_capacity = self.total_budget - protected
        remaining = planning_capacity - mandatory_cost
        selected = list(mandatory)
        optional = sorted(
            (u for u in units if not u.mandatory),
            key=lambda u: (u.value / u.cost if u.cost else float("inf"), u.value),
            reverse=True,
        )
        # Greedy by value density, but never borrow from protected reaction capacity.
        for unit in optional:
            if unit.cost <= remaining:
                selected.append(unit)
                remaining -= unit.cost
        spent = sum(unit.cost for unit in selected)
        return BudgetAllocation(
            tuple(u.id for u in selected),
            spent,
            remaining,
            protected,
        )
