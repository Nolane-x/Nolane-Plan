from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .hashing import digest
from .wave8_chaos import run_wave8_chaos_invariant
from .wave8_differential import run_wave8_differential_invariant
from .wave8_metamorphic import run_wave8_metamorphic_relation
from .wave8_properties import run_wave8_property


WORLD_IDS = tuple(f"W{index:02d}" for index in range(1, 7))


@dataclass(frozen=True, slots=True)
class ReferenceWorldFixture:
    world_id: str
    title: str
    initial_state: tuple[tuple[str, object], ...]
    event_schedule: tuple[str, ...]
    invariant_ids: tuple[str, ...]
    expected_terminal_classification: str
    measurement_names: tuple[str, ...]
    measurements_gate_correctness: bool = False

    def canonical_payload(self) -> dict[str, object]:
        return {
            "world_id": self.world_id,
            "title": self.title,
            "initial_state": {key: value for key, value in self.initial_state},
            "event_schedule": list(self.event_schedule),
            "invariant_ids": list(self.invariant_ids),
            "expected_terminal_classification": self.expected_terminal_classification,
            "measurement_names": list(self.measurement_names),
            "measurements_gate_correctness": self.measurements_gate_correctness,
        }


@dataclass(frozen=True, slots=True)
class ReferenceWorldResult:
    world_id: str
    passed: bool
    failed_invariant_ids: tuple[str, ...]
    expected_terminal_classification: str
    terminal_classification: str
    measurements: tuple[tuple[str, int], ...]
    empirical_superiority_claimed: bool
    canonical_digest: str


REFERENCE_WORLD_FIXTURES = (
    ReferenceWorldFixture(
        "W01",
        "Principal Relay",
        (("principals", 3), ("observation_mode", "delayed-asymmetric"), ("seed", 0)),
        ("P02@0", "P02@1", "D07@0", "D07@1"),
        ("P02", "D07"),
        "ASYMMETRIC_OBSERVATION_PRESERVED",
        ("scheduled_relations", "executed_seed_cases", "failed_relations"),
    ),
    ReferenceWorldFixture(
        "W02",
        "Open-World Recovery",
        (("world_model", "incomplete"), ("unknown_events_fail_closed", True), ("seed", 0)),
        ("P10@0", "P10@1", "C03@0", "C03@1"),
        ("P10", "C03"),
        "UNKNOWN_QUARANTINED",
        ("scheduled_relations", "executed_seed_cases", "failed_relations"),
    ),
    ReferenceWorldFixture(
        "W03",
        "Deadline Resource Contention",
        (("workers", 2), ("writer_slots", 1), ("approval_slots", 1), ("seed", 0)),
        ("P06@0", "P06@1", "D09@0", "D09@1"),
        ("P06", "D09"),
        "BOUNDED_CONTENTION_CLASSIFIED",
        ("scheduled_relations", "executed_seed_cases", "failed_relations"),
    ),
    ReferenceWorldFixture(
        "W04",
        "Handoff Chain",
        (("handoff_budget", 5), ("stutter_budget", 1), ("seed", 0)),
        ("P07@0", "P07@1", "C09@0", "C09@1"),
        ("P07", "C09"),
        "HANDOFF_LIVENESS_BOUNDED",
        ("scheduled_relations", "executed_seed_cases", "failed_relations"),
    ),
    ReferenceWorldFixture(
        "W05",
        "Migration And Ambiguous External Effect",
        (("idempotent", False), ("external_effect", "unknown"), ("seed", 0)),
        ("C05@0", "C07@0", "D06@0", "D06@1"),
        ("C05", "C07", "D06"),
        "RECONCILIATION_AND_RECHECK_REQUIRED",
        ("scheduled_relations", "executed_seed_cases", "failed_relations"),
    ),
    ReferenceWorldFixture(
        "W06",
        "Dormant Hedge And Compaction",
        (("protected_fallback", True), ("representation_only_compaction", True), ("seed", 0)),
        ("P09@0", "M10@0", "M10@1", "C08@0"),
        ("P09", "M10", "C08"),
        "HISTORY_AND_FALLBACK_RETAINED",
        ("scheduled_relations", "executed_seed_cases", "failed_relations"),
    ),
)


def _run_target(invariant_id: str, seed: int):
    if invariant_id.startswith("P"):
        return run_wave8_property(invariant_id, (seed,))
    if invariant_id.startswith("M"):
        return run_wave8_metamorphic_relation(invariant_id, (seed,))
    if invariant_id.startswith("C"):
        return run_wave8_chaos_invariant(invariant_id, (seed,))
    if invariant_id.startswith("D"):
        return run_wave8_differential_invariant(invariant_id, (seed,))
    raise ValueError(f"unsupported reference-world target: {invariant_id}")


def _run_world(fixture: ReferenceWorldFixture) -> ReferenceWorldResult:
    failed: list[str] = []
    executed = 0
    for step in fixture.event_schedule:
        invariant_id, raw_seed = step.split("@", 1)
        seed = int(raw_seed)
        executed += 1
        if _run_target(invariant_id, seed):
            failed.append(invariant_id)
    failed_ids = tuple(sorted(set(failed)))
    passed = not failed_ids
    terminal = fixture.expected_terminal_classification if passed else "COUNTEREXAMPLE_FOUND"
    measurements = (
        ("scheduled_relations", len(fixture.event_schedule)),
        ("executed_seed_cases", executed),
        ("failed_relations", len(failed_ids)),
    )
    body = {
        "world_id": fixture.world_id,
        "passed": passed,
        "failed_invariant_ids": failed_ids,
        "expected_terminal_classification": fixture.expected_terminal_classification,
        "terminal_classification": terminal,
        "measurements": measurements,
        "empirical_superiority_claimed": False,
    }
    return ReferenceWorldResult(
        world_id=fixture.world_id,
        passed=passed,
        failed_invariant_ids=failed_ids,
        expected_terminal_classification=fixture.expected_terminal_classification,
        terminal_classification=terminal,
        measurements=measurements,
        empirical_superiority_claimed=False,
        canonical_digest=digest(body),
    )


def run_reference_worlds() -> tuple[ReferenceWorldResult, ...]:
    results = tuple(_run_world(fixture) for fixture in REFERENCE_WORLD_FIXTURES)
    if tuple(result.world_id for result in results) != WORLD_IDS:
        raise RuntimeError("Wave-8 reference-world registry drift")
    return results
