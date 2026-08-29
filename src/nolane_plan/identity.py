from __future__ import annotations

from dataclasses import dataclass

from .hashing import digest
from .types import PlanError


class IdentityError(PlanError):
    """Raised when a principal identity cannot satisfy the requested assurance."""


@dataclass(frozen=True, slots=True)
class PrincipalAttestation:
    attestation_id: str
    canonical_principal_ref: str
    source: str
    source_subject: str
    revision: int
    issued_at: int | float
    valid_until: int | float | None
    assurance: float
    session_ref: str | None
    provenance_digest: str

    @classmethod
    def create(
        cls,
        *,
        attestation_id: str,
        canonical_principal_ref: str,
        source: str,
        source_subject: str,
        revision: int,
        issued_at: int | float,
        valid_until: int | float | None = None,
        assurance: float = 1.0,
        session_ref: str | None = None,
    ) -> "PrincipalAttestation":
        body = {
            "attestation_id": attestation_id,
            "canonical_principal_ref": canonical_principal_ref,
            "source": source,
            "source_subject": source_subject,
            "revision": revision,
            "issued_at": issued_at,
            "valid_until": valid_until,
            "assurance": assurance,
            "session_ref": session_ref,
        }
        return cls(
            attestation_id=attestation_id,
            canonical_principal_ref=canonical_principal_ref,
            source=source,
            source_subject=source_subject,
            revision=revision,
            issued_at=issued_at,
            valid_until=valid_until,
            assurance=assurance,
            session_ref=session_ref,
            provenance_digest=digest(body),
        )


@dataclass(frozen=True, slots=True)
class PrincipalBindingRevision:
    binding_id: str
    canonical_principal_ref: str
    attestation_id: str
    binding_revision: int
    source: str
    source_subject: str
    assurance: float
    created_at: int | float
    provenance_digest: str


class PrincipalIdentityLedger:
    """Consumes host/platform identity evidence and produces durable principal bindings.

    This ledger deliberately does not authenticate accounts. It only enforces that a
    correctness-bearing principal reference has a stable, versioned host identity
    provenance and a bounded assurance level.
    """

    def __init__(self) -> None:
        self._attestations: dict[str, PrincipalAttestation] = {}
        self._bindings: dict[str, list[PrincipalBindingRevision]] = {}
        self._subject_principals: dict[tuple[str, str], str] = {}
        self._subject_revisions: dict[tuple[str, str], int] = {}
        self._revoked_at: dict[str, int | float] = {}

    @staticmethod
    def _validate(attestation: PrincipalAttestation, now: int | float) -> None:
        if not attestation.attestation_id.strip():
            raise IdentityError("attestation id must be non-empty")
        if not attestation.canonical_principal_ref.strip():
            raise IdentityError("canonical principal ref must be non-empty")
        if not attestation.source.strip() or not attestation.source_subject.strip():
            raise IdentityError("identity source and source subject must be non-empty")
        if attestation.revision < 1:
            raise IdentityError("identity revision must be positive")
        if not 0.0 <= attestation.assurance <= 1.0:
            raise IdentityError("identity assurance must be within [0, 1]")
        if attestation.valid_until is not None and attestation.valid_until < attestation.issued_at:
            raise IdentityError("identity validity window is inverted")
        if now < attestation.issued_at:
            raise IdentityError("identity attestation is not valid yet")
        if attestation.valid_until is not None and now > attestation.valid_until:
            raise IdentityError("identity attestation is expired")

    def accept(self, attestation: PrincipalAttestation, *, now: int | float) -> PrincipalBindingRevision:
        self._validate(attestation, now)
        if attestation.attestation_id in self._attestations:
            raise IdentityError("attestation id already accepted")

        subject_key = (attestation.source, attestation.source_subject)
        existing_principal = self._subject_principals.get(subject_key)
        if existing_principal is not None and existing_principal != attestation.canonical_principal_ref:
            raise IdentityError("host identity subject cannot be rebound to a different canonical principal")
        previous_subject_revision = self._subject_revisions.get(subject_key, 0)
        if attestation.revision <= previous_subject_revision:
            raise IdentityError("identity revision must advance for the same source subject")

        revisions = self._bindings.setdefault(attestation.canonical_principal_ref, [])
        binding_revision = len(revisions) + 1
        binding_body = {
            "principal": attestation.canonical_principal_ref,
            "attestation": attestation.attestation_id,
            "binding_revision": binding_revision,
            "source": attestation.source,
            "source_subject": attestation.source_subject,
            "assurance": attestation.assurance,
            "created_at": now,
            "attestation_provenance": attestation.provenance_digest,
        }
        binding = PrincipalBindingRevision(
            binding_id=digest(binding_body)[:24],
            canonical_principal_ref=attestation.canonical_principal_ref,
            attestation_id=attestation.attestation_id,
            binding_revision=binding_revision,
            source=attestation.source,
            source_subject=attestation.source_subject,
            assurance=attestation.assurance,
            created_at=now,
            provenance_digest=digest(binding_body),
        )
        self._attestations[attestation.attestation_id] = attestation
        revisions.append(binding)
        self._subject_principals[subject_key] = attestation.canonical_principal_ref
        self._subject_revisions[subject_key] = attestation.revision
        return binding

    def accept_narrated_identity(self, narrated_label: str, *, now: int | float) -> PrincipalBindingRevision:
        del narrated_label, now
        raise IdentityError("model/role narration is not canonical host identity evidence")

    def revoke(self, attestation_id: str, *, revoked_at: int | float) -> None:
        if attestation_id not in self._attestations:
            raise IdentityError("unknown identity attestation")
        self._revoked_at[attestation_id] = revoked_at

    def current(
        self,
        canonical_principal_ref: str,
        *,
        now: int | float,
        minimum_assurance: float = 0.0,
    ) -> PrincipalBindingRevision:
        revisions = self._bindings.get(canonical_principal_ref)
        if not revisions:
            raise IdentityError("principal has no canonical host binding")
        binding = revisions[-1]
        attestation = self._attestations[binding.attestation_id]
        revoked_at = self._revoked_at.get(attestation.attestation_id)
        if now < binding.created_at:
            raise IdentityError("principal binding was not yet established at this decision boundary")
        if revoked_at is not None and now >= revoked_at:
            raise IdentityError("current principal attestation is revoked")
        if now < attestation.issued_at:
            raise IdentityError("current principal attestation is not valid yet")
        if attestation.valid_until is not None and now > attestation.valid_until:
            raise IdentityError("current principal attestation is expired")
        if binding.assurance < minimum_assurance:
            raise IdentityError("principal identity assurance below required floor")
        return binding

    def attestation(self, attestation_id: str) -> PrincipalAttestation:
        return self._attestations[attestation_id]

    def binding(self, canonical_principal_ref: str) -> PrincipalBindingRevision:
        revisions = self._bindings.get(canonical_principal_ref)
        if not revisions:
            raise IdentityError("principal has no canonical host binding")
        return revisions[-1]

    def revoked_at(self, attestation_id: str) -> int | float | None:
        return self._revoked_at.get(attestation_id)

    def all_attestations(self) -> tuple[PrincipalAttestation, ...]:
        return tuple(self._attestations.values())

    def all_bindings(self) -> tuple[PrincipalBindingRevision, ...]:
        return tuple(binding for revisions in self._bindings.values() for binding in revisions)
