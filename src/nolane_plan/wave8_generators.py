from __future__ import annotations

from dataclasses import dataclass
import random
from typing import Callable, Iterable

from .hashing import digest


GENERATOR_VERSION = "wave8-generator-v1"
GENERATOR_FAMILIES = (
    "principal_information",
    "evidence_support",
    "selector_candidates",
    "policy_information",
    "policy_bundle",
    "resource_jobs",
    "handoff",
    "resurrection",
    "relocation",
    "lineage_regime",
    "migration",
    "replay_compaction",
)

_LIMITS = {
    "principals": 3,
    "items": 8,
    "actions": 6,
    "resources": 5,
    "fault_points": 8,
}

_FAMILY_DIMENSIONS: dict[str, tuple[str, ...]] = {
    "principal_information": ("principals", "items", "actions"),
    "evidence_support": ("items", "actions"),
    "selector_candidates": ("actions",),
    "policy_information": ("principals", "items", "actions"),
    "policy_bundle": ("principals", "items", "actions"),
    "resource_jobs": ("actions", "resources"),
    "handoff": ("principals", "items", "actions", "resources"),
    "resurrection": ("items", "actions", "resources"),
    "relocation": ("items",),
    "lineage_regime": ("items", "actions"),
    "migration": ("items", "actions", "fault_points"),
    "replay_compaction": ("items", "actions", "fault_points"),
}


@dataclass(frozen=True, slots=True)
class Wave8CaseRecipe:
    generator_family: str
    seed: int
    generator_version: str
    dimensions: tuple[tuple[str, int], ...]
    operations: tuple[str, ...]
    parameters: tuple[tuple[str, str], ...]
    canonical_digest: str

    @classmethod
    def create(
        cls,
        *,
        generator_family: str,
        seed: int,
        dimensions: Iterable[tuple[str, int]],
        operations: Iterable[str],
        parameters: Iterable[tuple[str, str]] = (),
        generator_version: str = GENERATOR_VERSION,
    ) -> "Wave8CaseRecipe":
        family = str(generator_family).strip()
        if family not in GENERATOR_FAMILIES:
            raise ValueError(f"unknown Wave-8 generator family: {family}")
        version = str(generator_version).strip()
        if not version:
            raise ValueError("generator_version must be non-empty")
        dims = tuple(sorted((str(name), int(value)) for name, value in dimensions))
        if len({name for name, _ in dims}) != len(dims):
            raise ValueError("recipe dimensions must be unique")
        for name, value in dims:
            if name not in _LIMITS:
                raise ValueError(f"unknown recipe dimension: {name}")
            if value < 0 or value > _LIMITS[name]:
                raise ValueError(f"recipe dimension {name} exceeds bounded limit")
        ops = tuple(str(value).strip() for value in operations)
        if not ops or any(not value for value in ops):
            raise ValueError("recipe operations must be non-empty")
        params = tuple(sorted((str(name), str(value)) for name, value in parameters))
        if len({name for name, _ in params}) != len(params):
            raise ValueError("recipe parameters must be unique")
        body = {
            "generator_family": family,
            "seed": int(seed),
            "generator_version": version,
            "dimensions": dims,
            "operations": ops,
            "parameters": params,
        }
        return cls(
            generator_family=family,
            seed=int(seed),
            generator_version=version,
            dimensions=dims,
            operations=ops,
            parameters=params,
            canonical_digest=digest(body),
        )

    def with_operations(self, operations: Iterable[str]) -> "Wave8CaseRecipe":
        return Wave8CaseRecipe.create(
            generator_family=self.generator_family,
            seed=self.seed,
            generator_version=self.generator_version,
            dimensions=self.dimensions,
            operations=operations,
            parameters=self.parameters,
        )


class DeterministicCaseGenerator:
    """Small seed-owned recipe generator; it never mutates a PlanKernel directly."""

    def __init__(self, family: str, seed: int):
        if family not in GENERATOR_FAMILIES:
            raise ValueError(f"unknown Wave-8 generator family: {family}")
        self.family = family
        self.seed = int(seed)
        self._rng = random.Random(self.seed)

    def _dimensions(self) -> tuple[tuple[str, int], ...]:
        active = set(_FAMILY_DIMENSIONS[self.family])
        return tuple(
            (name, self._rng.randint(1, limit) if name in active else 0)
            for name, limit in _LIMITS.items()
        )

    def build(self) -> Wave8CaseRecipe:
        dimensions = self._dimensions()
        counts = dict(dimensions)
        token = self._rng.getrandbits(64)
        operations: list[str] = [
            f"begin:{self.family}",
            f"seed-token:{token:016x}",
        ]
        for name in _FAMILY_DIMENSIONS[self.family]:
            count = counts[name]
            for index in range(count):
                operations.append(f"{name}:{index}:{self._rng.getrandbits(24):06x}")
        # The terminal assertion token gives every recipe a stable, seed-specific
        # reproduction anchor and is intentionally safe for deterministic shrinking.
        operations.append(f"assert:{self.family}:{self._rng.getrandbits(32):08x}")
        parameters = (
            ("mode", "adversarial" if self._rng.getrandbits(1) else "valid"),
            ("variant", str(self._rng.randrange(0, 7))),
        )
        return Wave8CaseRecipe.create(
            generator_family=self.family,
            seed=self.seed,
            dimensions=dimensions,
            operations=operations,
            parameters=parameters,
        )


def generate_case(family: str, seed: int) -> Wave8CaseRecipe:
    return DeterministicCaseGenerator(family, seed).build()


def minimize_recipe(
    recipe: Wave8CaseRecipe,
    predicate: Callable[[Wave8CaseRecipe], bool],
) -> Wave8CaseRecipe:
    """Deterministically delete operations until no single deletion preserves failure."""

    current = recipe
    if not predicate(current):
        raise ValueError("minimizer requires an initially failing recipe")
    index = 0
    while index < len(current.operations):
        if len(current.operations) == 1:
            break
        candidate_ops = current.operations[:index] + current.operations[index + 1 :]
        candidate = current.with_operations(candidate_ops)
        if predicate(candidate):
            current = candidate
            index = 0
            continue
        index += 1
    return current
