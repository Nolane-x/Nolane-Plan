from __future__ import annotations

from dataclasses import dataclass

from .hashing import digest
from .wave8_chaos import run_wave8_chaos
from .wave8_coverage import audit_repository_coverage
from .wave8_differential import run_wave8_differential
from .wave8_metamorphic import run_wave8_metamorphic
from .wave8_properties import run_wave8_properties
from .wave8_registry import WAVE8_INVARIANTS, Wave8Counterexample, Wave8Layer, wave8_registry_digest
from .wave8_worlds import run_reference_worlds


FROZEN_SEEDS = tuple(range(16))
EXPECTED_LAYER_COUNTS = {
    Wave8Layer.PROPERTY: 10,
    Wave8Layer.METAMORPHIC: 12,
    Wave8Layer.CHAOS: 10,
    Wave8Layer.DIFFERENTIAL: 10,
    Wave8Layer.MUTATION: 12,
    Wave8Layer.WORLD: 6,
    Wave8Layer.COVERAGE: 8,
}
EXECUTABLE_LAYERS = (
    Wave8Layer.PROPERTY,
    Wave8Layer.METAMORPHIC,
    Wave8Layer.CHAOS,
    Wave8Layer.DIFFERENTIAL,
    Wave8Layer.WORLD,
    Wave8Layer.COVERAGE,
)


@dataclass(frozen=True, slots=True)
class Wave8ConformanceReport:
    green: bool
    registry_count: int
    registry_digest: str
    layer_counts: dict[Wave8Layer, int]
    layer_statuses: dict[Wave8Layer, str]
    counterexamples: tuple[Wave8Counterexample, ...]
    failures: tuple[str, ...]
    world_digests: tuple[str, ...]
    coverage_digest: str
    canonical_digest: str


def _registry_layer_counts() -> dict[Wave8Layer, int]:
    return {
        layer: sum(row.layer is layer for row in WAVE8_INVARIANTS)
        for layer in Wave8Layer
    }


def run_wave8_conformance() -> Wave8ConformanceReport:
    failures: list[str] = []
    registry_count = len(WAVE8_INVARIANTS)
    registry_digest = wave8_registry_digest()
    layer_counts = _registry_layer_counts()
    if registry_count != 68:
        failures.append(f"registry count drift: expected 68, got {registry_count}")
    if layer_counts != EXPECTED_LAYER_COUNTS:
        failures.append(f"layer count drift: expected {EXPECTED_LAYER_COUNTS!r}, got {layer_counts!r}")

    property_failures = run_wave8_properties(FROZEN_SEEDS)
    metamorphic_failures = run_wave8_metamorphic(FROZEN_SEEDS)
    chaos_failures = run_wave8_chaos(FROZEN_SEEDS)
    differential_failures = run_wave8_differential(FROZEN_SEEDS)
    counterexamples = tuple(
        sorted(
            (*property_failures, *metamorphic_failures, *chaos_failures, *differential_failures),
            key=lambda row: (row.invariant_id, row.seed, row.case_id),
        )
    )

    worlds = run_reference_worlds()
    failed_worlds = tuple(result for result in worlds if not result.passed)
    for result in failed_worlds:
        failures.append(
            f"reference world {result.world_id} failed invariants {result.failed_invariant_ids!r}"
        )

    coverage = audit_repository_coverage()
    failures.extend(coverage.failures)

    layer_statuses = {
        Wave8Layer.PROPERTY: "GREEN" if not property_failures else "RED",
        Wave8Layer.METAMORPHIC: "GREEN" if not metamorphic_failures else "RED",
        Wave8Layer.CHAOS: "GREEN" if not chaos_failures else "RED",
        Wave8Layer.DIFFERENTIAL: "GREEN" if not differential_failures else "RED",
        Wave8Layer.MUTATION: "SEPARATE_GATE",
        Wave8Layer.WORLD: "GREEN" if not failed_worlds else "RED",
        Wave8Layer.COVERAGE: "GREEN" if coverage.passed else "RED",
    }
    green = (
        not failures
        and not counterexamples
        and all(layer_statuses[layer] == "GREEN" for layer in EXECUTABLE_LAYERS)
    )
    body = {
        "green": green,
        "registry_count": registry_count,
        "registry_digest": registry_digest,
        "layer_counts": {layer.value: layer_counts[layer] for layer in Wave8Layer},
        "layer_statuses": {layer.value: layer_statuses[layer] for layer in Wave8Layer},
        "counterexample_digests": tuple(row.canonical_digest for row in counterexamples),
        "failures": tuple(failures),
        "world_digests": tuple(result.canonical_digest for result in worlds),
        "coverage_digest": coverage.canonical_digest,
        "frozen_seeds": FROZEN_SEEDS,
    }
    return Wave8ConformanceReport(
        green=green,
        registry_count=registry_count,
        registry_digest=registry_digest,
        layer_counts=layer_counts,
        layer_statuses=layer_statuses,
        counterexamples=counterexamples,
        failures=tuple(failures),
        world_digests=tuple(result.canonical_digest for result in worlds),
        coverage_digest=coverage.canonical_digest,
        canonical_digest=digest(body),
    )


def main() -> int:
    report = run_wave8_conformance()
    print(f"WAVE8_REGISTRY_COUNT={report.registry_count}")
    print(f"WAVE8_REGISTRY_DIGEST={report.registry_digest}")
    for layer in Wave8Layer:
        print(
            f"WAVE8_LAYER_{layer.value}={report.layer_counts[layer]}:{report.layer_statuses[layer]}"
        )
    print(f"WAVE8_COUNTEREXAMPLES={len(report.counterexamples)}")
    print(f"WAVE8_CONFORMANCE_DIGEST={report.canonical_digest}")
    for row in report.counterexamples:
        print(
            f"WAVE8_COUNTEREXAMPLE={row.invariant_id}:{row.case_id}:{row.canonical_digest}:{row.observed_summary}"
        )
    for failure in report.failures:
        print(f"WAVE8_CONFORMANCE_FAILURE={failure}")
    print(f"WAVE8_CONFORMANCE={'GREEN' if report.green else 'RED'}")
    return 0 if report.green else 1


if __name__ == "__main__":
    raise SystemExit(main())
