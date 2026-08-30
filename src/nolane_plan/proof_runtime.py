from __future__ import annotations

from dataclasses import asdict
from typing import Any, Iterable

from .proof_dependencies import ProofDependencyManifestRevision
from .proof_inputs import ProofInputEnvelopeRevision
from .query_domain import QueryDomainLedger, QueryDomainRevision
from .semantic_barrier import MutationImpactProfileRevision, SemanticClosureBarrier
from .support import (
    ArtifactAuthorityAssessment,
    InvalidityCause,
    SupportAlternativeSetRevision,
    SupportEvaluator,
    SupportNode,
)
from .types import AuthorizationError


def _install_state(self) -> None:
    self.proof_input_envelopes: dict[str, ProofInputEnvelopeRevision] = {}
    self.query_domains = QueryDomainLedger()
    self.proof_manifests: dict[str, ProofDependencyManifestRevision] = {}
    self.support_sets: dict[str, SupportAlternativeSetRevision] = {}
    self.support_nodes: dict[str, SupportNode] = {}
    self.proof_invalidity_causes: dict[str, tuple[InvalidityCause, ...]] = {}
    self.proof_authority_assessments: dict[str, ArtifactAuthorityAssessment] = {}
    self.proof_profile_refs: set[str] = set()
    self.proof_exact_revisions: dict[str, str] = {}
    self.proof_source_domains: dict[str, tuple[str, ...]] = {}
    self.proof_authorization_bindings: dict[str, dict[str, str]] = {}
    self.semantic_barrier = SemanticClosureBarrier(self.freshness, self._writer_lock)


def _register_semantic_source(
    self,
    source_id: str,
    *,
    revision_id: str,
    value: Any,
    dependency_domains: Iterable[str],
):
    with self._writer_lock:
        domains = tuple(sorted({str(domain) for domain in dependency_domains if str(domain)}))
        for domain in domains:
            self.freshness.ensure(domain)
        source = self.semantic_barrier.register_source(source_id, revision_id=revision_id, value=value)
        self.proof_exact_revisions[source_id] = revision_id
        self.proof_source_domains[source_id] = domains
        self._record(
            "proof.semantic_source_registered",
            {
                "source_id": source_id,
                "revision_id": revision_id,
                "value": value,
                "dependency_domains": list(domains),
                "linearization_sequence": source.linearization_sequence,
            },
        )
        return source


def _mutate_semantic_source(
    self,
    source_id: str,
    *,
    new_revision_id: str,
    new_value: Any,
    impact_profile: MutationImpactProfileRevision,
):
    with self._writer_lock:
        receipt = self.semantic_barrier.mutate(
            source_id,
            new_revision_id=new_revision_id,
            new_value=new_value,
            impact_profile=impact_profile,
        )
        self.proof_exact_revisions[source_id] = new_revision_id
        self._record(
            "proof.semantic_source_mutated",
            {
                "source_id": source_id,
                "previous_revision_id": receipt.previous_revision_id,
                "new_revision_id": receipt.new_revision_id,
                "new_value": new_value,
                "impact_profile": {
                    "revision_id": impact_profile.revision_id,
                    "source_id": impact_profile.source_id,
                    "affected_domains": list(impact_profile.affected_domains),
                    "coverage_complete": impact_profile.coverage_complete,
                    "conservative_fallback_domains": list(impact_profile.conservative_fallback_domains),
                },
                "affected_domains": list(receipt.affected_domains),
                "before_generations": [list(pair) for pair in receipt.before_generations],
                "after_generations": [list(pair) for pair in receipt.after_generations],
                "linearization_sequence": receipt.linearization_sequence,
            },
        )
        return receipt


def _register_proof_profile_refs(self, *refs: str) -> tuple[str, ...]:
    with self._writer_lock:
        normalized = tuple(sorted({str(ref) for ref in refs if str(ref)}))
        self.proof_profile_refs.update(normalized)
        self._record("proof.profile_refs_registered", {"refs": list(normalized)})
        return normalized


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


def _create_proof_query_domain(self, **kwargs: Any) -> QueryDomainRevision:
    with self._writer_lock:
        if "created_sequence" in kwargs:
            raise ValueError("created_sequence is kernel-owned")
        revision = self.query_domains.create(created_sequence=self.writer_sequence, **kwargs)
        self._record("proof.query_domain_created", _query_doc(revision))
        return revision


def _advance_proof_query_membership(
    self,
    query_domain_id: str,
    *,
    query_snapshot_id: str,
) -> QueryDomainRevision:
    with self._writer_lock:
        revision = self.query_domains.advance_membership(
            query_domain_id,
            query_snapshot_id=query_snapshot_id,
            created_sequence=self.writer_sequence,
        )
        self._record("proof.query_domain_membership_advanced", _query_doc(revision))
        return revision


def _record_proof_query_member_mutation(
    self,
    query_domain_id: str,
    *,
    predicate_result_may_change: bool,
    query_snapshot_id: str,
) -> QueryDomainRevision:
    with self._writer_lock:
        before = self.query_domains.latest(query_domain_id)
        revision = self.query_domains.record_member_mutation(
            query_domain_id,
            predicate_result_may_change=predicate_result_may_change,
            query_snapshot_id=query_snapshot_id,
            created_sequence=self.writer_sequence,
        )
        if revision is not before:
            self._record("proof.query_domain_member_mutated", _query_doc(revision))
        return revision


def _register_proof_input(self, envelope: ProofInputEnvelopeRevision) -> ProofInputEnvelopeRevision:
    with self._writer_lock:
        if envelope.revision_id in self.proof_input_envelopes:
            raise ValueError(f"proof input envelope revision already exists: {envelope.revision_id}")
        self.proof_input_envelopes[envelope.revision_id] = envelope
        self._record(
            "proof.input_envelope_registered",
            {
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
            },
        )
        return envelope


def _capture_proof_manifest(
    self,
    *,
    manifest_id: str,
    revision_id: str,
    artifact_revision: str,
    proof_obligation_revision: str,
    producer_capability_revision: str,
    input_envelope_revision: str,
    positive_revision_dependencies: dict[str, str],
    dependency_domains: Iterable[str],
    query_domain_ids: Iterable[str] = (),
    semantic_profile_dependencies: Iterable[str] = (),
    trust_checker_normalizer_dependencies: Iterable[str] = (),
    assumption_basis_dependencies: Iterable[str] = (),
    execution_semantic_profile_dependencies: Iterable[str] = (),
    captured_external_evidence_refs: Iterable[str] = (),
    capture_gaps: Iterable[str] = (),
) -> ProofDependencyManifestRevision:
    with self._writer_lock:
        if artifact_revision in self.proof_manifests:
            raise ValueError(f"proof manifest already registered for artifact: {artifact_revision}")
        try:
            envelope = self.proof_input_envelopes[input_envelope_revision]
        except KeyError as exc:
            raise ValueError(f"unknown proof input envelope: {input_envelope_revision}") from exc
        query_revisions = tuple(self.query_domains.latest(query_id) for query_id in query_domain_ids)
        cut = self.current_cut()
        manifest = ProofDependencyManifestRevision.capture(
            self.freshness,
            manifest_id=manifest_id,
            revision_id=revision_id,
            artifact_revision=artifact_revision,
            proof_obligation_revision=proof_obligation_revision,
            producer_capability_revision=producer_capability_revision,
            input_envelope=envelope,
            positive_revision_dependencies=positive_revision_dependencies,
            dependency_domains=dependency_domains,
            query_domain_revisions=query_revisions,
            semantic_profile_dependencies=semantic_profile_dependencies,
            trust_checker_normalizer_dependencies=trust_checker_normalizer_dependencies,
            assumption_basis_dependencies=assumption_basis_dependencies,
            execution_semantic_profile_dependencies=execution_semantic_profile_dependencies,
            captured_external_evidence_refs=captured_external_evidence_refs,
            capture_gaps=capture_gaps,
            created_sequence=self.writer_sequence,
            evaluated_at_cut=cut.id,
        )
        self.proof_manifests[artifact_revision] = manifest
        self._record(
            "proof.manifest_captured",
            {
                "artifact_revision": artifact_revision,
                "manifest_id": manifest.manifest_id,
                "revision_id": manifest.revision_id,
                "proof_obligation_revision": manifest.proof_obligation_revision,
                "producer_capability_revision": manifest.producer_capability_revision,
                "input_envelope_revision": manifest.input_envelope_revision,
                "input_envelope_digest": manifest.input_envelope_digest,
                "capture_assurance": manifest.capture_assurance.value,
                "positive_revision_dependencies": [list(pair) for pair in manifest.positive_revision_dependencies],
                "dependency_domain_generation_pairs": [list(pair) for pair in manifest.freshness_vector.dependency_domain_generation_pairs],
                "query_domain_ids": [query.query_domain_id for query in manifest.query_domain_revisions],
                "query_domain_revision_digests": [
                    [query.query_domain_id, query.canonical_digest] for query in manifest.query_domain_revisions
                ],
                "semantic_profile_dependencies": list(manifest.semantic_profile_dependencies),
                "trust_checker_normalizer_dependencies": list(manifest.trust_checker_normalizer_dependencies),
                "assumption_basis_dependencies": list(manifest.assumption_basis_dependencies),
                "execution_semantic_profile_dependencies": list(manifest.execution_semantic_profile_dependencies),
                "captured_external_evidence_refs": list(manifest.captured_external_evidence_refs),
                "capture_gaps": list(manifest.capture_gaps),
                "created_sequence": manifest.created_sequence,
                "evaluated_at_cut": manifest.evaluated_at_cut,
                "freshness_vector_digest": manifest.freshness_vector.canonical_digest,
                "canonical_digest": manifest.canonical_digest,
            },
        )
        return manifest


def _register_support_node(self, node: SupportNode) -> SupportNode:
    with self._writer_lock:
        if node.ref in self.support_nodes:
            raise ValueError(f"support node already exists: {node.ref}")
        self.support_nodes[node.ref] = node
        self._record(
            "proof.support_node_registered",
            {
                "ref": node.ref,
                "current": node.current,
                "direct_grounding_roots": sorted(node.direct_grounding_roots),
                "support_refs": list(node.support_refs),
                "scope": node.scope,
                "assumption_basis": sorted(node.assumption_basis),
                "proof_kind": node.proof_kind,
                "validity_regime": node.validity_regime,
                "context_tags": sorted(node.context_tags),
            },
        )
        return node


def _register_support_set(self, support_set: SupportAlternativeSetRevision) -> SupportAlternativeSetRevision:
    with self._writer_lock:
        artifact_revision = support_set.subject_artifact_revision
        if artifact_revision not in self.proof_manifests:
            raise ValueError("support set requires an existing proof manifest")
        if artifact_revision in self.support_sets:
            raise ValueError(f"support set already exists for artifact: {artifact_revision}")
        self.support_sets[artifact_revision] = support_set
        self._record(
            "proof.support_set_registered",
            {
                "support_set_id": support_set.support_set_id,
                "revision_id": support_set.revision_id,
                "subject_artifact_revision": artifact_revision,
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
            },
        )
        return support_set


def _set_proof_invalidity_causes(
    self,
    artifact_revision: str,
    causes: Iterable[InvalidityCause],
) -> tuple[InvalidityCause, ...]:
    with self._writer_lock:
        if artifact_revision not in self.proof_manifests:
            raise ValueError(f"unknown proof artifact: {artifact_revision}")
        value = tuple(causes)
        self.proof_invalidity_causes[artifact_revision] = value
        self._record(
            "proof.invalidity_causes_set",
            {
                "artifact_revision": artifact_revision,
                "causes": [asdict(cause) for cause in value],
            },
        )
        return value


def _evaluate_proof_authority(
    self,
    artifact_revision: str,
    *,
    active_context: Iterable[str],
    minimum_query_assurance: float = 0.8,
) -> ArtifactAuthorityAssessment:
    with self._writer_lock:
        try:
            manifest = self.proof_manifests[artifact_revision]
            support_set = self.support_sets[artifact_revision]
        except KeyError as exc:
            raise AuthorizationError("proof artifact has incomplete authority lineage") from exc

        if not manifest.strong_reuse_eligible(
            freshness=self.freshness,
            exact_current_revisions=self.proof_exact_revisions,
            query_domains=self.query_domains,
            current_trust_profile_refs=self.proof_profile_refs,
            minimum_query_assurance=minimum_query_assurance,
        ):
            raise AuthorizationError("proof dependency/capture authority is stale or incomplete")

        cut = self.current_cut()
        support = SupportEvaluator.evaluate(
            support_set,
            self.support_nodes,
            active_context=active_context,
            evaluated_at_cut=cut.id,
            generation=self.writer_sequence,
        )
        assessment = ArtifactAuthorityAssessment(
            support=support,
            invalidity_causes=self.proof_invalidity_causes.get(artifact_revision, ()),
        )
        self.proof_authority_assessments[artifact_revision] = assessment
        if not assessment.current_usable:
            raise AuthorizationError("proof artifact lacks current positive support or has a blocking invalidity")
        return assessment


def _authorize_proof_carrying(
    self,
    action_id: str,
    acting_principal_ref: str,
    grant_ids: tuple[str, ...],
    now: int | float,
    *,
    proof_artifact_revision: str,
    active_context: Iterable[str],
    capsule_id: str | None = None,
    adapter_id: str | None = None,
    **kwargs: Any,
):
    with self._writer_lock:
        assessment = self.evaluate_proof_authority(
            proof_artifact_revision,
            active_context=active_context,
        )
        manifest = self.proof_manifests[proof_artifact_revision]
        authorization = self.authorize_strong(
            action_id,
            acting_principal_ref,
            grant_ids,
            now,
            capsule_id=capsule_id,
            adapter_id=adapter_id,
            **kwargs,
        )
        self.proof_authorization_bindings[authorization.id] = {
            "proof_artifact_revision": proof_artifact_revision,
            "manifest_digest": manifest.canonical_digest,
            "support_assessment_digest": assessment.support.assessment_digest,
        }
        self._record(
            "proof.authorization_bound",
            {
                "authorization_id": authorization.id,
                "proof_artifact_revision": proof_artifact_revision,
                "manifest_digest": manifest.canonical_digest,
                "support_assessment_digest": assessment.support.assessment_digest,
                "support_status": assessment.support.status.value,
                "surviving_clause_refs": list(assessment.support.surviving_clause_refs),
            },
        )
        return authorization


def install_proof_runtime(kernel_cls) -> None:
    if getattr(kernel_cls, "_wave4_proof_runtime_installed", False):
        return
    original_init = kernel_cls.__init__

    def __init__(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        _install_state(self)

    kernel_cls.__init__ = __init__
    kernel_cls.register_semantic_source = _register_semantic_source
    kernel_cls.mutate_semantic_source = _mutate_semantic_source
    kernel_cls.register_proof_profile_refs = _register_proof_profile_refs
    kernel_cls.create_proof_query_domain = _create_proof_query_domain
    kernel_cls.advance_proof_query_membership = _advance_proof_query_membership
    kernel_cls.record_proof_query_member_mutation = _record_proof_query_member_mutation
    kernel_cls.register_proof_input = _register_proof_input
    kernel_cls.capture_proof_manifest = _capture_proof_manifest
    kernel_cls.register_support_node = _register_support_node
    kernel_cls.register_support_set = _register_support_set
    kernel_cls.set_proof_invalidity_causes = _set_proof_invalidity_causes
    kernel_cls.evaluate_proof_authority = _evaluate_proof_authority
    kernel_cls.authorize_proof_carrying = _authorize_proof_carrying
    kernel_cls._wave4_proof_runtime_installed = True
