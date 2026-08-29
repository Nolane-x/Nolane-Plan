from __future__ import annotations

from dataclasses import dataclass


class ReservationConflict(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class SharedCommitment:
    resource_id: str
    principal_ref: str
    start: int | float
    end: int | float
    exclusive: bool = True

    def overlaps(self, other: "SharedCommitment") -> bool:
        return self.start < other.end and other.start < self.end


class ReservationLedger:
    def __init__(self) -> None:
        self.commitments: list[SharedCommitment] = []

    def reserve(self, commitment: SharedCommitment) -> SharedCommitment:
        for existing in self.commitments:
            if existing.resource_id == commitment.resource_id and existing.overlaps(commitment) and (existing.exclusive or commitment.exclusive):
                raise ReservationConflict(f"resource conflict: {commitment.resource_id}")
        self.commitments.append(commitment)
        return commitment
