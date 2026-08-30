from __future__ import annotations

from pathlib import Path
from typing import Any

from .actions import ActionAuthorization, ActionIntent, AuthorityGrant, ExecutionReceipt
from .artifacts import ArtifactBinding
from .capsule import DecisionCapsule
from .decision_cut import DecisionCutRevision
from .evidence import EvidencePolarity, EvidenceRecord
from .execution import ActionTransaction, AdapterProfile, TransactionState
from .freshness import DependencyStamp
from .future import FutureFamily
from .hashing import digest
from .lineage import SemanticRegimeKind, SemanticRegimeRevision
from .lineage_runtime import AuthorizationLineageBinding
from .migration import (
    FieldMigrationDisposition,
    IdentityMapping,
    MigrationBridgeEvidence,
    MigrationManifest,
    MigrationResult,
)
from .mission import MissionContract, MissionLedger
from .obligations import ObligationStatus, StrategicObligation
from .persistence import HashJournal, SnapshotStore
from .policy_recovery import POLICY_SNAPSHOT_SCHEMA, _replay_entry as _replay_policy_entry, _restore_policy_state
from .principals import InformationItem
from .proof_recovery import PROOF_SNAPSHOT_SCHEMA, _restore_proof_state
from .recovery import RecoveryMode, RecoveryState
from .relocation import CandidateRegion, LocationStatus, StrategicLocationRevision
from .replay_registry import DEFAULT_REPLAY_REGISTRY, ReplayEventClass
from .resources import SharedCommitment
from .resume import SNAPSHOT_SCHEMA as BASE_SNAPSHOT_SCHEMA
from .resume import _find_snapshot_prefix, _replay_suffix as _legacy_base_replay, _restore_state
from .schedulability_recovery import (
    SCHEDULABILITY_SNAPSHOT_SCHEMA,
    _replay_schedulability_entry,
    _restore_schedulability_state,
)
from .trust_recovery import TRUST_SNAPSHOT_SCHEMA, _restore_trust_state
from .types import ReplayError, RiskClass
from .verification import BoundCompletionReport


def _require_doc(payload: dict[str, Any], key: str, event_type: str) -> dict[str, Any]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise ReplayError(f"{event_type} lacks exact Wave-7 replay payload: {key}")
    return dict(value)


def _restore_meta(kernel, payload: dict[str, Any]) -> None:
    meta = payload.get("_replay")
    if not isinstance(meta, dict):
        return
    kernel.plan_snapshot_version = int(meta["plan_snapshot_version"])
    kernel.freshness.generations = {
        str(key): int(value) for key, value in dict(meta["freshness_generations"]).items()
    }
    kernel._location_revision = int(meta["location_revision"])
    kernel.evidence.generation = int(meta["evidence_generation"])
    kernel.principals._partition_revision = int(meta["principal_partition_revision"])
    kernel.decision_cuts._revision = int(meta["decision_cut_revision"])


def _restore_cut(kernel, raw: dict[str, Any] | None) -> None:
    if not isinstance(raw, dict):
        return
    cut = DecisionCutRevision(
        str(raw["id"]),
        int(raw["revision"]),
        int(raw["commit_frontier_sequence"]),
        int(raw["mission_revision"]),
        int(raw["canonical_state_revision"]),
        int(raw["strategic_location_revision"]),
        tuple((str(key), int(value)) for key, value in raw.get("source_generations", ())),
    )
    existing = kernel.decision_cuts._items.get(cut.id)
    if existing is not None and existing != cut:
        raise ReplayError("decision cut id was rebound during replay")
    kernel.decision_cuts._items[cut.id] = cut
    kernel.decision_cuts._revision = max(kernel.decision_cuts._revision, cut.revision)


def _register_object_lineage(
    kernel,
    entry,
    *,
    object_family: str,
    logical_id: str,
    semantic_payload: Any,
    provenance_refs: tuple[str, ...],
    mission_dependency: bool = True,
) -> None:
    kernel._register_lineage(
        object_family=object_family,
        logical_id=logical_id,
        semantic_payload=semantic_payload,
        provenance_refs=provenance_refs,
        created_sequence=entry.sequence,
        mission_dependency=mission_dependency,
    )


def _flush_pending_canonical(kernel) -> None:
    pending = getattr(kernel, "_wave7_pending_canonical_lineage", None)
    if pending is None:
        return
    previous_revision_id, semantic_digest, provenance_refs, created_sequence = pending
    kernel._register_lineage(
        object_family="CanonicalState",
        logical_id="canonical-state",
        semantic_digest=semantic_digest,
        provenance_refs=provenance_refs,
        parent_revision_ids=(previous_revision_id,),
        supersedes_revision_id=previous_revision_id,
        created_sequence=created_sequence,
    )
    kernel._wave7_pending_canonical_lineage = None


def _replay_base_entry(kernel, entry) -> bool:
    event = entry.event_type
    payload = dict(entry.payload)

    if event == "mission.created":
        doc = _require_doc(payload, "mission", event)
        current = kernel.mission.current
        if int(doc["version"]) != current.version or str(doc["objective"]) != current.objective:
            raise ReplayError("mission.created suffix conflicts with restored mission")
        _restore_meta(kernel, payload)
        return True

    if event == "mission.revised":
        doc = _require_doc(payload, "mission", event)
        previous = kernel.lineage.current("MissionRevision", "mission")
        expected_version = kernel.mission.current.version + 1
        if int(doc["version"]) != expected_version:
            raise ReplayError("mission revision sequence is non-monotonic")
        kernel.mission.revise(
            objective=str(doc["objective"]),
            success_conditions=tuple(doc.get("success_conditions", ())),
            hard_constraints=tuple(doc.get("hard_constraints", ())),
            soft_preferences=tuple(doc.get("soft_preferences", ())),
            anti_goals=tuple(doc.get("anti_goals", ())),
            risk_budget=doc.get("risk_budget"),
        )
        _restore_meta(kernel, payload)
        kernel._register_lineage(
            object_family="MissionRevision",
            logical_id="mission",
            semantic_digest=kernel._mission_semantic_digest(),
            provenance_refs=("kernel:mission-ledger",),
            parent_revision_ids=(previous.revision_id,),
            supersedes_revision_id=previous.revision_id,
            created_sequence=entry.sequence,
            mission_dependency=False,
        )
        return True

    if event == "freshness.bumped":
        domain = str(payload["domain"])
        generation = int(payload["generation"])
        if generation < kernel.freshness.generation(domain):
            raise ReplayError("freshness generation moved backwards during replay")
        kernel.freshness.generations[domain] = generation
        _restore_meta(kernel, payload)
        return True

    if event in {"principal.registered", "principal.access_changed"}:
        doc = _require_doc(payload, "profile", event)
        principal_ref = str(doc["principal_ref"])
        if event == "principal.registered":
            profile = kernel.principals.register(principal_ref, set(doc.get("allowed_tags", ())))
        else:
            profile = kernel.principals.update_access(principal_ref, set(doc.get("allowed_tags", ())))
        if profile.revision != int(doc["revision"]):
            raise ReplayError("principal access revision did not replay exactly")
        _restore_meta(kernel, payload)
        return True

    if event == "information.published":
        doc = _require_doc(payload, "item", event)
        item = InformationItem(
            str(doc["id"]), doc.get("payload"), frozenset(str(x) for x in doc.get("tags", ())),
            doc.get("visible_at", 0), doc.get("valid_until"), str(doc.get("provenance", "host")),
            float(doc.get("assurance", 1.0)),
        )
        if item.id in kernel.information_items:
            raise ReplayError("duplicate information item during replay")
        kernel.information_items[item.id] = item
        _restore_meta(kernel, payload)
        return True

    if event == "information.observed":
        kernel.principals.observe(
            str(payload["principal_ref"]), str(payload["item_id"]), payload["observed_at"]
        )
        _restore_meta(kernel, payload)
        return True

    if event == "evidence.added":
        doc = _require_doc(payload, "record", event)
        record = EvidenceRecord(
            str(doc["id"]), str(doc["claim"]), EvidencePolarity(str(doc["polarity"])),
            str(doc["source_id"]), str(doc["lineage_root"]), doc["observed_at"],
            doc.get("valid_until"), float(doc.get("assurance", 0.5)), bool(doc.get("revoked", False)),
            doc.get("revocation_reason"),
        )
        kernel.evidence.add(record)
        _restore_meta(kernel, payload)
        _register_object_lineage(
            kernel,
            entry,
            object_family="EvidenceRecord",
            logical_id=record.id,
            semantic_payload={
                "id": record.id,
                "claim": record.claim,
                "polarity": record.polarity.value,
                "source_id": record.source_id,
                "lineage_root": record.lineage_root,
                "observed_at": record.observed_at,
                "valid_until": record.valid_until,
                "assurance": record.assurance,
                "revoked": record.revoked,
                "revocation_reason": record.revocation_reason,
            },
            provenance_refs=("kernel:evidence-ledger",),
        )
        return True

    if event == "future.family_added":
        doc = _require_doc(payload, "family", event)
        family = FutureFamily(
            str(doc["id"]), str(doc["predicate"]), doc.get("probability"), float(doc.get("support", 0.0)),
            tuple(str(x) for x in doc.get("assumptions", ())), float(doc.get("impact", 1.0)),
            bool(doc.get("residual", False)),
        )
        kernel.future.add_family(family)
        _restore_meta(kernel, payload)
        _register_object_lineage(
            kernel, entry, object_family="FutureFamily", logical_id=family.id,
            semantic_payload={
                "id": family.id, "predicate": family.predicate, "probability": family.probability,
                "impact": family.impact, "residual": family.residual,
                "assumptions": sorted(family.assumptions), "support": family.support,
            }, provenance_refs=("kernel:future-lattice",),
        )
        return True

    if event == "obligation.added":
        doc = _require_doc(payload, "obligation", event)
        obligation = StrategicObligation(
            str(doc["id"]), str(doc["condition"]), doc.get("deadline"), doc.get("required_capability"),
            bool(doc.get("hard", True)), ObligationStatus(str(doc.get("status", "open"))),
            tuple(str(x) for x in doc.get("lineage", ())),
        )
        kernel.obligations.add(obligation)
        _restore_meta(kernel, payload)
        _register_object_lineage(
            kernel, entry, object_family="StrategicObligation", logical_id=obligation.id,
            semantic_payload={
                "id": obligation.id, "condition": obligation.condition, "hard": obligation.hard,
                "deadline": obligation.deadline, "required_capability": obligation.required_capability,
                "status": obligation.status.value, "lineage": list(obligation.lineage),
            }, provenance_refs=("kernel:obligation-ledger",),
        )
        return True

    if event == "action.proposed":
        doc = _require_doc(payload, "action", event)
        action = ActionIntent(
            str(doc["id"]), str(doc["family"]), RiskClass(str(doc["risk_class"])),
            tuple((str(k), str(v)) for k, v in doc.get("parameters", ())),
            tuple(str(x) for x in doc.get("preconditions", ())),
            tuple(str(x) for x in doc.get("required_capabilities", ())),
            bool(doc.get("idempotent", True)), bool(doc.get("executor_sensitive", False)),
        )
        kernel.actions[action.id] = action
        _restore_meta(kernel, payload)
        _register_object_lineage(
            kernel, entry, object_family="ActionIntent", logical_id=action.id,
            semantic_payload={
                "id": action.id, "family": action.family, "risk_class": action.risk_class.value,
                "parameters": list(action.parameters), "preconditions": list(action.preconditions),
                "required_capabilities": list(action.required_capabilities), "idempotent": action.idempotent,
                "executor_sensitive": action.executor_sensitive,
            }, provenance_refs=("kernel:action-registry",),
        )
        return True

    if event == "authority.grant_added":
        doc = _require_doc(payload, "grant", event)
        grant = AuthorityGrant(
            str(doc["id"]), str(doc["principal_ref"]), frozenset(str(x) for x in doc.get("scopes", ())),
            doc.get("expires_at"), bool(doc.get("revoked", False)),
            frozenset(RiskClass(str(x)) for x in doc.get("risk_classes", ())),
        )
        kernel.grants[grant.id] = grant
        _restore_meta(kernel, payload)
        _register_object_lineage(
            kernel, entry, object_family="AuthorityGrant", logical_id=grant.id,
            semantic_payload={
                "id": grant.id, "principal_ref": grant.principal_ref, "scopes": sorted(grant.scopes),
                "expires_at": grant.expires_at, "revoked": grant.revoked,
                "risk_classes": sorted(item.value for item in grant.risk_classes),
            }, provenance_refs=("kernel:authority-registry",),
        )
        return True

    if event == "adapter.registered":
        doc = _require_doc(payload, "adapter", event)
        profile = AdapterProfile(
            str(doc["adapter_id"]), int(doc["revision"]), bool(doc["principal_attestation"]),
            bool(doc["dispatch_fence"]), float(doc["postcondition_assurance"]),
        )
        if profile.capability_digest != str(doc["capability_digest"]):
            raise ReplayError("adapter capability digest mismatch during replay")
        kernel.adapters[profile.adapter_id] = profile
        _restore_meta(kernel, payload)
        _register_object_lineage(
            kernel,
            entry,
            object_family="AdapterProfile",
            logical_id=profile.adapter_id,
            semantic_payload={
                "adapter_id": profile.adapter_id,
                "revision": profile.revision,
                "principal_attestation": profile.principal_attestation,
                "dispatch_fence": profile.dispatch_fence,
                "postcondition_assurance": profile.postcondition_assurance,
                "capability_digest": profile.capability_digest,
            },
            provenance_refs=("kernel:adapter-registry",),
        )
        return True

    if event == "region.registered":
        doc = _require_doc(payload, "region", event)
        region = CandidateRegion(str(doc["id"]), dict(doc.get("required_facts", {})), str(doc["decision_signature"]))
        if any(existing.id == region.id for existing in kernel.regions):
            raise ReplayError("duplicate region during replay")
        kernel.regions.append(region)
        _restore_meta(kernel, payload)
        _register_object_lineage(
            kernel,
            entry,
            object_family="CandidateRegion",
            logical_id=region.id,
            semantic_payload={
                "id": region.id,
                "required_facts": region.required_facts,
                "decision_signature": region.decision_signature,
            },
            provenance_refs=("kernel:region-registry",),
        )
        return True

    if event == "resource.reserved":
        kernel.reservations.reserve(
            SharedCommitment(
                str(payload["resource_id"]), str(payload["principal_ref"]), payload["start"], payload["end"],
                bool(payload.get("exclusive", False)),
            )
        )
        if "reservation_count" in payload and len(kernel.reservations.commitments) != int(payload["reservation_count"]):
            raise ReplayError("reservation replay cardinality mismatch")
        _restore_meta(kernel, payload)
        return True

    if event == "capsule.compiled":
        doc = _require_doc(payload, "capsule", event)
        _restore_cut(kernel, payload.get("decision_cut"))
        capsule = DecisionCapsule(
            str(doc["id"]), str(doc["recipient_principal_ref"]), str(doc["information_partition_digest"]),
            int(doc["information_access_profile_revision"]), int(doc["plan_snapshot_version"]),
            int(doc["mission_version"]), int(doc["canonical_version"]), int(doc["evidence_watermark"]),
            doc["decision_time"], tuple(str(x) for x in doc.get("item_ids", ())),
            tuple(str(x) for x in doc.get("action_ids", ())), str(doc["dependency_digest"]),
            doc.get("expires_at"), str(doc.get("decision_cut_id", "")),
        )
        kernel.capsules[capsule.id] = capsule
        artifact = _require_doc(payload, "artifact", event)
        kernel.artifacts._items[capsule.id] = ArtifactBinding(
            str(artifact["id"]), str(artifact["kind"]), int(artifact["produced_sequence"]),
            DependencyStamp(tuple((str(k), int(v)) for k, v in artifact.get("dependency_generations", ()))),
            str(artifact["decision_cut_id"]),
        )
        _restore_meta(kernel, payload)
        return True

    if event == "action.authorized":
        doc = _require_doc(payload, "authorization", event)
        _restore_cut(kernel, payload.get("decision_cut"))
        authorization = ActionAuthorization(
            str(doc["id"]), str(doc["action_id"]), str(doc["action_family"]), str(doc["acting_principal_ref"]),
            tuple(str(x) for x in doc.get("grant_refs", ())), int(doc["mission_version"]),
            int(doc["canonical_version"]), doc["issued_at"], doc.get("expires_at"), doc.get("decision_cut_id"),
            doc.get("capsule_id"), doc.get("adapter_id"), doc.get("adapter_revision"),
        )
        if authorization.id in kernel.authorizations:
            raise ReplayError("duplicate authorization during replay")
        kernel.authorizations[authorization.id] = authorization
        tx_doc = _require_doc(payload, "transaction", event)
        transaction = ActionTransaction(
            str(tx_doc["id"]), str(tx_doc["action_id"]), str(tx_doc["authorization_id"]),
            str(tx_doc["principal_ref"]), bool(tx_doc["idempotent"]), TransactionState(str(tx_doc["state"])),
            tx_doc.get("adapter_id"), tx_doc.get("adapter_revision"), tx_doc.get("detail"),
        )
        kernel.transactions.restore(transaction)
        kernel.authorization_transactions[authorization.id] = transaction.id
        _restore_meta(kernel, payload)

        mission_lineage = kernel.lineage.current("MissionRevision", "mission")
        canonical_lineage = kernel.lineage.current("CanonicalState", "canonical-state")
        action_lineage = kernel.lineage.current("ActionIntent", authorization.action_id)
        grant_lineages = tuple(
            kernel.lineage.current("AuthorityGrant", grant_id).revision_id for grant_id in authorization.grant_refs
        )
        binding = AuthorizationLineageBinding.create(
            authorization_id=authorization.id,
            mission_revision_id=mission_lineage.revision_id,
            canonical_state_revision_id=canonical_lineage.revision_id,
            action_revision_id=action_lineage.revision_id,
            grant_revision_ids=grant_lineages,
            regime_revisions=(
                (kind.value, kernel.lineage.current_regime(kind).revision_id) for kind in SemanticRegimeKind
            ),
            created_sequence=entry.sequence,
        )
        kernel.authorization_lineage_bindings[authorization.id] = binding
        return True

    if event == "action.outcome_observed":
        doc = _require_doc(payload, "receipt", event)
        receipt = ExecutionReceipt(
            str(doc["id"]), str(doc["action_id"]), str(doc["authorization_id"]),
            str(doc["executing_principal_ref"]), bool(doc["transport_ok"]),
            bool(doc["postconditions_verified"]), dict(doc.get("state_patch", {})), doc["observed_at"],
        )
        kernel.receipts[receipt.id] = receipt
        tx_id = str(payload["transaction_id"])
        if kernel.transactions.get(tx_id).state == TransactionState.DISPATCH_RECORDED:
            kernel.transactions.record_outcome(tx_id)
        _restore_meta(kernel, payload)
        return True

    if event in {"action.dispatch_recorded", "action.reconciliation_required", "action.reconciled"}:
        _legacy_base_replay(kernel, entry)
        _restore_meta(kernel, payload)
        return True

    if event == "canonical.committed":
        previous = kernel.lineage.current("CanonicalState", "canonical-state")
        _legacy_base_replay(kernel, entry)
        _restore_meta(kernel, payload)
        kernel._wave7_pending_canonical_lineage = (
            previous.revision_id,
            kernel._canonical_state_semantic_digest(),
            tuple(ref for ref in (payload.get("receipt_id"), payload.get("transaction_id")) if ref),
            entry.sequence,
        )
        return True

    if event == "state.relocated":
        doc = _require_doc(payload, "location", event)
        kernel.strategic_location = StrategicLocationRevision(
            LocationStatus(str(doc["status"])), tuple(str(x) for x in doc.get("region_ids", ())),
            tuple(str(x) for x in doc.get("decision_signatures", ())),
        )
        _restore_meta(kernel, payload)
        pending = getattr(kernel, "_wave7_pending_canonical_lineage", None)
        if pending is not None:
            kernel._wave7_pending_canonical_lineage = (*pending[:3], entry.sequence)
        return True

    if event == "recovery.model_class_uncertain":
        doc = _require_doc(payload, "recovery", event)
        kernel.recovery.state = RecoveryState(
            RecoveryMode(str(doc["mode"])), doc.get("reason"), float(doc.get("residual_weight", 0.0)),
            int(doc.get("generation", 1)),
        )
        _restore_meta(kernel, payload)
        pending = getattr(kernel, "_wave7_pending_canonical_lineage", None)
        if pending is not None:
            kernel._wave7_pending_canonical_lineage = (*pending[:3], entry.sequence)
        return True

    if event == "completion.verified":
        doc = _require_doc(payload, "report", event)
        report = BoundCompletionReport(
            bool(doc["complete"]), tuple(str(x) for x in doc.get("missing_success_conditions", ())),
            tuple(str(x) for x in doc.get("open_hard_obligations", ())),
            tuple(str(x) for x in doc.get("anti_goal_violations", ())), str(doc["artifact_id"]),
            str(doc["decision_cut_id"]),
        )
        kernel.completion_reports[report.artifact_id] = report
        _restore_meta(kernel, payload)
        return True

    if event == "model.proposal_received":
        proposal_id = str(payload["proposal_id"])
        proposal = payload.get("proposal")
        if not isinstance(proposal, dict):
            raise ReplayError("model proposal lacks exact replay payload")
        kernel.model_proposals[proposal_id] = dict(proposal)
        _restore_meta(kernel, payload)
        return True

    return False


def _replay_semantic_regime(kernel, entry) -> None:
    payload = dict(entry.payload)
    revision = SemanticRegimeRevision.create(
        regime_kind=str(payload["regime_kind"]), logical_id=str(payload["logical_id"]),
        revision_id=str(payload["revision_id"]), created_sequence=int(payload["created_sequence"]),
        parent_revision_id=payload.get("parent_revision_id"), semantic_digest=str(payload["semantic_digest"]),
        provenance_refs=tuple(str(x) for x in payload.get("provenance_refs", ())),
    )
    if revision.canonical_digest != str(payload["canonical_digest"]):
        raise ReplayError("semantic regime digest mismatch during replay")
    kernel.lineage.register_regime(revision)
    kind = SemanticRegimeKind.parse(payload["regime_kind"])
    kernel.semantic_regimes[kind] = revision.revision_id
    kernel.freshness.generations[f"semantic-regime:{kind.value}"] = int(payload["freshness_generation"])
    kernel.freshness.generations["plan"] = int(payload["plan_generation"])
    kernel.plan_snapshot_version += 1
    _restore_meta(kernel, payload)


def _manifest_from_doc(raw: dict[str, Any]) -> MigrationManifest:
    dispositions = tuple(
        FieldMigrationDisposition(
            str(row["object_family"]), str(row["field_path"]), str(row["disposition"]),
            row.get("source_ref"), row.get("target_ref"), row.get("debt_ref"),
        )
        for row in raw.get("field_dispositions", ())
    )
    mappings = tuple(
        IdentityMapping(
            str(row["object_family"]), str(row["source_logical_id"]), str(row["target_logical_id"]),
            str(row["source_revision_id"]), str(row["target_revision_id"]),
        )
        for row in raw.get("identity_mappings", ())
    )
    manifest = MigrationManifest.create(
        manifest_id=str(raw["manifest_id"]), source_schema_revision=str(raw["source_schema_revision"]),
        target_schema_revision=str(raw["target_schema_revision"]),
        target_schema_semantic_digest=str(raw["target_schema_semantic_digest"]),
        changed_correctness_fields=tuple((str(a), str(b)) for a, b in raw.get("changed_correctness_fields", ())),
        field_dispositions=dispositions, identity_mappings=mappings,
        checked_invariants=tuple(str(x) for x in raw.get("checked_invariants", ())),
        revoked_certificate_refs=tuple(str(x) for x in raw.get("revoked_certificate_refs", ())),
        revoked_authorization_refs=tuple(str(x) for x in raw.get("revoked_authorization_refs", ())),
        new_debt_refs=tuple(str(x) for x in raw.get("new_debt_refs", ())),
        replay_fixture_digests=tuple(str(x) for x in raw.get("replay_fixture_digests", ())),
        rollback_procedure_ref=str(raw["rollback_procedure_ref"]), backup_ref=str(raw["backup_ref"]),
        unsupported_legacy_cases=tuple(str(x) for x in raw.get("unsupported_legacy_cases", ())),
        external_effect_history_refs=tuple(str(x) for x in raw.get("external_effect_history_refs", ())),
        provenance_refs=tuple(str(x) for x in raw.get("provenance_refs", ())),
    )
    if raw.get("canonical_digest") and manifest.canonical_digest != str(raw["canonical_digest"]):
        raise ReplayError("migration manifest digest mismatch during replay")
    return manifest


def _replay_migration(kernel, entry) -> None:
    payload = dict(entry.payload)
    manifest = _manifest_from_doc(_require_doc(payload, "manifest", entry.event_type))
    current = kernel.lineage.current_regime(SemanticRegimeKind.SCHEMA)
    if current.revision_id != manifest.source_schema_revision:
        raise ReplayError("migration replay source schema is not current")
    sequence = entry.sequence
    target = SemanticRegimeRevision.create(
        regime_kind=SemanticRegimeKind.SCHEMA,
        logical_id=current.logical_id,
        revision_id=manifest.target_schema_revision,
        created_sequence=sequence,
        parent_revision_id=current.revision_id,
        semantic_digest=manifest.target_schema_semantic_digest,
        provenance_refs=tuple(manifest.provenance_refs) + (manifest.manifest_id,),
    )
    kernel.lineage.register_regime(target)
    kernel.semantic_regimes[SemanticRegimeKind.SCHEMA] = target.revision_id
    kernel.freshness.generations[f"semantic-regime:{SemanticRegimeKind.SCHEMA.value}"] = int(payload["freshness_generation"])
    kernel.freshness.generations["plan"] = int(payload["plan_generation"])
    kernel.plan_snapshot_version += 1
    invalidated = tuple(str(x) for x in payload.get("invalidated_authorization_ids", ()))
    kernel.migration_recheck_authorizations.update(invalidated)
    kernel.migration_manifests[manifest.manifest_id] = manifest
    bridge = payload.get("bridge")
    bridge_ref = None
    if isinstance(bridge, dict):
        value = MigrationBridgeEvidence.create(
            evidence_ref=str(bridge["evidence_ref"]),
            source_schema_revision=str(bridge["source_schema_revision"]),
            target_schema_revision=str(bridge["target_schema_revision"]),
            transaction_ids=tuple(str(x) for x in bridge.get("transaction_ids", ())),
            verified=bool(bridge["verified"]),
        )
        if value.canonical_digest != str(bridge["canonical_digest"]):
            raise ReplayError("migration bridge digest mismatch during replay")
        kernel.migration_bridges[value.evidence_ref] = value
        bridge_ref = value.evidence_ref
    result = MigrationResult.create(
        manifest_id=manifest.manifest_id, source_schema_revision=manifest.source_schema_revision,
        target_schema_revision=manifest.target_schema_revision,
        invalidated_authorization_ids=invalidated, new_debt_refs=manifest.new_debt_refs,
        bridge_evidence_ref=bridge_ref, root_switched_sequence=sequence,
    )
    kernel.migration_history.append(result)
    _restore_meta(kernel, payload)


def canonical_semantic_digest(kernel) -> str:
    """Digest correctness-authoritative runtime state, excluding journal transport bytes."""
    def lineage_row(row):
        return (
            row.object_family, row.logical_id, row.revision_id, row.created_sequence,
            row.mission_revision_dependency, row.plan_revision, row.world_model_revision,
            row.environment_regime_revision, row.validity_regime, row.parent_revision_ids,
            row.provenance_refs, row.assurance_profile, row.debt_refs, row.supersedes_revision_id,
            row.semantic_digest, row.lineage_digest,
        )

    return digest({
        "mission": {
            "version": kernel.mission.current.version,
            "objective": kernel.mission.current.objective,
            "success_conditions": kernel.mission.current.success_conditions,
            "hard_constraints": kernel.mission.current.hard_constraints,
            "soft_preferences": kernel.mission.current.soft_preferences,
            "anti_goals": kernel.mission.current.anti_goals,
            "risk_budget": kernel.mission.current.risk_budget,
        },
        "canonical": (kernel.canonical_version, kernel.canonical_state),
        "plan_snapshot_version": kernel.plan_snapshot_version,
        "principals": tuple(sorted(
            (ref, profile.revision, tuple(sorted(profile.allowed_tags)))
            for ref, profile in kernel.principals._profiles.items()
        )),
        "deliveries": tuple(sorted(
            (principal, item, row.observed_at)
            for (principal, item), row in kernel.principals._deliveries.items()
        )),
        "information": tuple(sorted(
            (item.id, item.payload, tuple(sorted(item.tags)), item.visible_at, item.valid_until, item.provenance, item.assurance)
            for item in kernel.information_items.values()
        )),
        "evidence": (
            kernel.evidence.generation,
            tuple(sorted(
                (row.id, row.claim, row.polarity.value, row.source_id, row.lineage_root, row.observed_at,
                 row.valid_until, row.assurance, row.revoked, row.revocation_reason)
                for row in kernel.evidence.records.values()
            )),
        ),
        "future": tuple(sorted(
            (row.id, row.predicate, row.probability, row.support, row.assumptions, row.impact, row.residual)
            for row in kernel.future.families.values()
        )),
        "obligations": tuple(sorted(
            (row.id, row.condition, row.deadline, row.required_capability, row.hard, row.status.value, row.lineage)
            for row in kernel.obligations._items.values()
        )),
        "actions": tuple(sorted(
            (row.id, row.family, row.risk_class.value, row.parameters, row.preconditions, row.required_capabilities,
             row.idempotent, row.executor_sensitive)
            for row in kernel.actions.values()
        )),
        "grants": tuple(sorted(
            (row.id, row.principal_ref, tuple(sorted(row.scopes)), row.expires_at, row.revoked,
             tuple(sorted(item.value for item in row.risk_classes)))
            for row in kernel.grants.values()
        )),
        "adapters": tuple(sorted(
            (row.adapter_id, row.revision, row.principal_attestation, row.dispatch_fence,
             row.postcondition_assurance, row.capability_digest)
            for row in kernel.adapters.values()
        )),
        "regions": tuple(sorted(
            (row.id, row.required_facts, row.decision_signature) for row in kernel.regions
        )),
        "location": (
            kernel._location_revision, kernel.strategic_location.status.value,
            kernel.strategic_location.region_ids, kernel.strategic_location.decision_signatures,
        ),
        "reservations": tuple(
            (row.resource_id, row.principal_ref, row.start, row.end, row.exclusive)
            for row in kernel.reservations.commitments
        ),
        "recovery": (
            kernel.recovery.state.mode.value, kernel.recovery.state.reason,
            kernel.recovery.state.residual_weight, kernel.recovery.state.generation,
        ),
        "authorizations": tuple(sorted(
            (row.id, row.action_id, row.action_family, row.acting_principal_ref, row.grant_refs,
             row.mission_version, row.canonical_version, row.issued_at, row.expires_at,
             row.decision_cut_id, row.capsule_id, row.adapter_id, row.adapter_revision)
            for row in kernel.authorizations.values()
        )),
        "transactions": tuple(sorted(
            (row.id, row.action_id, row.authorization_id, row.principal_ref, row.idempotent,
             row.state.value, row.adapter_id, row.adapter_revision, row.detail)
            for row in kernel.transactions.all()
        )),
        "freshness": tuple(sorted(kernel.freshness.generations.items())),
        "lineage": tuple(lineage_row(row) for row in kernel.lineage.all_revisions()),
        "regimes": tuple(
            (row.regime_kind.value, row.logical_id, row.revision_id, row.created_sequence,
             row.parent_revision_id, row.semantic_digest, row.provenance_refs, row.canonical_digest)
            for row in kernel.lineage.all_regimes()
        ),
        "authorization_lineage": tuple(sorted(
            (key, value.canonical_digest) for key, value in kernel.authorization_lineage_bindings.items()
        )),
        "migration_recheck": tuple(sorted(kernel.migration_recheck_authorizations)),
    })


def _replay_entry(kernel, entry) -> None:
    spec = DEFAULT_REPLAY_REGISTRY.require(entry.event_type, correctness_significant=True)
    if spec is None:
        raise ReplayError(f"missing replay registry entry: {entry.event_type}")
    if spec.classification == ReplayEventClass.SNAPSHOT_BOUNDARY:
        return

    if entry.event_type not in {"state.relocated", "recovery.model_class_uncertain"}:
        _flush_pending_canonical(kernel)

    if _replay_base_entry(kernel, entry):
        return
    if entry.event_type == "semantic.regime_revised":
        _replay_semantic_regime(kernel, entry)
        return
    if entry.event_type == "migration.schema_root_switched":
        _replay_migration(kernel, entry)
        return
    if entry.event_type.startswith("schedulability."):
        if not _replay_schedulability_entry(kernel, entry):
            raise ReplayError(f"unsupported schedulability replay event: {entry.event_type}")
        _restore_meta(kernel, dict(entry.payload))
        return

    _replay_policy_entry(kernel, entry)
    _restore_meta(kernel, dict(entry.payload))


def _open(cls, root: Path):
    root = Path(root)
    journal = HashJournal(root / "journal.jsonl")
    journal.verify(raise_on_error=True)
    state = SnapshotStore(root / "snapshot.json").load()
    schema = state.get("snapshot_schema")
    supported = {
        BASE_SNAPSHOT_SCHEMA, TRUST_SNAPSHOT_SCHEMA, PROOF_SNAPSHOT_SCHEMA,
        POLICY_SNAPSHOT_SCHEMA, SCHEDULABILITY_SNAPSHOT_SCHEMA,
    }
    if schema not in supported:
        raise ReplayError("unsupported or missing snapshot schema")
    entries = journal.entries()
    prefix_length = _find_snapshot_prefix(entries, str(state.get("journal_head", "")))

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
    _restore_state(kernel, core_state)

    if schema in {TRUST_SNAPSHOT_SCHEMA, PROOF_SNAPSHOT_SCHEMA, POLICY_SNAPSHOT_SCHEMA, SCHEDULABILITY_SNAPSHOT_SCHEMA}:
        _restore_trust_state(kernel, dict(state.get("trust") or {}))
    if schema in {PROOF_SNAPSHOT_SCHEMA, POLICY_SNAPSHOT_SCHEMA, SCHEDULABILITY_SNAPSHOT_SCHEMA}:
        proof = state.get("proof")
        if not isinstance(proof, dict):
            raise ReplayError("proof-capable snapshot is missing proof lineage state")
        _restore_proof_state(kernel, proof)
    if schema in {POLICY_SNAPSHOT_SCHEMA, SCHEDULABILITY_SNAPSHOT_SCHEMA}:
        policy = state.get("policy")
        if not isinstance(policy, dict):
            raise ReplayError("policy-capable snapshot is missing policy closure state")
        _restore_policy_state(kernel, policy)
    if schema == SCHEDULABILITY_SNAPSHOT_SCHEMA:
        wave6 = state.get("schedulability")
        if not isinstance(wave6, dict):
            raise ReplayError("v6 snapshot is missing schedulability/liveness state")
        _restore_schedulability_state(kernel, wave6)

    for entry in entries[prefix_length:]:
        _replay_entry(kernel, entry)
    _flush_pending_canonical(kernel)
    return kernel


def install_lineage_recovery(kernel_cls) -> None:
    if getattr(kernel_cls, "_wave7_lineage_recovery_installed", False):
        return
    kernel_cls.open = classmethod(_open)
    kernel_cls._wave7_lineage_recovery_installed = True
