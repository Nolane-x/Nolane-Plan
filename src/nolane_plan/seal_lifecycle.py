from __future__ import annotations

from .hashing import digest
from .seals import PlanSeal, SealStatus


_ALLOWED_INVALIDATIONS: dict[SealStatus, frozenset[SealStatus]] = {
    SealStatus.SEALED: frozenset({SealStatus.STALE, SealStatus.REVOKED}),
    SealStatus.SEALED_WITH_ACCEPTED_DEBT: frozenset({SealStatus.STALE, SealStatus.REVOKED}),
    SealStatus.STALE: frozenset({SealStatus.REVOKED}),
    SealStatus.REVOKED: frozenset(),
}


def _invalidate(self: PlanSeal, status: SealStatus, *, revision_id: str) -> PlanSeal:
    target = SealStatus(status)
    revision = str(revision_id).strip()
    if not revision:
        raise ValueError("PlanSeal invalidation requires a non-empty revision_id")
    if revision == self.revision_id:
        raise ValueError("PlanSeal invalidation must advance revision identity")
    if target not in _ALLOWED_INVALIDATIONS[self.status]:
        raise ValueError(f"illegal PlanSeal status transition: {self.status.value} -> {target.value}")

    body = {
        "seal_id": self.seal_id,
        "revision_id": revision,
        "plan_root_revision": self.plan_root_revision,
        "mission_revision": self.mission_revision,
        "canonical_state_version": self.canonical_state_version,
        "action_closure_refs": self.action_closure_refs,
        "sufficiency_certificate_revision": self.sufficiency_certificate_revision,
        "sufficiency_certificate_digest": self.sufficiency_certificate_digest,
        "proof_context_digests": self.proof_context_digests,
        "composition_digest": self.composition_digest,
        "required_assurance": self.required_assurance.value,
        "assurance_floor": self.assurance_floor.value,
        "accepted_debt_refs": self.accepted_debt_refs,
        "compiler_pass_manifest": self.compiler_pass_manifest,
        "invariant_digest": self.invariant_digest,
        "created_sequence": self.created_sequence,
        "validity_regime": self.validity_regime,
        "status": target.value,
    }
    return PlanSeal(
        seal_id=self.seal_id,
        revision_id=revision,
        plan_root_revision=self.plan_root_revision,
        mission_revision=self.mission_revision,
        canonical_state_version=self.canonical_state_version,
        action_closure_refs=self.action_closure_refs,
        sufficiency_certificate_revision=self.sufficiency_certificate_revision,
        sufficiency_certificate_digest=self.sufficiency_certificate_digest,
        proof_context_digests=self.proof_context_digests,
        composition_digest=self.composition_digest,
        required_assurance=self.required_assurance,
        assurance_floor=self.assurance_floor,
        accepted_debt_refs=self.accepted_debt_refs,
        compiler_pass_manifest=self.compiler_pass_manifest,
        invariant_digest=self.invariant_digest,
        created_sequence=self.created_sequence,
        validity_regime=self.validity_regime,
        status=target,
        canonical_digest=digest(body),
    )


def install_seal_lifecycle() -> None:
    if getattr(PlanSeal, "_wave5_lifecycle_installed", False):
        return
    PlanSeal.invalidate = _invalidate  # type: ignore[attr-defined]
    PlanSeal._wave5_lifecycle_installed = True  # type: ignore[attr-defined]
