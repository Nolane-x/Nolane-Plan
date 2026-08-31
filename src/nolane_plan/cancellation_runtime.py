from __future__ import annotations

from collections.abc import Iterable

from .execution import ActionTransaction, TransactionState
from .replay_registry import DEFAULT_REPLAY_REGISTRY, ReplayEventClass, ReplayEventSpec
from .types import AuthorizationError, ReplayError


_CANCELLATION_EVENT = "action.cancellation_recorded"


def _register_replay_event() -> None:
    if _CANCELLATION_EVENT in DEFAULT_REPLAY_REGISTRY.event_types:
        return
    spec = ReplayEventSpec(
        _CANCELLATION_EVENT,
        ReplayEventClass.STATE_REDUCER,
        correctness_significant=True,
        reducer_name="action_cancellation_recorded",
    )
    DEFAULT_REPLAY_REGISTRY._specs = (*DEFAULT_REPLAY_REGISTRY._specs, spec)
    DEFAULT_REPLAY_REGISTRY._by_event[_CANCELLATION_EVENT] = spec


def _cancel_authorized_action(
    self,
    authorization_id: str,
    *,
    detail: str,
) -> ActionTransaction:
    with self._writer_lock:
        if authorization_id not in self.authorizations:
            raise AuthorizationError("unknown authorization for cancellation")
        tx = self.transaction_for_authorization(authorization_id)
        source_state = tx.state
        if source_state == TransactionState.AUTHORIZED:
            result = self.transactions.cancel_before_dispatch(tx.id, detail)
        elif source_state == TransactionState.DISPATCH_RECORDED:
            result = self.transactions.request_cancellation_after_dispatch(tx.id, detail)
        else:
            raise AuthorizationError(
                f"transaction cannot be cancelled from {source_state.value}; "
                "post-dispatch uncertainty requires reconciliation"
            )
        self._record(
            "action.cancellation_recorded",
            {
                "transaction_id": tx.id,
                "authorization_id": authorization_id,
                "source_state": source_state.value,
                "resulting_state": result.state.value,
                "detail": result.detail,
            },
        )
        return result


def _replay_cancellation(kernel, entry) -> None:
    payload = dict(entry.payload)
    required = ("transaction_id", "authorization_id", "source_state", "resulting_state", "detail")
    missing = tuple(key for key in required if key not in payload)
    if missing:
        raise ReplayError(f"cancellation replay payload is incomplete: {missing!r}")

    tx_id = str(payload["transaction_id"])
    authorization_id = str(payload["authorization_id"])
    try:
        tx = kernel.transactions.get(tx_id)
    except KeyError as exc:
        raise ReplayError("cancellation references an unknown transaction") from exc
    if tx.authorization_id != authorization_id:
        raise ReplayError("cancellation authorization/transaction binding mismatch")

    try:
        source_state = TransactionState(str(payload["source_state"]))
        expected_state = TransactionState(str(payload["resulting_state"]))
    except ValueError as exc:
        raise ReplayError("cancellation replay contains an unknown transaction state") from exc
    if tx.state != source_state:
        raise ReplayError(
            f"cancellation replay source-state mismatch: current={tx.state.value}, recorded={source_state.value}"
        )

    detail = str(payload["detail"])
    try:
        if source_state == TransactionState.AUTHORIZED:
            actual = kernel.transactions.cancel_before_dispatch(tx_id, detail)
        elif source_state == TransactionState.DISPATCH_RECORDED:
            actual = kernel.transactions.request_cancellation_after_dispatch(tx_id, detail)
        else:
            raise ReplayError(f"illegal cancellation replay source state: {source_state.value}")
    except AuthorizationError as exc:
        raise ReplayError(f"illegal cancellation transition during replay: {exc}") from exc

    if actual.state != expected_state:
        raise ReplayError(
            f"cancellation resulting-state mismatch: actual={actual.state.value}, recorded={expected_state.value}"
        )
    if actual.detail != detail.strip():
        raise ReplayError("cancellation detail did not replay exactly")


def _install_replay_reducer() -> None:
    # Import modules, not function aliases, so the already-installed layered open
    # path keeps using the patched globals without creating a second replay engine.
    from . import lineage_recovery, resume

    original_base_entry = lineage_recovery._replay_base_entry

    def _replay_base_entry(kernel, entry) -> bool:
        if entry.event_type == _CANCELLATION_EVENT:
            _replay_cancellation(kernel, entry)
            lineage_recovery._restore_meta(kernel, dict(entry.payload))
            return True
        return original_base_entry(kernel, entry)

    lineage_recovery._replay_base_entry = _replay_base_entry

    original_legacy_suffix = resume._replay_suffix

    def _legacy_suffix(kernel, entries) -> None:
        if not isinstance(entries, Iterable) or hasattr(entries, "event_type"):
            entries = (entries,)
        for entry in entries:
            if entry.event_type == _CANCELLATION_EVENT:
                _replay_cancellation(kernel, entry)
            else:
                original_legacy_suffix(kernel, entry)

    resume._replay_suffix = _legacy_suffix
    # lineage_recovery captured the legacy reducer by name at import time.
    lineage_recovery._legacy_base_replay = _legacy_suffix


def install_cancellation_runtime(kernel_cls) -> None:
    """Install Wave-8 cancellation-fence semantics on the existing single writer."""
    if getattr(kernel_cls, "_wave8_cancellation_runtime_installed", False):
        return
    _register_replay_event()
    _install_replay_reducer()
    kernel_cls.cancel_authorized_action = _cancel_authorized_action
    kernel_cls._wave8_cancellation_runtime_installed = True
