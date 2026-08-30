from __future__ import annotations

from .execution import TransactionState
from .lineage import SemanticRegimeKind, SemanticRegimeRevision
from .migration import (
    MigrationBridgeEvidence,
    MigrationError,
    MigrationManifest,
    MigrationResult,
)
from .types import AuthorizationError


_AMBIGUOUS_MIGRATION_STATES = {
    TransactionState.DISPATCH_RECORDED,
    TransactionState.OUTCOME_OBSERVED,
    TransactionState.RECONCILIATION_REQUIRED,
}


def _validate_bridge(
    manifest: MigrationManifest,
    ambiguous_transaction_ids: tuple[str, ...],
    bridge: MigrationBridgeEvidence | None,
) -> None:
    if not ambiguous_transaction_ids:
        return
    if bridge is None:
        raise MigrationError(
            "semantic migration is blocked while an external action is in-flight or ambiguous"
        )
    if not bridge.verified:
        raise MigrationError("migration bridge evidence is not verified")
    if bridge.source_schema_revision != manifest.source_schema_revision:
        raise MigrationError("migration bridge source schema mismatch")
    if bridge.target_schema_revision != manifest.target_schema_revision:
        raise MigrationError("migration bridge target schema mismatch")
    missing = sorted(set(ambiguous_transaction_ids) - set(bridge.transaction_ids))
    if missing:
        raise MigrationError(f"migration bridge does not cover transactions: {missing!r}")


def _manifest_event_payload(
    manifest: MigrationManifest,
    *,
    bridge: MigrationBridgeEvidence | None,
    invalidated_authorization_ids: tuple[str, ...],
    freshness_generation: int,
    plan_generation: int,
    now: int | float,
) -> dict[str, object]:
    return {
        "manifest": manifest.canonical_payload(),
        "bridge": None
        if bridge is None
        else {
            "evidence_ref": bridge.evidence_ref,
            "source_schema_revision": bridge.source_schema_revision,
            "target_schema_revision": bridge.target_schema_revision,
            "transaction_ids": list(bridge.transaction_ids),
            "verified": bridge.verified,
            "canonical_digest": bridge.canonical_digest,
        },
        "invalidated_authorization_ids": list(invalidated_authorization_ids),
        "freshness_generation": freshness_generation,
        "plan_generation": plan_generation,
        "observed_at": now,
    }


def _apply_semantic_migration(
    self,
    manifest: MigrationManifest,
    *,
    now: int | float,
    bridge: MigrationBridgeEvidence | None = None,
) -> MigrationResult:
    with self._writer_lock:
        existing = self.migration_manifests.get(manifest.manifest_id)
        if existing is not None:
            if existing.canonical_digest != manifest.canonical_digest:
                raise MigrationError("migration manifest ID cannot be rebound to different semantics")
            for result in self.migration_history:
                if result.manifest_id == manifest.manifest_id:
                    return result
            raise MigrationError("migration manifest exists without a durable result")

        current_schema = self.lineage.current_regime(SemanticRegimeKind.SCHEMA)
        if current_schema.revision_id != manifest.source_schema_revision:
            raise MigrationError(
                f"migration source schema is stale: expected {current_schema.revision_id}, "
                f"got {manifest.source_schema_revision}"
            )

        ambiguous = tuple(
            sorted(
                transaction.id
                for transaction in self.transactions.all()
                if transaction.state in _AMBIGUOUS_MIGRATION_STATES
            )
        )
        _validate_bridge(manifest, ambiguous, bridge)

        # A schema transition conservatively invalidates all currently minted
        # authorizations. Explicit revoked refs are retained in the result even
        # if the authorization is no longer resident, preserving audit intent.
        invalidated = tuple(
            sorted(set(self.authorizations) | set(manifest.revoked_authorization_refs))
        )

        target_sequence = self.writer_sequence + 1
        target_schema = SemanticRegimeRevision.create(
            regime_kind=SemanticRegimeKind.SCHEMA,
            logical_id=current_schema.logical_id,
            revision_id=manifest.target_schema_revision,
            created_sequence=target_sequence,
            parent_revision_id=current_schema.revision_id,
            semantic_digest=manifest.target_schema_semantic_digest,
            provenance_refs=tuple(manifest.provenance_refs) + (manifest.manifest_id,),
        )

        # All failure-prone semantic checks above run before the current root is
        # moved. Registering this immutable child is the in-memory root switch.
        self.lineage.register_regime(target_schema)
        self.semantic_regimes[SemanticRegimeKind.SCHEMA] = target_schema.revision_id
        freshness_generation = self.freshness.bump("semantic-regime:SCHEMA")
        plan_generation = self.freshness.bump("plan")
        self.plan_snapshot_version += 1
        self.migration_recheck_required_authorizations.update(invalidated)
        self.migration_manifests[manifest.manifest_id] = manifest

        self._record(
            "migration.schema_root_switched",
            _manifest_event_payload(
                manifest,
                bridge=bridge,
                invalidated_authorization_ids=invalidated,
                freshness_generation=freshness_generation,
                plan_generation=plan_generation,
                now=now,
            ),
        )

        result = MigrationResult.create(
            manifest_id=manifest.manifest_id,
            source_schema_revision=manifest.source_schema_revision,
            target_schema_revision=manifest.target_schema_revision,
            invalidated_authorization_ids=invalidated,
            new_debt_refs=manifest.new_debt_refs,
            bridge_evidence_ref=None if bridge is None else bridge.evidence_ref,
            root_switched_sequence=self.writer_sequence,
        )
        self.migration_history.append(result)
        if bridge is not None:
            self.migration_bridges[bridge.evidence_ref] = bridge
        return result


def install_migration_runtime(kernel_cls) -> None:
    """Install typed semantic migration on the existing Wave-7 writer spine."""
    if getattr(kernel_cls, "_wave7_migration_runtime_installed", False):
        return

    original_init = kernel_cls.__init__
    original_dispatch = kernel_cls.dispatch

    def __init__(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        self.migration_manifests: dict[str, MigrationManifest] = {}
        self.migration_history: list[MigrationResult] = []
        self.migration_recheck_required_authorizations: set[str] = set()
        # Replay code and semantic-digest code share this exact mutable set;
        # the alias is compatibility-only and cannot diverge.
        self.migration_recheck_authorizations = self.migration_recheck_required_authorizations
        self.migration_bridges: dict[str, MigrationBridgeEvidence] = {}

    def dispatch(self, authorization_id, *args, **kwargs):
        with self._writer_lock:
            if authorization_id in self.migration_recheck_required_authorizations:
                raise AuthorizationError("authorization requires recheck after semantic migration")
            return original_dispatch(self, authorization_id, *args, **kwargs)

    kernel_cls.__init__ = __init__
    kernel_cls.dispatch = dispatch
    kernel_cls.apply_semantic_migration = _apply_semantic_migration
    kernel_cls._wave7_migration_runtime_installed = True
