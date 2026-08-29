from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum


class EvidencePolarity(str, Enum):
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    UNKNOWN = "unknown"
    NOT_APPLICABLE = "not_applicable"


@dataclass(frozen=True, slots=True)
class EvidenceRecord:
    id: str
    claim: str
    polarity: EvidencePolarity
    source_id: str
    lineage_root: str
    observed_at: int | float
    valid_until: int | float | None = None
    assurance: float = 0.5
    revoked: bool = False
    revocation_reason: str | None = None


class EvidenceLedger:
    def __init__(self) -> None:
        self.records: dict[str, EvidenceRecord] = {}
        self.generation = 1

    def add(self, record: EvidenceRecord) -> EvidenceRecord:
        if record.id in self.records:
            raise ValueError(f"duplicate evidence id: {record.id}")
        self.records[record.id] = record
        self.generation += 1
        return record

    def revoke(self, evidence_id: str, reason: str) -> EvidenceRecord:
        record = self.records[evidence_id]
        updated = replace(record, revoked=True, revocation_reason=reason)
        self.records[evidence_id] = updated
        self.generation += 1
        return updated

    def is_current(self, evidence_id: str, at_time: int | float) -> bool:
        r = self.records[evidence_id]
        return not r.revoked and (r.valid_until is None or at_time <= r.valid_until) and r.observed_at <= at_time

    def independent_support_count(self, claim: str, at_time: int | float) -> int:
        roots = {
            r.lineage_root
            for r in self.records.values()
            if r.claim == claim and r.polarity == EvidencePolarity.SUPPORTS and self.is_current(r.id, at_time)
        }
        return len(roots)

    def claim_summary(self, claim: str, at_time: int | float) -> dict[EvidencePolarity, int]:
        summary = {p: 0 for p in EvidencePolarity}
        for r in self.records.values():
            if r.claim == claim and self.is_current(r.id, at_time):
                summary[r.polarity] += 1
        return summary
