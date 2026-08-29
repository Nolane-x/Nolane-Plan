from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum

from .hashing import digest
from .identity import PrincipalBindingRevision
from .types import AuthorizationError, RiskClass


@dataclass(frozen=True, slots=True)
class AdapterProfile:
    adapter_id: str
    revision: int
    principal_attestation: bool
    dispatch_fence: bool
    postcondition_assurance: float

    @property
    def capability_digest(self) -> str:
        return digest({
            "adapter_id": self.adapter_id,
            "revision": self.revision,
            "principal_attestation": self.principal_attestation,
            "dispatch_fence": self.dispatch_fence,
            "postcondition_assurance": self.postcondition_assurance,
        })

    def require_for(self, risk_class: RiskClass, executor_sensitive: bool = False) -> None:
        if executor_sensitive and (not self.principal_attestation or not self.dispatch_fence):
            raise AuthorizationError("adapter cannot strongly attest/fence the acting principal")
        if risk_class in {RiskClass.CONSEQUENTIAL, RiskClass.IRREVERSIBLE} and self.postcondition_assurance < 0.8:
            raise AuthorizationError("adapter postcondition assurance below consequential floor")


@dataclass(frozen=True, slots=True)
class DispatchAttestation:
    attestation_id: str
    authorization_id: str
    transaction_id: str
    action_id: str
    adapter_id: str
    adapter_revision: int
    canonical_principal_ref: str
    principal_attestation_id: str
    observed_at: int | float
    assurance: float
    provenance: str
    provenance_digest: str

    @classmethod
    def create(
        cls,
        *,
        attestation_id: str,
        authorization_id: str,
        transaction_id: str,
        action_id: str,
        adapter_id: str,
        adapter_revision: int,
        canonical_principal_ref: str,
        principal_attestation_id: str,
        observed_at: int | float,
        assurance: float,
        provenance: str,
    ) -> "DispatchAttestation":
        if not 0.0 <= assurance <= 1.0:
            raise AuthorizationError("dispatch attestation assurance must be within [0, 1]")
        values = (
            attestation_id,
            authorization_id,
            transaction_id,
            action_id,
            adapter_id,
            canonical_principal_ref,
            principal_attestation_id,
            provenance,
        )
        if any(not value.strip() for value in values):
            raise AuthorizationError("dispatch attestation references must be non-empty")
        if adapter_revision < 1:
            raise AuthorizationError("dispatch adapter revision must be positive")
        body = {
            "attestation_id": attestation_id,
            "authorization_id": authorization_id,
            "transaction_id": transaction_id,
            "action_id": action_id,
            "adapter_id": adapter_id,
            "adapter_revision": adapter_revision,
            "canonical_principal_ref": canonical_principal_ref,
            "principal_attestation_id": principal_attestation_id,
            "observed_at": observed_at,
            "assurance": assurance,
            "provenance": provenance,
        }
        return cls(
            attestation_id=attestation_id,
            authorization_id=authorization_id,
            transaction_id=transaction_id,
            action_id=action_id,
            adapter_id=adapter_id,
            adapter_revision=adapter_revision,
            canonical_principal_ref=canonical_principal_ref,
            principal_attestation_id=principal_attestation_id,
            observed_at=observed_at,
            assurance=assurance,
            provenance=provenance,
            provenance_digest=digest(body),
        )


def verify_dispatch_attestation(
    attestation: DispatchAttestation,
    *,
    authorization_id: str,
    transaction_id: str,
    action_id: str,
    expected_principal_ref: str,
    adapter_id: str,
    adapter_revision: int,
    principal_binding: PrincipalBindingRevision,
    minimum_assurance: float = 0.8,
) -> bool:
    if attestation.authorization_id != authorization_id:
        raise AuthorizationError("dispatch attestation authorization mismatch")
    if attestation.transaction_id != transaction_id:
        raise AuthorizationError("dispatch attestation transaction mismatch")
    if attestation.action_id != action_id:
        raise AuthorizationError("dispatch attestation action mismatch")
    if attestation.adapter_id != adapter_id or attestation.adapter_revision != adapter_revision:
        raise AuthorizationError("dispatch attestation adapter revision mismatch")
    if attestation.canonical_principal_ref != expected_principal_ref:
        raise AuthorizationError("dispatch attestation principal mismatch")
    if principal_binding.canonical_principal_ref != expected_principal_ref:
        raise AuthorizationError("current host principal binding mismatch")
    if attestation.principal_attestation_id != principal_binding.attestation_id:
        raise AuthorizationError("dispatch identity evidence is not the current principal binding")
    if principal_binding.assurance < minimum_assurance or attestation.assurance < minimum_assurance:
        raise AuthorizationError("dispatch identity assurance below required floor")
    return True


@dataclass(frozen=True, slots=True)
class ReconciliationEvidence:
    evidence_id: str
    transaction_id: str
    action_id: str
    authorization_id: str
    canonical_principal_ref: str
    adapter_id: str
    adapter_revision: int
    outcome_applied: bool
    source: str
    observed_at: int | float
    assurance: float
    provenance_digest: str

    @classmethod
    def create(
        cls,
        *,
        evidence_id: str,
        transaction_id: str,
        action_id: str,
        authorization_id: str,
        canonical_principal_ref: str,
        adapter_id: str,
        adapter_revision: int,
        outcome_applied: bool,
        source: str,
        observed_at: int | float,
        assurance: float,
    ) -> "ReconciliationEvidence":
        if not 0.0 <= assurance <= 1.0:
            raise AuthorizationError("reconciliation assurance must be within [0, 1]")
        values = (
            evidence_id,
            transaction_id,
            action_id,
            authorization_id,
            canonical_principal_ref,
            adapter_id,
            source,
        )
        if any(not value.strip() for value in values):
            raise AuthorizationError("reconciliation evidence references must be non-empty")
        if adapter_revision < 1:
            raise AuthorizationError("reconciliation adapter revision must be positive")
        body = {
            "evidence_id": evidence_id,
            "transaction_id": transaction_id,
            "action_id": action_id,
            "authorization_id": authorization_id,
            "canonical_principal_ref": canonical_principal_ref,
            "adapter_id": adapter_id,
            "adapter_revision": adapter_revision,
            "outcome_applied": outcome_applied,
            "source": source,
            "observed_at": observed_at,
            "assurance": assurance,
        }
        return cls(
            evidence_id=evidence_id,
            transaction_id=transaction_id,
            action_id=action_id,
            authorization_id=authorization_id,
            canonical_principal_ref=canonical_principal_ref,
            adapter_id=adapter_id,
            adapter_revision=adapter_revision,
            outcome_applied=outcome_applied,
            source=source,
            observed_at=observed_at,
            assurance=assurance,
            provenance_digest=digest(body),
        )


class TransactionState(str, Enum):
    AUTHORIZED = "authorized"
    DISPATCH_RECORDED = "dispatch_recorded"
    OUTCOME_OBSERVED = "outcome_observed"
    RECONCILIATION_REQUIRED = "reconciliation_required"
    RECONCILED_APPLIED = "reconciled_applied"
    RECONCILED_NOT_APPLIED = "reconciled_not_applied"
    COMMITTED = "committed"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class ActionTransaction:
    id: str
    action_id: str
    authorization_id: str
    principal_ref: str
    idempotent: bool
    state: TransactionState = TransactionState.AUTHORIZED
    adapter_id: str | None = None
    adapter_revision: int | None = None
    detail: str | None = None


class ActionTransactionLedger:
    """Durable action protocol state, separate from transport success."""

    def __init__(self) -> None:
        self._items: dict[str, ActionTransaction] = {}

    def authorized(
        self,
        transaction_id: str,
        action_id: str,
        authorization_id: str,
        principal_ref: str,
        idempotent: bool,
    ) -> ActionTransaction:
        if transaction_id in self._items:
            raise ValueError(transaction_id)
        item = ActionTransaction(transaction_id, action_id, authorization_id, principal_ref, idempotent)
        self._items[item.id] = item
        return item

    def restore(self, item: ActionTransaction) -> ActionTransaction:
        if item.id in self._items:
            raise ValueError(item.id)
        self._items[item.id] = item
        return item

    def get(self, transaction_id: str) -> ActionTransaction:
        return self._items[transaction_id]

    def _set(self, transaction_id: str, **changes) -> ActionTransaction:
        item = replace(self.get(transaction_id), **changes)
        self._items[transaction_id] = item
        return item

    def record_dispatch(self, transaction_id: str, adapter_id: str, adapter_revision: int) -> ActionTransaction:
        item = self.get(transaction_id)
        if item.state not in {TransactionState.AUTHORIZED, TransactionState.RECONCILED_NOT_APPLIED}:
            raise AuthorizationError(f"transaction cannot dispatch from {item.state.value}")
        return self._set(
            transaction_id,
            state=TransactionState.DISPATCH_RECORDED,
            adapter_id=adapter_id,
            adapter_revision=adapter_revision,
        )

    def record_outcome(self, transaction_id: str, detail: str | None = None) -> ActionTransaction:
        item = self.get(transaction_id)
        if item.state != TransactionState.DISPATCH_RECORDED:
            raise AuthorizationError("outcome without recorded dispatch")
        return self._set(transaction_id, state=TransactionState.OUTCOME_OBSERVED, detail=detail)

    def record_unknown_outcome(self, transaction_id: str, detail: str) -> ActionTransaction:
        item = self.get(transaction_id)
        if item.state != TransactionState.DISPATCH_RECORDED:
            raise AuthorizationError("unknown outcome without recorded dispatch")
        return self._set(transaction_id, state=TransactionState.RECONCILIATION_REQUIRED, detail=detail)

    def assert_retry_allowed(self, transaction_id: str) -> bool:
        item = self.get(transaction_id)
        if item.state == TransactionState.RECONCILIATION_REQUIRED and not item.idempotent:
            raise AuthorizationError("non-idempotent action requires trusted reconciliation before retry")
        if item.state in {TransactionState.COMMITTED, TransactionState.RECONCILED_APPLIED}:
            raise AuthorizationError("action already applied")
        return True

    def reconcile(self, transaction_id: str, outcome_applied: bool, trusted: bool) -> ActionTransaction:
        """Wave-2 compatibility path.

        New strong kernel code must use `reconcile_with_evidence`; this method remains
        only so historical reference callers do not break while Wave 3 migrates the
        correctness path away from caller-supplied trust booleans.
        """
        item = self.get(transaction_id)
        if item.state != TransactionState.RECONCILIATION_REQUIRED:
            raise AuthorizationError("transaction is not awaiting reconciliation")
        if not trusted:
            raise AuthorizationError("reconciliation evidence is not trusted")
        state = TransactionState.RECONCILED_APPLIED if outcome_applied else TransactionState.RECONCILED_NOT_APPLIED
        return self._set(transaction_id, state=state)

    def reconcile_with_evidence(
        self,
        transaction_id: str,
        evidence: ReconciliationEvidence,
        *,
        minimum_assurance: float = 0.8,
    ) -> ActionTransaction:
        item = self.get(transaction_id)
        if item.state != TransactionState.RECONCILIATION_REQUIRED:
            raise AuthorizationError("transaction is not awaiting reconciliation")
        if evidence.transaction_id != item.id:
            raise AuthorizationError("reconciliation evidence transaction mismatch")
        if evidence.action_id != item.action_id:
            raise AuthorizationError("reconciliation evidence action mismatch")
        if evidence.authorization_id != item.authorization_id:
            raise AuthorizationError("reconciliation evidence authorization mismatch")
        if evidence.canonical_principal_ref != item.principal_ref:
            raise AuthorizationError("reconciliation evidence principal mismatch")
        if item.adapter_id is None or item.adapter_revision is None:
            raise AuthorizationError("transaction has no recorded adapter dispatch context")
        if evidence.adapter_id != item.adapter_id or evidence.adapter_revision != item.adapter_revision:
            raise AuthorizationError("reconciliation evidence adapter revision mismatch")
        if evidence.assurance < minimum_assurance:
            raise AuthorizationError("reconciliation evidence assurance below required floor")
        state = TransactionState.RECONCILED_APPLIED if evidence.outcome_applied else TransactionState.RECONCILED_NOT_APPLIED
        return self._set(transaction_id, state=state, detail=f"reconciled:{evidence.evidence_id}")

    def commit(self, transaction_id: str) -> ActionTransaction:
        item = self.get(transaction_id)
        if item.state not in {TransactionState.OUTCOME_OBSERVED, TransactionState.RECONCILED_APPLIED}:
            raise AuthorizationError("transaction cannot commit before observed/reconciled outcome")
        return self._set(transaction_id, state=TransactionState.COMMITTED)

    def all(self) -> tuple[ActionTransaction, ...]:
        return tuple(self._items.values())
