from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .multiwriter import (
    CommitDecision,
    CommitDecisionStatus,
    MultiWriterCoordinator,
    WriteConflict,
    WriteIntent,
    WriterIdentity,
    WriterLease,
)
from .production_store import AuthorityEpoch, InMemoryProductionStore
from .replay_registry import DEFAULT_REPLAY_REGISTRY, ReplayEventClass, ReplayEventSpec
from .types import AuthorizationError, ReplayError
from .hashing import digest


_EVENT_SPECS = (
    ("writer.epoch_acquired", "writer_epoch_acquired"),
    ("writer.conditional_commit", "writer_conditional_commit"),
    ("writer.conflict_recorded", "writer_conflict_recorded"),
    ("action.authorization_epoch_bound", "action_authorization_epoch_bound"),
)


def _required(name: str, value: object) -> str:
    text = str(value).strip()
    if not text:
        raise ValueError(f"{name} must be non-empty")
    return text


@dataclass(frozen=True, slots=True)
class AuthorizationAuthorityEpochBinding:
    authorization_id: str
    acting_principal_ref: str
    writer_id: str
    writer_identity_digest: str
    epoch: int
    epoch_digest: str
    storage_backend_id: str
    storage_backend_revision: int
    canonical_digest: str

    @classmethod
    def create(cls, authorization, lease: WriterLease) -> "AuthorizationAuthorityEpochBinding":
        if lease.writer.principal_ref != authorization.acting_principal_ref:
            raise AuthorizationError("authorization authority epoch must bind the exact acting principal")
        if lease.epoch.writer_identity_digest != lease.writer.canonical_digest:
            raise AuthorizationError("authorization authority epoch lease lacks exact writer identity binding")
        body = {
            "authorization_id": _required("authorization_id", authorization.id),
            "acting_principal_ref": _required("acting_principal_ref", authorization.acting_principal_ref),
            "writer_id": _required("writer_id", lease.writer.writer_id),
            "writer_identity_digest": _required("writer_identity_digest", lease.writer.canonical_digest),
            "epoch": int(lease.epoch.epoch),
            "epoch_digest": _required("epoch_digest", lease.epoch.canonical_digest),
            "storage_backend_id": _required("storage_backend_id", lease.epoch.backend_id),
            "storage_backend_revision": int(lease.epoch.backend_revision),
        }
        if body["epoch"] < 1 or body["storage_backend_revision"] < 1:
            raise AuthorizationError("authorization authority epoch binding contains invalid revisions")
        return cls(**body, canonical_digest=digest(body))

    def canonical_payload(self) -> dict[str, object]:
        return {
            "authorization_id": self.authorization_id,
            "acting_principal_ref": self.acting_principal_ref,
            "writer_id": self.writer_id,
            "writer_identity_digest": self.writer_identity_digest,
            "epoch": self.epoch,
            "epoch_digest": self.epoch_digest,
            "storage_backend_id": self.storage_backend_id,
            "storage_backend_revision": self.storage_backend_revision,
            "canonical_digest": self.canonical_digest,
        }

    @classmethod
    def from_payload(cls, raw: dict[str, Any]) -> "AuthorizationAuthorityEpochBinding":
        body = {
            "authorization_id": _required("authorization_id", raw["authorization_id"]),
            "acting_principal_ref": _required("acting_principal_ref", raw["acting_principal_ref"]),
            "writer_id": _required("writer_id", raw["writer_id"]),
            "writer_identity_digest": _required("writer_identity_digest", raw["writer_identity_digest"]),
            "epoch": int(raw["epoch"]),
            "epoch_digest": _required("epoch_digest", raw["epoch_digest"]),
            "storage_backend_id": _required("storage_backend_id", raw["storage_backend_id"]),
            "storage_backend_revision": int(raw["storage_backend_revision"]),
        }
        if body["epoch"] < 1 or body["storage_backend_revision"] < 1:
            raise ValueError("authorization authority epoch binding contains invalid revisions")
        row = cls(**body, canonical_digest=digest(body))
        if row.canonical_digest != str(raw.get("canonical_digest", "")):
            raise ValueError("authorization authority epoch binding digest mismatch")
        return row


@dataclass(frozen=True, slots=True)
class MultiWriterCommitObservation:
    status: CommitDecisionStatus
    intent_digest: str
    authoritative_intent_digest: str
    storage_revision: int
    epoch_digest: str
    writer_identity_digest: str
    fence_receipt_digest: str | None
    conflict_digest: str | None
    canonical_digest: str

    @classmethod
    def create(cls, decision: CommitDecision, lease: WriterLease) -> "MultiWriterCommitObservation":
        if lease.epoch.writer_identity_digest != lease.writer.canonical_digest:
            raise ValueError("multi-writer observation requires exact writer identity binding")
        if decision.status == CommitDecisionStatus.COMMITTED:
            if decision.fence_receipt is None or decision.conflict is not None:
                raise ValueError("committed decision has invalid proof shape")
            if decision.fence_receipt.epoch_digest != lease.epoch.canonical_digest:
                raise ValueError("commit fence receipt crosses authority epoch")
            if decision.fence_receipt.writer_digest != lease.writer.canonical_digest:
                raise ValueError("commit fence receipt crosses writer identity")
        elif decision.status == CommitDecisionStatus.CONFLICT_RECONCILIATION_REQUIRED:
            if decision.conflict is None:
                raise ValueError("conflict decision lacks conflict record")
        body = {
            "status": decision.status.value,
            "intent_digest": _required("intent_digest", decision.intent_digest),
            "authoritative_intent_digest": _required(
                "authoritative_intent_digest", decision.authoritative_intent_digest
            ),
            "storage_revision": int(decision.storage_revision),
            "epoch_digest": _required("epoch_digest", lease.epoch.canonical_digest),
            "writer_identity_digest": _required("writer_identity_digest", lease.writer.canonical_digest),
            "fence_receipt_digest": None
            if decision.fence_receipt is None
            else decision.fence_receipt.canonical_digest,
            "conflict_digest": None if decision.conflict is None else decision.conflict.canonical_digest,
        }
        if body["storage_revision"] < 0:
            raise ValueError("multi-writer observation storage revision cannot be negative")
        return cls(
            status=decision.status,
            intent_digest=body["intent_digest"],
            authoritative_intent_digest=body["authoritative_intent_digest"],
            storage_revision=body["storage_revision"],
            epoch_digest=body["epoch_digest"],
            writer_identity_digest=body["writer_identity_digest"],
            fence_receipt_digest=body["fence_receipt_digest"],
            conflict_digest=body["conflict_digest"],
            canonical_digest=digest(body),
        )

    def canonical_payload(self) -> dict[str, object]:
        return {
            "status": self.status.value,
            "intent_digest": self.intent_digest,
            "authoritative_intent_digest": self.authoritative_intent_digest,
            "storage_revision": self.storage_revision,
            "epoch_digest": self.epoch_digest,
            "writer_identity_digest": self.writer_identity_digest,
            "fence_receipt_digest": self.fence_receipt_digest,
            "conflict_digest": self.conflict_digest,
            "canonical_digest": self.canonical_digest,
        }

    @classmethod
    def from_payload(cls, raw: dict[str, Any]) -> "MultiWriterCommitObservation":
        try:
            status = CommitDecisionStatus(str(raw["status"]))
        except ValueError as exc:
            raise ValueError("unknown multi-writer commit observation status") from exc
        body = {
            "status": status.value,
            "intent_digest": _required("intent_digest", raw["intent_digest"]),
            "authoritative_intent_digest": _required(
                "authoritative_intent_digest", raw["authoritative_intent_digest"]
            ),
            "storage_revision": int(raw["storage_revision"]),
            "epoch_digest": _required("epoch_digest", raw["epoch_digest"]),
            "writer_identity_digest": _required("writer_identity_digest", raw["writer_identity_digest"]),
            "fence_receipt_digest": raw.get("fence_receipt_digest"),
            "conflict_digest": raw.get("conflict_digest"),
        }
        if body["storage_revision"] < 0:
            raise ValueError("multi-writer observation storage revision cannot be negative")
        if status == CommitDecisionStatus.COMMITTED and not body["fence_receipt_digest"]:
            raise ValueError("committed observation lacks fence receipt digest")
        if status == CommitDecisionStatus.CONFLICT_RECONCILIATION_REQUIRED and not body["conflict_digest"]:
            raise ValueError("conflict observation lacks conflict digest")
        row = cls(
            status=status,
            intent_digest=body["intent_digest"],
            authoritative_intent_digest=body["authoritative_intent_digest"],
            storage_revision=body["storage_revision"],
            epoch_digest=body["epoch_digest"],
            writer_identity_digest=body["writer_identity_digest"],
            fence_receipt_digest=None
            if body["fence_receipt_digest"] is None
            else _required("fence_receipt_digest", body["fence_receipt_digest"]),
            conflict_digest=None
            if body["conflict_digest"] is None
            else _required("conflict_digest", body["conflict_digest"]),
            canonical_digest=digest(body),
        )
        if row.canonical_digest != str(raw.get("canonical_digest", "")):
            raise ValueError("multi-writer commit observation digest mismatch")
        return row


def _epoch_payload(epoch: AuthorityEpoch) -> dict[str, object]:
    return {
        "backend_id": epoch.backend_id,
        "backend_revision": epoch.backend_revision,
        "epoch": epoch.epoch,
        "predecessor_epoch": epoch.predecessor_epoch,
        "writer_id": epoch.writer_id,
        "writer_identity_digest": epoch.writer_identity_digest,
        "acquisition_revision": epoch.acquisition_revision,
        "acquisition_receipt_digest": epoch.acquisition_receipt_digest,
        "canonical_digest": epoch.canonical_digest,
    }


def _epoch_from_payload(raw: dict[str, Any]) -> AuthorityEpoch:
    row = AuthorityEpoch.create(
        backend_id=str(raw["backend_id"]),
        backend_revision=int(raw["backend_revision"]),
        epoch=int(raw["epoch"]),
        predecessor_epoch=raw.get("predecessor_epoch"),
        writer_id=str(raw["writer_id"]),
        writer_identity_digest=raw.get("writer_identity_digest"),
        acquisition_revision=int(raw["acquisition_revision"]),
    )
    if row.acquisition_receipt_digest != str(raw.get("acquisition_receipt_digest", "")):
        raise ValueError("authority epoch acquisition receipt digest mismatch")
    if row.canonical_digest != str(raw.get("canonical_digest", "")):
        raise ValueError("authority epoch canonical digest mismatch")
    return row


def _lease_payload(lease: WriterLease) -> dict[str, object]:
    return {
        "writer": lease.writer.canonical_payload(),
        "epoch": _epoch_payload(lease.epoch),
        "valid_until": lease.valid_until,
        "canonical_digest": lease.canonical_digest,
    }


def _lease_from_payload(raw: dict[str, Any]) -> WriterLease:
    writer = WriterIdentity.from_payload(dict(raw["writer"]))
    epoch = _epoch_from_payload(dict(raw["epoch"]))
    lease = WriterLease.create(writer=writer, epoch=epoch, valid_until=raw.get("valid_until"))
    if lease.canonical_digest != str(raw.get("canonical_digest", "")):
        raise ValueError("writer lease canonical digest mismatch")
    return lease


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
    self.observed_authority_epochs: dict[str, WriterLease] = {}
    self.latest_observed_authority_epoch: WriterLease | None = None
    self.multiwriter_commit_observations: dict[str, MultiWriterCommitObservation] = {}
    self.authorization_authority_epoch_bindings: dict[str, AuthorizationAuthorityEpochBinding] = {}


def _accept_epoch_observation(kernel, lease: WriterLease, *, replay: bool) -> WriterLease:
    existing = kernel.observed_authority_epochs.get(lease.epoch.canonical_digest)
    if existing is not None:
        if existing.canonical_digest != lease.canonical_digest:
            error = "authority epoch observation digest was rebound"
            if replay:
                raise ReplayError(error)
            raise AuthorizationError(error)
        return existing

    latest = kernel.latest_observed_authority_epoch
    if latest is not None:
        if latest.epoch.backend_id != lease.epoch.backend_id or latest.epoch.backend_revision != lease.epoch.backend_revision:
            error = "authority epoch observation changed bounded storage identity"
            if replay:
                raise ReplayError(error)
            raise AuthorizationError(error)
        if lease.epoch.epoch <= latest.epoch.epoch:
            error = "authority epoch observation is not strictly monotonic"
            if replay:
                raise ReplayError(error)
            raise AuthorizationError(error)
        if lease.epoch.predecessor_epoch != latest.epoch.epoch:
            error = "authority epoch observation skips predecessor in kernel authority history"
            if replay:
                raise ReplayError(error)
            raise AuthorizationError(error)

    kernel.observed_authority_epochs[lease.epoch.canonical_digest] = lease
    kernel.latest_observed_authority_epoch = lease
    return lease


def _accept_commit_observation(kernel, observation: MultiWriterCommitObservation, *, replay: bool) -> None:
    lease = kernel.observed_authority_epochs.get(observation.epoch_digest)
    if lease is None:
        error = "multi-writer commit observation references an unobserved authority epoch"
        if replay:
            raise ReplayError(error)
        raise AuthorizationError(error)
    if lease.writer.canonical_digest != observation.writer_identity_digest:
        error = "multi-writer commit observation crosses writer identity"
        if replay:
            raise ReplayError(error)
        raise AuthorizationError(error)
    existing = kernel.multiwriter_commit_observations.get(observation.canonical_digest)
    if existing is not None and existing != observation:
        error = "multi-writer commit observation digest was rebound"
        if replay:
            raise ReplayError(error)
        raise AuthorizationError(error)
    kernel.multiwriter_commit_observations[observation.canonical_digest] = observation


def _acquire_authority_epoch(
    self,
    coordinator: MultiWriterCoordinator,
    writer: WriterIdentity,
    expected_epoch: int | None,
    *,
    valid_until: int | float | None = None,
) -> WriterLease:
    with self._writer_lock:
        lease = coordinator.acquire(writer, expected_epoch, valid_until=valid_until)
        self._record("writer.epoch_acquired", {"lease": _lease_payload(lease)})
        return _accept_epoch_observation(self, lease, replay=False)


def _conditional_correctness_commit(
    self,
    coordinator: MultiWriterCoordinator,
    intent: WriteIntent,
    lease: WriterLease,
    expected_revision: int,
    *,
    now: int | float | None = None,
) -> CommitDecision:
    with self._writer_lock:
        observed = self.observed_authority_epochs.get(lease.epoch.canonical_digest)
        if observed is None or observed.canonical_digest != lease.canonical_digest:
            raise AuthorizationError("conditional correctness commit requires a kernel-observed authority epoch")
        decision = coordinator.commit(intent, lease, expected_revision, now=now)
        observation = MultiWriterCommitObservation.create(decision, lease)
        if decision.status == CommitDecisionStatus.CONFLICT_RECONCILIATION_REQUIRED:
            assert decision.conflict is not None
            self._record(
                "writer.conflict_recorded",
                {
                    "observation": observation.canonical_payload(),
                    "conflict": decision.conflict.canonical_payload(),
                },
            )
        else:
            self._record(
                "writer.conditional_commit",
                {"observation": observation.canonical_payload()},
            )
        _accept_commit_observation(self, observation, replay=False)
        return decision


def _bind_authorization_authority_epoch(
    self,
    authorization_id: str,
    lease: WriterLease,
) -> AuthorizationAuthorityEpochBinding:
    with self._writer_lock:
        authorization = self.authorizations.get(authorization_id)
        if authorization is None:
            raise AuthorizationError("unknown authorization for authority-epoch binding")
        self.assert_authorization_execution_contract_current(authorization_id)
        observed = self.observed_authority_epochs.get(lease.epoch.canonical_digest)
        if observed is None or observed.canonical_digest != lease.canonical_digest:
            raise AuthorizationError("authorization authority epoch must use a kernel-observed lease")
        binding = AuthorizationAuthorityEpochBinding.create(authorization, lease)
        existing = self.authorization_authority_epoch_bindings.get(authorization_id)
        if existing is not None:
            if existing.canonical_digest == binding.canonical_digest:
                return existing
            if (
                existing.storage_backend_id != binding.storage_backend_id
                or existing.storage_backend_revision != binding.storage_backend_revision
            ):
                raise AuthorizationError("authorization authority epoch cannot cross bounded storage identity")
            if binding.epoch <= existing.epoch:
                raise AuthorizationError("authorization authority epoch rebind must advance monotonically")
        self._record(
            "action.authorization_epoch_bound",
            {
                "binding": binding.canonical_payload(),
                "lease_digest": lease.canonical_digest,
            },
        )
        self.authorization_authority_epoch_bindings[authorization_id] = binding
        return binding


def _assert_authorization_authority_epoch_current(
    self,
    authorization_id: str,
    store: InMemoryProductionStore,
) -> AuthorizationAuthorityEpochBinding:
    authorization = self.authorizations.get(authorization_id)
    if authorization is None:
        raise AuthorizationError("unknown authorization for authority-epoch check")
    self.assert_authorization_execution_contract_current(authorization_id)
    binding = self.authorization_authority_epoch_bindings.get(authorization_id)
    if binding is None:
        raise AuthorizationError("authorization has no Wave-9 authority-epoch binding")
    if binding.acting_principal_ref != authorization.acting_principal_ref:
        raise AuthorizationError("authorization authority-epoch principal binding is stale")
    current = store.current_epoch()
    if current is None:
        raise AuthorizationError("production store has no current authority epoch")
    if (
        current.backend_id != binding.storage_backend_id
        or current.backend_revision != binding.storage_backend_revision
        or current.epoch != binding.epoch
        or current.canonical_digest != binding.epoch_digest
        or current.writer_id != binding.writer_id
        or current.writer_identity_digest != binding.writer_identity_digest
    ):
        raise AuthorizationError("authorization was minted under a stale authority epoch")
    return binding


def _dispatch_epoch_bound(
    self,
    authorization_id: str,
    presented_principal_ref: str,
    adapter,
    now: int | float,
    *,
    store: InMemoryProductionStore,
    emergency_authorized: bool = False,
):
    with self._writer_lock:
        binding = self.assert_authorization_authority_epoch_current(authorization_id, store)
        if presented_principal_ref != binding.acting_principal_ref:
            raise AuthorizationError("presented principal does not match authority-epoch binding")
        return self.dispatch_contract_bound(
            authorization_id,
            presented_principal_ref,
            adapter,
            now,
            emergency_authorized=emergency_authorized,
        )


def _replay_epoch_acquired(kernel, entry) -> None:
    raw = entry.payload.get("lease")
    if not isinstance(raw, dict):
        raise ReplayError("authority epoch replay lacks lease payload")
    try:
        lease = _lease_from_payload(dict(raw))
    except Exception as exc:
        raise ReplayError(f"invalid authority epoch replay payload: {exc}") from exc
    _accept_epoch_observation(kernel, lease, replay=True)


def _replay_commit_observation(kernel, entry, *, conflict_event: bool) -> None:
    raw = entry.payload.get("observation")
    if not isinstance(raw, dict):
        raise ReplayError("multi-writer commit replay lacks observation payload")
    try:
        observation = MultiWriterCommitObservation.from_payload(dict(raw))
    except Exception as exc:
        raise ReplayError(f"invalid multi-writer commit replay payload: {exc}") from exc
    if conflict_event:
        if observation.status != CommitDecisionStatus.CONFLICT_RECONCILIATION_REQUIRED:
            raise ReplayError("writer conflict event does not contain a conflict observation")
        raw_conflict = entry.payload.get("conflict")
        if not isinstance(raw_conflict, dict):
            raise ReplayError("writer conflict event lacks conflict payload")
        try:
            conflict = WriteConflict.from_payload(dict(raw_conflict))
        except Exception as exc:
            raise ReplayError(f"invalid writer conflict replay payload: {exc}") from exc
        if observation.conflict_digest != conflict.canonical_digest:
            raise ReplayError("writer conflict replay digest mismatch")
    elif observation.status == CommitDecisionStatus.CONFLICT_RECONCILIATION_REQUIRED:
        raise ReplayError("conditional commit event cannot carry conflict status")
    _accept_commit_observation(kernel, observation, replay=True)


def _replay_authorization_epoch_bound(kernel, entry) -> None:
    raw = entry.payload.get("binding")
    if not isinstance(raw, dict):
        raise ReplayError("authorization authority-epoch replay lacks binding payload")
    try:
        binding = AuthorizationAuthorityEpochBinding.from_payload(dict(raw))
    except Exception as exc:
        raise ReplayError(f"invalid authorization authority-epoch replay payload: {exc}") from exc
    authorization = kernel.authorizations.get(binding.authorization_id)
    if authorization is None:
        raise ReplayError("authorization authority-epoch replay references unknown authorization")
    if authorization.acting_principal_ref != binding.acting_principal_ref:
        raise ReplayError("authorization authority-epoch replay crosses acting principal")
    if binding.authorization_id not in kernel.authorization_execution_contract_bindings:
        raise ReplayError("authorization authority-epoch replay lacks execution-contract binding")
    lease = kernel.observed_authority_epochs.get(binding.epoch_digest)
    if lease is None:
        raise ReplayError("authorization authority-epoch replay references unobserved epoch")
    if str(entry.payload.get("lease_digest", "")) != lease.canonical_digest:
        raise ReplayError("authorization authority-epoch replay lease digest mismatch")
    if (
        lease.writer.canonical_digest != binding.writer_identity_digest
        or lease.writer.writer_id != binding.writer_id
        or lease.writer.principal_ref != binding.acting_principal_ref
        or lease.epoch.backend_id != binding.storage_backend_id
        or lease.epoch.backend_revision != binding.storage_backend_revision
        or lease.epoch.epoch != binding.epoch
    ):
        raise ReplayError("authorization authority-epoch replay binding mismatch")
    existing = kernel.authorization_authority_epoch_bindings.get(binding.authorization_id)
    if existing is not None:
        if existing.canonical_digest == binding.canonical_digest:
            return
        if (
            existing.storage_backend_id != binding.storage_backend_id
            or existing.storage_backend_revision != binding.storage_backend_revision
            or binding.epoch <= existing.epoch
        ):
            raise ReplayError("authorization authority-epoch replay is non-monotonic")
    kernel.authorization_authority_epoch_bindings[binding.authorization_id] = binding


def _install_replay_reducer() -> None:
    from . import lineage_recovery

    original = lineage_recovery._replay_base_entry

    def _replay_base_entry(kernel, entry) -> bool:
        if entry.event_type == "writer.epoch_acquired":
            _replay_epoch_acquired(kernel, entry)
        elif entry.event_type == "writer.conditional_commit":
            _replay_commit_observation(kernel, entry, conflict_event=False)
        elif entry.event_type == "writer.conflict_recorded":
            _replay_commit_observation(kernel, entry, conflict_event=True)
        elif entry.event_type == "action.authorization_epoch_bound":
            _replay_authorization_epoch_bound(kernel, entry)
        else:
            return original(kernel, entry)
        lineage_recovery._restore_meta(kernel, dict(entry.payload))
        return True

    lineage_recovery._replay_base_entry = _replay_base_entry


def install_multiwriter_runtime(kernel_cls) -> None:
    """Install bounded Wave-9 multi-writer authority on the existing kernel/replay path."""
    if getattr(kernel_cls, "_wave9_multiwriter_runtime_installed", False):
        return
    _register_replay_events()
    original_init = kernel_cls.__init__

    def __init__(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        _install_state(self)

    kernel_cls.__init__ = __init__
    _install_replay_reducer()
    kernel_cls.acquire_authority_epoch = _acquire_authority_epoch
    kernel_cls.conditional_correctness_commit = _conditional_correctness_commit
    kernel_cls.bind_authorization_authority_epoch = _bind_authorization_authority_epoch
    kernel_cls.assert_authorization_authority_epoch_current = _assert_authorization_authority_epoch_current
    kernel_cls.dispatch_epoch_bound = _dispatch_epoch_bound
    kernel_cls._wave9_multiwriter_runtime_installed = True
