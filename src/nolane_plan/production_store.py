from __future__ import annotations

import copy
import threading
from dataclasses import dataclass
from enum import Enum
from typing import Any

from .hashing import digest


class StorageConflict(RuntimeError):
    """Raised when a conditional storage operation loses its authority race."""


class UnsupportedStorageCapability(RuntimeError):
    """Raised when a backend cannot support the requested correctness contract."""


class StorageSupport(str, Enum):
    UNSUPPORTED = "unsupported"
    SINGLE_WRITER = "single_writer"
    STRONG_MULTI_WRITER = "strong_multi_writer"


def _required(name: str, value: object) -> str:
    text = str(value).strip()
    if not text:
        raise ValueError(f"{name} must be non-empty")
    return text


@dataclass(frozen=True, slots=True)
class StorageCapabilityProfile:
    backend_id: str
    revision: int
    atomic_replace: bool
    durable_acknowledgement: bool
    compare_and_swap: bool
    fencing_tokens: bool
    transactional_batch: bool
    destructive_delete: bool
    crash_recovery_durable: bool
    canonical_digest: str

    @classmethod
    def create(
        cls,
        *,
        backend_id: str,
        revision: int,
        atomic_replace: bool,
        durable_acknowledgement: bool,
        compare_and_swap: bool,
        fencing_tokens: bool,
        transactional_batch: bool,
        destructive_delete: bool,
        crash_recovery_durable: bool,
    ) -> "StorageCapabilityProfile":
        backend = _required("backend_id", backend_id)
        rev = int(revision)
        if rev < 1:
            raise ValueError("storage capability revision must be positive")
        body = {
            "backend_id": backend,
            "revision": rev,
            "atomic_replace": bool(atomic_replace),
            "durable_acknowledgement": bool(durable_acknowledgement),
            "compare_and_swap": bool(compare_and_swap),
            "fencing_tokens": bool(fencing_tokens),
            "transactional_batch": bool(transactional_batch),
            "destructive_delete": bool(destructive_delete),
            "crash_recovery_durable": bool(crash_recovery_durable),
        }
        return cls(**body, canonical_digest=digest(body))

    @property
    def support(self) -> StorageSupport:
        if (
            self.atomic_replace
            and self.durable_acknowledgement
            and self.compare_and_swap
            and self.fencing_tokens
            and self.crash_recovery_durable
        ):
            return StorageSupport.STRONG_MULTI_WRITER
        if self.atomic_replace and self.durable_acknowledgement and self.crash_recovery_durable:
            return StorageSupport.SINGLE_WRITER
        return StorageSupport.UNSUPPORTED

    def require_strong_multiwriter(self) -> bool:
        if self.support != StorageSupport.STRONG_MULTI_WRITER:
            raise UnsupportedStorageCapability(
                "strong multi-writer storage requires durable acknowledgement, atomic replace, compare-and-swap, fencing tokens and crash recovery"
            )
        return True


@dataclass(frozen=True, slots=True)
class AuthorityEpoch:
    backend_id: str
    backend_revision: int
    epoch: int
    predecessor_epoch: int | None
    writer_id: str
    acquisition_revision: int
    acquisition_receipt_digest: str
    canonical_digest: str

    @classmethod
    def create(
        cls,
        *,
        backend_id: str,
        backend_revision: int,
        epoch: int,
        predecessor_epoch: int | None,
        writer_id: str,
        acquisition_revision: int,
    ) -> "AuthorityEpoch":
        backend = _required("backend_id", backend_id)
        writer = _required("writer_id", writer_id)
        backend_rev = int(backend_revision)
        epoch_value = int(epoch)
        acquisition_rev = int(acquisition_revision)
        if backend_rev < 1:
            raise ValueError("authority epoch backend revision must be positive")
        if epoch_value < 1:
            raise ValueError("authority epoch must be positive")
        if acquisition_rev < 0:
            raise ValueError("authority epoch acquisition revision cannot be negative")
        predecessor = None if predecessor_epoch is None else int(predecessor_epoch)
        if epoch_value == 1:
            if predecessor is not None:
                raise ValueError("first authority epoch cannot declare a predecessor")
        elif predecessor != epoch_value - 1:
            raise ValueError("authority epoch predecessor must be the immediately prior epoch")
        body = {
            "backend_id": backend,
            "backend_revision": backend_rev,
            "epoch": epoch_value,
            "predecessor_epoch": predecessor,
            "writer_id": writer,
            "acquisition_revision": acquisition_rev,
        }
        acquisition_receipt_digest = digest({"kind": "authority_epoch_acquisition", **body})
        canonical_digest = digest({**body, "acquisition_receipt_digest": acquisition_receipt_digest})
        return cls(
            backend_id=backend,
            backend_revision=backend_rev,
            epoch=epoch_value,
            predecessor_epoch=predecessor,
            writer_id=writer,
            acquisition_revision=acquisition_rev,
            acquisition_receipt_digest=acquisition_receipt_digest,
            canonical_digest=canonical_digest,
        )


@dataclass(frozen=True, slots=True)
class ConditionalWriteReceipt:
    backend_id: str
    backend_revision: int
    expected_revision: int
    committed_revision: int
    epoch: int
    writer_id: str
    payload_digest: str
    durable_acknowledged: bool
    canonical_digest: str

    @classmethod
    def create(
        cls,
        *,
        backend_id: str,
        backend_revision: int,
        expected_revision: int,
        committed_revision: int,
        epoch: int,
        writer_id: str,
        payload_digest: str,
        durable_acknowledged: bool,
    ) -> "ConditionalWriteReceipt":
        backend = _required("backend_id", backend_id)
        writer = _required("writer_id", writer_id)
        payload = _required("payload_digest", payload_digest)
        backend_rev = int(backend_revision)
        expected = int(expected_revision)
        committed = int(committed_revision)
        epoch_value = int(epoch)
        if backend_rev < 1:
            raise ValueError("conditional-write backend revision must be positive")
        if expected < 0 or committed != expected + 1:
            raise ValueError("conditional-write revision must advance exactly once")
        if epoch_value < 1:
            raise ValueError("conditional-write epoch must be positive")
        if not durable_acknowledged:
            raise ValueError("authoritative conditional write requires durable acknowledgement")
        body = {
            "backend_id": backend,
            "backend_revision": backend_rev,
            "expected_revision": expected,
            "committed_revision": committed,
            "epoch": epoch_value,
            "writer_id": writer,
            "payload_digest": payload,
            "durable_acknowledged": True,
        }
        return cls(**body, canonical_digest=digest(body))


class InMemoryProductionStore:
    """Deterministic bounded reference store with real CAS/fencing semantics.

    The class models the storage contract required by Wave 9. It is intentionally
    not a distributed consensus implementation; callers requesting strong
    multi-writer behavior must supply a capability profile that proves the
    required primitives.
    """

    def __init__(
        self,
        capabilities: StorageCapabilityProfile,
        *,
        require_strong_multiwriter: bool = False,
    ) -> None:
        self.capabilities = capabilities
        if require_strong_multiwriter:
            capabilities.require_strong_multiwriter()
        self._strong_mode = bool(require_strong_multiwriter)
        self._lock = threading.RLock()
        self._epoch: AuthorityEpoch | None = None
        self._revision = 0
        self._payload: dict[str, Any] = {}

    def current_epoch(self) -> AuthorityEpoch | None:
        with self._lock:
            return self._epoch

    def current_revision(self) -> int:
        with self._lock:
            return self._revision

    def read_payload(self) -> dict[str, object]:
        with self._lock:
            return copy.deepcopy(self._payload)

    def acquire_epoch(self, writer_id: str, expected_epoch: int | None) -> AuthorityEpoch:
        with self._lock:
            self.capabilities.require_strong_multiwriter()
            current_epoch = None if self._epoch is None else self._epoch.epoch
            expected = None if expected_epoch is None else int(expected_epoch)
            if current_epoch != expected:
                raise StorageConflict(
                    f"authority epoch compare-and-swap failed: current={current_epoch!r}, expected={expected!r}"
                )
            next_epoch = 1 if current_epoch is None else current_epoch + 1
            value = AuthorityEpoch.create(
                backend_id=self.capabilities.backend_id,
                backend_revision=self.capabilities.revision,
                epoch=next_epoch,
                predecessor_epoch=current_epoch,
                writer_id=writer_id,
                acquisition_revision=self._revision,
            )
            self._epoch = value
            return value

    def _assert_current_epoch(self, epoch: AuthorityEpoch) -> AuthorityEpoch:
        current = self._epoch
        if current is None:
            raise StorageConflict("no authority epoch is currently held")
        if epoch.backend_id != self.capabilities.backend_id or epoch.backend_revision != self.capabilities.revision:
            raise StorageConflict("authority epoch storage capability binding is stale")
        if epoch.canonical_digest != current.canonical_digest:
            raise StorageConflict(
                f"stale authority epoch: current={current.epoch}, attempted={epoch.epoch}"
            )
        return current

    def conditional_commit(
        self,
        epoch: AuthorityEpoch,
        *,
        expected_revision: int,
        payload: dict[str, object],
    ) -> ConditionalWriteReceipt:
        with self._lock:
            self.capabilities.require_strong_multiwriter()
            current = self._assert_current_epoch(epoch)
            expected = int(expected_revision)
            if expected != self._revision:
                raise StorageConflict(
                    f"storage revision compare-and-swap failed: current={self._revision}, expected={expected}"
                )
            next_revision = self._revision + 1
            payload_copy = copy.deepcopy(dict(payload))
            receipt = ConditionalWriteReceipt.create(
                backend_id=self.capabilities.backend_id,
                backend_revision=self.capabilities.revision,
                expected_revision=self._revision,
                committed_revision=next_revision,
                epoch=current.epoch,
                writer_id=current.writer_id,
                payload_digest=digest(payload_copy),
                durable_acknowledged=self.capabilities.durable_acknowledgement,
            )
            self._payload = payload_copy
            self._revision = next_revision
            return receipt
