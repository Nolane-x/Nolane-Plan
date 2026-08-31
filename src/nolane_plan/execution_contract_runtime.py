from __future__ import annotations

from .execution import TransactionState
from .execution_contract import (
    CompensationRecord,
    CompensationStatus,
    ExecutionContract,
    RemoteCancellationAcknowledgement,
    validate_remote_cancellation_acknowledgement,
)
from .replay_registry import DEFAULT_REPLAY_REGISTRY, ReplayEventClass, ReplayEventSpec
from .types import AuthorizationError, ReplayError


_EVENT_SPECS = (
    ("execution.contract_registered", "execution_contract_registered"),
    ("action.execution_contract_bound", "action_execution_contract_bound"),
    ("action.remote_cancellation_acknowledged", "action_remote_cancellation_acknowledged"),
    ("action.compensation_registered", "action_compensation_registered"),
    ("action.compensation_updated", "action_compensation_updated"),
)


def _contract_key(adapter_id: str, adapter_revision: int) -> str:
    return f"{adapter_id}@{int(adapter_revision)}"


def _register_replay_events() -> None:
    for event_type, reducer_name in _EVENT_SPECS:
        if event_type in DEFAULT_REPLAY_REGISTRY.event_types:
            continue
        spec = ReplayEventSpec(
            event_type,
            ReplayEventClass.STATE_REDUCER,
            correctness_significant=True,
            reducer_name=reducer_name,
        )
        DEFAULT_REPLAY_REGISTRY._specs = (*DEFAULT_REPLAY_REGISTRY._specs, spec)
        DEFAULT_REPLAY_REGISTRY._by_event[event_type] = spec


def _install_state(self) -> None:
    self.execution_contracts: dict[str, ExecutionContract] = {}
    self.authorization_execution_contract_bindings: dict[str, str] = {}
    self.remote_cancellation_acknowledgements: dict[str, RemoteCancellationAcknowledgement] = {}
    self.compensation_records: dict[str, CompensationRecord] = {}


def _register_execution_contract(self, contract: ExecutionContract) -> ExecutionContract:
    with self._writer_lock:
        profile = self.adapters.get(contract.adapter_id)
        if profile is None:
            raise AuthorizationError("execution contract references an unknown adapter")
        if profile.revision != contract.adapter_revision:
            raise AuthorizationError("execution contract adapter revision is not current")
        key = _contract_key(contract.adapter_id, contract.adapter_revision)
        existing = self.execution_contracts.get(key)
        if existing is not None:
            if existing.canonical_digest != contract.canonical_digest:
                raise AuthorizationError("execution contract revision cannot be rebound")
            return existing
        self.execution_contracts[key] = contract
        self._record("execution.contract_registered", {"contract": contract.canonical_payload()})
        return contract


def _execution_contract_for(self, adapter_id: str, adapter_revision: int) -> ExecutionContract:
    key = _contract_key(adapter_id, adapter_revision)
    contract = self.execution_contracts.get(key)
    if contract is None:
        raise AuthorizationError("adapter revision has no Wave-9 execution contract")
    return contract


def _bind_authorization_execution_contract(self, authorization_id: str) -> ExecutionContract:
    with self._writer_lock:
        authorization = self.authorizations.get(authorization_id)
        if authorization is None:
            raise AuthorizationError("unknown authorization for execution-contract binding")
        if authorization.adapter_id is None or authorization.adapter_revision is None:
            raise AuthorizationError("execution-contract binding requires adapter-bound authorization")
        contract = self.execution_contract_for(authorization.adapter_id, authorization.adapter_revision)
        action = self.actions[authorization.action_id]
        contract.require_for_strong_dispatch(action_idempotent=action.idempotent)
        current_profile = self.adapters.get(authorization.adapter_id)
        if current_profile is None or current_profile.revision != authorization.adapter_revision:
            raise AuthorizationError("adapter capability revision changed before execution-contract binding")
        existing = self.authorization_execution_contract_bindings.get(authorization_id)
        if existing is not None:
            if existing != contract.canonical_digest:
                raise AuthorizationError("authorization execution-contract binding cannot be rebound")
            return contract
        self.authorization_execution_contract_bindings[authorization_id] = contract.canonical_digest
        self._record(
            "action.execution_contract_bound",
            {
                "authorization_id": authorization_id,
                "adapter_id": contract.adapter_id,
                "adapter_revision": contract.adapter_revision,
                "execution_contract_digest": contract.canonical_digest,
            },
        )
        return contract


def _assert_authorization_execution_contract_current(self, authorization_id: str) -> ExecutionContract:
    authorization = self.authorizations.get(authorization_id)
    if authorization is None:
        raise AuthorizationError("unknown authorization for execution-contract check")
    if authorization.adapter_id is None or authorization.adapter_revision is None:
        raise AuthorizationError("authorization is not adapter-bound")
    bound_digest = self.authorization_execution_contract_bindings.get(authorization_id)
    if bound_digest is None:
        raise AuthorizationError("authorization has no Wave-9 execution-contract binding")
    profile = self.adapters.get(authorization.adapter_id)
    if profile is None or profile.revision != authorization.adapter_revision:
        raise AuthorizationError("adapter capability revision is stale")
    contract = self.execution_contract_for(authorization.adapter_id, authorization.adapter_revision)
    if contract.canonical_digest != bound_digest:
        raise AuthorizationError("authorization execution-contract binding is stale")
    action = self.actions[authorization.action_id]
    contract.require_for_strong_dispatch(action_idempotent=action.idempotent)
    return contract


def _dispatch_contract_bound(
    self,
    authorization_id: str,
    presented_principal_ref: str,
    adapter,
    now: int | float,
    *,
    emergency_authorized: bool = False,
):
    with self._writer_lock:
        self.assert_authorization_execution_contract_current(authorization_id)
        return self.dispatch(
            authorization_id,
            presented_principal_ref,
            adapter,
            now,
            emergency_authorized=emergency_authorized,
        )


def _record_remote_cancellation_acknowledgement(
    self,
    authorization_id: str,
    acknowledgement: RemoteCancellationAcknowledgement,
    *,
    authority_epoch: int,
    minimum_assurance: float = 0.8,
):
    with self._writer_lock:
        contract = self.assert_authorization_execution_contract_current(authorization_id)
        tx = self.transaction_for_authorization(authorization_id)
        if tx.state != TransactionState.CANCELLATION_PENDING:
            raise AuthorizationError("remote cancellation acknowledgement requires cancellation-pending transaction")
        if acknowledgement.acknowledgement_id in self.remote_cancellation_acknowledgements:
            raise AuthorizationError("remote cancellation acknowledgement was already consumed")
        validate_remote_cancellation_acknowledgement(
            acknowledgement,
            contract,
            transaction_id=tx.id,
            action_id=tx.action_id,
            authorization_id=authorization_id,
            principal_ref=tx.principal_ref,
            authority_epoch=authority_epoch,
            minimum_assurance=minimum_assurance,
        )
        evidence = acknowledgement.as_reconciliation_evidence()
        reconciled = self.transactions.reconcile_with_evidence(
            tx.id,
            evidence,
            minimum_assurance=max(minimum_assurance, contract.cancellation_ack_assurance),
        )
        self.remote_cancellation_acknowledgements[acknowledgement.acknowledgement_id] = acknowledgement
        self._record(
            "action.remote_cancellation_acknowledged",
            {
                "authorization_id": authorization_id,
                "execution_contract_digest": contract.canonical_digest,
                "acknowledgement": acknowledgement.canonical_payload(),
                "resulting_state": reconciled.state.value,
            },
        )
        return reconciled


def _register_compensation(self, record: CompensationRecord) -> CompensationRecord:
    with self._writer_lock:
        if record.record_id in self.compensation_records:
            existing = self.compensation_records[record.record_id]
            if existing.canonical_digest != record.canonical_digest:
                raise AuthorizationError("compensation record ID cannot be rebound")
            return existing
        try:
            original = self.transactions.get(record.original_transaction_id)
            compensation = self.transactions.get(record.compensation_transaction_id)
        except KeyError as exc:
            raise AuthorizationError("compensation references an unknown transaction") from exc
        if compensation.authorization_id != record.compensation_authorization_id:
            raise AuthorizationError("compensation transaction/authorization binding mismatch")
        original_applied = original.state in {TransactionState.COMMITTED, TransactionState.RECONCILED_APPLIED}
        if original_applied != record.original_outcome_applied:
            raise AuthorizationError("compensation record misstates original effect outcome")
        self.compensation_records[record.record_id] = record
        self._record("action.compensation_registered", {"record": record.canonical_payload()})
        return record


def _update_compensation(
    self,
    record_id: str,
    status: CompensationStatus | str,
    *,
    evidence_ref: str,
) -> CompensationRecord:
    with self._writer_lock:
        current = self.compensation_records.get(record_id)
        if current is None:
            raise AuthorizationError("unknown compensation record")
        updated = current.transition(status, evidence_ref=evidence_ref)
        original_before = self.transactions.get(current.original_transaction_id)
        self.compensation_records[record_id] = updated
        original_after = self.transactions.get(current.original_transaction_id)
        if original_before != original_after:
            raise AuthorizationError("compensation transition attempted to rewrite original transaction")
        self._record("action.compensation_updated", {"record": updated.canonical_payload()})
        return updated


def _replay_contract_registered(kernel, entry) -> None:
    try:
        contract = ExecutionContract.from_payload(dict(entry.payload["contract"]))
    except Exception as exc:
        raise ReplayError(f"invalid execution-contract replay payload: {exc}") from exc
    profile = kernel.adapters.get(contract.adapter_id)
    if profile is None or profile.revision < contract.adapter_revision:
        raise ReplayError("execution-contract replay lacks matching adapter revision")
    key = _contract_key(contract.adapter_id, contract.adapter_revision)
    existing = kernel.execution_contracts.get(key)
    if existing is not None and existing.canonical_digest != contract.canonical_digest:
        raise ReplayError("execution-contract replay attempted revision rebind")
    kernel.execution_contracts[key] = contract


def _replay_contract_bound(kernel, entry) -> None:
    payload = dict(entry.payload)
    authorization_id = str(payload.get("authorization_id", ""))
    authorization = kernel.authorizations.get(authorization_id)
    if authorization is None:
        raise ReplayError("execution-contract binding references unknown authorization")
    adapter_id = str(payload.get("adapter_id", ""))
    adapter_revision = int(payload.get("adapter_revision", 0))
    contract = kernel.execution_contracts.get(_contract_key(adapter_id, adapter_revision))
    if contract is None:
        raise ReplayError("execution-contract binding references unknown contract")
    recorded_digest = str(payload.get("execution_contract_digest", ""))
    if contract.canonical_digest != recorded_digest:
        raise ReplayError("execution-contract binding digest mismatch")
    if authorization.adapter_id != adapter_id or authorization.adapter_revision != adapter_revision:
        raise ReplayError("execution-contract binding crosses authorization adapter identity")
    kernel.authorization_execution_contract_bindings[authorization_id] = recorded_digest


def _replay_remote_cancellation(kernel, entry) -> None:
    payload = dict(entry.payload)
    authorization_id = str(payload.get("authorization_id", ""))
    try:
        acknowledgement = RemoteCancellationAcknowledgement.from_payload(dict(payload["acknowledgement"]))
    except Exception as exc:
        raise ReplayError(f"invalid remote cancellation replay payload: {exc}") from exc
    authorization = kernel.authorizations.get(authorization_id)
    if authorization is None or authorization.adapter_id is None or authorization.adapter_revision is None:
        raise ReplayError("remote cancellation replay references invalid authorization")
    contract = kernel.execution_contracts.get(_contract_key(authorization.adapter_id, authorization.adapter_revision))
    if contract is None or contract.canonical_digest != str(payload.get("execution_contract_digest", "")):
        raise ReplayError("remote cancellation replay execution contract mismatch")
    tx = kernel.transaction_for_authorization(authorization_id)
    if tx.state != TransactionState.CANCELLATION_PENDING:
        raise ReplayError("remote cancellation replay source state is not cancellation-pending")
    try:
        validate_remote_cancellation_acknowledgement(
            acknowledgement,
            contract,
            transaction_id=tx.id,
            action_id=tx.action_id,
            authorization_id=authorization_id,
            principal_ref=tx.principal_ref,
            authority_epoch=acknowledgement.authority_epoch,
        )
        reconciled = kernel.transactions.reconcile_with_evidence(
            tx.id,
            acknowledgement.as_reconciliation_evidence(),
            minimum_assurance=max(0.8, contract.cancellation_ack_assurance),
        )
    except AuthorizationError as exc:
        raise ReplayError(f"remote cancellation replay is invalid: {exc}") from exc
    if reconciled.state.value != str(payload.get("resulting_state", "")):
        raise ReplayError("remote cancellation replay resulting state mismatch")
    kernel.remote_cancellation_acknowledgements[acknowledgement.acknowledgement_id] = acknowledgement


def _replay_compensation(kernel, entry, *, update: bool) -> None:
    try:
        record = CompensationRecord.from_payload(dict(entry.payload["record"]))
    except Exception as exc:
        raise ReplayError(f"invalid compensation replay payload: {exc}") from exc
    if record.original_transaction_id not in {tx.id for tx in kernel.transactions.all()}:
        raise ReplayError("compensation replay references unknown original transaction")
    if record.compensation_transaction_id not in {tx.id for tx in kernel.transactions.all()}:
        raise ReplayError("compensation replay references unknown compensation transaction")
    existing = kernel.compensation_records.get(record.record_id)
    if update:
        if existing is None:
            raise ReplayError("compensation update replay has no registered record")
        if existing.original_transaction_id != record.original_transaction_id or existing.compensation_transaction_id != record.compensation_transaction_id:
            raise ReplayError("compensation update replay changed transaction identity")
    elif existing is not None and existing.canonical_digest != record.canonical_digest:
        raise ReplayError("compensation replay attempted record rebind")
    kernel.compensation_records[record.record_id] = record


def _install_replay_reducer() -> None:
    from . import lineage_recovery

    original = lineage_recovery._replay_base_entry

    def _replay_base_entry(kernel, entry) -> bool:
        if entry.event_type == "execution.contract_registered":
            _replay_contract_registered(kernel, entry)
        elif entry.event_type == "action.execution_contract_bound":
            _replay_contract_bound(kernel, entry)
        elif entry.event_type == "action.remote_cancellation_acknowledged":
            _replay_remote_cancellation(kernel, entry)
        elif entry.event_type == "action.compensation_registered":
            _replay_compensation(kernel, entry, update=False)
        elif entry.event_type == "action.compensation_updated":
            _replay_compensation(kernel, entry, update=True)
        else:
            return original(kernel, entry)
        lineage_recovery._restore_meta(kernel, dict(entry.payload))
        return True

    lineage_recovery._replay_base_entry = _replay_base_entry


def install_execution_contract_runtime(kernel_cls) -> None:
    """Install Wave-9 external execution contracts on the existing kernel/replay path."""
    if getattr(kernel_cls, "_wave9_execution_contract_runtime_installed", False):
        return
    _register_replay_events()
    original_init = kernel_cls.__init__

    def __init__(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        _install_state(self)

    kernel_cls.__init__ = __init__
    _install_replay_reducer()
    kernel_cls.register_execution_contract = _register_execution_contract
    kernel_cls.execution_contract_for = _execution_contract_for
    kernel_cls.bind_authorization_execution_contract = _bind_authorization_execution_contract
    kernel_cls.assert_authorization_execution_contract_current = _assert_authorization_execution_contract_current
    kernel_cls.dispatch_contract_bound = _dispatch_contract_bound
    kernel_cls.record_remote_cancellation_acknowledgement = _record_remote_cancellation_acknowledgement
    kernel_cls.register_compensation = _register_compensation
    kernel_cls.update_compensation = _update_compensation
    kernel_cls._wave9_execution_contract_runtime_installed = True
