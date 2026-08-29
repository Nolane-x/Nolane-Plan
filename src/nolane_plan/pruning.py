from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum


class UnsafePrune(RuntimeError):
    pass


class BranchState(str, Enum):
    ACTIVE = "active"
    DORMANT = "dormant"


@dataclass(frozen=True, slots=True)
class BranchRecord:
    id: str
    support: float
    catastrophic_exposure: bool
    sole_hard_route: bool
    unique_hedge: bool
    information_value: float
    state: BranchState = BranchState.ACTIVE


class PruningEngine:
    def prune(self, branch: BranchRecord) -> BranchRecord:
        if branch.sole_hard_route:
            raise UnsafePrune("sole route preserving hard obligation")
        if branch.unique_hedge:
            raise UnsafePrune("unique hedge against model failure")
        if branch.catastrophic_exposure:
            raise UnsafePrune("catastrophic branch cannot be probability-pruned")
        if branch.information_value > 0:
            raise UnsafePrune("information-rich branch cannot be silently pruned")
        return replace(branch, state=BranchState.DORMANT)

    def resurrect(self, branch: BranchRecord, dependencies_current: bool) -> BranchRecord:
        if not dependencies_current:
            raise UnsafePrune("resurrection requires dependency revalidation")
        return replace(branch, state=BranchState.ACTIVE)
