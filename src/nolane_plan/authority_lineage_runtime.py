from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from .hashing import digest
from .lineage import LineageError, SemanticRegimeKind
from .lineage_snapshot import LINEAGE_SNAPSHOT_SCHEMA
from .persistence import SnapshotStore
from .types import AuthorizationError, ReplayError


_CURRENT_SEAL_VALUES = {"sealed", "sealed_with_accepted_debt"}
_CURRENT_EXEC_VALUES = {"EXEC_BOUNDED", "EXEC_BOUNDED_WITH_ACCEPTED_DEBT", "exec_bounded", "exec_bounded_with_accepted_debt"}


def _state_payload(self) -> dict[str, Any]:
    body = {
        "decision_epoch_bindings": {
            key: dict(sorted(value.items()))
            for key, value in sorted(self.decision_epoch_lineage_bindings.items())
        },
        "authorization_bindings": {
            key: dict(sorted(value.items()))
            for key, value in sorted(self.authority_lineage_closure_bindings.items())
        },
    }
    return {**body, "canonical_digest": digest(body)}


def _install_state(self) -> None:
    self.decision_epoch_lineage_bindings: dict[str, dict[str, str]] = {}
    self.authority_lineage_closure_bindings: dict[str, dict[str, str]] = {}


def _semantic_regime_digest(self) -> str:
    rows = tuple(
        sorted(
            (kind.value, self.lineage.current_regime(kind).revision_id)
            for kind in SemanticRegimeKind
        )
    )
    return digest(rows)


def _register_sidecar(
    self,
    *,
    family: str,
    logical_id: str,
    semantic_digest: str,
    provenance: tuple[str, ...],
    created_sequence: int | None = None,
    debt_refs: tuple[str, ...] = (),
):
    return self._register_lineage(
        object_family=family,
        logical_id=str(logical_id),
        semantic_digest=str(semantic_digest),
        provenance_refs=provenance,
        debt_refs=debt_refs,
        created_sequence=created_sequence,
    )


def _current_sidecar(self, family: str, logical_id: str) -> str:
    try:
        return self.lineage.current(family, str(logical_id)).revision_id
    except LineageError as exc:
        raise AuthorizationError(f"missing exact {family} lineage for {logical_id}") from exc


def _strategic_location_digest(self) -> str:
    return digest(
        {
            "revision": int(self._location_revision),
            "status": self.strategic_location.status.value,
            "region_ids": tuple(self.strategic_location.region_ids),
            "decision_signatures": tuple(self.strategic_location.decision_signatures),
        }
    )


def _register_strategic_location_lineage(self, created_sequence: int | None = None):
    return _register_sidecar(
        self,
        family="StrategicLocation",
        logical_id="strategic-location",
        semantic_digest=_strategic_location_digest(self),
        provenance=("kernel:strategic-location",),
        created_sequence=created_sequence,
    )


def _source_digest(source) -> str:
    return digest(
        {
            "source_id": source.source_id,
            "revision_id": source.revision_id,
            "value": source.value,
        }
    )


def _register_proof_source_lineage(self, source_id: str, created_sequence: int | None = None):
    source = self.semantic_barrier.read_source(source_id)
    return _register_sidecar(
        self,
        family="ProofSemanticSource",
        logical_id=source_id,
        semantic_digest=_source_digest(source),
        provenance=("proof:semantic-source", source.revision_id),
        created_sequence=created_sequence,
    )


def _register_proof_input_lineage(self, envelope, created_sequence: int | None = None):
    return _register_sidecar(
        self,
        family="ProofInputEnvelope",
        logical_id=envelope.input_envelope_id,
        semantic_digest=envelope.canonical_input_digest,
        provenance=("proof:input-envelope", envelope.revision_id),
        created_sequence=created_sequence,
    )


def _register_query_lineage(self, query, created_sequence: int | None = None):
    return _register_sidecar(
        self,
        family="ProofQueryDomain",
        logical_id=query.query_domain_id,
        semantic_digest=query.canonical_digest,
        provenance=("proof:query-domain", query.revision_id),
        created_sequence=created_sequence,
    )


def _register_manifest_lineage(self, manifest, created_sequence: int | None = None):
    return _register_sidecar(
        self,
        family="ProofManifest",
        logical_id=manifest.artifact_revision,
        semantic_digest=manifest.canonical_digest,
        provenance=("proof:dependency-manifest", manifest.revision_id),
        created_sequence=created_sequence,
    )


def _support_node_digest(node) -> str:
    return digest(
        {
            "ref": node.ref,
            "current": bool(node.current),
            "direct_grounding_roots": tuple(sorted(node.direct_grounding_roots)),
            "support_refs": tuple(node.support_refs),
            "scope": node.scope,
            "assumption_basis": tuple(sorted(node.assumption_basis)),
            "proof_kind": node.proof_kind,
            "validity_regime": node.validity_regime,
            "context_tags": tuple(sorted(node.context_tags)),
        }
    )


def _register_support_node_lineage(self, node, created_sequence: int | None = None):
    return _register_sidecar(
        self,
        family="ProofSupportNode",
        logical_id=node.ref,
        semantic_digest=_support_node_digest(node),
        provenance=("proof:support-node",),
        created_sequence=created_sequence,
    )


def _register_support_set_lineage(self, support_set, created_sequence: int | None = None):
    return _register_sidecar(
        self,
        family="ProofSupportSet",
        logical_id=support_set.subject_artifact_revision,
        semantic_digest=support_set.canonical_digest,
        provenance=("proof:support-set", support_set.revision_id),
        created_sequence=created_sequence,
    )


def _invalidity_digest(self, artifact_revision: str) -> str:
    causes = self.proof_invalidity_causes.get(artifact_revision, ())
    rows = tuple(
        sorted(
            (
                cause.cause_id,
                cause.code,
                bool(cause.active),
                bool(cause.blocking),
                cause.detail,
            )
            for cause in causes
        )
    )
    return digest(rows)


def _refresh_proof_authority_lineage(self, artifact_revision: str, created_sequence: int | None = None):
    manifest = self.proof_manifests.get(artifact_revision)
    support_set = self.support_sets.get(artifact_revision)
    if manifest is None or support_set is None:
        return None
    try:
        manifest_lineage = self.lineage.current("ProofManifest", artifact_revision).revision_id
        support_lineage = self.lineage.current("ProofSupportSet", artifact_revision).revision_id
    except LineageError:
        return None

    source_lineages: list[tuple[str, str]] = []
    for source_id, _bound_revision in manifest.positive_revision_dependencies:
        try:
            source_lineages.append(
                (source_id, self.lineage.current("ProofSemanticSource", source_id).revision_id)
            )
        except LineageError:
            source_lineages.append((source_id, "MISSING"))

    query_lineages: list[tuple[str, str]] = []
    for query in manifest.query_domain_revisions:
        try:
            query_lineages.append(
                (query.query_domain_id, self.lineage.current("ProofQueryDomain", query.query_domain_id).revision_id)
            )
        except LineageError:
            query_lineages.append((query.query_domain_id, "MISSING"))

    support_node_lineages: list[tuple[str, str]] = []
    support_refs = sorted(
        {
            ref
            for clause in support_set.clauses
            for ref in clause.required_support_refs
        }
    )
    for ref in support_refs:
        try:
            support_node_lineages.append((ref, self.lineage.current("ProofSupportNode", ref).revision_id))
        except LineageError:
            support_node_lineages.append((ref, "MISSING"))

    input_lineage = "MISSING"
    envelope = self.proof_input_envelopes.get(manifest.input_envelope_revision)
    if envelope is not None:
        try:
            input_lineage = self.lineage.current("ProofInputEnvelope", envelope.input_envelope_id).revision_id
        except LineageError:
            pass

    semantic = digest(
        {
            "artifact_revision": artifact_revision,
            "manifest_lineage_revision": manifest_lineage,
            "support_lineage_revision": support_lineage,
            "input_lineage_revision": input_lineage,
            "source_lineage_revisions": tuple(source_lineages),
            "query_lineage_revisions": tuple(query_lineages),
            "support_node_lineage_revisions": tuple(support_node_lineages),
            "invalidity_digest": _invalidity_digest(self, artifact_revision),
            "proof_profile_refs": tuple(sorted(self.proof_profile_refs)),
            "semantic_regime_lineage_digest": _semantic_regime_digest(self),
        }
    )
    return _register_sidecar(
        self,
        family="ProofAuthority",
        logical_id=artifact_revision,
        semantic_digest=semantic,
        provenance=("proof:authority-closure", artifact_revision),
        created_sequence=created_sequence,
    )


def _refresh_proofs_for_source(self, source_id: str, created_sequence: int | None = None) -> None:
    for artifact_revision, manifest in sorted(self.proof_manifests.items()):
        if any(bound_source == source_id for bound_source, _ in manifest.positive_revision_dependencies):
            _refresh_proof_authority_lineage(self, artifact_revision, created_sequence)


def _refresh_proofs_for_query(self, query_id: str, created_sequence: int | None = None) -> None:
    for artifact_revision, manifest in sorted(self.proof_manifests.items()):
        if any(query.query_domain_id == query_id for query in manifest.query_domain_revisions):
            _refresh_proof_authority_lineage(self, artifact_revision, created_sequence)


def _refresh_all_proof_authority(self, created_sequence: int | None = None) -> None:
    for artifact_revision in sorted(self.proof_manifests):
        _refresh_proof_authority_lineage(self, artifact_revision, created_sequence)


def _register_policy_sidecar(
    self,
    *,
    family: str,
    logical_id: str,
    value,
    provenance: str,
    created_sequence: int | None = None,
):
    return _register_sidecar(
        self,
        family=family,
        logical_id=logical_id,
        semantic_digest=value.canonical_digest,
        provenance=(provenance, value.revision_id if hasattr(value, "revision_id") else logical_id),
        created_sequence=created_sequence,
        debt_refs=tuple(getattr(value, "debt_refs", ()) or ()),
    )


def _register_information_regime_lineage(self, epoch, partition, frontier, created_sequence: int | None = None):
    semantic = digest(
        {
            "principal": epoch.decision_principal_ref,
            "access_revision": epoch.principal_information_access_profile_revision,
            "partition_lineage_revision": _current_sidecar(self, "PolicyInformationPartition", partition.logical_id),
            "frontier_lineage_revision": _current_sidecar(self, "PolicyObservationFrontier", frontier.frontier_id),
            "partition_revision": partition.revision_id,
            "frontier_revision": frontier.revision_id,
        }
    )
    return _register_sidecar(
        self,
        family="InformationRegime",
        logical_id=epoch.decision_principal_ref,
        semantic_digest=semantic,
        provenance=("policy:decision-information-regime", epoch.epoch_id),
        created_sequence=created_sequence,
    )


def _register_decision_epoch_lineage(self, epoch, created_sequence: int | None = None):
    partition = self.policy_partitions[epoch.information_partition_revision]
    frontier = self.policy_frontiers[epoch.observation_frontier_revision]
    location = _register_strategic_location_lineage(self, created_sequence)
    information_regime = _register_information_regime_lineage(
        self, epoch, partition, frontier, created_sequence
    )
    mission_lineage = self.lineage.current("MissionRevision", "mission").revision_id
    canonical_lineage = self.lineage.current("CanonicalState", "canonical-state").revision_id
    partition_lineage = _current_sidecar(self, "PolicyInformationPartition", partition.logical_id)
    frontier_lineage = _current_sidecar(self, "PolicyObservationFrontier", frontier.frontier_id)
    regime_digest = _semantic_regime_digest(self)
    epoch_semantic = digest(
        {
            "epoch_digest": epoch.canonical_digest,
            "mission_lineage_revision": mission_lineage,
            "canonical_state_lineage_revision": canonical_lineage,
            "strategic_location_lineage_revision": location.revision_id,
            "strategic_location_revision": str(epoch.strategic_location_revision),
            "partition_lineage_revision": partition_lineage,
            "frontier_lineage_revision": frontier_lineage,
            "information_regime_lineage_revision": information_regime.revision_id,
            "principal_access_revision": epoch.principal_information_access_profile_revision,
            "regime_lineage_digest": regime_digest,
        }
    )
    epoch_lineage = _register_sidecar(
        self,
        family="DecisionEpoch",
        logical_id=epoch.epoch_id,
        semantic_digest=epoch_semantic,
        provenance=("policy:decision-epoch", epoch.epoch_id),
        created_sequence=created_sequence,
    )
    binding = {
        "mission_lineage_revision": mission_lineage,
        "canonical_state_lineage_revision": canonical_lineage,
        "strategic_location_revision": str(epoch.strategic_location_revision),
        "strategic_location_lineage_revision": location.revision_id,
        "information_partition_revision": partition.revision_id,
        "observation_frontier_revision": frontier.revision_id,
        "partition_lineage_revision": partition_lineage,
        "frontier_lineage_revision": frontier_lineage,
        "information_regime_lineage_revision": information_regime.revision_id,
        "principal_access_revision": epoch.principal_information_access_profile_revision,
        "decision_epoch_lineage_revision": epoch_lineage.revision_id,
        "regime_lineage_digest": regime_digest,
    }
    self.decision_epoch_lineage_bindings[epoch.epoch_id] = binding
    return epoch_lineage


def _register_wave6_sidecar(
    self,
    *,
    family: str,
    logical_id: str,
    value,
    provenance: str,
    created_sequence: int | None = None,
):
    return _register_sidecar(
        self,
        family=family,
        logical_id=logical_id,
        semantic_digest=value.canonical_digest,
        provenance=(provenance, getattr(value, "revision_id", logical_id)),
        created_sequence=created_sequence,
        debt_refs=tuple(getattr(value, "model_adequacy_debt_refs", ()) or ())
        + tuple(getattr(value, "residual_debt_refs", ()) or ()),
    )


def _proof_binding_fields(self, authorization_id: str) -> dict[str, str]:
    binding = self.proof_authorization_bindings.get(authorization_id)
    if binding is None:
        return {}
    artifact = str(binding["proof_artifact_revision"])
    return {
        "proof_lineage_revision": _current_sidecar(self, "ProofAuthority", artifact),
        "proof_manifest_lineage_revision": _current_sidecar(self, "ProofManifest", artifact),
        "proof_support_lineage_revision": _current_sidecar(self, "ProofSupportSet", artifact),
    }


def _policy_binding_fields(self, authorization_id: str) -> dict[str, str]:
    binding = self.policy_authorization_bindings.get(authorization_id)
    if binding is None:
        return {}
    node = self.policy_nodes[str(binding["policy_node_revision"])]
    selection = self.policy_selections[str(binding["selection_record_id"])]
    sufficiency = self.policy_sufficiency[str(binding["sufficiency_revision"])]
    seal = self.policy_seals[str(binding["seal_revision"])]
    executability = self.policy_executability[str(binding["executability_revision"])]
    epoch = self.policy_epochs[node.decision_epoch_ref]
    partition = self.policy_partitions[node.information_partition_revision]
    frontier = self.policy_frontiers[node.observation_frontier_revision]
    return {
        "decision_epoch_lineage_revision": _current_sidecar(self, "DecisionEpoch", epoch.epoch_id),
        "partition_lineage_revision": _current_sidecar(self, "PolicyInformationPartition", partition.logical_id),
        "frontier_lineage_revision": _current_sidecar(self, "PolicyObservationFrontier", frontier.frontier_id),
        "policy_node_lineage_revision": _current_sidecar(self, "PolicyNode", node.policy_node_id),
        "selection_lineage_revision": _current_sidecar(self, "PolicySelection", selection.record_id),
        "sufficiency_lineage_revision": _current_sidecar(self, "DecisionSufficiency", sufficiency.certificate_id),
        "seal_lineage_revision": _current_sidecar(self, "PlanSeal", seal.seal_id),
        "executability_lineage_revision": _current_sidecar(self, "PolicyExecutability", executability.assessment_id),
        "decision_epoch_ref": epoch.epoch_id,
        "principal_access_revision": epoch.principal_information_access_profile_revision,
    }


def _sched_binding_fields(self, authorization_id: str) -> dict[str, str]:
    binding = self.schedulability_authorization_bindings.get(authorization_id)
    if binding is None:
        return {}
    sched = self.schedulability_certificates[str(binding["schedulability_revision"])]
    coverage = self.policy_coverage_assessments[str(binding["coverage_revision"])]
    job_lineages = tuple(
        sorted(
            _current_sidecar(self, "ReactionJob", job_id)
            for job_id, _ in sched.reaction_job_digests
        )
    )
    resource_lineages = tuple(
        sorted(
            _current_sidecar(self, "ControlPlaneResource", resource_id)
            for resource_id, _ in sched.control_resource_digests
        )
    )
    fields = {
        "schedulability_lineage_revision": _current_sidecar(
            self, "SchedulabilityCertificate", sched.certificate_id
        ),
        "coverage_lineage_revision": _current_sidecar(
            self, "PolicyCoverage", coverage.assessment_id
        ),
        "reaction_job_lineage_digest": digest(job_lineages),
        "control_resource_lineage_digest": digest(resource_lineages),
    }
    optional = (
        ("liveness_revision", "HandoffLiveness", self.handoff_liveness_certificates, "certificate_id", "liveness_lineage_revision"),
        ("stability_contract_revision", "HandoffStability", self.handoff_stability_contracts, "contract_id", "stability_lineage_revision"),
        ("independence_revision", "OptionIndependence", self.option_independence_certificates, "certificate_id", "independence_lineage_revision"),
    )
    for binding_key, family, registry, logical_attr, output_key in optional:
        revision = binding.get(binding_key)
        if revision:
            value = registry.get(str(revision))
            if value is not None:
                fields[output_key] = _current_sidecar(self, family, getattr(value, logical_attr))
    return fields


def _augment_authority_closure(self, authorization_id: str) -> dict[str, str]:
    closure = dict(self.authority_lineage_closure_bindings.get(authorization_id, {}))
    proof_fields = _proof_binding_fields(self, authorization_id)
    policy_fields = _policy_binding_fields(self, authorization_id)
    sched_fields = _sched_binding_fields(self, authorization_id)

    if proof_fields:
        self.proof_authorization_bindings[authorization_id].update(proof_fields)
        closure.update(proof_fields)
    if policy_fields:
        self.policy_authorization_bindings[authorization_id].update(policy_fields)
        closure.update(policy_fields)
    if sched_fields:
        self.schedulability_authorization_bindings[authorization_id].update(sched_fields)
        closure.update(sched_fields)

    base = self.authorization_lineage_bindings.get(authorization_id)
    if base is not None:
        closure["base_authorization_lineage_digest"] = base.canonical_digest
    authorization = self.authorizations.get(authorization_id)
    if authorization is not None:
        closure["acting_principal_ref"] = authorization.acting_principal_ref
        if hasattr(self, "current_policy_access_revision") and authorization.acting_principal_ref in self.principals._profiles:
            closure["current_principal_access_revision_at_bind"] = self.current_policy_access_revision(
                authorization.acting_principal_ref
            )
    closure["semantic_regime_lineage_digest"] = _semantic_regime_digest(self)
    body = {key: value for key, value in closure.items() if key != "closure_digest"}
    closure["closure_digest"] = digest(dict(sorted(body.items())))
    self.authority_lineage_closure_bindings[authorization_id] = closure
    return closure


def _assert_decision_epoch_current(self, epoch_id: str) -> None:
    binding = self.decision_epoch_lineage_bindings.get(epoch_id)
    if binding is None:
        raise AuthorizationError("decision epoch lacks exact Wave-7 lineage sidecar")
    epoch = self.policy_epochs.get(epoch_id)
    if epoch is None:
        raise AuthorizationError("decision epoch lineage references missing epoch")
    if self.lineage.current("MissionRevision", "mission").revision_id != binding["mission_lineage_revision"]:
        raise AuthorizationError("decision epoch mission lineage is stale")
    if self.lineage.current("CanonicalState", "canonical-state").revision_id != binding["canonical_state_lineage_revision"]:
        raise AuthorizationError("decision epoch canonical-state lineage is stale")
    if str(self._location_revision) != binding["strategic_location_revision"]:
        raise AuthorizationError("decision epoch strategic-location revision is stale")
    if _current_sidecar(self, "StrategicLocation", "strategic-location") != binding["strategic_location_lineage_revision"]:
        raise AuthorizationError("decision epoch strategic-location lineage is stale")
    if _semantic_regime_digest(self) != binding["regime_lineage_digest"]:
        raise AuthorizationError("decision epoch semantic-regime lineage is stale")
    if self.current_policy_access_revision(epoch.decision_principal_ref) != binding["principal_access_revision"]:
        raise AuthorizationError("decision epoch principal access lineage is stale")
    if _current_sidecar(self, "DecisionEpoch", epoch_id) != binding["decision_epoch_lineage_revision"]:
        raise AuthorizationError("decision epoch sidecar lineage is stale")


def _assert_exact_field(self, closure: dict[str, str], key: str, family: str, logical_id: str) -> None:
    expected = closure.get(key)
    if not expected:
        raise AuthorizationError(f"authority closure lacks {key}")
    if _current_sidecar(self, family, logical_id) != expected:
        raise AuthorizationError(f"authority exact lineage is stale: {key}")


def _assert_authority_closure_current(self, authorization_id: str, base_assert: Callable) -> None:
    base_assert(self, authorization_id)
    recheck = getattr(self, "migration_recheck_required_authorizations", set())
    if authorization_id in recheck:
        raise AuthorizationError("authorization requires recheck after semantic migration")

    has_derived = any(
        authorization_id in registry
        for registry in (
            getattr(self, "proof_authorization_bindings", {}),
            getattr(self, "policy_authorization_bindings", {}),
            getattr(self, "schedulability_authorization_bindings", {}),
        )
    )
    closure = self.authority_lineage_closure_bindings.get(authorization_id)
    if closure is None:
        if has_derived:
            raise AuthorizationError("derived authority lineage closure is missing")
        return
    body = {key: value for key, value in closure.items() if key != "closure_digest"}
    if closure.get("closure_digest") != digest(dict(sorted(body.items()))):
        raise AuthorizationError("authority lineage closure digest mismatch")

    if authorization_id in self.proof_authorization_bindings:
        artifact = str(self.proof_authorization_bindings[authorization_id]["proof_artifact_revision"])
        _assert_exact_field(self, closure, "proof_lineage_revision", "ProofAuthority", artifact)
        _assert_exact_field(self, closure, "proof_manifest_lineage_revision", "ProofManifest", artifact)
        _assert_exact_field(self, closure, "proof_support_lineage_revision", "ProofSupportSet", artifact)

    if authorization_id in self.policy_authorization_bindings:
        binding = self.policy_authorization_bindings[authorization_id]
        node = self.policy_nodes[str(binding["policy_node_revision"])]
        selection = self.policy_selections[str(binding["selection_record_id"])]
        sufficiency = self.policy_sufficiency[str(binding["sufficiency_revision"])]
        seal = self.policy_seals[str(binding["seal_revision"])]
        executability = self.policy_executability[str(binding["executability_revision"])]
        epoch = self.policy_epochs[node.decision_epoch_ref]
        partition = self.policy_partitions[node.information_partition_revision]
        frontier = self.policy_frontiers[node.observation_frontier_revision]
        _assert_decision_epoch_current(self, epoch.epoch_id)
        _assert_exact_field(self, closure, "decision_epoch_lineage_revision", "DecisionEpoch", epoch.epoch_id)
        _assert_exact_field(self, closure, "partition_lineage_revision", "PolicyInformationPartition", partition.logical_id)
        _assert_exact_field(self, closure, "frontier_lineage_revision", "PolicyObservationFrontier", frontier.frontier_id)
        _assert_exact_field(self, closure, "policy_node_lineage_revision", "PolicyNode", node.policy_node_id)
        _assert_exact_field(self, closure, "selection_lineage_revision", "PolicySelection", selection.record_id)
        _assert_exact_field(self, closure, "sufficiency_lineage_revision", "DecisionSufficiency", sufficiency.certificate_id)
        _assert_exact_field(self, closure, "seal_lineage_revision", "PlanSeal", seal.seal_id)
        _assert_exact_field(self, closure, "executability_lineage_revision", "PolicyExecutability", executability.assessment_id)
        if self._current_selection_status(selection).value != "advisory":
            raise AuthorizationError("selection lineage is no longer advisory/current")
        if seal.status.value not in _CURRENT_SEAL_VALUES:
            raise AuthorizationError("PlanSeal lineage is stale or revoked")
        if executability.status.value not in _CURRENT_EXEC_VALUES:
            raise AuthorizationError("policy executability lineage is no longer bounded")

    if authorization_id in self.schedulability_authorization_bindings:
        binding = self.schedulability_authorization_bindings[authorization_id]
        sched = self.schedulability_certificates[str(binding["schedulability_revision"])]
        coverage = self.policy_coverage_assessments[str(binding["coverage_revision"])]
        _assert_exact_field(
            self, closure, "schedulability_lineage_revision", "SchedulabilityCertificate", sched.certificate_id
        )
        _assert_exact_field(self, closure, "coverage_lineage_revision", "PolicyCoverage", coverage.assessment_id)
        current_job_digest = digest(
            tuple(
                sorted(
                    _current_sidecar(self, "ReactionJob", job_id)
                    for job_id, _ in sched.reaction_job_digests
                )
            )
        )
        current_resource_digest = digest(
            tuple(
                sorted(
                    _current_sidecar(self, "ControlPlaneResource", resource_id)
                    for resource_id, _ in sched.control_resource_digests
                )
            )
        )
        if closure.get("reaction_job_lineage_digest") != current_job_digest:
            raise AuthorizationError("reaction-job authority lineage is stale")
        if closure.get("control_resource_lineage_digest") != current_resource_digest:
            raise AuthorizationError("control-resource authority lineage is stale")


def _apply_closure_to_layer_bindings(self, authorization_id: str, closure: dict[str, str]) -> None:
    if authorization_id in getattr(self, "proof_authorization_bindings", {}):
        for key in ("proof_lineage_revision", "proof_manifest_lineage_revision", "proof_support_lineage_revision"):
            if key in closure:
                self.proof_authorization_bindings[authorization_id][key] = closure[key]
    if authorization_id in getattr(self, "policy_authorization_bindings", {}):
        for key in (
            "decision_epoch_lineage_revision",
            "partition_lineage_revision",
            "frontier_lineage_revision",
            "policy_node_lineage_revision",
            "selection_lineage_revision",
            "sufficiency_lineage_revision",
            "seal_lineage_revision",
            "executability_lineage_revision",
            "decision_epoch_ref",
            "principal_access_revision",
        ):
            if key in closure:
                self.policy_authorization_bindings[authorization_id][key] = closure[key]
    if authorization_id in getattr(self, "schedulability_authorization_bindings", {}):
        for key in (
            "schedulability_lineage_revision",
            "coverage_lineage_revision",
            "reaction_job_lineage_digest",
            "control_resource_lineage_digest",
            "liveness_lineage_revision",
            "stability_lineage_revision",
            "independence_lineage_revision",
        ):
            if key in closure:
                self.schedulability_authorization_bindings[authorization_id][key] = closure[key]


def _restore_state_payload(self, raw: dict[str, Any]) -> None:
    body = {
        "decision_epoch_bindings": {
            str(key): {str(k): str(v) for k, v in dict(value).items()}
            for key, value in dict(raw.get("decision_epoch_bindings", {})).items()
        },
        "authorization_bindings": {
            str(key): {str(k): str(v) for k, v in dict(value).items()}
            for key, value in dict(raw.get("authorization_bindings", {})).items()
        },
    }
    if str(raw.get("canonical_digest", "")) != digest(body):
        raise ReplayError("Wave-7 authority-lineage closure snapshot digest mismatch")

    for epoch_id, binding in body["decision_epoch_bindings"].items():
        if epoch_id not in self.policy_epochs:
            raise ReplayError("authority-lineage snapshot references missing DecisionEpoch")
        for key in (
            "mission_lineage_revision",
            "canonical_state_lineage_revision",
            "strategic_location_lineage_revision",
            "partition_lineage_revision",
            "frontier_lineage_revision",
            "information_regime_lineage_revision",
            "decision_epoch_lineage_revision",
        ):
            revision = binding.get(key)
            if not revision:
                raise ReplayError(f"DecisionEpoch lineage snapshot lacks {key}")
            try:
                self.lineage.get(revision)
            except Exception as exc:
                raise ReplayError("DecisionEpoch lineage snapshot references missing revision") from exc
    self.decision_epoch_lineage_bindings = body["decision_epoch_bindings"]

    restored: dict[str, dict[str, str]] = {}
    for authorization_id, closure in body["authorization_bindings"].items():
        if authorization_id not in self.authorizations:
            raise ReplayError("authority-lineage closure references missing authorization")
        closure_body = {key: value for key, value in closure.items() if key != "closure_digest"}
        if closure.get("closure_digest") != digest(dict(sorted(closure_body.items()))):
            raise ReplayError("authority-lineage closure binding digest mismatch")
        for key, revision in closure.items():
            if key.endswith("_lineage_revision") and revision and key not in {
                "principal_access_revision",
            }:
                try:
                    self.lineage.get(revision)
                except Exception as exc:
                    raise ReplayError(f"authority closure references missing revision: {key}") from exc
        restored[authorization_id] = closure
    self.authority_lineage_closure_bindings = restored
    for authorization_id, closure in restored.items():
        _apply_closure_to_layer_bindings(self, authorization_id, closure)


def _event_sidecar_replay(self, entry) -> None:
    event = entry.event_type
    payload = dict(entry.payload)
    sequence = entry.sequence

    if event in {"region.registered", "state.relocated"}:
        _register_strategic_location_lineage(self, sequence)
        return

    if event in {"proof.semantic_source_registered", "proof.semantic_source_mutated"}:
        source_id = str(payload["source_id"])
        _register_proof_source_lineage(self, source_id, sequence)
        _refresh_proofs_for_source(self, source_id, sequence)
        return
    if event == "proof.profile_refs_registered":
        _refresh_all_proof_authority(self, sequence)
        return
    if event in {"proof.query_domain_created", "proof.query_domain_membership_advanced", "proof.query_domain_member_mutated"}:
        query_id = str(payload["query_domain_id"])
        query = self.query_domains.latest(query_id)
        _register_query_lineage(self, query, sequence)
        _refresh_proofs_for_query(self, query_id, sequence)
        return
    if event == "proof.input_envelope_registered":
        envelope = self.proof_input_envelopes[str(payload["revision_id"])]
        _register_proof_input_lineage(self, envelope, sequence)
        return
    if event == "proof.manifest_captured":
        artifact = str(payload["artifact_revision"])
        _register_manifest_lineage(self, self.proof_manifests[artifact], sequence)
        _refresh_proof_authority_lineage(self, artifact, sequence)
        return
    if event == "proof.support_node_registered":
        _register_support_node_lineage(self, self.support_nodes[str(payload["ref"])], sequence)
        _refresh_all_proof_authority(self, sequence)
        return
    if event == "proof.support_set_registered":
        artifact = str(payload["subject_artifact_revision"])
        _register_support_set_lineage(self, self.support_sets[artifact], sequence)
        _refresh_proof_authority_lineage(self, artifact, sequence)
        return
    if event == "proof.invalidity_causes_set":
        _refresh_proof_authority_lineage(self, str(payload["artifact_revision"]), sequence)
        return
    if event == "proof.authorization_bound":
        _augment_authority_closure(self, str(payload["authorization_id"]))
        return

    if event == "policy.frontier_registered":
        value = self.policy_frontiers[str(payload["revision_id"])]
        _register_policy_sidecar(
            self, family="PolicyObservationFrontier", logical_id=value.frontier_id,
            value=value, provenance="policy:observation-frontier", created_sequence=sequence,
        )
        return
    if event == "policy.partition_registered":
        value = self.policy_partitions[str(payload["revision_id"])]
        _register_policy_sidecar(
            self, family="PolicyInformationPartition", logical_id=value.logical_id,
            value=value, provenance="policy:information-partition", created_sequence=sequence,
        )
        return
    if event == "policy.epoch_registered":
        _register_decision_epoch_lineage(self, self.policy_epochs[str(payload["epoch_id"])], sequence)
        return
    if event == "policy.node_registered":
        value = self.policy_nodes[str(payload["revision_id"])]
        _register_policy_sidecar(
            self, family="PolicyNode", logical_id=value.policy_node_id,
            value=value, provenance="policy:node", created_sequence=sequence,
        )
        return
    if event == "policy.selection_registered":
        value = self.policy_selections[str(payload["record_id"])]
        _register_policy_sidecar(
            self, family="PolicySelection", logical_id=value.record_id,
            value=value, provenance="policy:selection", created_sequence=sequence,
        )
        return
    if event == "policy.sufficiency_registered":
        value = self.policy_sufficiency[str(payload["revision_id"])]
        _register_policy_sidecar(
            self, family="DecisionSufficiency", logical_id=value.certificate_id,
            value=value, provenance="policy:sufficiency", created_sequence=sequence,
        )
        return
    if event == "policy.seal_registered":
        value = self.policy_seals[str(payload["revision_id"])]
        _register_policy_sidecar(
            self, family="PlanSeal", logical_id=value.seal_id,
            value=value, provenance="policy:seal", created_sequence=sequence,
        )
        return
    if event == "policy.executability_registered":
        value = self.policy_executability[str(payload["revision_id"])]
        _register_policy_sidecar(
            self, family="PolicyExecutability", logical_id=value.assessment_id,
            value=value, provenance="policy:executability", created_sequence=sequence,
        )
        return
    if event == "policy.authorization_bound":
        _augment_authority_closure(self, str(payload["authorization_id"]))
        return

    wave6_map = {
        "schedulability.resource_registered": ("ControlPlaneResource", self.control_plane_resources, "revision_id", "resource_id", "schedulability:resource"),
        "schedulability.job_registered": ("ReactionJob", self.reaction_jobs, "revision_id", "reaction_job_id", "schedulability:reaction-job"),
        "schedulability.certificate_registered": ("SchedulabilityCertificate", self.schedulability_certificates, "revision_id", "certificate_id", "schedulability:certificate"),
        "schedulability.coverage_registered": ("PolicyCoverage", self.policy_coverage_assessments, "revision_id", "assessment_id", "schedulability:coverage"),
        "schedulability.independence_registered": ("OptionIndependence", self.option_independence_certificates, "revision_id", "certificate_id", "schedulability:independence"),
        "schedulability.robust_preparedness_registered": ("RobustPreparedness", self.robust_preparedness_assessments, "revision_id", "assessment_id", "schedulability:robust-preparedness"),
        "schedulability.liveness_registered": ("HandoffLiveness", self.handoff_liveness_certificates, "revision_id", "certificate_id", "schedulability:liveness"),
        "schedulability.stability_registered": ("HandoffStability", self.handoff_stability_contracts, "revision_id", "contract_id", "schedulability:stability"),
    }
    if event in wave6_map:
        family, registry, payload_key, logical_attr, provenance = wave6_map[event]
        value = registry[str(payload[payload_key])]
        _register_wave6_sidecar(
            self, family=family, logical_id=getattr(value, logical_attr), value=value,
            provenance=provenance, created_sequence=sequence,
        )
        return
    if event == "schedulability.edge_activation_registered":
        activation = self.edge_activation_assessments[str(payload["canonical_digest"])]
        _register_wave6_sidecar(
            self, family="EdgeActivation", logical_id=activation.contract_digest,
            value=activation, provenance="schedulability:edge-activation", created_sequence=sequence,
        )
        return
    if event == "schedulability.authorization_bound":
        _augment_authority_closure(self, str(payload["authorization_id"]))


def _wrap_method(kernel_cls, name: str, after: Callable) -> None:
    original = getattr(kernel_cls, name)

    def wrapped(self, *args, **kwargs):
        with self._writer_lock:
            value = original(self, *args, **kwargs)
            after(self, value, args, kwargs)
            return value

    setattr(kernel_cls, name, wrapped)


def install_authority_lineage_runtime(kernel_cls) -> None:
    """Close Wave-7 derived authority lineage without creating a second authority source."""
    if getattr(kernel_cls, "_wave7_authority_lineage_installed", False):
        return

    original_init = kernel_cls.__init__
    base_assert = kernel_cls._assert_authorization_lineage_current
    base_dispatch = kernel_cls.dispatch
    base_snapshot_state = kernel_cls.snapshot_state
    base_open = kernel_cls.open

    def __init__(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        _install_state(self)
        _register_strategic_location_lineage(self, 0)

    kernel_cls.__init__ = __init__
    kernel_cls.current_semantic_regime_lineage_digest = _semantic_regime_digest
    kernel_cls._refresh_proof_authority_lineage = _refresh_proof_authority_lineage
    kernel_cls._augment_authority_lineage_closure = _augment_authority_closure
    kernel_cls._replay_authority_lineage_event = _event_sidecar_replay

    _wrap_method(
        kernel_cls,
        "register_region",
        lambda self, _value, _args, _kwargs: _register_strategic_location_lineage(self),
    )
    _wrap_method(
        kernel_cls,
        "_relocate_after_commit",
        lambda self, _value, _args, _kwargs: _register_strategic_location_lineage(self),
    )

    _wrap_method(
        kernel_cls,
        "register_semantic_source",
        lambda self, value, _args, _kwargs: _register_proof_source_lineage(self, value.source_id),
    )
    _wrap_method(
        kernel_cls,
        "mutate_semantic_source",
        lambda self, value, _args, _kwargs: (
            _register_proof_source_lineage(self, value.source_id),
            _refresh_proofs_for_source(self, value.source_id),
        ),
    )
    _wrap_method(
        kernel_cls,
        "register_proof_profile_refs",
        lambda self, _value, _args, _kwargs: _refresh_all_proof_authority(self),
    )
    _wrap_method(
        kernel_cls,
        "create_proof_query_domain",
        lambda self, value, _args, _kwargs: _register_query_lineage(self, value),
    )
    _wrap_method(
        kernel_cls,
        "advance_proof_query_membership",
        lambda self, value, _args, _kwargs: (
            _register_query_lineage(self, value),
            _refresh_proofs_for_query(self, value.query_domain_id),
        ),
    )
    _wrap_method(
        kernel_cls,
        "record_proof_query_member_mutation",
        lambda self, value, _args, _kwargs: (
            _register_query_lineage(self, value),
            _refresh_proofs_for_query(self, value.query_domain_id),
        ),
    )
    _wrap_method(
        kernel_cls,
        "register_proof_input",
        lambda self, value, _args, _kwargs: _register_proof_input_lineage(self, value),
    )
    _wrap_method(
        kernel_cls,
        "capture_proof_manifest",
        lambda self, value, _args, _kwargs: (
            _register_manifest_lineage(self, value),
            _refresh_proof_authority_lineage(self, value.artifact_revision),
        ),
    )
    _wrap_method(
        kernel_cls,
        "register_support_node",
        lambda self, value, _args, _kwargs: (
            _register_support_node_lineage(self, value),
            _refresh_all_proof_authority(self),
        ),
    )
    _wrap_method(
        kernel_cls,
        "register_support_set",
        lambda self, value, _args, _kwargs: (
            _register_support_set_lineage(self, value),
            _refresh_proof_authority_lineage(self, value.subject_artifact_revision),
        ),
    )
    _wrap_method(
        kernel_cls,
        "set_proof_invalidity_causes",
        lambda self, _value, args, _kwargs: _refresh_proof_authority_lineage(self, str(args[0])),
    )

    _wrap_method(
        kernel_cls,
        "register_policy_frontier",
        lambda self, value, _args, _kwargs: _register_policy_sidecar(
            self, family="PolicyObservationFrontier", logical_id=value.frontier_id,
            value=value, provenance="policy:observation-frontier"
        ),
    )
    _wrap_method(
        kernel_cls,
        "register_information_partition",
        lambda self, value, _args, _kwargs: _register_policy_sidecar(
            self, family="PolicyInformationPartition", logical_id=value.logical_id,
            value=value, provenance="policy:information-partition"
        ),
    )
    _wrap_method(
        kernel_cls,
        "register_decision_epoch",
        lambda self, value, _args, _kwargs: _register_decision_epoch_lineage(self, value),
    )
    _wrap_method(
        kernel_cls,
        "register_policy_node",
        lambda self, value, _args, _kwargs: _register_policy_sidecar(
            self, family="PolicyNode", logical_id=value.policy_node_id,
            value=value, provenance="policy:node"
        ),
    )
    _wrap_method(
        kernel_cls,
        "register_selection_record",
        lambda self, value, _args, _kwargs: _register_policy_sidecar(
            self, family="PolicySelection", logical_id=value.record_id,
            value=value, provenance="policy:selection"
        ),
    )
    _wrap_method(
        kernel_cls,
        "register_decision_sufficiency",
        lambda self, value, _args, _kwargs: _register_policy_sidecar(
            self, family="DecisionSufficiency", logical_id=value.certificate_id,
            value=value, provenance="policy:sufficiency"
        ),
    )
    _wrap_method(
        kernel_cls,
        "register_plan_seal",
        lambda self, value, _args, _kwargs: _register_policy_sidecar(
            self, family="PlanSeal", logical_id=value.seal_id,
            value=value, provenance="policy:seal"
        ),
    )
    _wrap_method(
        kernel_cls,
        "register_policy_executability",
        lambda self, value, _args, _kwargs: _register_policy_sidecar(
            self, family="PolicyExecutability", logical_id=value.assessment_id,
            value=value, provenance="policy:executability"
        ),
    )

    wave6_wrappers = (
        ("register_control_plane_resource", "ControlPlaneResource", "resource_id", "schedulability:resource"),
        ("register_reaction_job", "ReactionJob", "reaction_job_id", "schedulability:reaction-job"),
        ("register_schedulability_certificate", "SchedulabilityCertificate", "certificate_id", "schedulability:certificate"),
        ("register_policy_coverage_assessment", "PolicyCoverage", "assessment_id", "schedulability:coverage"),
        ("register_option_independence_certificate", "OptionIndependence", "certificate_id", "schedulability:independence"),
        ("register_robust_preparedness_assessment", "RobustPreparedness", "assessment_id", "schedulability:robust-preparedness"),
        ("register_handoff_liveness_certificate", "HandoffLiveness", "certificate_id", "schedulability:liveness"),
        ("register_handoff_stability_contract", "HandoffStability", "contract_id", "schedulability:stability"),
    )
    for method_name, family, logical_attr, provenance in wave6_wrappers:
        _wrap_method(
            kernel_cls,
            method_name,
            lambda self, value, _args, _kwargs, family=family, logical_attr=logical_attr, provenance=provenance: _register_wave6_sidecar(
                self, family=family, logical_id=getattr(value, logical_attr), value=value, provenance=provenance
            ),
        )
    _wrap_method(
        kernel_cls,
        "register_edge_activation_assessment",
        lambda self, value, _args, _kwargs: _register_wave6_sidecar(
            self, family="EdgeActivation", logical_id=value.contract_digest,
            value=value, provenance="schedulability:edge-activation"
        ),
    )

    for method_name in ("authorize_proof_carrying", "authorize_sealed_policy", "authorize_schedulable_policy"):
        original = getattr(kernel_cls, method_name)

        def wrapped_authorize(self, *args, __original=original, **kwargs):
            with self._writer_lock:
                authorization = __original(self, *args, **kwargs)
                _augment_authority_closure(self, authorization.id)
                return authorization

        setattr(kernel_cls, method_name, wrapped_authorize)

    def assert_authorization_lineage_current(self, authorization_id: str) -> None:
        _assert_authority_closure_current(self, authorization_id, base_assert)

    def dispatch(self, authorization_id, *args, **kwargs):
        with self._writer_lock:
            assert_authorization_lineage_current(self, authorization_id)
            return base_dispatch(self, authorization_id, *args, **kwargs)

    kernel_cls._assert_authorization_lineage_current = assert_authorization_lineage_current
    kernel_cls.dispatch = dispatch

    def snapshot_state(self):
        state = dict(base_snapshot_state(self))
        if str(state.get("snapshot_schema", "")) == LINEAGE_SNAPSHOT_SCHEMA:
            lineage = dict(state.get("lineage") or {})
            lineage["authority_closure"] = _state_payload(self)
            state["lineage"] = lineage
        return state

    def save_snapshot(self):
        with self._writer_lock:
            state = snapshot_state(self)
            self.snapshots.save(state)
            self._record(
                "snapshot.saved",
                {
                    "snapshot_schema": str(state.get("snapshot_schema", LINEAGE_SNAPSHOT_SCHEMA)),
                    "snapshot_digest": digest(state),
                    "bound_journal_head": state["journal_head"],
                },
            )
            return state

    kernel_cls.snapshot_state = snapshot_state
    kernel_cls.save_snapshot = save_snapshot

    # Replay owner events first, then deterministically rebuild their Wave-7
    # sidecars while the exact event-time mission/regime/plan state is current.
    from . import lineage_snapshot as lineage_snapshot_module

    replay_entry = lineage_snapshot_module._replay_entry

    def replay_with_authority_lineage(kernel, entry):
        replay_entry(kernel, entry)
        if hasattr(kernel, "_replay_authority_lineage_event"):
            kernel._replay_authority_lineage_event(entry)

    lineage_snapshot_module._replay_entry = replay_with_authority_lineage

    @classmethod
    def open_with_authority_lineage(cls, root: Path):
        root = Path(root)
        state = SnapshotStore(root / "snapshot.json").load()
        kernel = base_open(root)
        if str(state.get("snapshot_schema", "")) != LINEAGE_SNAPSHOT_SCHEMA:
            return kernel
        raw_lineage = state.get("lineage")
        raw_authority = raw_lineage.get("authority_closure") if isinstance(raw_lineage, dict) else None

        # Suffix replay may already have produced newer closure entries. Preserve
        # those while restoring the snapshot-prefix authority history.
        suffix_epochs = dict(kernel.decision_epoch_lineage_bindings)
        suffix_authority = dict(kernel.authority_lineage_closure_bindings)
        if isinstance(raw_authority, dict):
            _restore_state_payload(kernel, raw_authority)
        else:
            # v7 snapshots written before Task 7 remain readable, but derived
            # authority is explicitly conservative rather than silently rebound.
            for authorization_id in set(getattr(kernel, "proof_authorization_bindings", {})).union(
                getattr(kernel, "policy_authorization_bindings", {}),
                getattr(kernel, "schedulability_authorization_bindings", {}),
            ):
                kernel.migration_recheck_required_authorizations.add(authorization_id)

        kernel.decision_epoch_lineage_bindings.update(suffix_epochs)
        kernel.authority_lineage_closure_bindings.update(suffix_authority)
        for authorization_id, closure in kernel.authority_lineage_closure_bindings.items():
            _apply_closure_to_layer_bindings(kernel, authorization_id, closure)
        return kernel

    kernel_cls.open = open_with_authority_lineage
    kernel_cls._wave7_authority_lineage_installed = True
