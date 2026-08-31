from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Iterable

from .compaction import CompactionArchive
from .hashing import digest
from .production_store import (
    AuthorityEpoch,
    ConditionalWriteReceipt,
    InMemoryProductionStore,
    StorageConflict,
    UnsupportedStorageCapability,
)


class DestructiveCompactionError(RuntimeError):
    """Raised when physical compaction cannot preserve the declared semantics."""


class InjectedCompactionFault(RuntimeError):
    """Deterministic crash injection used by the Wave-9 durability harness."""


class DestructiveCompactionPhase(str, Enum):
    PREPARED = "prepared"
    SHADOW_WRITTEN = "shadow_written"
    SWITCH_COMMITTED = "switch_committed"
    SOURCE_RETIRED = "source_retired"
    VERIFIED = "verified"


_PHASE_ORDER = {
    DestructiveCompactionPhase.PREPARED: 1,
    DestructiveCompactionPhase.SHADOW_WRITTEN: 2,
    DestructiveCompactionPhase.SWITCH_COMMITTED: 3,
    DestructiveCompactionPhase.SOURCE_RETIRED: 4,
    DestructiveCompactionPhase.VERIFIED: 5,
}


def _required(name: str, value: object) -> str:
    text = str(value).strip()
    if not text:
        raise DestructiveCompactionError(f"{name} must be non-empty")
    return text


def _canon(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(sorted({str(value).strip() for value in values if str(value).strip()}))


def _phase(raw: object) -> DestructiveCompactionPhase:
    try:
        return DestructiveCompactionPhase(str(raw))
    except ValueError as exc:
        raise DestructiveCompactionError(f"unknown destructive compaction phase: {raw!r}") from exc


@dataclass(frozen=True, slots=True)
class DestructiveCompactionIntent:
    compaction_id: str
    source_representation_id: str
    target_representation_id: str
    source_archive_digest: str
    source_semantic_root_digest: str
    source_canonical_semantic_digest: str
    active_authority_refs: tuple[str, ...]
    dormant_resurrection_refs: tuple[str, ...]
    proof_evidence_debt_refs: tuple[str, ...]
    unique_fallback_refs: tuple[str, ...]
    retained_refs: tuple[str, ...]
    prepared_epoch_digest: str
    canonical_digest: str

    @classmethod
    def create(
        cls,
        *,
        compaction_id: str,
        source_representation_id: str,
        target_representation_id: str,
        source_archive_digest: str,
        source_semantic_root_digest: str,
        source_canonical_semantic_digest: str,
        active_authority_refs: Iterable[str],
        dormant_resurrection_refs: Iterable[str],
        proof_evidence_debt_refs: Iterable[str],
        unique_fallback_refs: Iterable[str],
        prepared_epoch_digest: str,
    ) -> "DestructiveCompactionIntent":
        compaction = _required("compaction_id", compaction_id)
        source = _required("source_representation_id", source_representation_id)
        target = _required("target_representation_id", target_representation_id)
        if source == target:
            raise DestructiveCompactionError("source and target representations must differ")
        active = _canon(active_authority_refs)
        dormant = _canon(dormant_resurrection_refs)
        proof = _canon(proof_evidence_debt_refs)
        fallback = _canon(unique_fallback_refs)
        retained = _canon((*active, *dormant, *proof, *fallback))
        body = {
            "compaction_id": compaction,
            "source_representation_id": source,
            "target_representation_id": target,
            "source_archive_digest": _required("source_archive_digest", source_archive_digest),
            "source_semantic_root_digest": _required("source_semantic_root_digest", source_semantic_root_digest),
            "source_canonical_semantic_digest": _required("source_canonical_semantic_digest", source_canonical_semantic_digest),
            "active_authority_refs": active,
            "dormant_resurrection_refs": dormant,
            "proof_evidence_debt_refs": proof,
            "unique_fallback_refs": fallback,
            "retained_refs": retained,
            "prepared_epoch_digest": _required("prepared_epoch_digest", prepared_epoch_digest),
        }
        return cls(**body, canonical_digest=digest(body))

    def canonical_payload(self) -> dict[str, object]:
        return {
            "compaction_id": self.compaction_id,
            "source_representation_id": self.source_representation_id,
            "target_representation_id": self.target_representation_id,
            "source_archive_digest": self.source_archive_digest,
            "source_semantic_root_digest": self.source_semantic_root_digest,
            "source_canonical_semantic_digest": self.source_canonical_semantic_digest,
            "active_authority_refs": list(self.active_authority_refs),
            "dormant_resurrection_refs": list(self.dormant_resurrection_refs),
            "proof_evidence_debt_refs": list(self.proof_evidence_debt_refs),
            "unique_fallback_refs": list(self.unique_fallback_refs),
            "retained_refs": list(self.retained_refs),
            "prepared_epoch_digest": self.prepared_epoch_digest,
            "canonical_digest": self.canonical_digest,
        }

    @classmethod
    def from_payload(cls, raw: dict[str, Any]) -> "DestructiveCompactionIntent":
        value = cls.create(
            compaction_id=str(raw["compaction_id"]),
            source_representation_id=str(raw["source_representation_id"]),
            target_representation_id=str(raw["target_representation_id"]),
            source_archive_digest=str(raw["source_archive_digest"]),
            source_semantic_root_digest=str(raw["source_semantic_root_digest"]),
            source_canonical_semantic_digest=str(raw["source_canonical_semantic_digest"]),
            active_authority_refs=tuple(str(x) for x in raw.get("active_authority_refs", ())),
            dormant_resurrection_refs=tuple(str(x) for x in raw.get("dormant_resurrection_refs", ())),
            proof_evidence_debt_refs=tuple(str(x) for x in raw.get("proof_evidence_debt_refs", ())),
            unique_fallback_refs=tuple(str(x) for x in raw.get("unique_fallback_refs", ())),
            prepared_epoch_digest=str(raw["prepared_epoch_digest"]),
        )
        if tuple(str(x) for x in raw.get("retained_refs", ())) != value.retained_refs:
            raise DestructiveCompactionError("retention closure does not match its declared roots")
        if value.canonical_digest != str(raw.get("canonical_digest", "")):
            raise DestructiveCompactionError("destructive compaction intent digest mismatch")
        return value


@dataclass(frozen=True, slots=True)
class ProductionRepresentation:
    representation_id: str
    archive: CompactionArchive
    retained_refs: tuple[str, ...]
    semantic_root_digest: str
    canonical_semantic_digest: str
    canonical_digest: str

    @classmethod
    def create(
        cls,
        *,
        representation_id: str,
        archive: CompactionArchive,
        retained_refs: Iterable[str],
        canonical_semantic_digest: str,
        expected_semantic_root_digest: str | None = None,
    ) -> "ProductionRepresentation":
        representation = _required("representation_id", representation_id)
        try:
            semantic_root = archive.reconstruct().semantic_root_digest()
        except Exception as exc:
            raise DestructiveCompactionError("representation archive cannot reconstruct a valid semantic root") from exc
        if expected_semantic_root_digest is not None and semantic_root != str(expected_semantic_root_digest):
            raise DestructiveCompactionError("representation changed the semantic root")
        retained = _canon(retained_refs)
        canonical_semantic = _required("canonical_semantic_digest", canonical_semantic_digest)
        body = {
            "representation_id": representation,
            "archive_digest": archive.canonical_digest,
            "retained_refs": retained,
            "semantic_root_digest": semantic_root,
            "canonical_semantic_digest": canonical_semantic,
        }
        return cls(
            representation_id=representation,
            archive=archive,
            retained_refs=retained,
            semantic_root_digest=semantic_root,
            canonical_semantic_digest=canonical_semantic,
            canonical_digest=digest(body),
        )

    def canonical_payload(self) -> dict[str, object]:
        return {
            "representation_id": self.representation_id,
            "archive": self.archive.canonical_payload(),
            "retained_refs": list(self.retained_refs),
            "semantic_root_digest": self.semantic_root_digest,
            "canonical_semantic_digest": self.canonical_semantic_digest,
            "canonical_digest": self.canonical_digest,
        }

    @classmethod
    def from_payload(cls, raw: dict[str, Any]) -> "ProductionRepresentation":
        archive_raw = raw.get("archive")
        if not isinstance(archive_raw, dict):
            raise DestructiveCompactionError("representation lacks an archive payload")
        try:
            archive = CompactionArchive.from_payload(dict(archive_raw))
        except Exception as exc:
            raise DestructiveCompactionError("representation archive failed validation") from exc
        value = cls.create(
            representation_id=str(raw["representation_id"]),
            archive=archive,
            retained_refs=tuple(str(x) for x in raw.get("retained_refs", ())),
            canonical_semantic_digest=str(raw["canonical_semantic_digest"]),
            expected_semantic_root_digest=str(raw["semantic_root_digest"]),
        )
        if value.canonical_digest != str(raw.get("canonical_digest", "")):
            raise DestructiveCompactionError("production representation digest mismatch")
        return value


@dataclass(frozen=True, slots=True)
class SwitchReceipt:
    expected_storage_revision: int
    committed_storage_revision: int
    authority_epoch: int
    writer_id: str
    authority_epoch_digest: str
    source_representation_id: str
    target_representation_id: str
    canonical_digest: str

    @classmethod
    def create(
        cls,
        *,
        expected_storage_revision: int,
        authority_epoch: AuthorityEpoch,
        source_representation_id: str,
        target_representation_id: str,
    ) -> "SwitchReceipt":
        expected = int(expected_storage_revision)
        if expected < 0:
            raise DestructiveCompactionError("switch expected revision cannot be negative")
        source = _required("source_representation_id", source_representation_id)
        target = _required("target_representation_id", target_representation_id)
        if source == target:
            raise DestructiveCompactionError("switch source and target must differ")
        body = {
            "expected_storage_revision": expected,
            "committed_storage_revision": expected + 1,
            "authority_epoch": int(authority_epoch.epoch),
            "writer_id": _required("writer_id", authority_epoch.writer_id),
            "authority_epoch_digest": _required("authority_epoch_digest", authority_epoch.canonical_digest),
            "source_representation_id": source,
            "target_representation_id": target,
        }
        return cls(**body, canonical_digest=digest(body))

    def canonical_payload(self) -> dict[str, object]:
        return {
            "expected_storage_revision": self.expected_storage_revision,
            "committed_storage_revision": self.committed_storage_revision,
            "authority_epoch": self.authority_epoch,
            "writer_id": self.writer_id,
            "authority_epoch_digest": self.authority_epoch_digest,
            "source_representation_id": self.source_representation_id,
            "target_representation_id": self.target_representation_id,
            "canonical_digest": self.canonical_digest,
        }

    @classmethod
    def from_payload(cls, raw: dict[str, Any]) -> "SwitchReceipt":
        expected = int(raw["expected_storage_revision"])
        committed = int(raw["committed_storage_revision"])
        if committed != expected + 1:
            raise DestructiveCompactionError("switch receipt revision did not advance exactly once")
        body = {
            "expected_storage_revision": expected,
            "committed_storage_revision": committed,
            "authority_epoch": int(raw["authority_epoch"]),
            "writer_id": _required("writer_id", raw["writer_id"]),
            "authority_epoch_digest": _required("authority_epoch_digest", raw["authority_epoch_digest"]),
            "source_representation_id": _required("source_representation_id", raw["source_representation_id"]),
            "target_representation_id": _required("target_representation_id", raw["target_representation_id"]),
        }
        if body["source_representation_id"] == body["target_representation_id"]:
            raise DestructiveCompactionError("switch source and target must differ")
        value = cls(**body, canonical_digest=digest(body))
        if value.canonical_digest != str(raw.get("canonical_digest", "")):
            raise DestructiveCompactionError("switch receipt digest mismatch")
        return value


@dataclass(frozen=True, slots=True)
class RetirementManifest:
    compaction_id: str
    delete_representation_ids: tuple[str, ...]
    retained_representation_ids: tuple[str, ...]
    switch_receipt_digest: str
    canonical_digest: str

    @classmethod
    def create(
        cls,
        *,
        compaction_id: str,
        source_representation_id: str,
        target_representation_id: str,
        switch_receipt_digest: str,
    ) -> "RetirementManifest":
        compaction = _required("compaction_id", compaction_id)
        source = _required("source_representation_id", source_representation_id)
        target = _required("target_representation_id", target_representation_id)
        if source == target:
            raise DestructiveCompactionError("retirement source and target must differ")
        body = {
            "compaction_id": compaction,
            "delete_representation_ids": (source,),
            "retained_representation_ids": (target,),
            "switch_receipt_digest": _required("switch_receipt_digest", switch_receipt_digest),
        }
        return cls(**body, canonical_digest=digest(body))

    def canonical_payload(self) -> dict[str, object]:
        return {
            "compaction_id": self.compaction_id,
            "delete_representation_ids": list(self.delete_representation_ids),
            "retained_representation_ids": list(self.retained_representation_ids),
            "switch_receipt_digest": self.switch_receipt_digest,
            "canonical_digest": self.canonical_digest,
        }

    @classmethod
    def from_payload(cls, raw: dict[str, Any]) -> "RetirementManifest":
        deleted = tuple(str(x) for x in raw.get("delete_representation_ids", ()))
        retained = tuple(str(x) for x in raw.get("retained_representation_ids", ()))
        if len(deleted) != 1 or len(retained) != 1:
            raise DestructiveCompactionError("retirement manifest must delete exactly one source and retain exactly one target")
        value = cls.create(
            compaction_id=str(raw["compaction_id"]),
            source_representation_id=deleted[0],
            target_representation_id=retained[0],
            switch_receipt_digest=str(raw["switch_receipt_digest"]),
        )
        if value.canonical_digest != str(raw.get("canonical_digest", "")):
            raise DestructiveCompactionError("retirement manifest digest mismatch")
        return value


@dataclass(frozen=True, slots=True)
class DestructiveCompactionState:
    intent: DestructiveCompactionIntent
    phase: DestructiveCompactionPhase
    switch_receipt: SwitchReceipt | None
    retirement_manifest: RetirementManifest | None
    source_semantic_root_digest: str
    target_semantic_root_digest: str | None
    source_canonical_semantic_digest: str
    target_canonical_semantic_digest: str | None
    canonical_digest: str

    @classmethod
    def create(
        cls,
        *,
        intent: DestructiveCompactionIntent,
        phase: DestructiveCompactionPhase | str,
        switch_receipt: SwitchReceipt | None = None,
        retirement_manifest: RetirementManifest | None = None,
        target_semantic_root_digest: str | None = None,
        target_canonical_semantic_digest: str | None = None,
    ) -> "DestructiveCompactionState":
        parsed = phase if isinstance(phase, DestructiveCompactionPhase) else _phase(phase)
        order = _PHASE_ORDER[parsed]
        if order < _PHASE_ORDER[DestructiveCompactionPhase.SWITCH_COMMITTED]:
            if switch_receipt is not None:
                raise DestructiveCompactionError("pre-switch state cannot carry a switch receipt")
        elif switch_receipt is None:
            raise DestructiveCompactionError("post-switch state requires a switch receipt")
        if order < _PHASE_ORDER[DestructiveCompactionPhase.SOURCE_RETIRED]:
            if retirement_manifest is not None:
                raise DestructiveCompactionError("pre-retirement state cannot carry a retirement manifest")
        elif retirement_manifest is None:
            raise DestructiveCompactionError("retired state requires an exact retirement manifest")
        target_root = None if target_semantic_root_digest is None else _required("target_semantic_root_digest", target_semantic_root_digest)
        target_canonical = None if target_canonical_semantic_digest is None else _required("target_canonical_semantic_digest", target_canonical_semantic_digest)
        if order >= _PHASE_ORDER[DestructiveCompactionPhase.SHADOW_WRITTEN]:
            if target_root is None or target_canonical is None:
                raise DestructiveCompactionError("shadow-written state requires target semantic bindings")
        elif target_root is not None or target_canonical is not None:
            raise DestructiveCompactionError("prepared state cannot claim target semantic bindings")
        body = {
            "intent_digest": intent.canonical_digest,
            "phase": parsed.value,
            "switch_receipt_digest": None if switch_receipt is None else switch_receipt.canonical_digest,
            "retirement_manifest_digest": None if retirement_manifest is None else retirement_manifest.canonical_digest,
            "source_semantic_root_digest": intent.source_semantic_root_digest,
            "target_semantic_root_digest": target_root,
            "source_canonical_semantic_digest": intent.source_canonical_semantic_digest,
            "target_canonical_semantic_digest": target_canonical,
        }
        return cls(
            intent=intent,
            phase=parsed,
            switch_receipt=switch_receipt,
            retirement_manifest=retirement_manifest,
            source_semantic_root_digest=intent.source_semantic_root_digest,
            target_semantic_root_digest=target_root,
            source_canonical_semantic_digest=intent.source_canonical_semantic_digest,
            target_canonical_semantic_digest=target_canonical,
            canonical_digest=digest(body),
        )

    def canonical_payload(self) -> dict[str, object]:
        return {
            "intent": self.intent.canonical_payload(),
            "phase": self.phase.value,
            "switch_receipt": None if self.switch_receipt is None else self.switch_receipt.canonical_payload(),
            "retirement_manifest": None if self.retirement_manifest is None else self.retirement_manifest.canonical_payload(),
            "source_semantic_root_digest": self.source_semantic_root_digest,
            "target_semantic_root_digest": self.target_semantic_root_digest,
            "source_canonical_semantic_digest": self.source_canonical_semantic_digest,
            "target_canonical_semantic_digest": self.target_canonical_semantic_digest,
            "canonical_digest": self.canonical_digest,
        }

    @classmethod
    def from_payload(cls, raw: dict[str, Any]) -> "DestructiveCompactionState":
        intent_raw = raw.get("intent")
        if not isinstance(intent_raw, dict):
            raise DestructiveCompactionError("destructive compaction state lacks intent")
        intent = DestructiveCompactionIntent.from_payload(dict(intent_raw))
        switch_raw = raw.get("switch_receipt")
        retirement_raw = raw.get("retirement_manifest")
        if switch_raw is not None and not isinstance(switch_raw, dict):
            raise DestructiveCompactionError("invalid switch receipt envelope")
        if retirement_raw is not None and not isinstance(retirement_raw, dict):
            raise DestructiveCompactionError("invalid retirement manifest envelope")
        switch = None if switch_raw is None else SwitchReceipt.from_payload(dict(switch_raw))
        retirement = None if retirement_raw is None else RetirementManifest.from_payload(dict(retirement_raw))
        value = cls.create(
            intent=intent,
            phase=str(raw["phase"]),
            switch_receipt=switch,
            retirement_manifest=retirement,
            target_semantic_root_digest=raw.get("target_semantic_root_digest"),
            target_canonical_semantic_digest=raw.get("target_canonical_semantic_digest"),
        )
        if value.source_semantic_root_digest != str(raw.get("source_semantic_root_digest", "")):
            raise DestructiveCompactionError("source semantic root binding mismatch")
        if value.source_canonical_semantic_digest != str(raw.get("source_canonical_semantic_digest", "")):
            raise DestructiveCompactionError("source canonical semantic binding mismatch")
        if value.canonical_digest != str(raw.get("canonical_digest", "")):
            raise DestructiveCompactionError("destructive compaction state digest mismatch")
        return value


class DestructiveCompactionCoordinator:
    """CAS/fencing coordinator for physical representation replacement.

    Every phase is a separate durable CAS commit. The production pointer changes
    in the same payload commit that records SWITCH_COMMITTED. Physical source
    deletion is a later CAS, so a crash never turns a shadow write into authority.
    """

    def __init__(self, store: InMemoryProductionStore) -> None:
        self.store = store
        store.capabilities.require_strong_multiwriter()
        if not store.capabilities.transactional_batch:
            raise UnsupportedStorageCapability("destructive compaction requires transactional batch replacement")
        if not store.capabilities.destructive_delete:
            raise UnsupportedStorageCapability("destructive compaction requires explicit destructive-delete support")
        if not store.capabilities.crash_recovery_durable:
            raise UnsupportedStorageCapability("destructive compaction requires durable crash recovery")

    def _read_snapshot(self) -> tuple[int, dict[str, object]]:
        before = self.store.current_revision()
        payload = self.store.read_payload()
        after = self.store.current_revision()
        if before != after:
            raise StorageConflict("storage changed while reading compaction snapshot; retry with a fresh authority view")
        return before, payload

    def _payload_maps(self, payload: dict[str, object]) -> tuple[dict[str, object], dict[str, object]]:
        representations = payload.setdefault("representations", {})
        compactions = payload.setdefault("destructive_compactions", {})
        if not isinstance(representations, dict) or not isinstance(compactions, dict):
            raise DestructiveCompactionError("invalid production compaction envelope")
        return representations, compactions

    def _inject(self, requested: DestructiveCompactionPhase | str | None, committed: DestructiveCompactionPhase) -> None:
        if requested is None:
            return
        parsed = requested if isinstance(requested, DestructiveCompactionPhase) else _phase(requested)
        if parsed == committed:
            raise InjectedCompactionFault(f"injected crash after durable {committed.value} commit")

    def _commit(self, *, epoch: AuthorityEpoch, expected_revision: int, payload: dict[str, object]) -> ConditionalWriteReceipt:
        return self.store.conditional_commit(epoch, expected_revision=expected_revision, payload=payload)

    def _representation(self, representations: dict[str, object], representation_id: str) -> ProductionRepresentation:
        raw = representations.get(representation_id)
        if not isinstance(raw, dict):
            raise DestructiveCompactionError(f"missing production representation: {representation_id}")
        return ProductionRepresentation.from_payload(dict(raw))

    def _recover_payload(self, payload: dict[str, object], compaction_id: str) -> DestructiveCompactionState:
        representations, compactions = self._payload_maps(payload)
        raw = compactions.get(str(compaction_id))
        if not isinstance(raw, dict):
            raise DestructiveCompactionError(f"unknown destructive compaction: {compaction_id}")
        state = DestructiveCompactionState.from_payload(dict(raw))
        if state.intent.compaction_id != str(compaction_id):
            raise DestructiveCompactionError("compaction key does not match intent identity")

        intent = state.intent
        pointer = payload.get("production_pointer")
        source_raw = representations.get(intent.source_representation_id)
        target_raw = representations.get(intent.target_representation_id)
        if source_raw is not None and not isinstance(source_raw, dict):
            raise DestructiveCompactionError("invalid source representation envelope")
        if target_raw is not None and not isinstance(target_raw, dict):
            raise DestructiveCompactionError("invalid target representation envelope")
        source = None if source_raw is None else ProductionRepresentation.from_payload(dict(source_raw))
        target = None if target_raw is None else ProductionRepresentation.from_payload(dict(target_raw))

        order = _PHASE_ORDER[state.phase]
        if order <= _PHASE_ORDER[DestructiveCompactionPhase.SHADOW_WRITTEN]:
            if pointer != intent.source_representation_id:
                raise DestructiveCompactionError("pre-switch phase does not point at the source representation")
            if source is None:
                raise DestructiveCompactionError("source representation disappeared before switch")
        if state.phase == DestructiveCompactionPhase.PREPARED and target is not None:
            raise DestructiveCompactionError("prepared phase cannot already expose a target representation")
        if order >= _PHASE_ORDER[DestructiveCompactionPhase.SHADOW_WRITTEN]:
            if target is None:
                raise DestructiveCompactionError("shadow-written phase lacks target representation")
            if target.semantic_root_digest != intent.source_semantic_root_digest:
                raise DestructiveCompactionError("target representation changed semantic root")
            if target.canonical_semantic_digest != intent.source_canonical_semantic_digest:
                raise DestructiveCompactionError("target representation changed canonical semantic digest")
            if target.retained_refs != intent.retained_refs:
                raise DestructiveCompactionError("target representation does not preserve exact retention closure")
            if target.archive.canonical_digest != intent.source_archive_digest:
                raise DestructiveCompactionError("target archive is not the exact verified source archive")
        if source is not None:
            if source.archive.canonical_digest != intent.source_archive_digest:
                raise DestructiveCompactionError("source archive digest no longer matches intent")
            if source.semantic_root_digest != intent.source_semantic_root_digest:
                raise DestructiveCompactionError("source semantic root no longer matches intent")
            if source.retained_refs != intent.retained_refs:
                raise DestructiveCompactionError("source representation retention closure drifted")

        if order >= _PHASE_ORDER[DestructiveCompactionPhase.SWITCH_COMMITTED]:
            if pointer != intent.target_representation_id:
                raise DestructiveCompactionError("post-switch phase is not bound to the target production pointer")
            receipt = state.switch_receipt
            assert receipt is not None
            if receipt.source_representation_id != intent.source_representation_id or receipt.target_representation_id != intent.target_representation_id:
                raise DestructiveCompactionError("switch receipt crosses representation identity")
        if state.phase == DestructiveCompactionPhase.SWITCH_COMMITTED and source is None:
            raise DestructiveCompactionError("source representation retired in the switch commit")
        if order >= _PHASE_ORDER[DestructiveCompactionPhase.SOURCE_RETIRED]:
            if source is not None:
                raise DestructiveCompactionError("retired phase still exposes the source representation")
            manifest = state.retirement_manifest
            assert manifest is not None
            if manifest.compaction_id != intent.compaction_id:
                raise DestructiveCompactionError("retirement manifest crosses compaction identity")
            if manifest.delete_representation_ids != (intent.source_representation_id,):
                raise DestructiveCompactionError("retirement deletion set broadened or changed")
            if manifest.retained_representation_ids != (intent.target_representation_id,):
                raise DestructiveCompactionError("retirement retained representation changed")
            assert state.switch_receipt is not None
            if manifest.switch_receipt_digest != state.switch_receipt.canonical_digest:
                raise DestructiveCompactionError("retirement manifest is not bound to the exact switch")
        if state.phase == DestructiveCompactionPhase.VERIFIED:
            if state.target_semantic_root_digest != state.source_semantic_root_digest:
                raise DestructiveCompactionError("verified compaction changed semantic root")
            if state.target_canonical_semantic_digest != state.source_canonical_semantic_digest:
                raise DestructiveCompactionError("verified compaction changed canonical semantics")
        return state

    def recover(self, compaction_id: str) -> DestructiveCompactionState:
        _, payload = self._read_snapshot()
        return self._recover_payload(payload, str(compaction_id))

    def production_pointer(self) -> str | None:
        _, payload = self._read_snapshot()
        value = payload.get("production_pointer")
        return None if value is None else str(value)

    def representation_ids(self) -> tuple[str, ...]:
        _, payload = self._read_snapshot()
        representations, _ = self._payload_maps(payload)
        for raw in representations.values():
            if not isinstance(raw, dict):
                raise DestructiveCompactionError("invalid representation envelope")
            ProductionRepresentation.from_payload(dict(raw))
        return tuple(sorted(str(key) for key in representations))

    def production_representation(self) -> ProductionRepresentation:
        _, payload = self._read_snapshot()
        pointer = payload.get("production_pointer")
        if pointer is None:
            raise DestructiveCompactionError("production pointer is not initialized")
        representations, _ = self._payload_maps(payload)
        return self._representation(representations, str(pointer))

    def prepare(
        self,
        *,
        compaction_id: str,
        source_representation_id: str,
        target_representation_id: str,
        source_archive: CompactionArchive,
        source_canonical_semantic_digest: str,
        active_authority_refs: Iterable[str],
        dormant_resurrection_refs: Iterable[str],
        proof_evidence_debt_refs: Iterable[str],
        unique_fallback_refs: Iterable[str],
        authority_epoch: AuthorityEpoch,
        fault_after: DestructiveCompactionPhase | str | None = None,
    ) -> DestructiveCompactionState:
        revision, payload = self._read_snapshot()
        representations, compactions = self._payload_maps(payload)
        compaction_key = _required("compaction_id", compaction_id)
        existing = compactions.get(compaction_key)
        if existing is not None:
            state = self._recover_payload(payload, compaction_key)
            self._inject(fault_after, state.phase)
            return state

        try:
            source_root = source_archive.reconstruct().semantic_root_digest()
        except Exception as exc:
            raise DestructiveCompactionError("source archive cannot reconstruct exact source semantics") from exc
        intent = DestructiveCompactionIntent.create(
            compaction_id=compaction_key,
            source_representation_id=source_representation_id,
            target_representation_id=target_representation_id,
            source_archive_digest=source_archive.canonical_digest,
            source_semantic_root_digest=source_root,
            source_canonical_semantic_digest=source_canonical_semantic_digest,
            active_authority_refs=active_authority_refs,
            dormant_resurrection_refs=dormant_resurrection_refs,
            proof_evidence_debt_refs=proof_evidence_debt_refs,
            unique_fallback_refs=unique_fallback_refs,
            prepared_epoch_digest=authority_epoch.canonical_digest,
        )
        source_representation = ProductionRepresentation.create(
            representation_id=intent.source_representation_id,
            archive=source_archive,
            retained_refs=intent.retained_refs,
            canonical_semantic_digest=intent.source_canonical_semantic_digest,
            expected_semantic_root_digest=intent.source_semantic_root_digest,
        )
        pointer = payload.get("production_pointer")
        if pointer is None:
            payload["production_pointer"] = intent.source_representation_id
        elif str(pointer) != intent.source_representation_id:
            raise DestructiveCompactionError("prepare source does not match current production pointer")
        source_existing = representations.get(intent.source_representation_id)
        if source_existing is None:
            representations[intent.source_representation_id] = source_representation.canonical_payload()
        elif not isinstance(source_existing, dict) or ProductionRepresentation.from_payload(dict(source_existing)) != source_representation:
            raise DestructiveCompactionError("source representation identity is already bound to different content")
        if intent.target_representation_id in representations:
            raise DestructiveCompactionError("target representation already exists before prepare")
        state = DestructiveCompactionState.create(intent=intent, phase=DestructiveCompactionPhase.PREPARED)
        compactions[compaction_key] = state.canonical_payload()
        self._commit(epoch=authority_epoch, expected_revision=revision, payload=payload)
        self._inject(fault_after, DestructiveCompactionPhase.PREPARED)
        return state

    def write_shadow(
        self,
        compaction_id: str,
        target_archive: CompactionArchive,
        *,
        authority_epoch: AuthorityEpoch,
        fault_after: DestructiveCompactionPhase | str | None = None,
    ) -> DestructiveCompactionState:
        revision, payload = self._read_snapshot()
        representations, compactions = self._payload_maps(payload)
        state = self._recover_payload(payload, str(compaction_id))
        if _PHASE_ORDER[state.phase] >= _PHASE_ORDER[DestructiveCompactionPhase.SHADOW_WRITTEN]:
            existing = self._representation(representations, state.intent.target_representation_id)
            if existing.archive.canonical_digest != target_archive.canonical_digest:
                raise DestructiveCompactionError("shadow retry attempted to rebind target representation")
            self._inject(fault_after, state.phase)
            return state
        if state.phase != DestructiveCompactionPhase.PREPARED:
            raise DestructiveCompactionError("shadow write requires PREPARED phase")
        target = ProductionRepresentation.create(
            representation_id=state.intent.target_representation_id,
            archive=target_archive,
            retained_refs=state.intent.retained_refs,
            canonical_semantic_digest=state.intent.source_canonical_semantic_digest,
            expected_semantic_root_digest=state.intent.source_semantic_root_digest,
        )
        if target.archive.canonical_digest != state.intent.source_archive_digest:
            raise DestructiveCompactionError("shadow archive does not reproduce the exact verified source archive")
        representations[target.representation_id] = target.canonical_payload()
        next_state = DestructiveCompactionState.create(
            intent=state.intent,
            phase=DestructiveCompactionPhase.SHADOW_WRITTEN,
            target_semantic_root_digest=target.semantic_root_digest,
            target_canonical_semantic_digest=target.canonical_semantic_digest,
        )
        compactions[state.intent.compaction_id] = next_state.canonical_payload()
        self._commit(epoch=authority_epoch, expected_revision=revision, payload=payload)
        self._inject(fault_after, DestructiveCompactionPhase.SHADOW_WRITTEN)
        return next_state

    def commit_switch(
        self,
        compaction_id: str,
        *,
        authority_epoch: AuthorityEpoch,
        fault_after: DestructiveCompactionPhase | str | None = None,
    ) -> DestructiveCompactionState:
        revision, payload = self._read_snapshot()
        representations, compactions = self._payload_maps(payload)
        state = self._recover_payload(payload, str(compaction_id))
        if _PHASE_ORDER[state.phase] >= _PHASE_ORDER[DestructiveCompactionPhase.SWITCH_COMMITTED]:
            self._inject(fault_after, state.phase)
            return state
        if state.phase != DestructiveCompactionPhase.SHADOW_WRITTEN:
            raise DestructiveCompactionError("switch requires SHADOW_WRITTEN phase")
        self._representation(representations, state.intent.source_representation_id)
        target = self._representation(representations, state.intent.target_representation_id)
        if target.semantic_root_digest != state.source_semantic_root_digest:
            raise DestructiveCompactionError("target semantic root is stale before switch")
        switch = SwitchReceipt.create(
            expected_storage_revision=revision,
            authority_epoch=authority_epoch,
            source_representation_id=state.intent.source_representation_id,
            target_representation_id=state.intent.target_representation_id,
        )
        next_state = DestructiveCompactionState.create(
            intent=state.intent,
            phase=DestructiveCompactionPhase.SWITCH_COMMITTED,
            switch_receipt=switch,
            target_semantic_root_digest=target.semantic_root_digest,
            target_canonical_semantic_digest=target.canonical_semantic_digest,
        )
        payload["production_pointer"] = state.intent.target_representation_id
        compactions[state.intent.compaction_id] = next_state.canonical_payload()
        receipt = self._commit(epoch=authority_epoch, expected_revision=revision, payload=payload)
        if receipt.expected_revision != switch.expected_storage_revision or receipt.committed_revision != switch.committed_storage_revision or receipt.epoch != switch.authority_epoch or receipt.writer_id != switch.writer_id:
            raise DestructiveCompactionError("storage acknowledgement disagrees with committed switch receipt")
        self._inject(fault_after, DestructiveCompactionPhase.SWITCH_COMMITTED)
        return next_state

    def retire_source(
        self,
        compaction_id: str,
        *,
        authority_epoch: AuthorityEpoch,
        fault_after: DestructiveCompactionPhase | str | None = None,
    ) -> DestructiveCompactionState:
        revision, payload = self._read_snapshot()
        representations, compactions = self._payload_maps(payload)
        state = self._recover_payload(payload, str(compaction_id))
        if _PHASE_ORDER[state.phase] >= _PHASE_ORDER[DestructiveCompactionPhase.SOURCE_RETIRED]:
            self._inject(fault_after, state.phase)
            return state
        if state.phase != DestructiveCompactionPhase.SWITCH_COMMITTED:
            raise DestructiveCompactionError("source retirement is forbidden before SWITCH_COMMITTED")
        if payload.get("production_pointer") != state.intent.target_representation_id:
            raise DestructiveCompactionError("source cannot retire before durable target pointer switch")
        self._representation(representations, state.intent.source_representation_id)
        target = self._representation(representations, state.intent.target_representation_id)
        assert state.switch_receipt is not None
        manifest = RetirementManifest.create(
            compaction_id=state.intent.compaction_id,
            source_representation_id=state.intent.source_representation_id,
            target_representation_id=state.intent.target_representation_id,
            switch_receipt_digest=state.switch_receipt.canonical_digest,
        )
        for representation_id in manifest.delete_representation_ids:
            if representation_id != state.intent.source_representation_id:
                raise DestructiveCompactionError("retirement attempted to broaden deletion set")
            representations.pop(representation_id, None)
        next_state = DestructiveCompactionState.create(
            intent=state.intent,
            phase=DestructiveCompactionPhase.SOURCE_RETIRED,
            switch_receipt=state.switch_receipt,
            retirement_manifest=manifest,
            target_semantic_root_digest=target.semantic_root_digest,
            target_canonical_semantic_digest=target.canonical_semantic_digest,
        )
        compactions[state.intent.compaction_id] = next_state.canonical_payload()
        self._commit(epoch=authority_epoch, expected_revision=revision, payload=payload)
        self._inject(fault_after, DestructiveCompactionPhase.SOURCE_RETIRED)
        return next_state

    def verify(
        self,
        compaction_id: str,
        *,
        authority_epoch: AuthorityEpoch,
        fault_after: DestructiveCompactionPhase | str | None = None,
    ) -> DestructiveCompactionState:
        revision, payload = self._read_snapshot()
        representations, compactions = self._payload_maps(payload)
        state = self._recover_payload(payload, str(compaction_id))
        if state.phase == DestructiveCompactionPhase.VERIFIED:
            self._inject(fault_after, DestructiveCompactionPhase.VERIFIED)
            return state
        if state.phase != DestructiveCompactionPhase.SOURCE_RETIRED:
            raise DestructiveCompactionError("verification requires SOURCE_RETIRED phase")
        if state.intent.source_representation_id in representations:
            raise DestructiveCompactionError("verification observed source representation after retirement")
        target = self._representation(representations, state.intent.target_representation_id)
        reconstructed_root = target.archive.reconstruct().semantic_root_digest()
        if reconstructed_root != state.source_semantic_root_digest:
            raise DestructiveCompactionError("target reconstruction does not reproduce source semantic root")
        if target.canonical_semantic_digest != state.source_canonical_semantic_digest:
            raise DestructiveCompactionError("target canonical semantic digest differs from source")
        if target.retained_refs != state.intent.retained_refs:
            raise DestructiveCompactionError("target lost required retention closure before verification")
        next_state = DestructiveCompactionState.create(
            intent=state.intent,
            phase=DestructiveCompactionPhase.VERIFIED,
            switch_receipt=state.switch_receipt,
            retirement_manifest=state.retirement_manifest,
            target_semantic_root_digest=reconstructed_root,
            target_canonical_semantic_digest=target.canonical_semantic_digest,
        )
        compactions[state.intent.compaction_id] = next_state.canonical_payload()
        self._commit(epoch=authority_epoch, expected_revision=revision, payload=payload)
        self._inject(fault_after, DestructiveCompactionPhase.VERIFIED)
        return next_state
