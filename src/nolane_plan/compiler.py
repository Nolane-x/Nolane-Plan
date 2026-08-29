from __future__ import annotations

import itertools
from typing import Mapping, Sequence

from .future import FutureFamily, FutureLattice


class FutureSpaceCompiler:
    def __init__(self, max_families: int = 128):
        if max_families < 1:
            raise ValueError("max_families must be positive")
        self.max_families = max_families

    def compile(self, dimensions: Mapping[str, Sequence[str]]) -> FutureLattice:
        lattice = FutureLattice()
        names = tuple(sorted(dimensions))
        values = [tuple(dimensions[name]) for name in names]
        for index, combo in enumerate(itertools.islice(itertools.product(*values), self.max_families), start=1):
            clauses = tuple(f"{name}={value}" for name, value in zip(names, combo))
            lattice.add_family(FutureFamily(f"F{index:04d}", " AND ".join(clauses), assumptions=clauses))
        return lattice
