from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .execution import ReconciliationEvidence
from .hashing import digest
from .types import AuthorizationError


class DispatchAcknowledgementClass(str, Enum):
    NONE = "none"
    TRANSPORT_ONLY = "transport_only"
    DURABLE_REMOTE = "durable_remote"


class IdempotencyGuaranteeClass(str, Enum):
    NONE = "none"
    CALLER_ASSERTED = "caller_asserted"
    REMOTE_DEDUPLICATED = "remote_deduplicated"


class CancellationClass(str, Enum):
    UNSUPPORTED = "unsupported"
    PRE_DISPATCH_ONLY = "pre_dispatch_only"
    REMOTE_BEST_EFFORT = "remote_best_effort"
    REMOTE_ACKNOWLEDGED = "remote_acknowledged"
    FENCED_EFFECT = "fenced_effect"


class OutcomeFinalityClass(str, Enum):
    UNKNOWN = "unknown"
    OBSERVABLE = "observable"
    FINAL = "final"


class CompensationStatus(str, Enum):
    AUTHORIZED = "authorized"
    UNKNOWN = "unknown"
    APPLIED = "applied"
    FAILED = "failed"


def _required(name: str, value: object) -> str:
    text = str(value).strip()
    if not text:
        raise AuthorizationError(f"{name} must be non-empty")
    return text


@dataclass(frozen=True, slots=True)
class ExecutionContract:
    adapter_id: str
    adapter_revision: int
    dispatch_acknowledgement: DispatchAcknowledgementClass
    idempotency_guarantee: IdempotencyGuaranteeClass
    deduplication_keys: bool
    remote_fencing_tokens: bool
    cancellation_class: CancellationClass
    cancellation_ack_assurance: float
    compensation_supported: bool
    reconciliation_observable: bool
    outcome_finality: OutcomeFinalityClass
    canonical_digest: str

    @classmethod
    def create(
        cls,
        *,
        adapter_id: str,
        adapter_revision: int,
        dispatch_acknowledgement: DispatchAcknowledgementClass | str,
        idempotency_guarantee: IdempotencyGuaranteeClass | str,
        deduplication_keys: bool,
        remote_fencing_tokens: bool,
        cancellation_class: CancellationClass | str,
        cancellation_ack_assurance: float,
        compensation_supported: bool,
        reconciliation_observable: bool,
        outcome_finality: OutcomeFinalityClass | str,
    ) -> "ExecutionContract":
        adapter = _required("adapter_id", adapter_id)
        revision = int(adapter_revision)
        assurance = float(cancellation_ack_assurance)
        if revision < 1:
            raise AuthorizationError("execution contract adapter revision must be positive")
        if not 0.0 <= assurance <= 1.0:
            raise AuthorizationError("cancellation acknowledgement assurance must be within [0, 1]")
        dispatch = DispatchAcknowledgementClass(dispatch_acknowledgement)
        idempotency = IdempotencyGuaranteeClass(idempotency_guarantee)
        cancellation = CancellationClass(cancellation_class)
        finality = OutcomeFinalityClass(outcome_finality)
        if idempotency == IdempotencyGuaranteeClass.REMOTE_DEDUPLICATED and not deduplication_keys:
            raise AuthorizationError("remote deduplication guarantee requires deduplication-key support")
        if cancellation in {CancellationClass.REMOTE_ACKNOWLEDGED, CancellationClass.FENCED_EFFECT}:
            if assurance < 0.8:
                raise AuthorizationError("acknowledged cancellation requires assurance >= 0.8")
            if dispatch != DispatchAcknowledgementClass.DURABLE_REMOTE:
                raise AuthorizationError("acknowledged cancellation requires durable remote dispatch acknowledgement")
        if cancellation == CancellationClass.FENCED_EFFECT and not remote_fencing_tokens:
            raise AuthorizationError("fenced-effect cancellation requires remote fencing-token support")
        body = {
            "adapter_id": adapter,
            "adapter_revision": revision,
            "dispatch_acknowledgement": dispatch.value,
            "idempotency_guarantee": idempotency.value,
            "deduplication_keys": bool(deduplication_keys),
            "remote_fencing_tokens": bool(remote_fencing_tokens),
            "cancellation_class": cancellation.value,
            "cancellation_ack_assurance": assurance,
            "compensation_supported": bool(compensation_supported),
            "reconciliation_observable": bool(reconciliation_observable),
            "outcome_finality": finality.value,
        }
        return cls(
            adapter_id=adapter,
            adapter_revision=revision,
            dispatch_acknowledgement=dispatch,
            idempotency_guarantee=idempotency,
            deduplication_keys=bool(deduplication_keys),
            remote_fencing_tokens=bool(remote_fencing_tokens),
            cancellation_class=cancellation,
            cancellation_ack_assurance=assurance,
            compensation_supported=bool(compensation_supported),
            reconciliation_observable=bool(reconciliation_observable),
            outcome_finality=finality,
            canonical_digest=digest(body),
        )

    def canonical_payload(self) -> dict[str, object]:
        return {
            "adapter_id": self.adapter_id,
            "adapter_revision": self.adapter_revision,
            "dispatch_acknowledgement": self.dispatch_acknowledgement.value,
            "idempotency_guarantee": self.idempotency_guarantee.value,
            "deduplication_keys": self.deduplication_keys,
            "remote_fencing_tokens": self.remote_fencing_tokens,
            "cancellation_class": self.cancellation_class.value,
            "cancellation_ack_assurance": self.cancellation_ack_assurance,
            "compensation_supported": self.compensation_supported,
            "reconciliation_observable": self.reconciliation_observable,
            "outcome_finality": self.outcome_finality.value,
            "canonical_digest": self.canonical_digest,
        }

    @classmethod
    def from_payload(cls, raw: dict[str, object]) -> "ExecutionContract":
        value = cls.create(
            adapter_id=str(raw["adapter_id"]),
            adapter_revision=int(raw["adapter_revision"]),
            dispatch_acknowledgement=str(raw["dispatch_acknowledgement"]),
            idempotency_guarantee=str(raw["idempotency_guarantee"]),
            deduplication_keys=bool(raw["deduplication_keys"]),
            remote_fencing_tokens=bool(raw["remote_fencing_tokens"]),
            cancellation_class=str(raw["cancellation_class"]),
            cancellation_ack_assurance=float(raw["cancellation_ack_assurance"]),
            compensation_supported=bool(raw["compensation_supported"]),
            reconciliation_observable=bool(raw["reconciliation_observable"]),
            outcome_finality=str(raw["outcome_finality"]),
        )
        if value.canonical_digest != str(raw.get("canonical_digest", "")):
            raise AuthorizationError("execution contract canonical digest mismatch")
        return value

    def require_for_strong_dispatch(self, *, action_idempotent: bool) -> bool:
        if self.dispatch_acknowledgement != DispatchAcknowledgementClass.DURABLE_REMOTE:
            raise AuthorizationError("strong production dispatch requires durable remote acknowledgement")
        if not self.reconciliation_observable:
            raise AuthorizationError("strong production dispatch requires observable reconciliation")
        if self.outcome_finality == OutcomeFinalityClass.UNKNOWN:
            raise AuthorizationError("strong production dispatch cannot use unknown outcome-finality semantics")
        if not action_idempotent and self.idempotency_guarantee == IdempotencyGuaranteeClass.CALLER_ASSERTED:
            raise AuthorizationError("non-idempotent strong dispatch cannot rely on caller-asserted idempotency")
        return True


@dataclass(frozen=True, slots=True)
class RemoteCancellationAcknowledgement:
    acknowledgement_id: str
    transaction_id: str
    action_id: str
    authorization_id: str
    canonical_principal_ref: str
    adapter_id: str
    adapter_revision: int
    authority_epoch: int
    effect_prevented: bool
    fence_excludes_stale_effect: bool
    observed_at: int | float
    assurance: float
    provenance: str
    canonical_digest: str

    @classmethod
    def create(
        cls,
        *,
        acknowledgement_id: str,
        transaction_id: str,
        action_id: str,
        authorization_id: str,
        canonical_principal_ref: str,
        adapter_id: str,
        adapter_revision: int,
        authority_epoch: int,
        effect_prevented: bool,
        fence_excludes_stale_effect: bool,
        observed_at: int | float,
        assurance: float,
        provenance: str,
    ) -> "RemoteCancellationAcknowledgement":
        values = {
            "acknowledgement_id": _required("acknowledgement_id", acknowledgement_id),
            "transaction_id": _required("transaction_id", transaction_id),
            "action_id": _required("action_id", action_id),
            "authorization_id": _required("authorization_id", authorization_id),
            "canonical_principal_ref": _required("canonical_principal_ref", canonical_principal_ref),
            "adapter_id": _required("adapter_id", adapter_id),
            "provenance": _required("provenance", provenance),
        }
        revision = int(adapter_revision)
        epoch = int(authority_epoch)
        assurance_value = float(assurance)
        if revision < 1:
            raise AuthorizationError("cancellation acknowledgement adapter revision must be positive")
        if epoch < 1:
            raise AuthorizationError("cancellation acknowledgement authority epoch must be positive")
        if not 0.0 <= assurance_value <= 1.0:
            raise AuthorizationError("cancellation acknowledgement assurance must be within [0, 1]")
        body = {
            **values,
            "adapter_revision": revision,
            "authority_epoch": epoch,
            "effect_prevented": bool(effect_prevented),
            "fence_excludes_stale_effect": bool(fence_excludes_stale_effect),
            "observed_at": observed_at,
            "assurance": assurance_value,
        }
        return cls(**body, canonical_digest=digest(body))

    def canonical_payload(self) -> dict[str, object]:
        return {
            "acknowledgement_id": self.acknowledgement_id,
            "transaction_id": self.transaction_id,
            "action_id": self.action_id,
            "authorization_id": self.authorization_id,
            "canonical_principal_ref": self.canonical_principal_ref,
            "adapter_id": self.adapter_id,
            "adapter_revision": self.adapter_revision,
            "authority_epoch": self.authority_epoch,
            "effect_prevented": self.effect_prevented,
            "fence_excludes_stale_effect": self.fence_excludes_stale_effect,
            "observed_at": self.observed_at,
            "assurance": self.assurance,
            "provenance": self.provenance,
            "canonical_digest": self.canonical_digest,
        }

    @classmethod
    def from_payload(cls, raw: dict[str, object]) -> "RemoteCancellationAcknowledgement":
        value = cls.create(
            acknowledgement_id=str(raw["acknowledgement_id"]),
            transaction_id=str(raw["transaction_id"]),
            action_id=str(raw["action_id"]),
            authorization_id=str(raw["authorization_id"]),
            canonical_principal_ref=str(raw["canonical_principal_ref"]),
            adapter_id=str(raw["adapter_id"]),
            adapter_revision=int(raw["adapter_revision"]),
            authority_epoch=int(raw["authority_epoch"]),
            effect_prevented=bool(raw["effect_prevented"]),
            fence_excludes_stale_effect=bool(raw["fence_excludes_stale_effect"]),
            observed_at=raw["observed_at"],
            assurance=float(raw["assurance"]),
            provenance=str(raw["provenance"]),
        )
        if value.canonical_digest != str(raw.get("canonical_digest", "")):
            raise AuthorizationError("cancellation acknowledgement canonical digest mismatch")
        return value

    def as_reconciliation_evidence(self) -> ReconciliationEvidence:
        return ReconciliationEvidence.create(
            evidence_id=self.acknowledgement_id,
            transaction_id=self.transaction_id,
            action_id=self.action_id,
            authorization_id=self.authorization_id,
            canonical_principal_ref=self.canonical_principal_ref,
            adapter_id=self.adapter_id,
            adapter_revision=self.adapter_revision,
            outcome_applied=not self.effect_prevented,
            source=f"remote-cancellation:{self.provenance}",
            observed_at=self.observed_at,
            assurance=self.assurance,
        )


def validate_remote_cancellation_acknowledgement(
    acknowledgement: RemoteCancellationAcknowledgement,
    contract: ExecutionContract,
    *,
    transaction_id: str,
    action_id: str,
    authorization_id: str,
    principal_ref: str,
    authority_epoch: int,
    minimum_assurance: float = 0.8,
) -> bool:
    if contract.cancellation_class not in {CancellationClass.REMOTE_ACKNOWLEDGED, CancellationClass.FENCED_EFFECT}:
        raise AuthorizationError("adapter cancellation contract cannot produce a clean remote cancellation")
    if acknowledgement.transaction_id != transaction_id:
        raise AuthorizationError("remote cancellation transaction mismatch")
    if acknowledgement.action_id != action_id:
        raise AuthorizationError("remote cancellation action mismatch")
    if acknowledgement.authorization_id != authorization_id:
        raise AuthorizationError("remote cancellation authorization mismatch")
    if acknowledgement.canonical_principal_ref != principal_ref:
        raise AuthorizationError("remote cancellation principal mismatch")
    if acknowledgement.adapter_id != contract.adapter_id or acknowledgement.adapter_revision != contract.adapter_revision:
        raise AuthorizationError("remote cancellation adapter revision mismatch")
    if acknowledgement.authority_epoch != int(authority_epoch):
        raise AuthorizationError("remote cancellation authority epoch mismatch")
    required_assurance = max(float(minimum_assurance), contract.cancellation_ack_assurance)
    if acknowledgement.assurance < required_assurance:
        raise AuthorizationError("remote cancellation acknowledgement assurance below required floor")
    if not acknowledgement.effect_prevented:
        raise AuthorizationError("remote cancellation acknowledgement does not prove the effect was prevented")
    if contract.cancellation_class == CancellationClass.FENCED_EFFECT:
        if not contract.remote_fencing_tokens or not acknowledgement.fence_excludes_stale_effect:
            raise AuthorizationError("fenced-effect cancellation lacks stale-effect exclusion evidence")
    return True


@dataclass(frozen=True, slots=True)
class CompensationRecord:
    record_id: str
    original_transaction_id: str
    compensation_transaction_id: str
    compensation_authorization_id: str
    original_outcome_applied: bool
    status: CompensationStatus
    evidence_ref: str | None
    canonical_digest: str

    @classmethod
    def create(
        cls,
        *,
        record_id: str,
        original_transaction_id: str,
        compensation_transaction_id: str,
        compensation_authorization_id: str,
        original_outcome_applied: bool,
        status: CompensationStatus | str = CompensationStatus.AUTHORIZED,
        evidence_ref: str | None = None,
    ) -> "CompensationRecord":
        record = _required("record_id", record_id)
        original = _required("original_transaction_id", original_transaction_id)
        compensation = _required("compensation_transaction_id", compensation_transaction_id)
        authorization = _required("compensation_authorization_id", compensation_authorization_id)
        if original == compensation:
            raise AuthorizationError("compensation must use a distinct transaction")
        status_value = CompensationStatus(status)
        evidence = None if evidence_ref is None else _required("evidence_ref", evidence_ref)
        if status_value != CompensationStatus.AUTHORIZED and evidence is None:
            raise AuthorizationError("observed compensation status requires evidence")
        body = {
            "record_id": record,
            "original_transaction_id": original,
            "compensation_transaction_id": compensation,
            "compensation_authorization_id": authorization,
            "original_outcome_applied": bool(original_outcome_applied),
            "status": status_value.value,
            "evidence_ref": evidence,
        }
        return cls(
            record_id=record,
            original_transaction_id=original,
            compensation_transaction_id=compensation,
            compensation_authorization_id=authorization,
            original_outcome_applied=bool(original_outcome_applied),
            status=status_value,
            evidence_ref=evidence,
            canonical_digest=digest(body),
        )

    def transition(self, status: CompensationStatus | str, *, evidence_ref: str) -> "CompensationRecord":
        target = CompensationStatus(status)
        if self.status in {CompensationStatus.APPLIED, CompensationStatus.FAILED}:
            raise AuthorizationError("terminal compensation record cannot transition")
        if target == CompensationStatus.AUTHORIZED:
            raise AuthorizationError("compensation cannot transition back to authorized")
        return CompensationRecord.create(
            record_id=self.record_id,
            original_transaction_id=self.original_transaction_id,
            compensation_transaction_id=self.compensation_transaction_id,
            compensation_authorization_id=self.compensation_authorization_id,
            original_outcome_applied=self.original_outcome_applied,
            status=target,
            evidence_ref=evidence_ref,
        )

    def canonical_payload(self) -> dict[str, object]:
        return {
            "record_id": self.record_id,
            "original_transaction_id": self.original_transaction_id,
            "compensation_transaction_id": self.compensation_transaction_id,
            "compensation_authorization_id": self.compensation_authorization_id,
            "original_outcome_applied": self.original_outcome_applied,
            "status": self.status.value,
            "evidence_ref": self.evidence_ref,
            "canonical_digest": self.canonical_digest,
        }

    @classmethod
    def from_payload(cls, raw: dict[str, object]) -> "CompensationRecord":
        value = cls.create(
            record_id=str(raw["record_id"]),
            original_transaction_id=str(raw["original_transaction_id"]),
            compensation_transaction_id=str(raw["compensation_transaction_id"]),
            compensation_authorization_id=str(raw["compensation_authorization_id"]),
            original_outcome_applied=bool(raw["original_outcome_applied"]),
            status=str(raw["status"]),
            evidence_ref=raw.get("evidence_ref"),
        )
        if value.canonical_digest != str(raw.get("canonical_digest", "")):
            raise AuthorizationError("compensation record canonical digest mismatch")
        return value
