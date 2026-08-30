from __future__ import annotations

import tempfile
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Callable

from . import PlanKernel
from .actions import ActionIntent, AuthorityGrant
from .evidence import EvidencePolarity, EvidenceRecord
from .future_resurrection import DormantBranchRevision
from .handoff_stability import HandoffStabilityContract
from .hashing import digest
from .lineage import (
    CanonicalLineageRevision,
    LineageError,
    LineageRegistry,
    SemanticRegimeKind,
)
from .lineage_recovery import canonical_semantic_digest
from .migration import (
    FieldMigrationDisposition,
    IdentityMapping,
    MigrationDisposition,
    MigrationError,
    MigrationManifest,
)
from .types import AuthorizationError, ReplayError


WAVE7_TAXONOMY = ("LG", "MG", "RP", "GC")


@dataclass(frozen=True, slots=True)
class Wave7Case:
    name: str
    check: Callable[[], bool]


def _raises(exc_type, fn: Callable[[], object]) -> bool:
    try:
        fn()
    except exc_type:
        return True
    return False


def _root() -> Path:
    return Path(tempfile.mkdtemp(prefix="nolane-wave7-conformance-"))


def _kernel() -> PlanKernel:
    return PlanKernel.create(_root(), "wave7 conformance", ("done",), ("preserve rollback",))


def _lineage_row(
    *,
    family: str = "Artifact",
    logical_id: str = "artifact",
    revision_id: str = "artifact@1",
    semantic: str = "semantic@1",
    sequence: int = 1,
    parents: tuple[str, ...] = (),
    supersedes: str | None = None,
    provenance: tuple[str, ...] = ("source@1",),
    debt: tuple[str, ...] = (),
    wall_time: float | None = None,
) -> CanonicalLineageRevision:
    return CanonicalLineageRevision.create(
        object_family=family,
        logical_id=logical_id,
        revision_id=revision_id,
        schema_version="schema@1",
        created_sequence=sequence,
        created_at_wall_time=wall_time,
        mission_revision_dependency=None,
        plan_revision=1,
        world_model_revision="world@1",
        environment_regime_revision="environment@1",
        validity_regime="ACTIVE",
        parent_revision_ids=parents,
        provenance_refs=provenance,
        assurance_profile="CHECKED",
        debt_refs=debt,
        supersedes_revision_id=supersedes,
        semantic_digest=semantic,
    )


def _manifest(**overrides) -> MigrationManifest:
    values = dict(
        manifest_id="migration:wave7-conformance",
        source_schema_revision="schema:nolane-plan:v7",
        target_schema_revision="schema:nolane-plan:v7b",
        target_schema_semantic_digest="schema-v7b-semantic",
        changed_correctness_fields=(("PolicyNodeRevision", "guard_semantics"),),
        field_dispositions=(
            FieldMigrationDisposition(
                "PolicyNodeRevision",
                "guard_semantics",
                MigrationDisposition.INVALIDATED_REQUIRES_RECHECK,
            ),
        ),
        identity_mappings=(),
        checked_invariants=("no_authority_promotion",),
        revoked_certificate_refs=("seal:old",),
        revoked_authorization_refs=(),
        new_debt_refs=("debt:migration-review",),
        replay_fixture_digests=("fixture:wave7",),
        rollback_procedure_ref="rollback:restore-v7-root",
        backup_ref="backup:v7",
        unsupported_legacy_cases=("schema:v3-opaque",),
        external_effect_history_refs=("receipt:external@1",),
        provenance_refs=("conformance:wave7",),
    )
    values.update(overrides)
    return MigrationManifest.create(**values)


def _authorized_kernel() -> tuple[PlanKernel, object]:
    kernel = _kernel()
    kernel.propose_action(ActionIntent("deploy", "deploy"))
    kernel.add_grant(AuthorityGrant("grant", "agent:a", frozenset({"deploy"})))
    return kernel, kernel.authorize("deploy", "agent:a", ("grant",), 1)


def _decision_epoch_kernel() -> tuple[PlanKernel, object]:
    from .policy_information import DecisionEpoch, InformationPartitionRevision, ObservationFrontierRevision

    kernel = _kernel()
    principal = "agent:a"
    kernel.principals.register(principal, set())
    access = kernel.current_policy_access_revision(principal)
    action_space = kernel.current_policy_action_space_revision()
    frontier = ObservationFrontierRevision.create(
        frontier_id="frontier",
        revision_id="frontier@1",
        principal_scope_ref=principal,
        information_access_profile_revision=access,
        currently_available_observations=("signal",),
        pending_observations=(),
        reveal_event_refs=(),
        latest_safe_observation_times={},
        observation_costs={},
        observation_side_effects=(),
        observation_dependencies=("observation-model@1",),
        unobservable_predicates=(),
        conditionally_observable_predicates=(),
        frontier_debt_refs=(),
        validity_regime="runtime@1",
    )
    partition = InformationPartitionRevision.create(
        logical_id="partition",
        revision_id="partition@1",
        mission_revision=kernel.mission.current.version,
        decision_epoch_ref="epoch@1",
        principal_scope_ref=principal,
        information_access_profile_revision=access,
        principal_observation_history_digest="principal-history@1",
        principal_delivery_frontier_refs=(),
        canonical_state_version=kernel.canonical_version,
        observation_history_digest="history@1",
        observable_predicate_set=("signal",),
        hidden_or_unrevealed_predicate_set=(),
        information_equivalence_classes={"visible": ("h1",)},
        reveal_event_refs=(),
        observation_model_refs=("observation-model@1",),
        perfect_recall_basis_ref="recall@1",
        abstraction_certificate_refs=("abstraction@1",),
        debt_refs=(),
        validity_regime="runtime@1",
    )
    epoch = DecisionEpoch.create(
        epoch_id="epoch@1",
        plan_snapshot_version=kernel.plan_snapshot_version,
        mission_revision=kernel.mission.current.version,
        decision_principal_ref=principal,
        strategic_location_revision=kernel._location_revision,
        information_partition_revision=partition.revision_id,
        principal_information_access_profile_revision=access,
        available_action_space_revision=action_space,
        active_authority_profile="authority@1",
        active_obligation_basis="obligations@1",
        risk_policy_revision="risk@1",
        observation_frontier_revision=frontier.revision_id,
        temporal_window=(0, 100),
    )
    kernel.register_policy_frontier(frontier)
    kernel.register_information_partition(partition)
    kernel.register_decision_epoch(epoch)
    return kernel, epoch


def _dormant_branch() -> DormantBranchRevision:
    return DormantBranchRevision.create(
        branch_id="branch:hedge",
        revision_id="branch:hedge@1",
        branch_digest="branch:digest:1",
        mission_revision="mission@1",
        assumption_revision_refs=("assumption@1",),
        evidence_revision_refs=("evidence:dormant@1",),
        transition_model_revision="transition@1",
        temporal_feasibility_revision="temporal@1",
        resource_revision_refs=("resource@1",),
        capability_revision_refs=("capability@1",),
        authority_revision_refs=("authority@1",),
        risk_classification="catastrophic",
        resurrection_dependency_refs=("trigger@1",),
        dormant_reason="currently unlikely",
        dormant_generation=4,
        catastrophic_exposure=True,
        sole_hard_route=False,
        unique_hedge=True,
        information_value=1.0,
    )


def _fallback_contract() -> HandoffStabilityContract:
    return HandoffStabilityContract.create(
        contract_id="edge:critical",
        revision_id="edge:critical@1",
        policy_edge_ref="parent->child",
        protected_predicate_refs=("inventory",),
        protected_generation_bindings=(("inventory", 1),),
        lock_or_reservation_refs=(),
        stability_start=0,
        stability_end=100,
        external_writer_assumption_refs=(),
        refresh_required_predicate_refs=("inventory",),
        authorization_time_precondition_refs=("inventory",),
        invalidating_event_refs=(),
        open_side_effect_refs=(),
        fallback_on_instability="fallback:unique@1",
        opacity_debt_refs=(),
        validity_regime="runtime@1",
    )


# Lineage --------------------------------------------------------------------------------

def _lg01() -> bool:
    registry = LineageRegistry()
    first = _lineage_row()
    registry.register(first)
    alias = _lineage_row(family="Other", logical_id="other")
    return _raises(LineageError, lambda: registry.register(alias))


def _lg02() -> bool:
    registry = LineageRegistry()
    registry.register(_lineage_row())
    rebound = _lineage_row(semantic="different")
    return _raises(LineageError, lambda: registry.register(rebound))


def _lg03() -> bool:
    kernel, authorization = _authorized_kernel()
    kernel.revise_semantic_regime(
        SemanticRegimeKind.ENVIRONMENT,
        semantic_digest="environment@changed",
        provenance_refs=("conformance",),
    )
    return _raises(
        AuthorizationError,
        lambda: kernel._assert_authorization_lineage_current(authorization.id),
    )


def _lg04() -> bool:
    return _raises(
        LineageError,
        lambda: _lineage_row(parents=("artifact@1",)),
    )


def _lg05() -> bool:
    kernel = _kernel()
    first = kernel._register_lineage(
        object_family="DerivedArtifact",
        logical_id="proof",
        semantic_payload={"v": 1},
        provenance_refs=("root:proof@1",),
    )
    kernel.bump_domain("conformance-lineage")
    second = kernel._register_lineage(
        object_family="DerivedArtifact",
        logical_id="proof",
        semantic_payload={"v": 2},
        provenance_refs=("root:proof@1", "evidence@1"),
    )
    result = kernel.compact_lineage("compaction:lg05")
    rebuilt = kernel.reconstruct_compacted_lineage(result.manifest_id)
    restored = rebuilt.get(second.revision_id)
    return (
        first.revision_id in restored.parent_revision_ids
        and restored.provenance_refs == second.provenance_refs
    )


def _lg06() -> bool:
    a = _lineage_row(wall_time=1.0)
    b = _lineage_row(wall_time=999999.0)
    return a.lineage_digest == b.lineage_digest and a.created_sequence == b.created_sequence


def _lg07() -> bool:
    kernel, authorization = _authorized_kernel()
    bound = dict(kernel.authorization_lineage_bindings[authorization.id].regime_revisions)
    kernel.revise_semantic_regime(
        SemanticRegimeKind.WORLD_MODEL,
        semantic_digest="world@changed",
        provenance_refs=("conformance",),
    )
    current = {
        kind.value: kernel.lineage.current_regime(kind).revision_id
        for kind in SemanticRegimeKind
    }
    return bound != current and _raises(
        AuthorizationError,
        lambda: kernel._assert_authorization_lineage_current(authorization.id),
    )


def _lg08() -> bool:
    kernel, epoch = _decision_epoch_kernel()
    binding = kernel.decision_epoch_lineage_bindings[epoch.epoch_id]
    before = binding["regime_lineage_digest"]
    kernel.revise_semantic_regime(
        SemanticRegimeKind.SEMANTIC_PROFILE,
        semantic_digest="semantic-profile@changed",
        provenance_refs=("conformance",),
    )
    return before != kernel.current_semantic_regime_lineage_digest()


# Migration ------------------------------------------------------------------------------

def _mg01() -> bool:
    return _raises(
        MigrationError,
        lambda: _manifest(
            changed_correctness_fields=(
                ("PolicyNodeRevision", "guard_semantics"),
                ("PlanSeal", "validity_regime"),
            )
        ),
    )


def _mg02() -> bool:
    return _raises(
        MigrationError,
        lambda: _manifest(target_schema_semantic_digest=""),
    )


def _mg03() -> bool:
    disposition = FieldMigrationDisposition(
        "PolicyNodeRevision", "logical_id", MigrationDisposition.PRESERVED_EXACTLY
    )
    return _raises(
        MigrationError,
        lambda: _manifest(
            changed_correctness_fields=(("PolicyNodeRevision", "logical_id"),),
            field_dispositions=(disposition,),
            identity_mappings=(),
        ),
    )


def _mg04() -> bool:
    row = FieldMigrationDisposition(
        "PolicyNodeRevision",
        "guard_semantics",
        MigrationDisposition.ESCALATED_TO_DEBT,
        debt_ref="debt:guard",
    )
    return _raises(
        MigrationError,
        lambda: _manifest(field_dispositions=(row,), new_debt_refs=()),
    )


def _mg05() -> bool:
    kernel, authorization = _authorized_kernel()
    result = kernel.apply_semantic_migration(_manifest(), now=2)
    return (
        authorization.id in result.invalidated_authorization_ids
        and authorization.id in kernel.migration_recheck_required_authorizations
        and _raises(
            AuthorizationError,
            lambda: kernel._assert_authorization_lineage_current(authorization.id),
        )
    )


def _mg06() -> bool:
    kernel = _kernel()
    kernel.propose_action(ActionIntent("deploy", "deploy", idempotent=False))
    kernel.add_grant(AuthorityGrant("grant", "agent:a", frozenset({"deploy"})))
    authorization = kernel.authorize("deploy", "agent:a", ("grant",), 1)
    transaction = kernel.transaction_for_authorization(authorization.id)
    kernel.transactions.record_dispatch(transaction.id, "adapter:x", 1)
    return _raises(MigrationError, lambda: kernel.apply_semantic_migration(_manifest(), now=2))


def _mg07() -> bool:
    kernel = _kernel()
    kernel.bump_domain("pre-migration")
    before = kernel.writer_sequence
    result = kernel.apply_semantic_migration(_manifest(), now=-1000)
    return result.root_switched_sequence == before + 1 == kernel.writer_sequence


def _mg08() -> bool:
    kernel = _kernel()
    before = set(kernel.authorizations)
    kernel.apply_semantic_migration(_manifest(), now=1)
    return set(kernel.authorizations) == before


def _mg09() -> bool:
    manifest = _manifest(
        external_effect_history_refs=("receipt:b", "receipt:a"),
        rollback_procedure_ref="rollback:root-only-not-world",
        backup_ref="backup:pre-migration",
    )
    return (
        manifest.external_effect_history_refs == ("receipt:a", "receipt:b")
        and manifest.rollback_procedure_ref == "rollback:root-only-not-world"
        and manifest.backup_ref == "backup:pre-migration"
    )


def _mg10() -> bool:
    manifest = _manifest(unsupported_legacy_cases=("schema:v3-opaque",))
    return not manifest.supports_legacy_case("schema:v3-opaque")


# Replay ---------------------------------------------------------------------------------

def _rp01() -> bool:
    kernel = _kernel()
    root = kernel.root
    kernel.save_snapshot()
    kernel.add_evidence(
        EvidenceRecord(
            "evidence:post",
            "suffix replay",
            EvidencePolarity.SUPPORTS,
            "host",
            "root:host",
            1,
            assurance=0.9,
        )
    )
    expected = canonical_semantic_digest(kernel)
    return canonical_semantic_digest(PlanKernel.open(root)) == expected


def _rp02() -> bool:
    kernel = _kernel()
    root = kernel.root
    kernel.save_snapshot()
    kernel.journal.append("wave7.unknown_correctness_event", {"semantic": True})
    return _raises(ReplayError, lambda: PlanKernel.open(root))


def _rp03() -> bool:
    kernel = _kernel()
    root = kernel.root
    kernel.save_snapshot()
    kernel.bump_domain("post-snapshot")
    first = PlanKernel.open(root)
    second = PlanKernel.open(root)
    return canonical_semantic_digest(first) == canonical_semantic_digest(second)


def _rp04() -> bool:
    kernel, authorization = _authorized_kernel()
    root = kernel.root
    kernel.save_snapshot_v6()
    reopened = PlanKernel.open(root)
    return (
        authorization.id in reopened.authorizations
        and authorization.id in reopened.migration_recheck_required_authorizations
        and authorization.id not in reopened.authorization_lineage_bindings
    )


def _rp05() -> bool:
    kernel, authorization = _authorized_kernel()
    root = kernel.root
    kernel.save_snapshot()
    kernel.revise_semantic_regime(
        SemanticRegimeKind.ENVIRONMENT,
        semantic_digest="environment@post-snapshot",
        provenance_refs=("conformance",),
    )
    reopened = PlanKernel.open(root)
    return authorization.id in reopened.authorizations and _raises(
        AuthorizationError,
        lambda: reopened._assert_authorization_lineage_current(authorization.id),
    )


def _rp06() -> bool:
    kernel = _kernel()
    first = kernel._register_lineage(
        object_family="HistoricalArtifact",
        logical_id="artifact",
        semantic_payload={"revision": 1},
        provenance_refs=("history@1",),
    )
    kernel.bump_domain("history-advance")
    kernel._register_lineage(
        object_family="HistoricalArtifact",
        logical_id="artifact",
        semantic_payload={"revision": 2},
        provenance_refs=("history@2",),
    )
    root = kernel.root
    kernel.save_snapshot()
    reopened = PlanKernel.open(root)
    return reopened.lineage.get(first.revision_id).revision_id == first.revision_id


# Compaction -----------------------------------------------------------------------------

def _gc01() -> bool:
    kernel = _kernel()
    mission = kernel.lineage.current("MissionRevision", "mission").revision_id
    regimes = {
        kind: kernel.lineage.current_regime(kind).revision_id
        for kind in SemanticRegimeKind
    }
    kernel.compact_lineage("compaction:gc01")
    return (
        kernel.lineage.current("MissionRevision", "mission").revision_id == mission
        and {kind: kernel.lineage.current_regime(kind).revision_id for kind in regimes} == regimes
    )


def _gc02() -> bool:
    kernel = _kernel()
    first = kernel._register_lineage(
        object_family="CompactionArtifact",
        logical_id="artifact",
        semantic_payload={"revision": 1},
        provenance_refs=("parent@1",),
    )
    kernel.bump_domain("compaction-parent")
    second = kernel._register_lineage(
        object_family="CompactionArtifact",
        logical_id="artifact",
        semantic_payload={"revision": 2},
        provenance_refs=("parent@1", "parent@2"),
    )
    result = kernel.compact_lineage("compaction:gc02")
    rebuilt = kernel.reconstruct_compacted_lineage(result.manifest_id)
    restored = rebuilt.get(second.revision_id)
    return first.revision_id in restored.parent_revision_ids


def _gc03() -> bool:
    kernel = _kernel()
    branch = _dormant_branch()
    result = kernel.compact_lineage("compaction:gc03", dormant_branches=(branch,))
    refs = set(kernel.compaction_manifests[result.manifest_id].dormant_resurrection_refs)
    expected = {
        branch.revision_id,
        *branch.assumption_revision_refs,
        *branch.evidence_revision_refs,
        branch.transition_model_revision,
        branch.temporal_feasibility_revision,
        *branch.resource_revision_refs,
        *branch.capability_revision_refs,
        *branch.authority_revision_refs,
        *branch.resurrection_dependency_refs,
    }
    return expected.issubset(refs)


def _gc04() -> bool:
    kernel = _kernel()
    kernel._register_lineage(
        object_family="ProofedArtifact",
        logical_id="artifact",
        semantic_payload={"verified": True},
        provenance_refs=("proof:root@1", "evidence:verified@1"),
        debt_refs=("debt:verify@1",),
    )
    result = kernel.compact_lineage("compaction:gc04")
    refs = set(kernel.compaction_manifests[result.manifest_id].proof_evidence_debt_refs)
    return {"proof:root@1", "evidence:verified@1", "debt:verify@1"}.issubset(refs)


def _gc05() -> bool:
    kernel = _kernel()
    contract = _fallback_contract()
    kernel.register_handoff_stability_contract(contract)
    result = kernel.compact_lineage("compaction:gc05")
    return contract.fallback_on_instability in kernel.compaction_manifests[
        result.manifest_id
    ].unique_fallback_refs


def _gc06() -> bool:
    kernel = _kernel()
    row = kernel.lineage.current("MissionRevision", "mission")
    result = kernel.compact_lineage("compaction:gc06")
    archive = kernel.compaction_archives[result.manifest_id]
    tampered = replace(row, semantic_digest="tampered")
    return _raises(Exception, lambda: archive.register_revision(tampered))


def _gc07() -> bool:
    kernel = _kernel()
    before = kernel.lineage.semantic_root_digest()
    result = kernel.compact_lineage("compaction:gc07")
    rebuilt = kernel.reconstruct_compacted_lineage(result.manifest_id)
    return rebuilt.semantic_root_digest() == before


def _gc08() -> bool:
    kernel, authorization = _authorized_kernel()
    kernel._assert_authorization_lineage_current(authorization.id)
    before = kernel.authorization_lineage_bindings[authorization.id]
    kernel.compact_lineage("compaction:gc08")
    kernel._assert_authorization_lineage_current(authorization.id)
    return kernel.authorization_lineage_bindings[authorization.id] == before


_CASES = (
    ("LG01_LOGICAL_IDENTITY_ALIAS", _lg01),
    ("LG02_REVISION_REBIND", _lg02),
    ("LG03_LOGICAL_ONLY_AUTHORITY", _lg03),
    ("LG04_PARENT_CYCLE", _lg04),
    ("LG05_PARENT_PROVENANCE_DROP", _lg05),
    ("LG06_WALL_CLOCK_CAUSALITY", _lg06),
    ("LG07_REGIME_DRIFT", _lg07),
    ("LG08_DECISION_EPOCH_REUSE", _lg08),
    ("MG01_MISSING_DISPOSITION", _mg01),
    ("MG02_SILENT_DEFAULT", _mg02),
    ("MG03_IDENTITY_MAPPING_OMITTED", _mg03),
    ("MG04_DEBT_DISAPPEARS", _mg04),
    ("MG05_AUTHORITY_SURVIVES_CHANGE", _mg05),
    ("MG06_AMBIGUOUS_EXTERNAL_ACTION", _mg06),
    ("MG07_JOURNAL_ORDER_REWRITE", _mg07),
    ("MG08_MIGRATION_MINTS_AUTHORITY", _mg08),
    ("MG09_ROLLBACK_FORGETS_EXTERNAL_EFFECT", _mg09),
    ("MG10_UNSUPPORTED_LEGACY_GUESS", _mg10),
    ("RP01_BASE_SUFFIX_EXACT", _rp01),
    ("RP02_UNKNOWN_EVENT_FAILS_CLOSED", _rp02),
    ("RP03_CANONICAL_DIGEST_REPRODUCIBLE", _rp03),
    ("RP04_V6_IMPORT_CONSERVATIVE", _rp04),
    ("RP05_STALE_AUTHORITY_NO_RESURRECTION", _rp05),
    ("RP06_HISTORICAL_REVISION_QUERYABLE", _rp06),
    ("GC01_MISSION_REGIME_INVARIANT", _gc01),
    ("GC02_PARENT_REFS_RETAINED", _gc02),
    ("GC03_DORMANT_RESURRECTION_RETAINED", _gc03),
    ("GC04_PROOF_EVIDENCE_DEBT_RETAINED", _gc04),
    ("GC05_UNIQUE_FALLBACK_RETAINED", _gc05),
    ("GC06_REVISION_ID_IMMUTABLE", _gc06),
    ("GC07_RECONSTRUCTION_DIGEST", _gc07),
    ("GC08_AUTHORITY_EQUIVALENCE", _gc08),
)

WAVE7_CASES = {name: Wave7Case(name, check) for name, check in _CASES}


def run_wave7_conformance() -> dict[str, tuple[bool, str]]:
    results: dict[str, tuple[bool, str]] = {}
    for name, case in WAVE7_CASES.items():
        try:
            passed = bool(case.check())
            results[name] = (passed, "defended" if passed else "invariant was not defended")
        except Exception as exc:  # conformance runner must report rather than abort
            results[name] = (False, f"{type(exc).__name__}: {exc}")
    return results
