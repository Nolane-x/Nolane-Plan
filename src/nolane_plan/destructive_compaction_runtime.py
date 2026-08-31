from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from .compaction_runtime import (
    _authority_lineage_refs,
    _dormant_refs,
    _make_archive,
    _proof_evidence_debt_refs,
    _unique_fallback_refs,
)
from .destructive_compaction import (
    DestructiveCompactionCoordinator,
    DestructiveCompactionPhase,
    DestructiveCompactionState,
)
from .hashing import digest
from .lineage_recovery import canonical_semantic_digest
from .production_store import AuthorityEpoch, InMemoryProductionStore
from .replay_registry import DEFAULT_REPLAY_REGISTRY, ReplayEventClass, ReplayEventSpec
from .types import ReplayError


_EVENT_BY_PHASE = {
    DestructiveCompactionPhase.PREPARED: "compaction.destructive_prepared",
    DestructiveCompactionPhase.SHADOW_WRITTEN: "compaction.shadow_verified",
    DestructiveCompactionPhase.SWITCH_COMMITTED: "compaction.production_switched",
    DestructiveCompactionPhase.SOURCE_RETIRED: "compaction.source_retired",
    DestructiveCompactionPhase.VERIFIED: "compaction.destructive_verified",
}
_PHASE_ORDER = {phase: index for index, phase in enumerate(DestructiveCompactionPhase, start=1)}


def _required(name: str, value: object) -> str:
    text = str(value).strip()
    if not text:
        raise ValueError(f"{name} must be non-empty")
    return text


@dataclass(frozen=True, slots=True)
class DestructiveCompactionObservation:
    compaction_id: str
    phase: DestructiveCompactionPhase
    state_digest: str
    storage_revision: int
    authority_epoch_digest: str
    source_representation_id: str
    target_representation_id: str
    production_pointer: str
    representation_ids: tuple[str, ...]
    canonical_digest: str

    @classmethod
    def create(
        cls,
        *,
        compaction_id: str,
        phase: DestructiveCompactionPhase | str,
        state_digest: str,
        storage_revision: int,
        authority_epoch_digest: str,
        source_representation_id: str,
        target_representation_id: str,
        production_pointer: str,
        representation_ids: Iterable[str],
    ) -> "DestructiveCompactionObservation":
        parsed = phase if isinstance(phase, DestructiveCompactionPhase) else DestructiveCompactionPhase(str(phase))
        revision = int(storage_revision)
        if revision < 1:
            raise ValueError("destructive-compaction observation storage revision must be positive")
        source = _required("source_representation_id", source_representation_id)
        target = _required("target_representation_id", target_representation_id)
        if source == target:
            raise ValueError("destructive-compaction observation source and target must differ")
        pointer = _required("production_pointer", production_pointer)
        ids = tuple(sorted({_required("representation_id", value) for value in representation_ids}))
        if parsed in {DestructiveCompactionPhase.PREPARED, DestructiveCompactionPhase.SHADOW_WRITTEN}:
            if pointer != source:
                raise ValueError("pre-switch observation must point at source representation")
        else:
            if pointer != target:
                raise ValueError("post-switch observation must point at target representation")
        if parsed == DestructiveCompactionPhase.PREPARED and ids != (source,):
            raise ValueError("prepared observation must expose only source representation")
        if parsed in {DestructiveCompactionPhase.SHADOW_WRITTEN, DestructiveCompactionPhase.SWITCH_COMMITTED}:
            if set(ids) != {source, target}:
                raise ValueError("shadow/switch observation must expose source and target representations")
        if parsed in {DestructiveCompactionPhase.SOURCE_RETIRED, DestructiveCompactionPhase.VERIFIED} and ids != (target,):
            raise ValueError("retired/verified observation must expose only target representation")
        body = {
            "compaction_id": _required("compaction_id", compaction_id),
            "phase": parsed.value,
            "state_digest": _required("state_digest", state_digest),
            "storage_revision": revision,
            "authority_epoch_digest": _required("authority_epoch_digest", authority_epoch_digest),
            "source_representation_id": source,
            "target_representation_id": target,
            "production_pointer": pointer,
            "representation_ids": ids,
        }
        return cls(
            compaction_id=body["compaction_id"],
            phase=parsed,
            state_digest=body["state_digest"],
            storage_revision=revision,
            authority_epoch_digest=body["authority_epoch_digest"],
            source_representation_id=source,
            target_representation_id=target,
            production_pointer=pointer,
            representation_ids=ids,
            canonical_digest=digest(body),
        )

    def canonical_payload(self) -> dict[str, object]:
        return {
            "compaction_id": self.compaction_id,
            "phase": self.phase.value,
            "state_digest": self.state_digest,
            "storage_revision": self.storage_revision,
            "authority_epoch_digest": self.authority_epoch_digest,
            "source_representation_id": self.source_representation_id,
            "target_representation_id": self.target_representation_id,
            "production_pointer": self.production_pointer,
            "representation_ids": list(self.representation_ids),
            "canonical_digest": self.canonical_digest,
        }

    @classmethod
    def from_payload(cls, raw: dict[str, Any]) -> "DestructiveCompactionObservation":
        try:
            value = cls.create(
                compaction_id=str(raw["compaction_id"]),
                phase=str(raw["phase"]),
                state_digest=str(raw["state_digest"]),
                storage_revision=int(raw["storage_revision"]),
                authority_epoch_digest=str(raw["authority_epoch_digest"]),
                source_representation_id=str(raw["source_representation_id"]),
                target_representation_id=str(raw["target_representation_id"]),
                production_pointer=str(raw["production_pointer"]),
                representation_ids=tuple(str(x) for x in raw.get("representation_ids", ())),
            )
        except Exception as exc:
            raise ValueError(f"invalid destructive-compaction observation: {exc}") from exc
        if value.canonical_digest != str(raw.get("canonical_digest", "")):
            raise ValueError("destructive-compaction observation digest mismatch")
        return value


def _register_replay_events() -> None:
    for phase, event_type in _EVENT_BY_PHASE.items():
        if event_type in DEFAULT_REPLAY_REGISTRY.event_types:
            continue
        spec = ReplayEventSpec(
            event_type,
            ReplayEventClass.STATE_REDUCER,
            correctness_significant=True,
            reducer_name=f"destructive_compaction_{phase.value}",
        )
        DEFAULT_REPLAY_REGISTRY._specs = (*DEFAULT_REPLAY_REGISTRY._specs, spec)
        DEFAULT_REPLAY_REGISTRY._by_event[event_type] = spec


def _install_state(self) -> None:
    self.destructive_compaction_observations: dict[str, DestructiveCompactionObservation] = {}


def _accept_observation(kernel, observation: DestructiveCompactionObservation, *, replay: bool) -> DestructiveCompactionObservation:
    existing = kernel.destructive_compaction_observations.get(observation.compaction_id)
    if existing is not None:
        if observation.source_representation_id != existing.source_representation_id or observation.target_representation_id != existing.target_representation_id:
            error = "destructive compaction observation changed representation identity"
            if replay:
                raise ReplayError(error)
            raise ValueError(error)
        old_order = _PHASE_ORDER[existing.phase]
        new_order = _PHASE_ORDER[observation.phase]
        if new_order < old_order:
            error = "destructive compaction observation regressed durable phase"
            if replay:
                raise ReplayError(error)
            raise ValueError(error)
        if new_order == old_order:
            if observation.state_digest != existing.state_digest:
                error = "destructive compaction phase was rebound to different durable state"
                if replay:
                    raise ReplayError(error)
                raise ValueError(error)
            return existing
        if observation.storage_revision <= existing.storage_revision:
            error = "destructive compaction observation advanced without storage revision progress"
            if replay:
                raise ReplayError(error)
            raise ValueError(error)
    kernel.destructive_compaction_observations[observation.compaction_id] = observation
    return observation


def _emit_observation(self, observation: DestructiveCompactionObservation) -> None:
    payload = {"observation": observation.canonical_payload()}
    if observation.phase == DestructiveCompactionPhase.PREPARED:
        self._record("compaction.destructive_prepared", payload)
    elif observation.phase == DestructiveCompactionPhase.SHADOW_WRITTEN:
        self._record("compaction.shadow_verified", payload)
    elif observation.phase == DestructiveCompactionPhase.SWITCH_COMMITTED:
        self._record("compaction.production_switched", payload)
    elif observation.phase == DestructiveCompactionPhase.SOURCE_RETIRED:
        self._record("compaction.source_retired", payload)
    elif observation.phase == DestructiveCompactionPhase.VERIFIED:
        self._record("compaction.destructive_verified", payload)
    else:
        raise ValueError(f"unsupported destructive compaction phase: {observation.phase!r}")


def _observe(self, store: InMemoryProductionStore, epoch: AuthorityEpoch, state: DestructiveCompactionState) -> DestructiveCompactionObservation:
    coordinator = DestructiveCompactionCoordinator(store)
    pointer = coordinator.production_pointer()
    if pointer is None:
        raise ValueError("durable destructive compaction phase has no production pointer")
    observation = DestructiveCompactionObservation.create(
        compaction_id=state.intent.compaction_id,
        phase=state.phase,
        state_digest=state.canonical_digest,
        storage_revision=store.current_revision(),
        authority_epoch_digest=epoch.canonical_digest,
        source_representation_id=state.intent.source_representation_id,
        target_representation_id=state.intent.target_representation_id,
        production_pointer=pointer,
        representation_ids=coordinator.representation_ids(),
    )
    existing = self.destructive_compaction_observations.get(observation.compaction_id)
    if existing is not None and existing.phase == observation.phase and existing.state_digest == observation.state_digest:
        return existing
    # The production-store CAS is the physical authority. The journal is an
    # independently durable observation stream. Persist the observation before
    # advancing the in-memory sidecar; a later idempotent retry reconciles a
    # store commit that survived while the journal write did not.
    _emit_observation(self, observation)
    return _accept_observation(self, observation, replay=False)


def _prepare_destructive_compaction(
    self,
    store: InMemoryProductionStore,
    authority_epoch: AuthorityEpoch,
    *,
    compaction_id: str,
    source_representation_id: str,
    target_representation_id: str,
    dormant_branches: Iterable[object] = (),
    fault_after: DestructiveCompactionPhase | str | None = None,
) -> DestructiveCompactionState:
    with self._writer_lock:
        archive = _make_archive(self)
        coordinator = DestructiveCompactionCoordinator(store)
        state = coordinator.prepare(
            compaction_id=compaction_id,
            source_representation_id=source_representation_id,
            target_representation_id=target_representation_id,
            source_archive=archive,
            source_canonical_semantic_digest=canonical_semantic_digest(self),
            active_authority_refs=_authority_lineage_refs(self),
            dormant_resurrection_refs=_dormant_refs(tuple(dormant_branches)),
            proof_evidence_debt_refs=_proof_evidence_debt_refs(self),
            unique_fallback_refs=_unique_fallback_refs(self),
            authority_epoch=authority_epoch,
            fault_after=fault_after,
        )
        _observe(self, store, authority_epoch, state)
        return state


def _verify_compaction_shadow(
    self,
    store: InMemoryProductionStore,
    authority_epoch: AuthorityEpoch,
    compaction_id: str,
    *,
    target_archive=None,
    fault_after: DestructiveCompactionPhase | str | None = None,
) -> DestructiveCompactionState:
    with self._writer_lock:
        coordinator = DestructiveCompactionCoordinator(store)
        archive = _make_archive(self) if target_archive is None else target_archive
        state = coordinator.write_shadow(
            compaction_id,
            archive,
            authority_epoch=authority_epoch,
            fault_after=fault_after,
        )
        _observe(self, store, authority_epoch, state)
        return state


def _commit_compaction_switch(
    self,
    store: InMemoryProductionStore,
    authority_epoch: AuthorityEpoch,
    compaction_id: str,
    *,
    fault_after: DestructiveCompactionPhase | str | None = None,
) -> DestructiveCompactionState:
    with self._writer_lock:
        coordinator = DestructiveCompactionCoordinator(store)
        state = coordinator.commit_switch(compaction_id, authority_epoch=authority_epoch, fault_after=fault_after)
        _observe(self, store, authority_epoch, state)
        return state


def _retire_compaction_source(
    self,
    store: InMemoryProductionStore,
    authority_epoch: AuthorityEpoch,
    compaction_id: str,
    *,
    fault_after: DestructiveCompactionPhase | str | None = None,
) -> DestructiveCompactionState:
    with self._writer_lock:
        coordinator = DestructiveCompactionCoordinator(store)
        state = coordinator.retire_source(compaction_id, authority_epoch=authority_epoch, fault_after=fault_after)
        _observe(self, store, authority_epoch, state)
        return state


def _verify_destructive_compaction(
    self,
    store: InMemoryProductionStore,
    authority_epoch: AuthorityEpoch,
    compaction_id: str,
    *,
    fault_after: DestructiveCompactionPhase | str | None = None,
) -> DestructiveCompactionState:
    with self._writer_lock:
        coordinator = DestructiveCompactionCoordinator(store)
        state = coordinator.verify(compaction_id, authority_epoch=authority_epoch, fault_after=fault_after)
        _observe(self, store, authority_epoch, state)
        return state


def _replay_observation(kernel, entry) -> None:
    raw = entry.payload.get("observation")
    if not isinstance(raw, dict):
        raise ReplayError("destructive-compaction replay lacks observation payload")
    try:
        observation = DestructiveCompactionObservation.from_payload(dict(raw))
    except Exception as exc:
        raise ReplayError(f"invalid destructive-compaction observation replay: {exc}") from exc
    expected_event = _EVENT_BY_PHASE[observation.phase]
    if entry.event_type != expected_event:
        raise ReplayError("destructive-compaction event type/phase mismatch")
    _accept_observation(kernel, observation, replay=True)


def _install_replay_reducer() -> None:
    from . import lineage_recovery

    original = lineage_recovery._replay_base_entry

    def _replay_base_entry(kernel, entry) -> bool:
        if entry.event_type not in set(_EVENT_BY_PHASE.values()):
            return original(kernel, entry)
        _replay_observation(kernel, entry)
        lineage_recovery._restore_meta(kernel, dict(entry.payload))
        return True

    lineage_recovery._replay_base_entry = _replay_base_entry


def install_destructive_compaction_runtime(kernel_cls) -> None:
    """Install Wave-9 physical compaction integration on the existing kernel/replay path."""
    if getattr(kernel_cls, "_wave9_destructive_compaction_runtime_installed", False):
        return
    _register_replay_events()
    original_init = kernel_cls.__init__

    def __init__(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        _install_state(self)

    kernel_cls.__init__ = __init__
    _install_replay_reducer()
    kernel_cls.prepare_destructive_compaction = _prepare_destructive_compaction
    kernel_cls.verify_compaction_shadow = _verify_compaction_shadow
    kernel_cls.commit_compaction_switch = _commit_compaction_switch
    kernel_cls.retire_compaction_source = _retire_compaction_source
    kernel_cls.verify_destructive_compaction = _verify_destructive_compaction
    kernel_cls._wave9_destructive_compaction_runtime_installed = True
