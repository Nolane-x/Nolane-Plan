from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum

from .hashing import digest
from .types import PlanError


class CommunicationError(PlanError):
    """Raised when planning-relevant communication evidence is invalid."""


class CommunicationState(str, Enum):
    SENT = "sent"
    DELIVERED = "delivered"
    OBSERVED = "observed"
    EXPIRED = "expired"
    REVOKED = "revoked"


@dataclass(frozen=True, slots=True)
class CommunicationReceipt:
    id: str
    source_principal_ref: str
    recipient_principal_ref: str
    semantic_payload_refs: tuple[str, ...]
    semantic_payload_digest: str
    state: CommunicationState
    sent_at: int | float
    delivered_at: int | float | None
    observed_at: int | float | None
    valid_until: int | float | None
    access_condition: str | None
    provenance: str
    delivery_evidence_ref: str | None = None
    observation_evidence_ref: str | None = None


class CommunicationLedger:
    """Models only the communication state needed for planning correctness.

    `SENT` and `DELIVERED` deliberately do not imply recipient knowledge. A
    transfer becomes decision-usable only after an `OBSERVED` receipt for the
    exact recipient at or before the decision boundary.
    """

    def __init__(self) -> None:
        self._receipts: dict[str, CommunicationReceipt] = {}

    def sent(
        self,
        *,
        receipt_id: str,
        source_principal_ref: str,
        recipient_principal_ref: str,
        semantic_payload_refs: tuple[str, ...],
        sent_at: int | float,
        valid_until: int | float | None = None,
        access_condition: str | None = None,
        provenance: str = "host",
    ) -> CommunicationReceipt:
        if receipt_id in self._receipts:
            raise CommunicationError("communication receipt already exists")
        if not receipt_id.strip() or not source_principal_ref.strip() or not recipient_principal_ref.strip():
            raise CommunicationError("receipt and principal references must be non-empty")
        if source_principal_ref == recipient_principal_ref:
            raise CommunicationError("inter-principal transfer requires distinct source and recipient principals")
        if not semantic_payload_refs:
            raise CommunicationError("communication requires at least one semantic payload reference")
        if valid_until is not None and valid_until < sent_at:
            raise CommunicationError("communication validity window is inverted")
        payload_refs = tuple(semantic_payload_refs)
        receipt = CommunicationReceipt(
            id=receipt_id,
            source_principal_ref=source_principal_ref,
            recipient_principal_ref=recipient_principal_ref,
            semantic_payload_refs=payload_refs,
            semantic_payload_digest=digest(payload_refs),
            state=CommunicationState.SENT,
            sent_at=sent_at,
            delivered_at=None,
            observed_at=None,
            valid_until=valid_until,
            access_condition=access_condition,
            provenance=provenance,
        )
        self._receipts[receipt.id] = receipt
        return receipt

    def get(self, receipt_id: str) -> CommunicationReceipt:
        try:
            return self._receipts[receipt_id]
        except KeyError as exc:
            raise CommunicationError("unknown communication receipt") from exc

    def delivered(
        self,
        receipt_id: str,
        *,
        delivered_at: int | float,
        evidence_ref: str,
    ) -> CommunicationReceipt:
        receipt = self.get(receipt_id)
        if receipt.state != CommunicationState.SENT:
            raise CommunicationError("delivery requires SENT state")
        if delivered_at < receipt.sent_at:
            raise CommunicationError("delivery cannot precede send")
        if not evidence_ref.strip():
            raise CommunicationError("delivery evidence reference must be non-empty")
        updated = replace(
            receipt,
            state=CommunicationState.DELIVERED,
            delivered_at=delivered_at,
            delivery_evidence_ref=evidence_ref,
        )
        self._receipts[receipt_id] = updated
        return updated

    def observed(
        self,
        receipt_id: str,
        *,
        observed_at: int | float,
        evidence_ref: str,
    ) -> CommunicationReceipt:
        receipt = self.get(receipt_id)
        if receipt.state != CommunicationState.DELIVERED:
            raise CommunicationError("observation requires DELIVERED state")
        if receipt.delivered_at is None or observed_at < receipt.delivered_at:
            raise CommunicationError("observation cannot precede delivery")
        if not evidence_ref.strip():
            raise CommunicationError("observation evidence reference must be non-empty")
        updated = replace(
            receipt,
            state=CommunicationState.OBSERVED,
            observed_at=observed_at,
            observation_evidence_ref=evidence_ref,
        )
        self._receipts[receipt_id] = updated
        return updated

    def revoke(self, receipt_id: str) -> CommunicationReceipt:
        receipt = self.get(receipt_id)
        updated = replace(receipt, state=CommunicationState.REVOKED)
        self._receipts[receipt_id] = updated
        return updated

    def decision_usable(
        self,
        receipt_id: str,
        recipient_principal_ref: str,
        *,
        decision_time: int | float,
    ) -> bool:
        receipt = self.get(receipt_id)
        if receipt.recipient_principal_ref != recipient_principal_ref:
            return False
        if receipt.state != CommunicationState.OBSERVED or receipt.observed_at is None:
            return False
        if receipt.observed_at > decision_time:
            return False
        if receipt.valid_until is not None and decision_time > receipt.valid_until:
            return False
        return True

    def all(self) -> tuple[CommunicationReceipt, ...]:
        return tuple(self._receipts.values())
