from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ActionScore:
    action_id: str
    progress: float
    information: float
    optionality: float
    convergence: float
    reversibility: float
    tail_risk: float
    debt: float
    cost: float
    hard_veto: bool = False


def _dominates(a: ActionScore, b: ActionScore) -> bool:
    gains_a = (a.progress, a.information, a.optionality, a.convergence, a.reversibility)
    gains_b = (b.progress, b.information, b.optionality, b.convergence, b.reversibility)
    losses_a = (a.tail_risk, a.debt, a.cost)
    losses_b = (b.tail_risk, b.debt, b.cost)
    no_worse = all(x >= y for x, y in zip(gains_a, gains_b)) and all(x <= y for x, y in zip(losses_a, losses_b))
    strictly = any(x > y for x, y in zip(gains_a, gains_b)) or any(x < y for x, y in zip(losses_a, losses_b))
    return no_worse and strictly


def pareto_front(scores: list[ActionScore]) -> list[ActionScore]:
    eligible = [s for s in scores if not s.hard_veto]
    return [s for s in eligible if not any(_dominates(other, s) for other in eligible if other is not s)]
