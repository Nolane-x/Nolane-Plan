from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable

from .hashing import digest
from .types import PlanError


class ProofInputError(PlanError):
    """Raised when a correctness procedure cannot justify its semantic input surface."""


class DependencyCaptureAssurance(str, Enum):
    FULL_ENVELOPE_ENFORCED = "full_envelope_enforced"
    TRUSTED_DYNAMIC_CAPTURE = "trusted_dynamic_capture"
    SELF_REPORTED_DECLARED = "self_reported_declared"
    DEPENDENCY_OPAQUE = "dependency_opaque"
    UNSUPPORTED_CAPTURE = "unsupported_capture"


class ExternalReadPolicy(str, Enum):
    DENY_UNDECLARED = "deny_undeclared"
    CAPTURE_REQUIRED = "capture_required"
    ALLOW_OPAQUE = "allow_opaque"


def _canon(values: Iterable[str]) -> tuple[str, ...]:
    normalized = tuple(sorted({str(value).strip() for value in values if str(value).strip()}))
    return normalized


@dataclass(frozen=True, slots=True)
class ProofInputEnvelopeRevision:
    input_envelope_id: str
    revision_id: str
    procedure_kind: str
    procedure_capability_revision: str
    subject_revision_refs: tuple[str, ...]
    explicit_input_revision_refs: tuple[str, ...]
    query_domain_revision_refs: tuple[str, ...]
    collection_membership_revision_refs: tuple[str, ...]
    semantic_profile_refs: tuple[str, ...]
    assumption_basis_refs: tuple[str, ...]
    trusted_axiom_model_refs: tuple[str, ...]
    canonical_unit_numeric_profile_refs: tuple[str, ...]
    execution_environment_profile_refs: tuple[str, ...]
    external_read_policy: ExternalReadPolicy
    captured_external_evidence_refs: tuple[str, ...]
    resource_budget_profile_refs: tuple[str, ...]
    created_from_decision_cut: str
    capture_assurance: DependencyCaptureAssurance
    capture_mechanism_ref: str | None
    canonical_input_digest: str

    @classmethod
    def create(
        cls,
        *,
        input_envelope_id: str,
        revision_id: str,
        procedure_kind: str,
        procedure_capability_revision: str,
        subject_revision_refs: Iterable[str] = (),
        explicit_input_revision_refs: Iterable[str] = (),
        query_domain_revision_refs: Iterable[str] = (),
        collection_membership_revision_refs: Iterable[str] = (),
        semantic_profile_refs: Iterable[str] = (),
        assumption_basis_refs: Iterable[str] = (),
        trusted_axiom_model_refs: Iterable[str] = (),
        canonical_unit_numeric_profile_refs: Iterable[str] = (),
        execution_environment_profile_refs: Iterable[str] = (),
        external_read_policy: ExternalReadPolicy = ExternalReadPolicy.DENY_UNDECLARED,
        captured_external_evidence_refs: Iterable[str] = (),
        resource_budget_profile_refs: Iterable[str] = (),
        created_from_decision_cut: str,
        capture_assurance: DependencyCaptureAssurance,
        capture_mechanism_ref: str | None = None,
    ) -> "ProofInputEnvelopeRevision":
        required = {
            "input_envelope_id": input_envelope_id,
            "revision_id": revision_id,
            "procedure_kind": procedure_kind,
            "procedure_capability_revision": procedure_capability_revision,
            "created_from_decision_cut": created_from_decision_cut,
        }
        for name, value in required.items():
            if not str(value).strip():
                raise ProofInputError(f"{name} must be non-empty")

        mechanism = capture_mechanism_ref.strip() if capture_mechanism_ref else None
        if capture_assurance == DependencyCaptureAssurance.TRUSTED_DYNAMIC_CAPTURE and not mechanism:
            raise ProofInputError("trusted dynamic capture requires an independently identified capture mechanism")
        if capture_assurance == DependencyCaptureAssurance.FULL_ENVELOPE_ENFORCED and external_read_policy == ExternalReadPolicy.ALLOW_OPAQUE:
            raise ProofInputError("full-envelope capture cannot simultaneously allow opaque correctness reads")
        if capture_assurance == DependencyCaptureAssurance.TRUSTED_DYNAMIC_CAPTURE and external_read_policy == ExternalReadPolicy.ALLOW_OPAQUE:
            raise ProofInputError("trusted dynamic capture cannot silently allow opaque correctness reads")

        fields = {
            "subject_revision_refs": _canon(subject_revision_refs),
            "explicit_input_revision_refs": _canon(explicit_input_revision_refs),
            "query_domain_revision_refs": _canon(query_domain_revision_refs),
            "collection_membership_revision_refs": _canon(collection_membership_revision_refs),
            "semantic_profile_refs": _canon(semantic_profile_refs),
            "assumption_basis_refs": _canon(assumption_basis_refs),
            "trusted_axiom_model_refs": _canon(trusted_axiom_model_refs),
            "canonical_unit_numeric_profile_refs": _canon(canonical_unit_numeric_profile_refs),
            "execution_environment_profile_refs": _canon(execution_environment_profile_refs),
            "captured_external_evidence_refs": _canon(captured_external_evidence_refs),
            "resource_budget_profile_refs": _canon(resource_budget_profile_refs),
        }
        body = {
            "input_envelope_id": input_envelope_id,
            "revision_id": revision_id,
            "procedure_kind": procedure_kind,
            "procedure_capability_revision": procedure_capability_revision,
            **fields,
            "external_read_policy": external_read_policy.value,
            "created_from_decision_cut": created_from_decision_cut,
            "capture_assurance": capture_assurance.value,
            "capture_mechanism_ref": mechanism,
        }
        return cls(
            input_envelope_id=input_envelope_id,
            revision_id=revision_id,
            procedure_kind=procedure_kind,
            procedure_capability_revision=procedure_capability_revision,
            subject_revision_refs=fields["subject_revision_refs"],
            explicit_input_revision_refs=fields["explicit_input_revision_refs"],
            query_domain_revision_refs=fields["query_domain_revision_refs"],
            collection_membership_revision_refs=fields["collection_membership_revision_refs"],
            semantic_profile_refs=fields["semantic_profile_refs"],
            assumption_basis_refs=fields["assumption_basis_refs"],
            trusted_axiom_model_refs=fields["trusted_axiom_model_refs"],
            canonical_unit_numeric_profile_refs=fields["canonical_unit_numeric_profile_refs"],
            execution_environment_profile_refs=fields["execution_environment_profile_refs"],
            external_read_policy=external_read_policy,
            captured_external_evidence_refs=fields["captured_external_evidence_refs"],
            resource_budget_profile_refs=fields["resource_budget_profile_refs"],
            created_from_decision_cut=created_from_decision_cut,
            capture_assurance=capture_assurance,
            capture_mechanism_ref=mechanism,
            canonical_input_digest=digest(body),
        )

    @property
    def strong_dependency_complete(self) -> bool:
        if self.capture_assurance == DependencyCaptureAssurance.FULL_ENVELOPE_ENFORCED:
            return self.external_read_policy != ExternalReadPolicy.ALLOW_OPAQUE
        if self.capture_assurance == DependencyCaptureAssurance.TRUSTED_DYNAMIC_CAPTURE:
            return bool(self.capture_mechanism_ref) and self.external_read_policy == ExternalReadPolicy.CAPTURE_REQUIRED
        return False

    @property
    def declared_revision_refs(self) -> frozenset[str]:
        refs: set[str] = set()
        for values in (
            self.subject_revision_refs,
            self.explicit_input_revision_refs,
            self.query_domain_revision_refs,
            self.collection_membership_revision_refs,
            self.semantic_profile_refs,
            self.assumption_basis_refs,
            self.trusted_axiom_model_refs,
            self.canonical_unit_numeric_profile_refs,
            self.execution_environment_profile_refs,
            self.captured_external_evidence_refs,
            self.resource_budget_profile_refs,
        ):
            refs.update(values)
        refs.add(self.procedure_capability_revision)
        refs.add(self.created_from_decision_cut)
        if self.capture_mechanism_ref:
            refs.add(self.capture_mechanism_ref)
        return frozenset(refs)

    def require_strong_capture(self) -> None:
        if not self.strong_dependency_complete:
            raise ProofInputError(
                f"capture assurance {self.capture_assurance.value} does not establish strong dependency completeness"
            )

    def assert_observed_reads_captured(self, observed_revision_refs: Iterable[str]) -> None:
        observed = {str(value).strip() for value in observed_revision_refs if str(value).strip()}
        if not self.strong_dependency_complete:
            raise ProofInputError("observed-read completeness cannot be asserted under a weak/opaque capture contract")
        hidden = observed.difference(self.declared_revision_refs)
        if hidden:
            raise ProofInputError(f"correctness procedure observed undeclared/uncaptured revisions: {sorted(hidden)!r}")
