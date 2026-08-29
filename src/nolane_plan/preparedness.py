from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum


class PreparednessLevel(IntEnum):
    BASIN = 0
    CONCEPT = 1
    SCHEMA = 2
    EXECUTABLE = 3
    VERIFIED = 4


@dataclass(frozen=True, slots=True)
class PreparednessProfile:
    level: PreparednessLevel
    dependencies_current: bool
    schedulable: bool

    def satisfies(self, required: PreparednessLevel) -> bool:
        return self.level >= required and self.dependencies_current and self.schedulable


def required_preparedness(distance: int, irreversible: bool, observation_lead_time: float, synthesis_latency: float) -> PreparednessLevel:
    if irreversible and distance <= 2:
        return PreparednessLevel.EXECUTABLE
    if observation_lead_time < synthesis_latency:
        return PreparednessLevel.EXECUTABLE
    if distance <= 3:
        return PreparednessLevel.SCHEMA
    if distance <= 8:
        return PreparednessLevel.CONCEPT
    return PreparednessLevel.BASIN
