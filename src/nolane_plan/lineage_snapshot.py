from __future__ import annotations

from pathlib import Path
from typing import Any

from .actions import ExecutionReceipt
from .hashing import digest
from .lineage import CanonicalLineageRevision, LineageRegistry, SemanticRegimeKind, SemanticRegimeRevision
from .lineage_recovery import _flush_pending_canonical, _manifest_from_doc, _replay_entry
from .lineage_runtime import (
    AuthorizationLineageBinding,
    _action_payload,
    _adapter_payload,
    _canonical_state_semantic_digest,
    _evidence_payload,
    _future_payload,
    _grant_payload,
    _mission_semantic_digest,
    _obligation_payload,
    _region_payload,
)
from .migration import MigrationBridgeEvidence, MigrationResult
from .mission import MissionContract, MissionLedger
from .persistence import HashJournal, SnapshotStore
from .policy_recovery import _restore_policy_state
from .proof_recovery import _restore_proof_state
from .replay_registry import DEFAULT_REPLAY_REGISTRY
from .resume import SNAPSHOT_SCHEMA as BASE_SNAPSHOT_SCHEMA
from .resume import _find_snapshot_prefix, _restore_state
from .schedulability_recovery import SCHEDULABILITY_SNAPSHOT_SCHEMA, _restore_schedulability_state
from .trust_recovery import _restore_trust_state
from .types import ReplayError


LINEAGE_SNAPSHOT_SCHEMA = "nolane-plan-runtime-snapshot-v7"
_LEGACY_IMPORT_PROVENANCE = "snapshot-v6-import"


def _lineage_revision_doc(row: CanonicalLineageRevision) -> dict[str, Any]:
    return {
        "object_family": row.object_family,
        "logical_id": row.logical_id,
        "revision_id": row.revision_id,
        "schema_version": row.schema_version,
        "created_sequence": row.created_sequence,
        "created_at_wall_time": row.created_at_wall_time,
        "mission_revision_dependency": row.mission_revision_dependency,
        "plan_revision": row.plan_revision,
        "world_model_revision": row.world_model_revision,
        "environment_regime_revision": row.environment_regime_revision,
        "validity_regime": row.validity_regime,
        "parent_revision_ids": list(row.parent_revision_ids),
        "provenance_refs": list(row.provenance_refs),
        "assurance_profile": row.assurance_profile,
        "debt_refs": list(row.debt_refs),
        "supersedes_revision_id": row.supersedes_revision_id,
        "semantic_digest": row.semantic_digest,
        "lineage_digest": row.lineage_digest,
    }


def _lineage_revision_from_doc(raw: dict[str, Any]) -> CanonicalLineageRevision:
    row = CanonicalLineageRevision.create(
        object_family=str(raw["object_family"]),
        logical_id=str(raw["logical_id"]),
        revision_id=str(raw["revision_id"]),
        schema_version=str(raw["schema_version"]),
        created_sequence=int(raw["created_sequence"]),
        created_at_wall_time=raw.get("created_at_wall_time"),
        mission_revision_dependency=raw.get("mission_revision_dependency"),
        plan_revision=int(raw["plan_revision"]),
        world_model_revision=str(raw["world_model_revision"]),
        environment_regime_revision=str(raw["environment_regime_revision"]),
        validity_regime=str(raw["validity_regime"]),
        parent_revision_ids=tuple(str(x) for x in raw.get("parent_revision_ids", ())),
        provenance_refs=tuple(str(x) for x in raw.get("provenance_refs", ())),
        assurance_profile=str(raw["assurance_profile"]),
        debt_refs=tuple(str(x) for x in raw.get("debt_refs", ())),
        supersedes_revision_id=raw.get("supersedes_revision_id"),
        semantic_digest=str(raw["semantic_digest"]),
    )
    if row.lineage_digest != str(raw.get("lineage_digest", "")):
        raise ReplayError("Wave-7 lineage record canonical digest mismatch")
    return row


def _regime_doc(row: SemanticRegimeRevision) -> dict[str, Any]:
    return {
        "regime_kind": row.regime_kind.value,
        "logical_id": row.logical_id,
        "revision_id": row.revision_id,
        "created_sequence": row.created_sequence,
        "parent_revision_id": row.parent_revision_id,
        "semantic_digest": row.semantic_digest,
        "provenance_refs": list(row.provenance_refs),
        "canonical_digest": row.canonical_digest,
    }


def _regime_from_doc(raw: dict[str, Any]) -> SemanticRegimeRevision:
    row = SemanticRegimeRevision.create(
        regime_kind=str(raw["regime_kind"]),
        logical_id=str(raw["logical_id"]),
        revision_id=str(raw["revision_id"]),
        created_sequence=int(raw["created_sequence"]),
        parent_revision_id=raw.get("parent_revision_id"),
        semantic_digest=str(raw["semantic_digest"]),
        provenance_refs=tuple(str(x) for x in raw.get("provenance_refs", ())),
    )
    if row.canonical_digest != str(raw.get("canonical_digest", "")):
        raise ReplayError("Wave-7 semantic-regime canonical digest mismatch")
    return row


def _authorization_binding_doc(binding: AuthorizationLineageBinding) -> dict[str, Any]:
    return {
        "authorization_id": binding.authorization_id,
        "mission_revision_id": binding.mission_revision_id,
        "canonical_state_revision_id": binding.canonical_state_revision_id,
        "action_revision_id": binding.action_revision_id,
        "grant_revision_ids": list(binding.grant_revision_ids),
        "regime_revisions": [list(pair) for pair in binding.regime_revisions],
        "created_sequence": binding.created_sequence,
        "canonical_digest": binding.canonical_digest,
    }


def _authorization_binding_from_doc(raw: dict[str, Any]) -> AuthorizationLineageBinding:
    binding = AuthorizationLineageBinding.create(
        authorization_id=str(raw["authorization_id"]),
        mission_revision_id=str(raw["mission_revision_id"]),
        canonical_state_revision_id=str(raw["canonical_state_revision_id"]),
        action_revision_id=str(raw["action_revision_id"]),
        grant_revision_ids=tuple(str(x) for x in raw.get("grant_revision_ids", ())),
        regime_revisions=tuple((str(a), str(b)) for a, b in raw.get("regime_revisions", ())),
        created_sequence=int(raw["created_sequence"]),
    )
    if binding.canonical_digest != str(raw.get("canonical_digest", "")):
        raise ReplayError("Wave-7 authorization lineage binding digest mismatch")
    return binding


def _migration_result_doc(row: MigrationResult) -> dict[str, Any]:
    return {
        "manifest_id": row.manifest_id,
        "source_schema_revision": row.source_schema_revision,
        "target_schema_revision": row.target_schema_revision,
        "invalidated_authorization_ids": list(row.invalidated_authorization_ids),
        "new_debt_refs": list(row.new_debt_refs),
        "bridge_evidence_ref": row.bridge_evidence_ref,
        "root_switched_sequence": row.root_switched_sequence,
        "canonical_digest": row.canonical_digest,
    }


def _migration_result_from_doc(raw: dict[str, Any]) -> MigrationResult:
    row = MigrationResult.create(
        manifest_id=str(raw["manifest_id"]),
        source_schema_revision=str(raw["source_schema_revision"]),
        target_schema_revision=str(raw["target_schema_revision"]),
        invalidated_authorization_ids=tuple(str(x) for x in raw.get("invalidated_authorization_ids", ())),
        new_debt_refs=tuple(str(x) for x in raw.get("new_debt_refs", ())),
        bridge_evidence_ref=raw.get("bridge_evidence_ref"),
        root_switched_sequence=int(raw["root_switched_sequence"]),
    )
    if row.canonical_digest != str(raw.get("canonical_digest", "")):
        raise ReplayError("Wave-7 migration result canonical digest mismatch")
    return row


def _bridge_doc(row: MigrationBridgeEvidence) -> dict[str, Any]:
    return {
        "evidence_ref": row.evidence_ref,
        "source_schema_revision": row.source_schema_revision,
        "target_schema_revision": row.target_schema_revision,
        "transaction_ids": list(row.transaction_ids),
        "verified": row.verified,
        "canonical_digest": row.canonical_digest,
    }


def _bridge_from_doc(raw: dict[str, Any]) -> MigrationBridgeEvidence:
    row = MigrationBridgeEvidence.create(
        evidence_ref=str(raw["evidence_ref"]),
        source_schema_revision=str(raw["source_schema_revision"]),
        target_schema_revision=str(raw["target_schema_revision"]),
        transaction_ids=tuple(str(x) for x in raw.get("transaction_ids", ())),
        verified=bool(raw["verified"]),
    )
    if row.canonical_digest != str(raw.get("canonical_digest", "")):
        raise ReplayError("Wave-7 migration bridge canonical digest mismatch")
    return row


def _receipt_payload(row: ExecutionReceipt) -> dict[str, Any]:
    return {
        "id": row.id,
        "action_id": row.action_id,
        "authorization_id": row.authorization_id,
        "executing_principal_ref": row.executing_principal_ref,
        "transport_ok": row.transport_ok,
        "postconditions_verified": row.postconditions_verified,
        "state_patch": row.state_patch,
        "observed_at": row.observed_at,
    }


def _receipt_doc(row: ExecutionReceipt) -> dict[str, Any]:
    payload = _receipt_payload(row)
    return {**payload, "canonical_digest": digest(payload)}


def _receipt_from_doc(raw: dict[str, Any]) -> ExecutionReceipt:
    payload = {
        "id": str(raw["id"]),
        "action_id": str(raw["action_id"]),
        "authorization_id": str(raw["authorization_id"]),
        "executing_principal_ref": str(raw["executing_principal_ref"]),
        "transport_ok": bool(raw["transport_ok"]),
        "postconditions_verified": bool(raw["postconditions_verified"]),
        "state_patch": dict(raw.get("state_patch", {})),
        "observed_at": raw["observed_at"],
    }
    if digest(payload) != str(raw.get("canonical_digest", "")):
        raise ReplayError("Wave-7 historical receipt canonical digest mismatch")
    return ExecutionReceipt(
        payload["id"], payload["action_id"], payload["authorization_id"],
        payload["executing_principal_ref"], payload["transport_ok"],
        payload["postconditions_verified"], payload["state_patch"], payload["observed_at"],
    )


def _replay_registry_state() -> dict[str, Any]:
    specs = [
        {
            "event_type": spec.event_type,
            "classification": spec.classification.value,
            "correctness_significant": spec.correctness_significant,
            "reducer_name": spec.reducer_name,
            "delegate_layer": spec.delegate_layer,
        }
        for spec in sorted(DEFAULT_REPLAY_REGISTRY.specs, key=lambda item: item.event_type)
    ]
    return {"specs": specs, "canonical_digest": digest(specs)}


def _current_pointer_rows(kernel) -> list[dict[str, str]]:
    keys = sorted({(row.object_family, row.logical_id) for row in kernel.lineage.all_revisions()})
    return [
        {
            "object_family": family,
            "logical_id": logical_id,
            "revision_id": kernel.lineage.current(family, logical_id).revision_id,
        }
        for family, logical_id in keys
    ]


def _wave7_state(kernel) -> dict[str, Any]:
    manifests = {
        key: value.canonical_payload()
        for key, value in sorted(kernel.migration_manifests.items())
    }
    bridges = {
        key: _bridge_doc(value)
        for key, value in sorted(kernel.migration_bridges.items())
    }
    receipts = {
        key: _receipt_doc(value)
        for key, value in sorted(kernel.receipts.items())
    }
    return {
        "revisions": [_lineage_revision_doc(row) for row in kernel.lineage.all_revisions()],
        "current_pointers": _current_pointer_rows(kernel),
        "regimes": [_regime_doc(row) for row in kernel.lineage.all_regimes()],
        "current_regime_pointers": {
            kind.value: kernel.lineage.current_regime(kind).revision_id
            for kind in SemanticRegimeKind
        },
        "semantic_root_digest": kernel.lineage.semantic_root_digest(),
        "authorization_bindings": {
            key: _authorization_binding_doc(value)
            for key, value in sorted(kernel.authorization_lineage_bindings.items())
        },
        "migration": {
            "manifests": manifests,
            "history": [_migration_result_doc(row) for row in kernel.migration_history],
            "bridges": bridges,
            "recheck_required_authorizations": sorted(kernel.migration_recheck_required_authorizations),
        },
        "receipts": receipts,
        # Task 6 owns the first non-empty compaction representation. Task 5
        # reserves and persists the envelope so absence cannot be confused with
        # an omitted correctness surface.
        "compaction": {
            "manifests": list(getattr(kernel, "_wave7_compaction_snapshot_manifests", ())),
            "archive": list(getattr(kernel, "_wave7_compaction_snapshot_archive", ())),
        },
        "replay_registry": _replay_registry_state(),
    }


def _snapshot_state(kernel, base_snapshot_state) -> dict[str, Any]:
    state = dict(base_snapshot_state(kernel))
    state["snapshot_schema"] = LINEAGE_SNAPSHOT_SCHEMA
    state["lineage"] = _wave7_state(kernel)
    return state


def _restore_base_v6_layers(cls, root: Path, state: dict[str, Any]):
    mission_doc = state.get("mission") or {}
    if not mission_doc:
        raise ReplayError("snapshot has no mission contract")
    mission = MissionLedger(MissionContract(
        int(mission_doc["version"]), str(mission_doc["objective"]),
        tuple(mission_doc.get("success_conditions", ())), tuple(mission_doc.get("hard_constraints", ())),
        tuple(mission_doc.get("soft_preferences", ())), tuple(mission_doc.get("anti_goals", ())),
        mission_doc.get("risk_budget"),
    ))
    kernel = cls(root, mission)
    core_state = dict(state)
    core_state["snapshot_schema"] = BASE_SNAPSHOT_SCHEMA
    core_state.pop("trust", None)
    core_state.pop("proof", None)
    core_state.pop("policy", None)
    core_state.pop("schedulability", None)
    core_state.pop("lineage", None)
    _restore_state(kernel, core_state)

    trust = state.get("trust")
    proof = state.get("proof")
    policy = state.get("policy")
    wave6 = state.get("schedulability")
    if not isinstance(trust, dict):
        raise ReplayError("v6/v7 snapshot is missing trust state")
    if not isinstance(proof, dict):
        raise ReplayError("v6/v7 snapshot is missing proof state")
    if not isinstance(policy, dict):
        raise ReplayError("v6/v7 snapshot is missing policy state")
    if not isinstance(wave6, dict):
        raise ReplayError("v6/v7 snapshot is missing schedulability state")
    _restore_trust_state(kernel, trust)
    _restore_proof_state(kernel, proof)
    _restore_policy_state(kernel, policy)
    _restore_schedulability_state(kernel, wave6)
    return kernel


def _reset_object_lineage_preserving_regimes(kernel) -> None:
    regimes = kernel.lineage.all_regimes()
    replacement = LineageRegistry()
    for regime in regimes:
        replacement.register_regime(regime)
    kernel.lineage = replacement
    kernel.semantic_regimes = {
        kind: replacement.current_regime(kind).revision_id for kind in SemanticRegimeKind
    }


def _legacy_root(kernel, *, object_family: str, logical_id: str, semantic_payload=None, semantic_digest=None, provenance: str):
    return kernel._register_lineage(
        object_family=object_family,
        logical_id=logical_id,
        semantic_payload=semantic_payload,
        semantic_digest=semantic_digest,
        provenance_refs=(_LEGACY_IMPORT_PROVENANCE, provenance),
        parent_revision_ids=(),
        supersedes_revision_id=None,
        created_sequence=0,
        mission_dependency=object_family != "MissionRevision",
    )


def _import_v6_roots(kernel) -> None:
    _reset_object_lineage_preserving_regimes(kernel)
    _legacy_root(
        kernel, object_family="MissionRevision", logical_id="mission",
        semantic_digest=_mission_semantic_digest(kernel), provenance="kernel:mission-ledger",
    )
    _legacy_root(
        kernel, object_family="CanonicalState", logical_id="canonical-state",
        semantic_digest=_canonical_state_semantic_digest(kernel), provenance="kernel:canonical-state",
    )
    for row in sorted(kernel.evidence.records.values(), key=lambda item: item.id):
        _legacy_root(
            kernel, object_family="EvidenceRecord", logical_id=row.id,
            semantic_payload=_evidence_payload(row), provenance="kernel:evidence-ledger",
        )
    for row in sorted(kernel.future.families.values(), key=lambda item: item.id):
        _legacy_root(
            kernel, object_family="FutureFamily", logical_id=row.id,
            semantic_payload=_future_payload(row), provenance="kernel:future-lattice",
        )
    for row in sorted(kernel.obligations._items.values(), key=lambda item: item.id):
        _legacy_root(
            kernel, object_family="StrategicObligation", logical_id=row.id,
            semantic_payload=_obligation_payload(row), provenance="kernel:obligation-ledger",
        )
    for row in sorted(kernel.actions.values(), key=lambda item: item.id):
        _legacy_root(
            kernel, object_family="ActionIntent", logical_id=row.id,
            semantic_payload=_action_payload(row), provenance="kernel:action-registry",
        )
    for row in sorted(kernel.grants.values(), key=lambda item: item.id):
        _legacy_root(
            kernel, object_family="AuthorityGrant", logical_id=row.id,
            semantic_payload=_grant_payload(row), provenance="kernel:authority-registry",
        )
    for row in sorted(kernel.adapters.values(), key=lambda item: item.adapter_id):
        _legacy_root(
            kernel, object_family="AdapterProfile", logical_id=row.adapter_id,
            semantic_payload=_adapter_payload(row), provenance="kernel:adapter-registry",
        )
    for row in sorted(kernel.regions, key=lambda item: item.id):
        _legacy_root(
            kernel, object_family="CandidateRegion", logical_id=row.id,
            semantic_payload=_region_payload(row), provenance="kernel:region-registry",
        )


def _restore_lineage_registry(kernel, state: dict[str, Any]) -> None:
    registry = LineageRegistry()
    regime_rows = [_regime_from_doc(dict(raw)) for raw in state.get("regimes", ())]
    for row in sorted(regime_rows, key=lambda item: (item.created_sequence, item.revision_id)):
        registry.register_regime(row)

    expected_regime_pointers = {
        SemanticRegimeKind.parse(kind): str(revision_id)
        for kind, revision_id in dict(state.get("current_regime_pointers", {})).items()
    }
    if set(expected_regime_pointers) != set(SemanticRegimeKind):
        raise ReplayError("Wave-7 snapshot has incomplete semantic-regime current pointers")
    for kind, revision_id in expected_regime_pointers.items():
        if registry.current_regime(kind).revision_id != revision_id:
            raise ReplayError("Wave-7 semantic-regime current pointer mismatch")

    revision_rows = [_lineage_revision_from_doc(dict(raw)) for raw in state.get("revisions", ())]
    for row in sorted(revision_rows, key=lambda item: (item.created_sequence, item.revision_id)):
        try:
            registry.register(row, make_current=False)
        except Exception as exc:
            raise ReplayError(f"invalid Wave-7 lineage history: {exc}") from exc

    pointers: dict[tuple[str, str], str] = {}
    for raw in state.get("current_pointers", ()):
        family = str(raw["object_family"])
        logical_id = str(raw["logical_id"])
        revision_id = str(raw["revision_id"])
        key = (family, logical_id)
        if key in pointers:
            raise ReplayError("duplicate Wave-7 current logical pointer")
        try:
            row = registry.get(revision_id)
        except Exception as exc:
            raise ReplayError("Wave-7 current pointer references missing lineage revision") from exc
        if (row.object_family, row.logical_id) != key:
            raise ReplayError("Wave-7 current pointer crosses logical identity")
        pointers[key] = revision_id
    registry._current = pointers

    kernel.lineage = registry
    kernel.semantic_regimes = {
        kind: registry.current_regime(kind).revision_id for kind in SemanticRegimeKind
    }
    expected_root = str(state.get("semantic_root_digest", ""))
    if not expected_root or registry.semantic_root_digest() != expected_root:
        raise ReplayError("Wave-7 semantic root digest mismatch")


def _restore_authorization_bindings(kernel, raw_bindings: dict[str, Any]) -> None:
    regime_ids = {row.revision_id for row in kernel.lineage.all_regimes()}
    restored: dict[str, AuthorizationLineageBinding] = {}
    for key, raw in sorted(raw_bindings.items()):
        binding = _authorization_binding_from_doc(dict(raw))
        if binding.authorization_id != str(key):
            raise ReplayError("Wave-7 authorization binding key/id mismatch")
        if binding.authorization_id not in kernel.authorizations:
            raise ReplayError("Wave-7 authorization lineage references missing authorization")
        try:
            kernel.lineage.get(binding.mission_revision_id)
            kernel.lineage.get(binding.canonical_state_revision_id)
            kernel.lineage.get(binding.action_revision_id)
            for revision_id in binding.grant_revision_ids:
                kernel.lineage.get(revision_id)
        except Exception as exc:
            raise ReplayError("Wave-7 authorization binding references missing object lineage") from exc
        if any(revision_id not in regime_ids for _, revision_id in binding.regime_revisions):
            raise ReplayError("Wave-7 authorization binding references missing regime lineage")
        restored[binding.authorization_id] = binding
    kernel.authorization_lineage_bindings = restored


def _restore_migration_state(kernel, raw: dict[str, Any]) -> None:
    manifests = {}
    regime_ids = {row.revision_id for row in kernel.lineage.all_regimes()}
    for key, doc in sorted(dict(raw.get("manifests", {})).items()):
        manifest = _manifest_from_doc(dict(doc))
        if manifest.manifest_id != str(key):
            raise ReplayError("Wave-7 migration manifest key/id mismatch")
        if manifest.source_schema_revision not in regime_ids or manifest.target_schema_revision not in regime_ids:
            raise ReplayError("Wave-7 migration manifest references missing schema lineage")
        manifests[manifest.manifest_id] = manifest

    history = []
    for doc in raw.get("history", ()):
        result = _migration_result_from_doc(dict(doc))
        if result.manifest_id not in manifests:
            raise ReplayError("Wave-7 migration result references missing manifest")
        history.append(result)

    bridges = {}
    for key, doc in sorted(dict(raw.get("bridges", {})).items()):
        bridge = _bridge_from_doc(dict(doc))
        if bridge.evidence_ref != str(key):
            raise ReplayError("Wave-7 migration bridge key/id mismatch")
        bridges[bridge.evidence_ref] = bridge

    recheck = {str(x) for x in raw.get("recheck_required_authorizations", ())}
    kernel.migration_manifests = manifests
    kernel.migration_history = history
    kernel.migration_bridges = bridges
    kernel.migration_recheck_required_authorizations = recheck
    kernel.migration_recheck_authorizations = kernel.migration_recheck_required_authorizations


def _restore_receipts(kernel, raw: dict[str, Any]) -> None:
    receipts = {}
    for key, doc in sorted(raw.items()):
        receipt = _receipt_from_doc(dict(doc))
        if receipt.id != str(key):
            raise ReplayError("Wave-7 receipt key/id mismatch")
        if receipt.authorization_id not in kernel.authorizations:
            raise ReplayError("Wave-7 receipt references missing authorization")
        receipts[receipt.id] = receipt
    kernel.receipts = receipts


def _validate_replay_registry(raw: dict[str, Any]) -> None:
    expected = _replay_registry_state()
    specs = list(raw.get("specs", ()))
    if digest(specs) != str(raw.get("canonical_digest", "")):
        raise ReplayError("Wave-7 replay registry snapshot digest mismatch")
    if raw != expected:
        raise ReplayError("Wave-7 replay registry differs from runtime schema contract")


def _restore_wave7_state(kernel, raw: dict[str, Any]) -> None:
    _restore_lineage_registry(kernel, raw)
    _restore_authorization_bindings(kernel, dict(raw.get("authorization_bindings", {})))
    _restore_migration_state(kernel, dict(raw.get("migration", {})))
    _restore_receipts(kernel, dict(raw.get("receipts", {})))
    compaction = raw.get("compaction")
    if not isinstance(compaction, dict):
        raise ReplayError("Wave-7 snapshot is missing compaction envelope")
    manifests = list(compaction.get("manifests", ()))
    archive = list(compaction.get("archive", ()))
    if manifests or archive:
        raise ReplayError("non-empty compaction snapshot requires the Task-6 compaction codec")
    kernel._wave7_compaction_snapshot_manifests = manifests
    kernel._wave7_compaction_snapshot_archive = archive
    replay_registry = raw.get("replay_registry")
    if not isinstance(replay_registry, dict):
        raise ReplayError("Wave-7 snapshot is missing replay-registry state")
    _validate_replay_registry(replay_registry)


def _open_v6_or_v7(cls, root: Path, state: dict[str, Any], schema: str):
    root = Path(root)
    journal = HashJournal(root / "journal.jsonl")
    journal.verify(raise_on_error=True)
    entries = journal.entries()
    prefix_length = _find_snapshot_prefix(entries, str(state.get("journal_head", "")))
    kernel = _restore_base_v6_layers(cls, root, state)

    if schema == SCHEDULABILITY_SNAPSHOT_SCHEMA:
        legacy_authorizations = tuple(sorted(kernel.authorizations))
        _import_v6_roots(kernel)
        kernel.authorization_lineage_bindings = {}
        kernel.migration_recheck_required_authorizations.update(legacy_authorizations)
        kernel.migration_recheck_authorizations = kernel.migration_recheck_required_authorizations
    else:
        wave7 = state.get("lineage")
        if not isinstance(wave7, dict):
            raise ReplayError("v7 snapshot is missing durable lineage state")
        _restore_wave7_state(kernel, wave7)

    for entry in entries[prefix_length:]:
        _replay_entry(kernel, entry)
    _flush_pending_canonical(kernel)
    return kernel


def install_lineage_snapshot(kernel_cls) -> None:
    """Install v7 snapshot persistence while retaining an explicit v6 fixture path."""
    if getattr(kernel_cls, "_wave7_lineage_snapshot_installed", False):
        return

    base_snapshot_state = kernel_cls.snapshot_state
    base_save_snapshot = kernel_cls.save_snapshot
    base_open = kernel_cls.open

    def snapshot_state(self):
        return _snapshot_state(self, base_snapshot_state)

    def save_snapshot(self):
        with self._writer_lock:
            state = snapshot_state(self)
            self.snapshots.save(state)
            self._record(
                "snapshot.saved",
                {
                    "snapshot_schema": LINEAGE_SNAPSHOT_SCHEMA,
                    "snapshot_digest": digest(state),
                    "bound_journal_head": state["journal_head"],
                },
            )
            return state

    def snapshot_state_v6(self):
        return base_snapshot_state(self)

    def save_snapshot_v6(self):
        return base_save_snapshot(self)

    @classmethod
    def open_snapshot(cls, root: Path):
        root = Path(root)
        state = SnapshotStore(root / "snapshot.json").load()
        schema = str(state.get("snapshot_schema", ""))
        if schema in {SCHEDULABILITY_SNAPSHOT_SCHEMA, LINEAGE_SNAPSHOT_SCHEMA}:
            return _open_v6_or_v7(cls, root, state, schema)
        return base_open(root)

    kernel_cls.snapshot_state = snapshot_state
    kernel_cls.save_snapshot = save_snapshot
    kernel_cls.snapshot_state_v6 = snapshot_state_v6
    kernel_cls.save_snapshot_v6 = save_snapshot_v6
    kernel_cls.open = open_snapshot
    kernel_cls._wave7_lineage_snapshot_installed = True
