from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum

from .hashing import digest
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
        return None


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
    """MUTANT: adapter assurance intentionally bypassed; transaction logic retained."""

    def __init__(self) -> None:
        self._items: dict[str, ActionTransaction] = {}

    def authorized(self, transaction_id: str, action_id: str, authorization_id: str, principal_ref: str, idempotent: bool) -> ActionTransaction:
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
        return self._set(transaction_id, state=TransactionState.DISPATCH_RECORDED, adapter_id=adapter_id, adapter_revision=adapter_revision)

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
        item = self.get(transaction_id)
        if item.state != TransactionState.RECONCILIATION_REQUIRED:
            raise AuthorizationError("transaction is not awaiting reconciliation")
        if not trusted:
            raise AuthorizationError("reconciliation evidence is not trusted")
        state = TransactionState.RECONCILED_APPLIED if outcome_applied else TransactionState.RECONCILED_NOT_APPLIED
        return self._set(transaction_id, state=state)

    def commit(self, transaction_id: str) -> ActionTransaction:
        item = self.get(transaction_id)
        if item.state not in {TransactionState.OUTCOME_OBSERVED, TransactionState.RECONCILED_APPLIED}:
            raise AuthorizationError("transaction cannot commit before observed/reconciled outcome")
        return self._set(transaction_id, state=TransactionState.COMMITTED)

    def all(self) -> tuple[ActionTransaction, ...]:
        return tuple(self._items.values())
