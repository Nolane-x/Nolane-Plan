from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Iterable

from .hashing import digest
from .production_store import (
    AuthorityEpoch,
    ConditionalWriteReceipt,
    InMemoryProductionStore,
    StorageConflict,
)


class CommitDecisionStatus(str, Enum):
    COMMITTED = "committed"
    DUPLICATE_CONVERGED = "duplicate_converged"
    CONFLICT_RECONCILIATION_REQUIRED = "conflict_reconciliation_required"


def _required(name: str, value: object) -> str:
    text = str(value).strip()
    if not text:
        raise ValueError(f"{name} must be non-empty")
    return text


def _optional_time(value: int | float | None) -> float | None:
    if value is None:
        return None
    parsed = float(value)
    if parsed < 0:
        raise ValueError("time cannot be negative")
    return parsed


@dataclass(frozen=True, slots=True)
class WriterIdentity:
    writer_id: str
    principal_ref: str
    process_instance_ref: str
    canonical_digest: str

    @classmethod
    def create(cls, *, writer_id: str, principal_ref: str, process_instance_ref: str) -> "WriterIdentity":
        body = {
            "writer_id": _required("writer_id", writer_id),
            "principal_ref": _required("principal_ref", principal_ref),
            "process_instance_ref": _required("process_instance_ref", process_instance_ref),
        }
        return cls(**body, canonical_digest=digest(body))

    def canonical_payload(self) -> dict[str, object]:
        return {
            "writer_id": self.writer_id,
            "principal_ref": self.principal_ref,
            "process_instance_ref": self.process_instance_ref,
            "canonical_digest": self.canonical_digest,
        }

    @classmethod
    def from_payload(cls, raw: dict[str, Any]) -> "WriterIdentity":
        row = cls.create(
            writer_id=str(raw["writer_id"]),
            principal_ref=str(raw["principal_ref"]),
            process_instance_ref=str(raw["process_instance_ref"]),
        )
        if row.canonical_digest != str(raw.get("canonical_digest", "")):
            raise ValueError("writer identity digest mismatch")
        return row


@dataclass(frozen=True, slots=True)
class WriterLease:
    writer: WriterIdentity
    epoch: AuthorityEpoch
    valid_until: float | None
    canonical_digest: str

    @classmethod
    def create(
        cls,
        *,
        writer: WriterIdentity,
        epoch: AuthorityEpoch,
        valid_until: int | float | None = None,
    ) -> "WriterLease":
        if epoch.writer_id != writer.writer_id:
            raise ValueError("writer lease crosses authority-epoch writer ID")
        if epoch.writer_identity_digest != writer.canonical_digest:
            raise ValueError("writer lease is not bound to exact writer identity")
        expiry = _optional_time(valid_until)
        body = {
            "writer_digest": writer.canonical_digest,
            "epoch_digest": epoch.canonical_digest,
            "valid_until": expiry,
        }
        return cls(writer, epoch, expiry, digest(body))

    def expired(self, now: int | float) -> bool:
        return self.valid_until is not None and float(now) > self.valid_until


@dataclass(frozen=True, slots=True)
class WriteIntent:
    intent_id: str
    writer_id: str
    operation_kind: str
    payload: dict[str, object]
    idempotent: bool
    idempotency_key: str | None
    conflict_scope: str
    external_effect_possible: bool
    semantic_digest: str
    canonical_digest: str

    @classmethod
    def create(
        cls,
        *,
        intent_id: str,
        writer_id: str,
        operation_kind: str,
        payload: dict[str, object],
        idempotent: bool,
        idempotency_key: str | None,
        conflict_scope: str,
        external_effect_possible: bool,
    ) -> "WriteIntent":
        intent = _required("intent_id", intent_id)
        writer = _required("writer_id", writer_id)
        operation = _required("operation_kind", operation_kind)
        scope = _required("conflict_scope", conflict_scope)
        idem = bool(idempotent)
        key = None if idempotency_key is None else _required("idempotency_key", idempotency_key)
        if key is not None and not idem:
            raise ValueError("non-idempotent intent cannot claim an idempotency key")
        payload_value = dict(payload)
        semantic_body = {
            "operation_kind": operation,
            "payload": payload_value,
            "idempotent": idem,
            "idempotency_key": key,
            "conflict_scope": scope,
            "external_effect_possible": bool(external_effect_possible),
        }
        semantic = digest(semantic_body)
        body = {
            "intent_id": intent,
            "writer_id": writer,
            **semantic_body,
            "semantic_digest": semantic,
        }
        return cls(
            intent,
            writer,
            operation,
            payload_value,
            idem,
            key,
            scope,
            bool(external_effect_possible),
            semantic,
            digest(body),
        )

    def canonical_payload(self) -> dict[str, object]:
        return {
            "intent_id": self.intent_id,
            "writer_id": self.writer_id,
            "operation_kind": self.operation_kind,
            "payload": dict(self.payload),
            "idempotent": self.idempotent,
            "idempotency_key": self.idempotency_key,
            "conflict_scope": self.conflict_scope,
            "external_effect_possible": self.external_effect_possible,
            "semantic_digest": self.semantic_digest,
            "canonical_digest": self.canonical_digest,
        }

    @classmethod
    def from_payload(cls, raw: dict[str, Any]) -> "WriteIntent":
        row = cls.create(
            intent_id=str(raw["intent_id"]),
            writer_id=str(raw["writer_id"]),
            operation_kind=str(raw["operation_kind"]),
            payload=dict(raw.get("payload", {})),
            idempotent=bool(raw["idempotent"]),
            idempotency_key=raw.get("idempotency_key"),
            conflict_scope=str(raw["conflict_scope"]),
            external_effect_possible=bool(raw.get("external_effect_possible", False)),
        )
        if row.semantic_digest != str(raw.get("semantic_digest", "")):
            raise ValueError("write intent semantic digest mismatch")
        if row.canonical_digest != str(raw.get("canonical_digest", "")):
            raise ValueError("write intent canonical digest mismatch")
        return row


@dataclass(frozen=True, slots=True)
class WriteConflict:
    conflict_id: str
    conflict_scope: str
    incumbent_intent_digest: str
    challenger_intent_digest: str
    reason: str
    reconciliation_required: bool
    external_effect_ambiguity: bool
    canonical_digest: str

    @classmethod
    def create(cls, incumbent: WriteIntent, challenger: WriteIntent, *, reason: str) -> "WriteConflict":
        if incumbent.conflict_scope != challenger.conflict_scope:
            raise ValueError("write conflict must share one correctness scope")
        pair = tuple(sorted((incumbent.canonical_digest, challenger.canonical_digest)))
        body = {
            "conflict_scope": challenger.conflict_scope,
            "incumbent_intent_digest": pair[0],
            "challenger_intent_digest": pair[1],
            "reason": _required("reason", reason),
            "reconciliation_required": True,
            "external_effect_ambiguity": bool(
                incumbent.external_effect_possible or challenger.external_effect_possible
            ),
        }
        conflict_id = f"conflict:{digest(body)[:24]}"
        return cls(
            conflict_id,
            body["conflict_scope"],
            body["incumbent_intent_digest"],
            body["challenger_intent_digest"],
            body["reason"],
            True,
            body["external_effect_ambiguity"],
            digest({"conflict_id": conflict_id, **body}),
        )

    def canonical_payload(self) -> dict[str, object]:
        return {
            "conflict_id": self.conflict_id,
            "conflict_scope": self.conflict_scope,
            "incumbent_intent_digest": self.incumbent_intent_digest,
            "challenger_intent_digest": self.challenger_intent_digest,
            "reason": self.reason,
            "reconciliation_required": self.reconciliation_required,
            "external_effect_ambiguity": self.external_effect_ambiguity,
            "canonical_digest": self.canonical_digest,
        }

    @classmethod
    def from_payload(cls, raw: dict[str, Any]) -> "WriteConflict":
        body = {
            "conflict_scope": _required("conflict_scope", raw["conflict_scope"]),
            "incumbent_intent_digest": _required("incumbent_intent_digest", raw["incumbent_intent_digest"]),
            "challenger_intent_digest": _required("challenger_intent_digest", raw["challenger_intent_digest"]),
            "reason": _required("reason", raw["reason"]),
            "reconciliation_required": bool(raw["reconciliation_required"]),
            "external_effect_ambiguity": bool(raw["external_effect_ambiguity"]),
        }
        if not body["reconciliation_required"]:
            raise ValueError("persisted multi-writer conflict must require reconciliation")
        conflict_id = _required("conflict_id", raw["conflict_id"])
        row = cls(
            conflict_id,
            body["conflict_scope"],
            body["incumbent_intent_digest"],
            body["challenger_intent_digest"],
            body["reason"],
            True,
            body["external_effect_ambiguity"],
            digest({"conflict_id": conflict_id, **body}),
        )
        if row.canonical_digest != str(raw.get("canonical_digest", "")):
            raise ValueError("write conflict digest mismatch")
        return row


@dataclass(frozen=True, slots=True)
class EpochFenceReceipt:
    writer_digest: str
    lease_digest: str
    epoch_digest: str
    intent_digest: str
    storage_receipt_digest: str
    committed_revision: int
    canonical_digest: str

    @classmethod
    def create(
        cls,
        *,
        writer: WriterIdentity,
        lease: WriterLease,
        intent: WriteIntent,
        storage_receipt: ConditionalWriteReceipt,
    ) -> "EpochFenceReceipt":
        if lease.writer != writer or intent.writer_id != writer.writer_id:
            raise ValueError("epoch fence receipt crosses writer identity")
        if lease.epoch.writer_identity_digest != writer.canonical_digest:
            raise ValueError("writer lease epoch is not exact-identity bound")
        if (
            storage_receipt.epoch != lease.epoch.epoch
            or storage_receipt.writer_id != writer.writer_id
            or storage_receipt.writer_identity_digest != writer.canonical_digest
        ):
            raise ValueError("storage receipt does not match exact writer lease")
        body = {
            "writer_digest": writer.canonical_digest,
            "lease_digest": lease.canonical_digest,
            "epoch_digest": lease.epoch.canonical_digest,
            "intent_digest": intent.canonical_digest,
            "storage_receipt_digest": storage_receipt.canonical_digest,
            "committed_revision": storage_receipt.committed_revision,
        }
        return cls(**body, canonical_digest=digest(body))


@dataclass(frozen=True, slots=True)
class CommitDecision:
    status: CommitDecisionStatus
    intent_digest: str
    authoritative_intent_digest: str
    storage_revision: int
    fence_receipt: EpochFenceReceipt | None
    conflict: WriteConflict | None
    canonical_digest: str

    @classmethod
    def create(
        cls,
        *,
        status: CommitDecisionStatus | str,
        intent_digest: str,
        authoritative_intent_digest: str,
        storage_revision: int,
        fence_receipt: EpochFenceReceipt | None = None,
        conflict: WriteConflict | None = None,
    ) -> "CommitDecision":
        parsed = status if isinstance(status, CommitDecisionStatus) else CommitDecisionStatus(str(status))
        revision = int(storage_revision)
        if revision < 0:
            raise ValueError("commit decision storage revision cannot be negative")
        if parsed == CommitDecisionStatus.COMMITTED and fence_receipt is None:
            raise ValueError("committed decision requires epoch fence receipt")
        if parsed == CommitDecisionStatus.CONFLICT_RECONCILIATION_REQUIRED and conflict is None:
            raise ValueError("conflict decision requires conflict record")
        if parsed != CommitDecisionStatus.CONFLICT_RECONCILIATION_REQUIRED and conflict is not None:
            raise ValueError("non-conflict decision cannot carry conflict record")
        body = {
            "status": parsed.value,
            "intent_digest": _required("intent_digest", intent_digest),
            "authoritative_intent_digest": _required("authoritative_intent_digest", authoritative_intent_digest),
            "storage_revision": revision,
            "fence_receipt_digest": None if fence_receipt is None else fence_receipt.canonical_digest,
            "conflict_digest": None if conflict is None else conflict.canonical_digest,
        }
        return cls(
            parsed,
            body["intent_digest"],
            body["authoritative_intent_digest"],
            revision,
            fence_receipt,
            conflict,
            digest(body),
        )


@dataclass(frozen=True, slots=True)
class LeaseExpiryAssessment:
    lease_digest: str
    expired: bool
    external_effect_absence_proven: bool
    reconciliation_required: bool
    canonical_digest: str

    @classmethod
    def create(cls, lease: WriterLease, *, expired: bool, reconciliation_required: bool) -> "LeaseExpiryAssessment":
        body = {
            "lease_digest": lease.canonical_digest,
            "expired": bool(expired),
            "external_effect_absence_proven": False,
            "reconciliation_required": bool(reconciliation_required),
        }
        return cls(**body, canonical_digest=digest(body))


@dataclass(frozen=True, slots=True)
class MultiWriterProjection:
    current_epoch_digest: str | None
    committed_intents: tuple[WriteIntent, ...]
    conflicts: tuple[WriteConflict, ...]
    canonical_digest: str

    @classmethod
    def create(
        cls,
        *,
        current_epoch_digest: str | None,
        committed_intents: Iterable[WriteIntent],
        conflicts: Iterable[WriteConflict],
    ) -> "MultiWriterProjection":
        commits = tuple(sorted(committed_intents, key=lambda row: row.canonical_digest))
        conflict_rows = tuple(sorted(conflicts, key=lambda row: row.conflict_id))
        body = {
            "current_epoch_digest": current_epoch_digest,
            "committed_intents": tuple(row.canonical_digest for row in commits),
            "conflicts": tuple(row.canonical_digest for row in conflict_rows),
        }
        return cls(current_epoch_digest, commits, conflict_rows, digest(body))


class MultiWriterCoordinator:
    """Bounded coordinator over a backend that already proves CAS/fencing.

    This is deliberately not a consensus algorithm. Strong construction fails
    closed unless the supplied production store advertises the Wave-9 strong
    multi-writer capability profile.
    """

    def __init__(self, store: InMemoryProductionStore) -> None:
        store.capabilities.require_strong_multiwriter()
        self.store = store

    def acquire(
        self,
        writer: WriterIdentity,
        expected_epoch: int | None,
        *,
        valid_until: int | float | None = None,
    ) -> WriterLease:
        epoch = self.store.acquire_epoch(
            writer.writer_id,
            expected_epoch,
            writer_identity_digest=writer.canonical_digest,
        )
        return WriterLease.create(writer=writer, epoch=epoch, valid_until=valid_until)

    @staticmethod
    def _state(payload: dict[str, object]) -> dict[str, object]:
        state = payload.setdefault(
            "multiwriter",
            {"commits": {}, "idempotency": {}, "scope_heads": {}, "conflicts": {}},
        )
        if not isinstance(state, dict):
            raise ValueError("invalid multi-writer storage envelope")
        for key in ("commits", "idempotency", "scope_heads", "conflicts"):
            value = state.setdefault(key, {})
            if not isinstance(value, dict):
                raise ValueError(f"invalid multi-writer {key} envelope")
        return state

    @staticmethod
    def _commits(state: dict[str, object]) -> dict[str, WriteIntent]:
        raw = state["commits"]
        assert isinstance(raw, dict)
        result: dict[str, WriteIntent] = {}
        for key, value in sorted(raw.items()):
            if not isinstance(value, dict):
                raise ValueError("invalid persisted multi-writer intent")
            row = WriteIntent.from_payload(dict(value))
            if row.canonical_digest != str(key):
                raise ValueError("persisted multi-writer intent key/digest mismatch")
            result[str(key)] = row
        return result

    @staticmethod
    def _conflicts(state: dict[str, object]) -> dict[str, WriteConflict]:
        raw = state["conflicts"]
        assert isinstance(raw, dict)
        result: dict[str, WriteConflict] = {}
        for key, value in sorted(raw.items()):
            if not isinstance(value, dict):
                raise ValueError("invalid persisted multi-writer conflict")
            row = WriteConflict.from_payload(dict(value))
            if row.conflict_id != str(key):
                raise ValueError("persisted multi-writer conflict key/id mismatch")
            result[str(key)] = row
        return result

    def _require_current_lease(
        self,
        lease: WriterLease,
        intent: WriteIntent,
        *,
        now: int | float | None,
    ) -> None:
        if intent.writer_id != lease.writer.writer_id:
            raise ValueError("write intent is not bound to the presenting writer lease")
        if lease.epoch.writer_identity_digest != lease.writer.canonical_digest:
            raise StorageConflict("writer lease exact identity binding is stale")
        if now is not None and lease.expired(now):
            raise ValueError("writer lease is locally expired; external-effect absence is not implied")
        current = self.store.current_epoch()
        if current is None or current.canonical_digest != lease.epoch.canonical_digest:
            raise StorageConflict("writer lease is fenced by a newer authority epoch")

    def _conflict_decision(
        self,
        *,
        payload: dict[str, object],
        state: dict[str, object],
        incumbent: WriteIntent,
        challenger: WriteIntent,
        lease: WriterLease,
        expected_revision: int,
        reason: str,
    ) -> CommitDecision:
        conflict = WriteConflict.create(incumbent, challenger, reason=reason)
        conflicts_raw = state["conflicts"]
        assert isinstance(conflicts_raw, dict)
        existing_raw = conflicts_raw.get(conflict.conflict_id)
        if existing_raw is not None:
            existing = WriteConflict.from_payload(dict(existing_raw))
            if existing != conflict:
                raise ValueError("multi-writer conflict identity was rebound")
            return CommitDecision.create(
                status=CommitDecisionStatus.CONFLICT_RECONCILIATION_REQUIRED,
                intent_digest=challenger.canonical_digest,
                authoritative_intent_digest=incumbent.canonical_digest,
                storage_revision=self.store.current_revision(),
                conflict=existing,
            )
        conflicts_raw[conflict.conflict_id] = conflict.canonical_payload()
        receipt = self.store.conditional_commit(
            lease.epoch,
            expected_revision=expected_revision,
            payload=payload,
        )
        return CommitDecision.create(
            status=CommitDecisionStatus.CONFLICT_RECONCILIATION_REQUIRED,
            intent_digest=challenger.canonical_digest,
            authoritative_intent_digest=incumbent.canonical_digest,
            storage_revision=receipt.committed_revision,
            conflict=conflict,
        )

    def commit(
        self,
        intent: WriteIntent,
        lease: WriterLease,
        expected_revision: int,
        *,
        now: int | float | None = None,
    ) -> CommitDecision:
        self._require_current_lease(lease, intent, now=now)
        expected = int(expected_revision)
        if expected != self.store.current_revision():
            raise StorageConflict(
                f"storage revision compare-and-swap failed: current={self.store.current_revision()}, expected={expected}"
            )

        payload = self.store.read_payload()
        state = self._state(payload)
        commits = self._commits(state)
        self._conflicts(state)
        idempotency = state["idempotency"]
        scope_heads = state["scope_heads"]
        commits_raw = state["commits"]
        assert isinstance(idempotency, dict)
        assert isinstance(scope_heads, dict)
        assert isinstance(commits_raw, dict)

        if intent.idempotency_key is not None:
            incumbent_digest = idempotency.get(intent.idempotency_key)
            if incumbent_digest is not None:
                incumbent = commits.get(str(incumbent_digest))
                if incumbent is None:
                    raise ValueError("idempotency index references missing committed intent")
                if incumbent.semantic_digest == intent.semantic_digest:
                    return CommitDecision.create(
                        status=CommitDecisionStatus.DUPLICATE_CONVERGED,
                        intent_digest=intent.canonical_digest,
                        authoritative_intent_digest=incumbent.canonical_digest,
                        storage_revision=self.store.current_revision(),
                    )
                return self._conflict_decision(
                    payload=payload,
                    state=state,
                    incumbent=incumbent,
                    challenger=intent,
                    lease=lease,
                    expected_revision=expected,
                    reason="idempotency key reused for different semantics",
                )

        incumbent_digest = scope_heads.get(intent.conflict_scope)
        if incumbent_digest is not None:
            incumbent = commits.get(str(incumbent_digest))
            if incumbent is None:
                raise ValueError("conflict-scope index references missing committed intent")
            if not intent.idempotent or not incumbent.idempotent:
                return self._conflict_decision(
                    payload=payload,
                    state=state,
                    incumbent=incumbent,
                    challenger=intent,
                    lease=lease,
                    expected_revision=expected,
                    reason="non-idempotent intents share one correctness conflict scope",
                )

        commits_raw[intent.canonical_digest] = intent.canonical_payload()
        if intent.idempotency_key is not None:
            idempotency[intent.idempotency_key] = intent.canonical_digest
        scope_heads[intent.conflict_scope] = intent.canonical_digest
        storage_receipt = self.store.conditional_commit(
            lease.epoch,
            expected_revision=expected,
            payload=payload,
        )
        fence = EpochFenceReceipt.create(
            writer=lease.writer,
            lease=lease,
            intent=intent,
            storage_receipt=storage_receipt,
        )
        return CommitDecision.create(
            status=CommitDecisionStatus.COMMITTED,
            intent_digest=intent.canonical_digest,
            authoritative_intent_digest=intent.canonical_digest,
            storage_revision=storage_receipt.committed_revision,
            fence_receipt=fence,
        )

    def assess_expired_lease(self, lease: WriterLease, *, now: int | float) -> LeaseExpiryAssessment:
        expired = lease.expired(now)
        state = self._state(self.store.read_payload())
        commits = self._commits(state)
        ambiguous = any(
            row.writer_id == lease.writer.writer_id and row.external_effect_possible
            for row in commits.values()
        )
        return LeaseExpiryAssessment.create(
            lease,
            expired=expired,
            reconciliation_required=bool(expired and ambiguous),
        )

    def reconstruct(self) -> MultiWriterProjection:
        state = self._state(self.store.read_payload())
        commits = self._commits(state)
        conflicts = self._conflicts(state)
        epoch = self.store.current_epoch()
        return MultiWriterProjection.create(
            current_epoch_digest=None if epoch is None else epoch.canonical_digest,
            committed_intents=commits.values(),
            conflicts=conflicts.values(),
        )
