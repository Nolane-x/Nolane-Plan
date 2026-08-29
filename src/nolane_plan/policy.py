from __future__ import annotations

from dataclasses import dataclass
from collections import defaultdict


@dataclass(frozen=True, slots=True)
class DecisionBranch:
    history_id: str
    principal_ref: str
    information_signature: str
    action_semantics: str


@dataclass(frozen=True, slots=True)
class NonAnticipativityViolation:
    principal_ref: str
    information_signature: str
    history_ids: tuple[str, ...]
    actions: tuple[str, ...]


def check_non_anticipativity(branches: list[DecisionBranch]) -> list[NonAnticipativityViolation]:
    grouped: dict[tuple[str, str], list[DecisionBranch]] = defaultdict(list)
    for branch in branches:
        grouped[(branch.principal_ref, branch.information_signature)].append(branch)
    out: list[NonAnticipativityViolation] = []
    for (principal, signature), rows in grouped.items():
        actions = tuple(sorted({r.action_semantics for r in rows}))
        if len(actions) > 1:
            out.append(NonAnticipativityViolation(principal, signature, tuple(sorted(r.history_id for r in rows)), actions))
    return out
