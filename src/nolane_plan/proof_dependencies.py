from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

from .freshness import FreshnessDomainLedger
from .hashing import digest
from .proof_inputs import DependencyCaptureAssurance, ProofInputEnvelopeRevision
from .query_domain import QueryDomainLedger, QueryDomainRevision, QueryDomainStatus


def _canon(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(sorted({str(value).strip() for value in values if str(value).strip()}))


def _canon_pairs(values: Mapping[str, str]) -> tuple[tuple[str, str], ...]:
    return tuple(sorted((str(key), str(value)) for key, value in values.items()))


@dataclass(frozen=True, slots=True)
class DependencyFreshnessVector:
    artifact_revision: str
    exact_dependency_revisions: tuple[tuple[str, str], ...]
    dependency_domain_generation_pairs: tuple[tuple[str, int], ...]
    query_domain_revision_digests: tuple[tuple[str, str], ...]
    trust_profile_capability_revision_refs: tuple[str, ...]
    evaluated_at_cut: str
    capture_assurance: DependencyCaptureAssurance
    canonical_digest: str

    @classmethod
    def capture(
        cls,
        freshness: FreshnessDomainLedger,
        *,
        artifact_revision: str,
        exact_dependency_revisions: Mapping[str, str],
        dependency_domains: Iterable[str],
        query_domain_revisions: Iterable[QueryDomainRevision],
        trust_profile_capability_revision_refs: Iterable[str],
        evaluated_at_cut: str,
        capture_assurance: DependencyCaptureAssurance,
    ) -> "DependencyFreshnessVector":
        domains = _canon(dependency_domains)
        exact = _canon_pairs(exact_dependency_revisions)
        query_digests = tuple(
            sorted((revision.query_domain_id, revision.canonical_digest) for revision in query_domain_revisions)
        )
        trust_refs = _canon(trust_profile_capability_revision_refs)
        generations = tuple((domain, freshness.generation(domain)) for domain in domains)
        body = {
            "artifact_revision": artifact_revision,
            "exact_dependency_revisions": exact,
            "dependency_domain_generation_pairs": generations,
            "query_domain_revision_digests": query_digests,
            "trust_profile_capability_revision_refs": trust_refs,
            "evaluated_at_cut": evaluated_at_cut,
            "capture_assurance": capture_assurance.value,
        }
        return cls(
            artifact_revision=artifact_revision,
            exact_dependency_revisions=exact,
            dependency_domain_generation_pairs=generations,
            query_domain_revision_digests=query_digests,
            trust_profile_capability_revision_refs=trust_refs,
            evaluated_at_cut=evaluated_at_cut,
            capture_assurance=capture_assurance,
            canonical_digest=digest(body),
        )

    def current(self, freshness: FreshnessDomainLedger) -> bool:
        return all(
            freshness.generation(domain) == generation
            for domain, generation in self.dependency_domain_generation_pairs
        )


@dataclass(frozen=True, slots=True)
class ProofDependencyManifestRevision:
    manifest_id: str
    revision_id: str
    artifact_revision: str
    proof_obligation_revision: str
    producer_capability_revision: str
    input_envelope_revision: str
    input_envelope_digest: str
    capture_assurance: DependencyCaptureAssurance
    positive_revision_dependencies: tuple[tuple[str, str], ...]
    query_domain_revisions: tuple[QueryDomainRevision, ...]
    semantic_profile_dependencies: tuple[str, ...]
    trust_checker_normalizer_dependencies: tuple[str, ...]
    assumption_basis_dependencies: tuple[str, ...]
    execution_semantic_profile_dependencies: tuple[str, ...]
    captured_external_evidence_refs: tuple[str, ...]
    capture_gaps: tuple[str, ...]
    created_sequence: int
    evaluated_at_cut: str
    freshness_vector: DependencyFreshnessVector
    canonical_digest: str

    @classmethod
    def capture(
        cls,
        freshness: FreshnessDomainLedger,
        *,
        manifest_id: str,
        revision_id: str,
        artifact_revision: str,
        proof_obligation_revision: str,
        producer_capability_revision: str,
        input_envelope: ProofInputEnvelopeRevision,
        positive_revision_dependencies: Mapping[str, str],
        dependency_domains: Iterable[str],
        query_domain_revisions: Iterable[QueryDomainRevision],
        semantic_profile_dependencies: Iterable[str] = (),
        trust_checker_normalizer_dependencies: Iterable[str] = (),
        assumption_basis_dependencies: Iterable[str] = (),
        execution_semantic_profile_dependencies: Iterable[str] = (),
        captured_external_evidence_refs: Iterable[str] = (),
        capture_gaps: Iterable[str] = (),
        created_sequence: int,
        evaluated_at_cut: str,
    ) -> "ProofDependencyManifestRevision":
        required = {
            "manifest_id": manifest_id,
            "revision_id": revision_id,
            "artifact_revision": artifact_revision,
            "proof_obligation_revision": proof_obligation_revision,
            "producer_capability_revision": producer_capability_revision,
            "evaluated_at_cut": evaluated_at_cut,
        }
        for name, value in required.items():
            if not str(value).strip():
                raise ValueError(f"{name} must be non-empty")
        if created_sequence < 0:
            raise ValueError("created_sequence cannot be negative")

        exact = _canon_pairs(positive_revision_dependencies)
        queries = tuple(sorted(tuple(query_domain_revisions), key=lambda item: item.query_domain_id))
        semantic = _canon(semantic_profile_dependencies)
        trust = _canon(trust_checker_normalizer_dependencies)
        assumptions = _canon(assumption_basis_dependencies)
        execution = _canon(execution_semantic_profile_dependencies)
        external = _canon(captured_external_evidence_refs)
        gaps = _canon(capture_gaps)
        all_profile_refs = _canon((*semantic, *trust, *execution))
        vector = DependencyFreshnessVector.capture(
            freshness,
            artifact_revision=artifact_revision,
            exact_dependency_revisions=dict(exact),
            dependency_domains=dependency_domains,
            query_domain_revisions=queries,
            trust_profile_capability_revision_refs=all_profile_refs,
            evaluated_at_cut=evaluated_at_cut,
            capture_assurance=input_envelope.capture_assurance,
        )
        body = {
            "manifest_id": manifest_id,
            "revision_id": revision_id,
            "artifact_revision": artifact_revision,
            "proof_obligation_revision": proof_obligation_revision,
            "producer_capability_revision": producer_capability_revision,
            "input_envelope_revision": input_envelope.revision_id,
            "input_envelope_digest": input_envelope.canonical_input_digest,
            "capture_assurance": input_envelope.capture_assurance.value,
            "positive_revision_dependencies": exact,
            "query_domain_revision_digests": tuple((item.query_domain_id, item.canonical_digest) for item in queries),
            "semantic_profile_dependencies": semantic,
            "trust_checker_normalizer_dependencies": trust,
            "assumption_basis_dependencies": assumptions,
            "execution_semantic_profile_dependencies": execution,
            "captured_external_evidence_refs": external,
            "capture_gaps": gaps,
            "created_sequence": created_sequence,
            "evaluated_at_cut": evaluated_at_cut,
            "freshness_vector_digest": vector.canonical_digest,
        }
        return cls(
            manifest_id=manifest_id,
            revision_id=revision_id,
            artifact_revision=artifact_revision,
            proof_obligation_revision=proof_obligation_revision,
            producer_capability_revision=producer_capability_revision,
            input_envelope_revision=input_envelope.revision_id,
            input_envelope_digest=input_envelope.canonical_input_digest,
            capture_assurance=input_envelope.capture_assurance,
            positive_revision_dependencies=exact,
            query_domain_revisions=queries,
            semantic_profile_dependencies=semantic,
            trust_checker_normalizer_dependencies=trust,
            assumption_basis_dependencies=assumptions,
            execution_semantic_profile_dependencies=execution,
            captured_external_evidence_refs=external,
            capture_gaps=gaps,
            created_sequence=created_sequence,
            evaluated_at_cut=evaluated_at_cut,
            freshness_vector=vector,
            canonical_digest=digest(body),
        )

    @property
    def capture_complete(self) -> bool:
        return (
            self.capture_assurance
            in {
                DependencyCaptureAssurance.FULL_ENVELOPE_ENFORCED,
                DependencyCaptureAssurance.TRUSTED_DYNAMIC_CAPTURE,
            }
            and not self.capture_gaps
        )

    def dependencies_current(
        self,
        *,
        freshness: FreshnessDomainLedger,
        exact_current_revisions: Mapping[str, str],
        query_domains: QueryDomainLedger,
        current_trust_profile_refs: Iterable[str],
        minimum_query_assurance: float = 0.0,
    ) -> bool:
        if not self.freshness_vector.current(freshness):
            return False

        for logical_key, bound_revision in self.positive_revision_dependencies:
            if exact_current_revisions.get(logical_key) != bound_revision:
                return False

        for bound_query in self.query_domain_revisions:
            if not query_domains.current(bound_query):
                return False
            if bound_query.status(minimum_query_assurance) != QueryDomainStatus.COMPLETE:
                return False

        current_profiles = {str(value) for value in current_trust_profile_refs}
        required_profiles = set(self.semantic_profile_dependencies)
        required_profiles.update(self.trust_checker_normalizer_dependencies)
        required_profiles.update(self.execution_semantic_profile_dependencies)
        if not required_profiles.issubset(current_profiles):
            return False
        return True

    def strong_reuse_eligible(
        self,
        *,
        freshness: FreshnessDomainLedger,
        exact_current_revisions: Mapping[str, str],
        query_domains: QueryDomainLedger,
        current_trust_profile_refs: Iterable[str],
        minimum_query_assurance: float = 0.0,
    ) -> bool:
        if not self.capture_complete:
            return False
        return self.dependencies_current(
            freshness=freshness,
            exact_current_revisions=exact_current_revisions,
            query_domains=query_domains,
            current_trust_profile_refs=current_trust_profile_refs,
            minimum_query_assurance=minimum_query_assurance,
        )
