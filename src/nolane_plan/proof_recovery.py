from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from .hashing import digest
from .mission import MissionContract, MissionLedger
from .persistence import HashJournal, SnapshotStore
from .proof_dependencies import DependencyFreshnessVector, ProofDependencyManifestRevision
from .proof_inputs import (
    DependencyCaptureAssurance,
    ExternalReadPolicy,
    ProofInputEnvelopeRevision,
)
from .query_domain import QueryDomainLedger, QueryDomainRevision
from .resume import SNAPSHOT_SCHEMA as BASE_SNAPSHOT_SCHEMA
from .resume import _find_snapshot_prefix, _restore_state
from .semantic_barrier import (
    MutationImpactProfileRevision,
    SemanticSourceRevision,
)
from .support import (
    InvalidityCause,
    SupportAlternativeSetRevision,
    SupportClause,
    SupportNode,
)
from .trust_recovery import (
    TRUST_SNAPSHOT_SCHEMA,
    _replay_entry as _replay_trust_entry,
    _restore_trust_state,
)
from .types import ReplayError


PROOF_SNAPSHOT_SCHEMA = "nolane-plan-runtime-snapshot-v4"


def _query_doc(revision: QueryDomainRevision) -> dict[str, Any]:
    return {
        "query_domain_id": revision.query_domain_id,
        "revision_id": revision.revision_id,
        "scope_revision": revision.scope_revision,
        "membership_generation": revision.membership_generation,
        "result_sensitivity_generation": revision.result_sensitivity_generation,
        "index_schema_revision": revision.index_schema_revision,
        "completeness_contract": revision.completeness_contract,
        "filter_predicate_revision": revision.filter_predicate_revision,
        "alias_equivalence_regime": revision.alias_equivalence_regime,
        "visibility_permission_regime": revision.visibility_permission_regime,
        "mutation_impact_profile_revision": revision.mutation_impact_profile_revision,
        "query_snapshot_id": revision.query_snapshot_id,
        "snapshot_complete": revision.snapshot_complete,
        "opaque": revision.opaque,
        "visibility_assurance": revision.visibility_assurance,
        "created_sequence": revision.created_sequence,
        "canonical_digest": revision.canonical_digest,
    }


def _query_from_doc(row: dict[str, Any]) -> QueryDomainRevision:
    body = {
        "query_domain_id": str(row["query_domain_id"]),
        "revision_id": str(row["revision_id"]),
        "scope_revision": str(row["scope_revision"]),
        "membership_generation": int(row["membership_generation"]),
        "result_sensitivity_generation": int(row["result_sensitivity_generation"]),
        "index_schema_revision": str(row["index_schema_revision"]),
        "completeness_contract": str(row["completeness_contract"]),
        "filter_predicate_revision": str(row["filter_predicate_revision"]),
        "alias_equivalence_regime": str(row["alias_equivalence_regime"]),
        "visibility_permission_regime": str(row["visibility_permission_regime"]),
        "mutation_impact_profile_revision": str(row["mutation_impact_profile_revision"]),
        "query_snapshot_id": str(row.get("query_snapshot_id", "")),
        "snapshot_complete": bool(row["snapshot_complete"]),
        "opaque": bool(row["opaque"]),
        "visibility_assurance": float(row["visibility_assurance"]),
        "created_sequence": int(row["created_sequence"]),
    }
    recorded = str(row["canonical_digest"])
    if digest(body) != recorded:
        raise ReplayError("query-domain canonical digest mismatch")
    return QueryDomainRevision(**body, canonical_digest=recorded)


def _envelope_doc(envelope: ProofInputEnvelopeRevision) -> dict[str, Any]:
    return {
        "input_envelope_id": envelope.input_envelope_id,
        "revision_id": envelope.revision_id,
        "procedure_kind": envelope.procedure_kind,
        "procedure_capability_revision": envelope.procedure_capability_revision,
        "subject_revision_refs": list(envelope.subject_revision_refs),
        "explicit_input_revision_refs": list(envelope.explicit_input_revision_refs),
        "query_domain_revision_refs": list(envelope.query_domain_revision_refs),
        "collection_membership_revision_refs": list(envelope.collection_membership_revision_refs),
        "semantic_profile_refs": list(envelope.semantic_profile_refs),
        "assumption_basis_refs": list(envelope.assumption_basis_refs),
        "trusted_axiom_model_refs": list(envelope.trusted_axiom_model_refs),
        "canonical_unit_numeric_profile_refs": list(envelope.canonical_unit_numeric_profile_refs),
        "execution_environment_profile_refs": list(envelope.execution_environment_profile_refs),
        "external_read_policy": envelope.external_read_policy.value,
        "captured_external_evidence_refs": list(envelope.captured_external_evidence_refs),
        "resource_budget_profile_refs": list(envelope.resource_budget_profile_refs),
        "created_from_decision_cut": envelope.created_from_decision_cut,
        "capture_assurance": envelope.capture_assurance.value,
        "capture_mechanism_ref": envelope.capture_mechanism_ref,
        "canonical_input_digest": envelope.canonical_input_digest,
    }


def _envelope_from_doc(row: dict[str, Any]) -> ProofInputEnvelopeRevision:
    envelope = ProofInputEnvelopeRevision.create(
        input_envelope_id=str(row["input_envelope_id"]),
        revision_id=str(row["revision_id"]),
        procedure_kind=str(row["procedure_kind"]),
        procedure_capability_revision=str(row["procedure_capability_revision"]),
        subject_revision_refs=tuple(row.get("subject_revision_refs", ())),
        explicit_input_revision_refs=tuple(row.get("explicit_input_revision_refs", ())),
        query_domain_revision_refs=tuple(row.get("query_domain_revision_refs", ())),
        collection_membership_revision_refs=tuple(row.get("collection_membership_revision_refs", ())),
        semantic_profile_refs=tuple(row.get("semantic_profile_refs", ())),
        assumption_basis_refs=tuple(row.get("assumption_basis_refs", ())),
        trusted_axiom_model_refs=tuple(row.get("trusted_axiom_model_refs", ())),
        canonical_unit_numeric_profile_refs=tuple(row.get("canonical_unit_numeric_profile_refs", ())),
        execution_environment_profile_refs=tuple(row.get("execution_environment_profile_refs", ())),
        external_read_policy=ExternalReadPolicy(str(row["external_read_policy"])),
        captured_external_evidence_refs=tuple(row.get("captured_external_evidence_refs", ())),
        resource_budget_profile_refs=tuple(row.get("resource_budget_profile_refs", ())),
        created_from_decision_cut=str(row["created_from_decision_cut"]),
        capture_assurance=DependencyCaptureAssurance(str(row["capture_assurance"])),
        capture_mechanism_ref=row.get("capture_mechanism_ref"),
    )
    if envelope.canonical_input_digest != str(row["canonical_input_digest"]):
        raise ReplayError("proof input envelope canonical digest mismatch")
    return envelope


def _freshness_doc(vector: DependencyFreshnessVector) -> dict[str, Any]:
    return {
        "artifact_revision": vector.artifact_revision,
        "exact_dependency_revisions": [list(pair) for pair in vector.exact_dependency_revisions],
        "dependency_domain_generation_pairs": [list(pair) for pair in vector.dependency_domain_generation_pairs],
        "query_domain_revision_digests": [list(pair) for pair in vector.query_domain_revision_digests],
        "trust_profile_capability_revision_refs": list(vector.trust_profile_capability_revision_refs),
        "evaluated_at_cut": vector.evaluated_at_cut,
        "capture_assurance": vector.capture_assurance.value,
        "canonical_digest": vector.canonical_digest,
    }


def _freshness_from_doc(row: dict[str, Any]) -> DependencyFreshnessVector:
    exact = tuple(tuple((str(pair[0]), str(pair[1]))) for pair in row.get("exact_dependency_revisions", ()))
    generations = tuple((str(pair[0]), int(pair[1])) for pair in row.get("dependency_domain_generation_pairs", ()))
    query_digests = tuple(tuple((str(pair[0]), str(pair[1]))) for pair in row.get("query_domain_revision_digests", ()))
    trust_refs = tuple(str(value) for value in row.get("trust_profile_capability_revision_refs", ()))
    assurance = DependencyCaptureAssurance(str(row["capture_assurance"]))
    body = {
        "artifact_revision": str(row["artifact_revision"]),
        "exact_dependency_revisions": exact,
        "dependency_domain_generation_pairs": generations,
        "query_domain_revision_digests": query_digests,
        "trust_profile_capability_revision_refs": trust_refs,
        "evaluated_at_cut": str(row["evaluated_at_cut"]),
        "capture_assurance": assurance.value,
    }
    recorded = str(row["canonical_digest"])
    if digest(body) != recorded:
        raise ReplayError("proof freshness-vector canonical digest mismatch")
    return DependencyFreshnessVector(
        artifact_revision=body["artifact_revision"],
        exact_dependency_revisions=exact,
        dependency_domain_generation_pairs=generations,
        query_domain_revision_digests=query_digests,
        trust_profile_capability_revision_refs=trust_refs,
        evaluated_at_cut=body["evaluated_at_cut"],
        capture_assurance=assurance,
        canonical_digest=recorded,
    )


def _manifest_doc(manifest: ProofDependencyManifestRevision) -> dict[str, Any]:
    return {
        "manifest_id": manifest.manifest_id,
        "revision_id": manifest.revision_id,
        "artifact_revision": manifest.artifact_revision,
        "proof_obligation_revision": manifest.proof_obligation_revision,
        "producer_capability_revision": manifest.producer_capability_revision,
        "input_envelope_revision": manifest.input_envelope_revision,
        "input_envelope_digest": manifest.input_envelope_digest,
        "capture_assurance": manifest.capture_assurance.value,
        "positive_revision_dependencies": [list(pair) for pair in manifest.positive_revision_dependencies],
        "query_domain_revisions": [_query_doc(query) for query in manifest.query_domain_revisions],
        "semantic_profile_dependencies": list(manifest.semantic_profile_dependencies),
        "trust_checker_normalizer_dependencies": list(manifest.trust_checker_normalizer_dependencies),
        "assumption_basis_dependencies": list(manifest.assumption_basis_dependencies),
        "execution_semantic_profile_dependencies": list(manifest.execution_semantic_profile_dependencies),
        "captured_external_evidence_refs": list(manifest.captured_external_evidence_refs),
        "capture_gaps": list(manifest.capture_gaps),
        "created_sequence": manifest.created_sequence,
        "evaluated_at_cut": manifest.evaluated_at_cut,
        "freshness_vector": _freshness_doc(manifest.freshness_vector),
        "canonical_digest": manifest.canonical_digest,
    }


def _manifest_from_doc(row: dict[str, Any]) -> ProofDependencyManifestRevision:
    queries = tuple(_query_from_doc(dict(query)) for query in row.get("query_domain_revisions", ()))
    vector = _freshness_from_doc(dict(row["freshness_vector"]))
    exact = tuple((str(pair[0]), str(pair[1])) for pair in row.get("positive_revision_dependencies", ()))
    assurance = DependencyCaptureAssurance(str(row["capture_assurance"]))
    if vector.artifact_revision != str(row["artifact_revision"]):
        raise ReplayError("manifest/freshness artifact revision mismatch")
    if vector.capture_assurance != assurance:
        raise ReplayError("manifest/freshness capture assurance mismatch")
    expected_query_digests = tuple((query.query_domain_id, query.canonical_digest) for query in queries)
    if vector.query_domain_revision_digests != expected_query_digests:
        raise ReplayError("manifest/freshness query-domain binding mismatch")
    if vector.exact_dependency_revisions != exact:
        raise ReplayError("manifest/freshness exact revision binding mismatch")

    semantic = tuple(str(value) for value in row.get("semantic_profile_dependencies", ()))
    trust = tuple(str(value) for value in row.get("trust_checker_normalizer_dependencies", ()))
    assumptions = tuple(str(value) for value in row.get("assumption_basis_dependencies", ()))
    execution = tuple(str(value) for value in row.get("execution_semantic_profile_dependencies", ()))
    external = tuple(str(value) for value in row.get("captured_external_evidence_refs", ()))
    gaps = tuple(str(value) for value in row.get("capture_gaps", ()))
    body = {
        "manifest_id": str(row["manifest_id"]),
        "revision_id": str(row["revision_id"]),
        "artifact_revision": str(row["artifact_revision"]),
        "proof_obligation_revision": str(row["proof_obligation_revision"]),
        "producer_capability_revision": str(row["producer_capability_revision"]),
        "input_envelope_revision": str(row["input_envelope_revision"]),
        "input_envelope_digest": str(row["input_envelope_digest"]),
        "capture_assurance": assurance.value,
        "positive_revision_dependencies": exact,
        "query_domain_revision_digests": expected_query_digests,
        "semantic_profile_dependencies": semantic,
        "trust_checker_normalizer_dependencies": trust,
        "assumption_basis_dependencies": assumptions,
        "execution_semantic_profile_dependencies": execution,
        "captured_external_evidence_refs": external,
        "capture_gaps": gaps,
        "created_sequence": int(row["created_sequence"]),
        "evaluated_at_cut": str(row["evaluated_at_cut"]),
        "freshness_vector_digest": vector.canonical_digest,
    }
    recorded = str(row["canonical_digest"])
    if digest(body) != recorded:
        raise ReplayError("proof dependency manifest canonical digest mismatch")
    return ProofDependencyManifestRevision(
        manifest_id=body["manifest_id"],
        revision_id=body["revision_id"],
        artifact_revision=body["artifact_revision"],
        proof_obligation_revision=body["proof_obligation_revision"],
        producer_capability_revision=body["producer_capability_revision"],
        input_envelope_revision=body["input_envelope_revision"],
        input_envelope_digest=body["input_envelope_digest"],
        capture_assurance=assurance,
        positive_revision_dependencies=exact,
        query_domain_revisions=queries,
        semantic_profile_dependencies=semantic,
        trust_checker_normalizer_dependencies=trust,
        assumption_basis_dependencies=assumptions,
        execution_semantic_profile_dependencies=execution,
        captured_external_evidence_refs=external,
        capture_gaps=gaps,
        created_sequence=body["created_sequence"],
        evaluated_at_cut=body["evaluated_at_cut"],
        freshness_vector=vector,
        canonical_digest=recorded,
    )


def _support_node_doc(node: SupportNode) -> dict[str, Any]:
    return {
        "ref": node.ref,
        "current": node.current,
        "direct_grounding_roots": sorted(node.direct_grounding_roots),
        "support_refs": list(node.support_refs),
        "scope": node.scope,
        "assumption_basis": sorted(node.assumption_basis),
        "proof_kind": node.proof_kind,
        "validity_regime": node.validity_regime,
        "context_tags": sorted(node.context_tags),
    }


def _support_node_from_doc(row: dict[str, Any]) -> SupportNode:
    return SupportNode(
        ref=str(row["ref"]),
        current=bool(row["current"]),
        direct_grounding_roots=frozenset(str(value) for value in row.get("direct_grounding_roots", ())),
        support_refs=tuple(str(value) for value in row.get("support_refs", ())),
        scope=str(row["scope"]),
        assumption_basis=frozenset(str(value) for value in row.get("assumption_basis", ())),
        proof_kind=str(row["proof_kind"]),
        validity_regime=str(row["validity_regime"]),
        context_tags=frozenset(str(value) for value in row.get("context_tags", ())),
    )


def _support_set_doc(support_set: SupportAlternativeSetRevision) -> dict[str, Any]:
    return {
        "support_set_id": support_set.support_set_id,
        "revision_id": support_set.revision_id,
        "subject_artifact_revision": support_set.subject_artifact_revision,
        "clauses": [
            {
                "clause_id": clause.clause_id,
                "required_support_refs": list(clause.required_support_refs),
                "scope": clause.scope,
                "assumption_basis": sorted(clause.assumption_basis),
                "proof_kind": clause.proof_kind,
                "grounding_root_requirements": sorted(clause.grounding_root_requirements),
                "validity_regime": clause.validity_regime,
                "context_tags": sorted(clause.context_tags),
                "minimum_independent_roots": clause.minimum_independent_roots,
            }
            for clause in support_set.clauses
        ],
        "scope": support_set.scope,
        "assumption_context_rules": list(support_set.assumption_context_rules),
        "proof_kind": support_set.proof_kind,
        "grounding_policy": support_set.grounding_policy,
        "support_evaluation_profile": support_set.support_evaluation_profile,
        "created_sequence": support_set.created_sequence,
        "canonical_digest": support_set.canonical_digest,
    }


def _support_set_from_doc(row: dict[str, Any]) -> SupportAlternativeSetRevision:
    clauses = tuple(
        SupportClause(
            clause_id=str(clause["clause_id"]),
            required_support_refs=tuple(str(value) for value in clause.get("required_support_refs", ())),
            scope=str(clause["scope"]),
            assumption_basis=frozenset(str(value) for value in clause.get("assumption_basis", ())),
            proof_kind=str(clause["proof_kind"]),
            grounding_root_requirements=frozenset(str(value) for value in clause.get("grounding_root_requirements", ())),
            validity_regime=str(clause["validity_regime"]),
            context_tags=frozenset(str(value) for value in clause.get("context_tags", ())),
            minimum_independent_roots=int(clause.get("minimum_independent_roots", 1)),
        )
        for clause in row.get("clauses", ())
    )
    value = SupportAlternativeSetRevision.create(
        support_set_id=str(row["support_set_id"]),
        revision_id=str(row["revision_id"]),
        subject_artifact_revision=str(row["subject_artifact_revision"]),
        clauses=clauses,
        scope=str(row["scope"]),
        assumption_context_rules=tuple(row.get("assumption_context_rules", ())),
        proof_kind=str(row["proof_kind"]),
        grounding_policy=str(row["grounding_policy"]),
        support_evaluation_profile=str(row["support_evaluation_profile"]),
        created_sequence=int(row["created_sequence"]),
    )
    if value.canonical_digest != str(row["canonical_digest"]):
        raise ReplayError("support alternative-set canonical digest mismatch")
    return value


def _proof_state(self) -> dict[str, Any]:
    return {
        "semantic_barrier_sequence": self.semantic_barrier._sequence,
        "semantic_sources": [
            {
                "source_id": source.source_id,
                "revision_id": source.revision_id,
                "value": source.value,
                "linearization_sequence": source.linearization_sequence,
                "dependency_domains": list(self.proof_source_domains.get(source.source_id, ())),
            }
            for source in sorted(self.semantic_barrier._sources.values(), key=lambda item: item.source_id)
        ],
        "proof_profile_refs": sorted(self.proof_profile_refs),
        "proof_exact_revisions": dict(sorted(self.proof_exact_revisions.items())),
        "proof_source_domains": {
            key: list(value) for key, value in sorted(self.proof_source_domains.items())
        },
        "query_domains": [
            {
                "query_domain_id": query_id,
                "history": [_query_doc(revision) for revision in history],
            }
            for query_id, history in sorted(self.query_domains._history.items())
        ],
        "input_envelopes": [
            _envelope_doc(value)
            for value in sorted(self.proof_input_envelopes.values(), key=lambda item: item.revision_id)
        ],
        "manifests": [
            _manifest_doc(value)
            for value in sorted(self.proof_manifests.values(), key=lambda item: item.artifact_revision)
        ],
        "support_nodes": [
            _support_node_doc(value)
            for value in sorted(self.support_nodes.values(), key=lambda item: item.ref)
        ],
        "support_sets": [
            _support_set_doc(value)
            for value in sorted(self.support_sets.values(), key=lambda item: item.subject_artifact_revision)
        ],
        "invalidity_causes": {
            artifact: [asdict(cause) for cause in causes]
            for artifact, causes in sorted(self.proof_invalidity_causes.items())
        },
        "authorization_bindings": {
            key: dict(value) for key, value in sorted(self.proof_authorization_bindings.items())
        },
    }


def _snapshot_state(self, base_snapshot_state) -> dict[str, Any]:
    state = dict(base_snapshot_state(self))
    state["snapshot_schema"] = PROOF_SNAPSHOT_SCHEMA
    state["proof"] = _proof_state(self)
    return state


def _restore_query_domains(kernel, rows: list[dict[str, Any]]) -> None:
    ledger = QueryDomainLedger()
    for domain_row in rows:
        query_id = str(domain_row["query_domain_id"])
        history = []
        for index, revision_row in enumerate(domain_row.get("history", ()), start=1):
            revision = _query_from_doc(dict(revision_row))
            if revision.query_domain_id != query_id:
                raise ReplayError("query-domain history contains a foreign query id")
            if revision.revision_id != f"{query_id}@{index}":
                raise ReplayError("query-domain revision history is non-contiguous")
            history.append(revision)
        if not history:
            raise ReplayError("query-domain history cannot be empty")
        if query_id in ledger._history:
            raise ReplayError("duplicate query-domain history")
        ledger._history[query_id] = history
    kernel.query_domains = ledger


def _restore_proof_state(kernel, proof: dict[str, Any]) -> None:
    kernel.proof_input_envelopes = {}
    kernel.query_domains = QueryDomainLedger()
    kernel.proof_manifests = {}
    kernel.support_sets = {}
    kernel.support_nodes = {}
    kernel.proof_invalidity_causes = {}
    kernel.proof_authority_assessments = {}
    kernel.proof_profile_refs = set(str(value) for value in proof.get("proof_profile_refs", ()))
    kernel.proof_exact_revisions = {
        str(key): str(value) for key, value in proof.get("proof_exact_revisions", {}).items()
    }
    kernel.proof_source_domains = {
        str(key): tuple(str(value) for value in values)
        for key, values in proof.get("proof_source_domains", {}).items()
    }
    kernel.proof_authorization_bindings = {}

    sources: dict[str, SemanticSourceRevision] = {}
    max_sequence = 0
    for row in proof.get("semantic_sources", ()):
        source_id = str(row["source_id"])
        if source_id in sources:
            raise ReplayError("duplicate semantic source in proof snapshot")
        sequence = int(row["linearization_sequence"])
        if sequence <= 0:
            raise ReplayError("semantic source has invalid linearization sequence")
        source = SemanticSourceRevision(
            source_id=source_id,
            revision_id=str(row["revision_id"]),
            value=row.get("value"),
            linearization_sequence=sequence,
        )
        sources[source_id] = source
        max_sequence = max(max_sequence, sequence)
        payload_domains = tuple(str(value) for value in row.get("dependency_domains", ()))
        stored_domains = kernel.proof_source_domains.get(source_id, payload_domains)
        if stored_domains != payload_domains:
            raise ReplayError("semantic source dependency-domain mismatch")
        kernel.proof_source_domains[source_id] = payload_domains
        if kernel.proof_exact_revisions.get(source_id) != source.revision_id:
            raise ReplayError("semantic source current revision disagrees with exact proof revision map")

    barrier_sequence = int(proof.get("semantic_barrier_sequence", 0))
    if barrier_sequence < max_sequence:
        raise ReplayError("semantic barrier sequence precedes a restored source")
    kernel.semantic_barrier._sources = sources
    kernel.semantic_barrier._sequence = barrier_sequence

    _restore_query_domains(kernel, list(proof.get("query_domains", ())))

    for row in proof.get("input_envelopes", ()):
        envelope = _envelope_from_doc(dict(row))
        if envelope.revision_id in kernel.proof_input_envelopes:
            raise ReplayError("duplicate proof input envelope revision")
        kernel.proof_input_envelopes[envelope.revision_id] = envelope

    for row in proof.get("manifests", ()):
        manifest = _manifest_from_doc(dict(row))
        if manifest.artifact_revision in kernel.proof_manifests:
            raise ReplayError("duplicate proof dependency manifest")
        envelope = kernel.proof_input_envelopes.get(manifest.input_envelope_revision)
        if envelope is None or envelope.canonical_input_digest != manifest.input_envelope_digest:
            raise ReplayError("proof manifest references missing or mismatched input envelope")
        for bound_query in manifest.query_domain_revisions:
            history = kernel.query_domains._history.get(bound_query.query_domain_id, ())
            if not any(candidate.canonical_digest == bound_query.canonical_digest for candidate in history):
                raise ReplayError("proof manifest references a missing query-domain revision")
        kernel.proof_manifests[manifest.artifact_revision] = manifest

    for row in proof.get("support_nodes", ()):
        node = _support_node_from_doc(dict(row))
        if node.ref in kernel.support_nodes:
            raise ReplayError("duplicate support node")
        kernel.support_nodes[node.ref] = node

    for row in proof.get("support_sets", ()):
        support_set = _support_set_from_doc(dict(row))
        artifact = support_set.subject_artifact_revision
        if artifact not in kernel.proof_manifests:
            raise ReplayError("support set references a missing proof manifest")
        if artifact in kernel.support_sets:
            raise ReplayError("duplicate support set")
        kernel.support_sets[artifact] = support_set

    kernel.proof_invalidity_causes = {
        str(artifact): tuple(
            InvalidityCause(
                cause_id=str(row["cause_id"]),
                code=str(row["code"]),
                active=bool(row["active"]),
                blocking=bool(row["blocking"]),
                detail=row.get("detail"),
            )
            for row in rows
        )
        for artifact, rows in proof.get("invalidity_causes", {}).items()
    }
    for artifact in kernel.proof_invalidity_causes:
        if artifact not in kernel.proof_manifests:
            raise ReplayError("invalidity cause references a missing proof manifest")

    for authorization_id, binding in proof.get("authorization_bindings", {}).items():
        authorization_id = str(authorization_id)
        if authorization_id not in kernel.authorizations:
            raise ReplayError("proof authorization binding references a missing authorization")
        artifact = str(binding["proof_artifact_revision"])
        manifest = kernel.proof_manifests.get(artifact)
        if manifest is None or manifest.canonical_digest != str(binding["manifest_digest"]):
            raise ReplayError("proof authorization binding references stale or missing manifest lineage")
        kernel.proof_authorization_bindings[authorization_id] = {
            "proof_artifact_revision": artifact,
            "manifest_digest": str(binding["manifest_digest"]),
            "support_assessment_digest": str(binding["support_assessment_digest"]),
        }


def _assert_query_matches_payload(value: QueryDomainRevision, payload: dict[str, Any]) -> None:
    expected = _query_from_doc(dict(payload))
    if value != expected:
        raise ReplayError("query-domain replay does not reproduce canonical revision")


def _replay_semantic_source_registered(kernel, payload: dict[str, Any]) -> None:
    source_id = str(payload["source_id"])
    domains = tuple(str(value) for value in payload.get("dependency_domains", ()))
    for domain in domains:
        kernel.freshness.ensure(domain)
    source = kernel.semantic_barrier.register_source(
        source_id,
        revision_id=str(payload["revision_id"]),
        value=payload.get("value"),
    )
    if source.linearization_sequence != int(payload["linearization_sequence"]):
        raise ReplayError("semantic source registration sequence mismatch")
    kernel.proof_exact_revisions[source_id] = source.revision_id
    kernel.proof_source_domains[source_id] = domains


def _replay_semantic_source_mutated(kernel, payload: dict[str, Any]) -> None:
    profile_row = dict(payload["impact_profile"])
    profile = MutationImpactProfileRevision(
        revision_id=str(profile_row["revision_id"]),
        source_id=str(profile_row["source_id"]),
        affected_domains=tuple(str(value) for value in profile_row.get("affected_domains", ())),
        coverage_complete=bool(profile_row["coverage_complete"]),
        conservative_fallback_domains=tuple(
            str(value) for value in profile_row.get("conservative_fallback_domains", ())
        ),
    )
    receipt = kernel.semantic_barrier.mutate(
        str(payload["source_id"]),
        new_revision_id=str(payload["new_revision_id"]),
        new_value=payload.get("new_value"),
        impact_profile=profile,
    )
    if receipt.previous_revision_id != str(payload["previous_revision_id"]):
        raise ReplayError("semantic mutation previous revision mismatch")
    if tuple(receipt.affected_domains) != tuple(str(value) for value in payload.get("affected_domains", ())):
        raise ReplayError("semantic mutation affected-domain mismatch")
    if tuple(receipt.before_generations) != tuple(
        (str(pair[0]), int(pair[1])) for pair in payload.get("before_generations", ())
    ):
        raise ReplayError("semantic mutation pre-generation mismatch")
    if tuple(receipt.after_generations) != tuple(
        (str(pair[0]), int(pair[1])) for pair in payload.get("after_generations", ())
    ):
        raise ReplayError("semantic mutation post-generation mismatch")
    if receipt.linearization_sequence != int(payload["linearization_sequence"]):
        raise ReplayError("semantic mutation linearization sequence mismatch")
    kernel.proof_exact_revisions[str(payload["source_id"])] = receipt.new_revision_id


def _replay_query_created(kernel, payload: dict[str, Any]) -> None:
    expected = _query_from_doc(dict(payload))
    value = kernel.query_domains.create(
        query_domain_id=expected.query_domain_id,
        scope_revision=expected.scope_revision,
        index_schema_revision=expected.index_schema_revision,
        completeness_contract=expected.completeness_contract,
        filter_predicate_revision=expected.filter_predicate_revision,
        alias_equivalence_regime=expected.alias_equivalence_regime,
        visibility_permission_regime=expected.visibility_permission_regime,
        mutation_impact_profile_revision=expected.mutation_impact_profile_revision,
        query_snapshot_id=expected.query_snapshot_id,
        snapshot_complete=expected.snapshot_complete,
        opaque=expected.opaque,
        visibility_assurance=expected.visibility_assurance,
        created_sequence=expected.created_sequence,
    )
    if value != expected:
        raise ReplayError("query-domain creation replay mismatch")


def _replay_query_membership(kernel, payload: dict[str, Any]) -> None:
    expected = _query_from_doc(dict(payload))
    value = kernel.query_domains.advance_membership(
        expected.query_domain_id,
        query_snapshot_id=expected.query_snapshot_id,
        created_sequence=expected.created_sequence,
    )
    if value != expected:
        raise ReplayError("query-domain membership replay mismatch")


def _replay_query_member_mutated(kernel, payload: dict[str, Any]) -> None:
    expected = _query_from_doc(dict(payload))
    previous = kernel.query_domains.latest(expected.query_domain_id)
    if expected.result_sensitivity_generation != previous.result_sensitivity_generation + 1:
        raise ReplayError("query member-mutation generation did not advance exactly once")
    value = kernel.query_domains.record_member_mutation(
        expected.query_domain_id,
        predicate_result_may_change=True,
        query_snapshot_id=expected.query_snapshot_id,
        created_sequence=expected.created_sequence,
    )
    if value != expected:
        raise ReplayError("query-domain member-mutation replay mismatch")


def _manifest_from_event(kernel, payload: dict[str, Any]) -> ProofDependencyManifestRevision:
    envelope_revision = str(payload["input_envelope_revision"])
    envelope = kernel.proof_input_envelopes.get(envelope_revision)
    if envelope is None:
        raise ReplayError("manifest replay references a missing input envelope")
    if envelope.canonical_input_digest != str(payload["input_envelope_digest"]):
        raise ReplayError("manifest replay input envelope digest mismatch")
    query_digest_pairs = tuple(
        (str(pair[0]), str(pair[1])) for pair in payload.get("query_domain_revision_digests", ())
    )
    queries: list[QueryDomainRevision] = []
    for query_id, query_digest in query_digest_pairs:
        history = kernel.query_domains._history.get(query_id, ())
        match = next((value for value in history if value.canonical_digest == query_digest), None)
        if match is None:
            raise ReplayError("manifest replay references a missing query-domain revision")
        queries.append(match)
    exact = tuple((str(pair[0]), str(pair[1])) for pair in payload.get("positive_revision_dependencies", ()))
    semantic = tuple(str(value) for value in payload.get("semantic_profile_dependencies", ()))
    trust = tuple(str(value) for value in payload.get("trust_checker_normalizer_dependencies", ()))
    assumptions = tuple(str(value) for value in payload.get("assumption_basis_dependencies", ()))
    execution = tuple(str(value) for value in payload.get("execution_semantic_profile_dependencies", ()))
    external = tuple(str(value) for value in payload.get("captured_external_evidence_refs", ()))
    gaps = tuple(str(value) for value in payload.get("capture_gaps", ()))
    generation_pairs = tuple(
        (str(pair[0]), int(pair[1])) for pair in payload.get("dependency_domain_generation_pairs", ())
    )
    trust_refs = tuple(sorted(set((*semantic, *trust, *execution))))
    assurance = DependencyCaptureAssurance(str(payload["capture_assurance"]))
    vector_body = {
        "artifact_revision": str(payload["artifact_revision"]),
        "exact_dependency_revisions": exact,
        "dependency_domain_generation_pairs": generation_pairs,
        "query_domain_revision_digests": query_digest_pairs,
        "trust_profile_capability_revision_refs": trust_refs,
        "evaluated_at_cut": str(payload["evaluated_at_cut"]),
        "capture_assurance": assurance.value,
    }
    vector_digest = digest(vector_body)
    if vector_digest != str(payload["freshness_vector_digest"]):
        raise ReplayError("manifest replay freshness-vector digest mismatch")
    vector = DependencyFreshnessVector(
        artifact_revision=vector_body["artifact_revision"],
        exact_dependency_revisions=exact,
        dependency_domain_generation_pairs=generation_pairs,
        query_domain_revision_digests=query_digest_pairs,
        trust_profile_capability_revision_refs=trust_refs,
        evaluated_at_cut=vector_body["evaluated_at_cut"],
        capture_assurance=assurance,
        canonical_digest=vector_digest,
    )
    body = {
        "manifest_id": str(payload["manifest_id"]),
        "revision_id": str(payload["revision_id"]),
        "artifact_revision": str(payload["artifact_revision"]),
        "proof_obligation_revision": str(payload["proof_obligation_revision"]),
        "producer_capability_revision": str(payload["producer_capability_revision"]),
        "input_envelope_revision": envelope_revision,
        "input_envelope_digest": envelope.canonical_input_digest,
        "capture_assurance": assurance.value,
        "positive_revision_dependencies": exact,
        "query_domain_revision_digests": query_digest_pairs,
        "semantic_profile_dependencies": semantic,
        "trust_checker_normalizer_dependencies": trust,
        "assumption_basis_dependencies": assumptions,
        "execution_semantic_profile_dependencies": execution,
        "captured_external_evidence_refs": external,
        "capture_gaps": gaps,
        "created_sequence": int(payload["created_sequence"]),
        "evaluated_at_cut": str(payload["evaluated_at_cut"]),
        "freshness_vector_digest": vector_digest,
    }
    recorded = str(payload["canonical_digest"])
    if digest(body) != recorded:
        raise ReplayError("manifest replay canonical digest mismatch")
    return ProofDependencyManifestRevision(
        manifest_id=body["manifest_id"],
        revision_id=body["revision_id"],
        artifact_revision=body["artifact_revision"],
        proof_obligation_revision=body["proof_obligation_revision"],
        producer_capability_revision=body["producer_capability_revision"],
        input_envelope_revision=envelope_revision,
        input_envelope_digest=envelope.canonical_input_digest,
        capture_assurance=assurance,
        positive_revision_dependencies=exact,
        query_domain_revisions=tuple(queries),
        semantic_profile_dependencies=semantic,
        trust_checker_normalizer_dependencies=trust,
        assumption_basis_dependencies=assumptions,
        execution_semantic_profile_dependencies=execution,
        captured_external_evidence_refs=external,
        capture_gaps=gaps,
        created_sequence=body["created_sequence"],
        evaluated_at_cut=body["evaluated_at_cut"],
        freshness_vector=vector,
        canonical_digest=recorded,
    )


def _replay_proof_entry(kernel, entry) -> bool:
    event = entry.event_type
    payload = entry.payload
    if event == "proof.semantic_source_registered":
        _replay_semantic_source_registered(kernel, payload)
        return True
    if event == "proof.semantic_source_mutated":
        _replay_semantic_source_mutated(kernel, payload)
        return True
    if event == "proof.profile_refs_registered":
        kernel.proof_profile_refs.update(str(value) for value in payload.get("refs", ()))
        return True
    if event == "proof.query_domain_created":
        _replay_query_created(kernel, payload)
        return True
    if event == "proof.query_domain_membership_advanced":
        _replay_query_membership(kernel, payload)
        return True
    if event == "proof.query_domain_member_mutated":
        _replay_query_member_mutated(kernel, payload)
        return True
    if event == "proof.input_envelope_registered":
        envelope = _envelope_from_doc(dict(payload))
        if envelope.revision_id in kernel.proof_input_envelopes:
            raise ReplayError("duplicate proof input envelope during replay")
        kernel.proof_input_envelopes[envelope.revision_id] = envelope
        return True
    if event == "proof.manifest_captured":
        manifest = _manifest_from_event(kernel, payload)
        if manifest.artifact_revision in kernel.proof_manifests:
            raise ReplayError("duplicate proof manifest during replay")
        kernel.proof_manifests[manifest.artifact_revision] = manifest
        return True
    if event == "proof.support_node_registered":
        node = _support_node_from_doc(dict(payload))
        if node.ref in kernel.support_nodes:
            raise ReplayError("duplicate support node during replay")
        kernel.support_nodes[node.ref] = node
        return True
    if event == "proof.support_set_registered":
        support_set = _support_set_from_doc(dict(payload))
        artifact = support_set.subject_artifact_revision
        if artifact not in kernel.proof_manifests:
            raise ReplayError("support set replay references a missing manifest")
        if artifact in kernel.support_sets:
            raise ReplayError("duplicate support set during replay")
        kernel.support_sets[artifact] = support_set
        return True
    if event == "proof.invalidity_causes_set":
        artifact = str(payload["artifact_revision"])
        if artifact not in kernel.proof_manifests:
            raise ReplayError("invalidity replay references a missing manifest")
        kernel.proof_invalidity_causes[artifact] = tuple(
            InvalidityCause(
                cause_id=str(row["cause_id"]),
                code=str(row["code"]),
                active=bool(row["active"]),
                blocking=bool(row["blocking"]),
                detail=row.get("detail"),
            )
            for row in payload.get("causes", ())
        )
        return True
    if event == "proof.authorization_bound":
        authorization_id = str(payload["authorization_id"])
        if authorization_id not in kernel.authorizations:
            raise ReplayError("proof authorization replay references a missing authorization")
        artifact = str(payload["proof_artifact_revision"])
        manifest = kernel.proof_manifests.get(artifact)
        if manifest is None or manifest.canonical_digest != str(payload["manifest_digest"]):
            raise ReplayError("proof authorization replay manifest lineage mismatch")
        kernel.proof_authorization_bindings[authorization_id] = {
            "proof_artifact_revision": artifact,
            "manifest_digest": str(payload["manifest_digest"]),
            "support_assessment_digest": str(payload["support_assessment_digest"]),
        }
        return True
    return False


def _replay_entry(kernel, entry) -> None:
    if entry.event_type.startswith("proof."):
        if not _replay_proof_entry(kernel, entry):
            raise ReplayError(f"unsupported Wave 4 proof replay event: {entry.event_type}")
        return
    _replay_trust_entry(kernel, entry)


def _open(cls, root: Path):
    root = Path(root)
    journal = HashJournal(root / "journal.jsonl")
    journal.verify(raise_on_error=True)
    state = SnapshotStore(root / "snapshot.json").load()
    schema = state.get("snapshot_schema")
    if schema not in {BASE_SNAPSHOT_SCHEMA, TRUST_SNAPSHOT_SCHEMA, PROOF_SNAPSHOT_SCHEMA}:
        raise ReplayError("unsupported or missing snapshot schema")
    entries = journal.entries()
    prefix_length = _find_snapshot_prefix(entries, str(state.get("journal_head", "")))

    mission_doc = state.get("mission") or {}
    if not mission_doc:
        raise ReplayError("snapshot has no mission contract")
    mission = MissionLedger(MissionContract(
        int(mission_doc["version"]),
        str(mission_doc["objective"]),
        tuple(mission_doc.get("success_conditions", ())),
        tuple(mission_doc.get("hard_constraints", ())),
        tuple(mission_doc.get("soft_preferences", ())),
        tuple(mission_doc.get("anti_goals", ())),
        mission_doc.get("risk_budget"),
    ))
    kernel = cls(root, mission)
    core_state = dict(state)
    core_state["snapshot_schema"] = BASE_SNAPSHOT_SCHEMA
    core_state.pop("trust", None)
    core_state.pop("proof", None)
    _restore_state(kernel, core_state)
    if schema in {TRUST_SNAPSHOT_SCHEMA, PROOF_SNAPSHOT_SCHEMA}:
        _restore_trust_state(kernel, dict(state.get("trust") or {}))
    if schema == PROOF_SNAPSHOT_SCHEMA:
        proof = state.get("proof")
        if not isinstance(proof, dict):
            raise ReplayError("v4 snapshot is missing proof lineage state")
        _restore_proof_state(kernel, proof)
    for entry in entries[prefix_length:]:
        _replay_entry(kernel, entry)
    return kernel


def install_proof_recovery(kernel_cls) -> None:
    if getattr(kernel_cls, "_wave4_proof_recovery_installed", False):
        return
    base_snapshot_state = kernel_cls.snapshot_state

    def snapshot_state(self):
        return _snapshot_state(self, base_snapshot_state)

    def save_snapshot(self):
        with self._writer_lock:
            state = snapshot_state(self)
            self.snapshots.save(state)
            self._record("snapshot.saved", {
                "snapshot_schema": PROOF_SNAPSHOT_SCHEMA,
                "snapshot_digest": digest(state),
                "bound_journal_head": state["journal_head"],
            })
            return state

    kernel_cls.snapshot_state = snapshot_state
    kernel_cls.save_snapshot = save_snapshot
    kernel_cls.open = classmethod(_open)
    kernel_cls._wave4_proof_recovery_installed = True
