from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class LocationStatus(str, Enum):
    LOCATED = "located"
    AMBIGUOUS = "ambiguous"
    UNLOCATED = "unlocated"


@dataclass(frozen=True, slots=True)
class CandidateRegion:
    id: str
    required_facts: dict[str, Any]
    decision_signature: str

    def compatible(self, canonical_state: dict[str, Any]) -> bool:
        return all(canonical_state.get(k) == v for k, v in self.required_facts.items())


@dataclass(frozen=True, slots=True)
class StrategicLocationRevision:
    status: LocationStatus
    region_ids: tuple[str, ...]
    decision_signatures: tuple[str, ...]


class StateRelocator:
    def __init__(self, regions: list[CandidateRegion]):
        self.regions = list(regions)

    def locate(self, canonical_state: dict[str, Any]) -> StrategicLocationRevision:
        matches = [r for r in self.regions if r.compatible(canonical_state)]
        if not matches:
            return StrategicLocationRevision(LocationStatus.UNLOCATED, (), ())
        signatures = tuple(sorted({r.decision_signature for r in matches}))
        status = LocationStatus.LOCATED if len(signatures) == 1 else LocationStatus.AMBIGUOUS
        return StrategicLocationRevision(status, tuple(sorted(r.id for r in matches)), signatures)
