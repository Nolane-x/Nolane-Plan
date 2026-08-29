from __future__ import annotations

from dataclasses import dataclass

from .types import InvariantViolation


@dataclass(frozen=True, slots=True)
class PlanningWorkUnit:
    id: str
    pool: str
    cost: float
    value: float
    mandatory: bool = False


@dataclass(frozen=True, slots=True)
class BudgetAllocation:
    selected_ids: tuple[str, ...]
    spent: float
    remaining: float


class PlanningBudgetGovernor:
    def __init__(self, total_budget: float):
        if total_budget < 0:
            raise ValueError("total_budget must be non-negative")
        self.total_budget = total_budget

    def allocate(self, units: list[PlanningWorkUnit]) -> BudgetAllocation:
        mandatory = [u for u in units if u.mandatory]
        mandatory_cost = sum(u.cost for u in mandatory)
        if mandatory_cost > self.total_budget:
            raise InvariantViolation("mandatory planning work exceeds budget; cannot silently prune")
        remaining = self.total_budget - mandatory_cost
        selected = list(mandatory)
        optional = sorted((u for u in units if not u.mandatory), key=lambda u: (u.value / u.cost if u.cost else float("inf"), u.value), reverse=True)
        # Greedy by value density, but skip any unit that cannot fit; this keeps the allocator anytime and bounded.
        for unit in optional:
            if unit.cost <= remaining:
                selected.append(unit)
                remaining -= unit.cost
        return BudgetAllocation(tuple(u.id for u in selected), self.total_budget - remaining, remaining)
