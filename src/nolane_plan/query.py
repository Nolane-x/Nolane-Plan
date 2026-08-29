from __future__ import annotations

from dataclasses import dataclass

from .freshness import FreshnessDomainLedger


@dataclass(frozen=True, slots=True)
class QuerySnapshotCompletenessReceipt:
    domain: str
    domain_generation: int
    snapshot_id: str
    complete: bool
    visibility_assurance: float

    @classmethod
    def capture(
        cls,
        ledger: FreshnessDomainLedger,
        domain: str,
        snapshot_id: str,
        complete: bool,
        visibility_assurance: float,
    ) -> "QuerySnapshotCompletenessReceipt":
        return cls(domain, ledger.generation(domain), snapshot_id, complete, visibility_assurance)


def strong_universal_current(receipt: QuerySnapshotCompletenessReceipt, ledger: FreshnessDomainLedger, minimum_assurance: float) -> bool:
    return (
        receipt.complete
        and receipt.visibility_assurance >= minimum_assurance
        and ledger.generation(receipt.domain) == receipt.domain_generation
        and bool(receipt.snapshot_id)
    )
