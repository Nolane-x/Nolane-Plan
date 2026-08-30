from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Mapping

from .hashing import digest


def _canon(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(sorted({str(value).strip() for value in values if str(value).strip()}))


def _required(name: str, value: object) -> str:
    text = str(value).strip()
    if not text:
        raise ValueError(f"{name} must be non-empty")
    return text


class ArtifactAssurance(str, Enum):
    DRAFT = "draft"
    STRUCTURALLY_VALID = "structurally_valid"
    GROUNDED = "grounded"
    CHECKED = "checked"
    INDEPENDENTLY_VERIFIED = "independently_verified"

    @property
    def rank(self) -> int:
        return {
            ArtifactAssurance.DRAFT: 0,
            ArtifactAssurance.STRUCTURALLY_VALID: 1,
            ArtifactAssurance.GROUNDED: 2,
            ArtifactAssurance.CHECKED: 3,
            ArtifactAssurance.INDEPENDENTLY_VERIFIED: 4,
        }[self]


class CompositionStatus(str, Enum):
    COMPOSABLE = "composable"
    COMPOSABLE_WITH_ACCEPTED_DEBT = "composable_with_accepted_debt"
    NONCOMPOSABLE_CONFLICT = "noncomposable_conflict"
    COMPOSITION_UNKNOWN = "composition_unknown"
    UNSUPPORTED_CONSTRAINT_THEORY = "unsupported_constraint_theory"


class SealStatus(str, Enum):
    SEALED = "sealed"
    SEALED_WITH_ACCEPTED_DEBT = "sealed_with_accepted_debt"
    STALE = "stale"
    REVOKED = "revoked"


@dataclass(frozen=True, slots=True)
class DecisionSufficiencyCertificate:
    certificate_id: str
    revision_id: str
    scope_ref: str
    action_ref: str
    decision_epoch_ref: str
    decision_principal_ref: str
    information_partition_revision: str
    exact_object_revisions: tuple[tuple[str, str], ...]
    included_object_refs: tuple[str, ...]
    excluded_known_object_refs: tuple[str, ...]
    compiler_profile_ref: str
    adequacy_limits: tuple[str, ...]
    debt_refs: tuple[str, ...]
    complete: bool
    created_sequence: int
    validity_regime: str
    canonical_digest: str

    @classmethod
    def create(
        cls,
        *,
        certificate_id: str,
        revision_id: str,
        scope_ref: str,
        action_ref: str,
        decision_epoch_ref: str,
        decision_principal_ref: str,
        information_partition_revision: str,
        exact_object_revisions: Mapping[str, str],
        included_object_refs: Iterable[str],
        excluded_known_object_refs: Iterable[str],
        compiler_profile_ref: str,
        adequacy_limits: Iterable[str],
        debt_refs: Iterable[str],
        complete: bool,
        created_sequence: int,
        validity_regime: str,
    ) -> "DecisionSufficiencyCertificate":
        if int(created_sequence) < 0:
            raise ValueError("created_sequence cannot be negative")
        exact = tuple(sorted((_required("object logical key", k), _required("object revision", v)) for k, v in exact_object_revisions.items()))
        included = _canon(included_object_refs)
        excluded = _canon(excluded_known_object_refs)
        if set(included).intersection(excluded):
            raise ValueError("decision sufficiency cannot include and exclude the same object")
        body = {
            "certificate_id": _required("certificate_id", certificate_id),
            "revision_id": _required("revision_id", revision_id),
            "scope_ref": _required("scope_ref", scope_ref),
            "action_ref": _required("action_ref", action_ref),
            "decision_epoch_ref": _required("decision_epoch_ref", decision_epoch_ref),
            "decision_principal_ref": _required("decision_principal_ref", decision_principal_ref),
            "information_partition_revision": _required("information_partition_revision", information_partition_revision),
            "exact_object_revisions": exact,
            "included_object_refs": included,
            "excluded_known_object_refs": excluded,
            "compiler_profile_ref": _required("compiler_profile_ref", compiler_profile_ref),
            "adequacy_limits": _canon(adequacy_limits),
            "debt_refs": _canon(debt_refs),
            "complete": bool(complete),
            "created_sequence": int(created_sequence),
            "validity_regime": _required("validity_regime", validity_regime),
        }
        return cls(**body, canonical_digest=digest(body))


@dataclass(frozen=True, slots=True)
class ProofContextComponent:
    component_ref: str
    assurance: ArtifactAssurance
    assumptions: tuple[str, ...]
    scope: str
    guarantee: str
    debt_refs: tuple[str, ...]
    risk_refs: tuple[str, ...]
    authority_refs: tuple[str, ...]
    resource_refs: tuple[str, ...]
    external_regime_refs: tuple[str, ...]
    validity_horizon: tuple[int | float, int | float]
    constraint_theory: str
    allowed_worlds: tuple[str, ...]
    canonical_digest: str

    @classmethod
    def create(
        cls,
        *,
        component_ref: str,
        assurance: ArtifactAssurance,
        assumptions: Iterable[str],
        scope: str,
        guarantee: str,
        debt_refs: Iterable[str],
        risk_refs: Iterable[str],
        authority_refs: Iterable[str],
        resource_refs: Iterable[str],
        external_regime_refs: Iterable[str],
        validity_horizon: tuple[int | float, int | float],
        constraint_theory: str,
        allowed_worlds: Iterable[str],
    ) -> "ProofContextComponent":
        if len(validity_horizon) != 2 or validity_horizon[0] < 0 or validity_horizon[1] < validity_horizon[0]:
            raise ValueError("proof context validity horizon is invalid")
        theory = _required("constraint_theory", constraint_theory)
        worlds = _canon(allowed_worlds)
        if theory == "finite-world-set" and not worlds:
            raise ValueError("finite-world-set proof context requires at least one allowed world")
        body = {
            "component_ref": _required("component_ref", component_ref),
            "assurance": assurance.value,
            "assumptions": _canon(assumptions),
            "scope": _required("scope", scope),
            "guarantee": _required("guarantee", guarantee),
            "debt_refs": _canon(debt_refs),
            "risk_refs": _canon(risk_refs),
            "authority_refs": _canon(authority_refs),
            "resource_refs": _canon(resource_refs),
            "external_regime_refs": _canon(external_regime_refs),
            "validity_horizon": validity_horizon,
            "constraint_theory": theory,
            "allowed_worlds": worlds,
        }
        return cls(
            component_ref=body["component_ref"],
            assurance=assurance,
            assumptions=body["assumptions"],
            scope=body["scope"],
            guarantee=body["guarantee"],
            debt_refs=body["debt_refs"],
            risk_refs=body["risk_refs"],
            authority_refs=body["authority_refs"],
            resource_refs=body["resource_refs"],
            external_regime_refs=body["external_regime_refs"],
            validity_horizon=validity_horizon,
            constraint_theory=theory,
            allowed_worlds=worlds,
            canonical_digest=digest(body),
        )


@dataclass(frozen=True, slots=True)
class GlobalCompositionResult:
    status: CompositionStatus
    component_refs: tuple[str, ...]
    assurance_floor: ArtifactAssurance | None
    guarantee_floor: str | None
    surviving_worlds: tuple[str, ...]
    accepted_debt_refs: tuple[str, ...]
    unaccepted_debt_refs: tuple[str, ...]
    conflict_component_refs: tuple[str, ...]
    validity_horizon: tuple[int | float, int | float] | None
    canonical_digest: str


@dataclass(frozen=True, slots=True)
class PlanSeal:
    seal_id: str
    revision_id: str
    plan_root_revision: str
    mission_revision: int
    canonical_state_version: int
    action_closure_refs: tuple[str, ...]
    sufficiency_certificate_revision: str
    sufficiency_certificate_digest: str
    proof_context_digests: tuple[str, ...]
    composition_digest: str
    required_assurance: ArtifactAssurance
    assurance_floor: ArtifactAssurance
    accepted_debt_refs: tuple[str, ...]
    compiler_pass_manifest: tuple[str, ...]
    invariant_digest: str
    created_sequence: int
    validity_regime: str
    status: SealStatus
    canonical_digest: str


class SealCompiler:
    @staticmethod
    def _guarantee_floor(guarantees: Iterable[str]) -> str:
        rows = tuple(guarantees)
        if not rows:
            return "UNKNOWN"
        parsed: list[tuple[int, str]] = []
        for value in rows:
            text = str(value)
            if text.startswith("G") and text[1:].isdigit():
                parsed.append((int(text[1:]), text))
            else:
                return "UNKNOWN"
        return min(parsed)[1]

    @classmethod
    def compose_contexts(
        cls,
        components: Iterable[ProofContextComponent],
        *,
        accepted_debt_refs: Iterable[str],
    ) -> GlobalCompositionResult:
        rows = tuple(components)
        if not rows:
            raise ValueError("global proof-context composition requires at least one component")
        accepted = set(_canon(accepted_debt_refs))
        refs = tuple(sorted(component.component_ref for component in rows))
        debts = set().union(*(set(component.debt_refs) for component in rows))
        unaccepted = debts.difference(accepted)
        accepted_present = debts.intersection(accepted)

        status: CompositionStatus
        survivors: tuple[str, ...] = ()
        conflicts: tuple[str, ...] = ()
        assurance_floor = min(rows, key=lambda component: component.assurance.rank).assurance
        guarantee_floor = cls._guarantee_floor(component.guarantee for component in rows)
        start = max(component.validity_horizon[0] for component in rows)
        end = min(component.validity_horizon[1] for component in rows)
        horizon: tuple[int | float, int | float] | None = (start, end) if start <= end else None

        scopes = {component.scope for component in rows}
        if len(scopes) != 1 or horizon is None:
            status = CompositionStatus.NONCOMPOSABLE_CONFLICT
            conflicts = refs
        elif any(component.constraint_theory != "finite-world-set" for component in rows):
            status = CompositionStatus.UNSUPPORTED_CONSTRAINT_THEORY
        else:
            world_sets = [set(component.allowed_worlds) for component in rows]
            intersection = set.intersection(*world_sets)
            survivors = tuple(sorted(intersection))
            if not survivors:
                status = CompositionStatus.NONCOMPOSABLE_CONFLICT
                # Keep every component in the diagnostic root: pairwise compatibility may still hold.
                conflicts = refs
            elif unaccepted:
                status = CompositionStatus.COMPOSITION_UNKNOWN
            elif accepted_present:
                status = CompositionStatus.COMPOSABLE_WITH_ACCEPTED_DEBT
            else:
                status = CompositionStatus.COMPOSABLE

        body = {
            "status": status.value,
            "component_refs": refs,
            "assurance_floor": assurance_floor.value if assurance_floor else None,
            "guarantee_floor": guarantee_floor,
            "surviving_worlds": survivors,
            "accepted_debt_refs": tuple(sorted(accepted_present)),
            "unaccepted_debt_refs": tuple(sorted(unaccepted)),
            "conflict_component_refs": conflicts,
            "validity_horizon": horizon,
        }
        return GlobalCompositionResult(
            status=status,
            component_refs=refs,
            assurance_floor=assurance_floor,
            guarantee_floor=guarantee_floor,
            surviving_worlds=survivors,
            accepted_debt_refs=tuple(sorted(accepted_present)),
            unaccepted_debt_refs=tuple(sorted(unaccepted)),
            conflict_component_refs=conflicts,
            validity_horizon=horizon,
            canonical_digest=digest(body),
        )

    @classmethod
    def issue(
        cls,
        *,
        seal_id: str,
        revision_id: str,
        plan_root_revision: str,
        mission_revision: int,
        canonical_state_version: int,
        action_closure_refs: Iterable[str],
        sufficiency: DecisionSufficiencyCertificate,
        proof_contexts: Iterable[ProofContextComponent],
        required_assurance: ArtifactAssurance,
        accepted_debt_refs: Iterable[str],
        compiler_pass_manifest: Iterable[str],
        invariant_digest: str,
        created_sequence: int,
        validity_regime: str,
    ) -> PlanSeal:
        if int(mission_revision) < 1 or int(canonical_state_version) < 1 or int(created_sequence) < 0:
            raise ValueError("seal version fields must be positive and sequence non-negative")
        if not sufficiency.complete:
            raise ValueError("PlanSeal requires a complete scope-specific decision sufficiency certificate")
        closure = _canon(action_closure_refs)
        if not closure or sufficiency.action_ref not in closure:
            raise ValueError("PlanSeal action closure must contain the sufficiency-bound action")
        passes = _canon(compiler_pass_manifest)
        if not passes:
            raise ValueError("PlanSeal requires an explicit compiler-pass manifest")
        accepted = set(_canon(accepted_debt_refs))
        contexts = tuple(proof_contexts)
        composition = cls.compose_contexts(contexts, accepted_debt_refs=accepted)
        if composition.status not in {CompositionStatus.COMPOSABLE, CompositionStatus.COMPOSABLE_WITH_ACCEPTED_DEBT}:
            raise ValueError(f"proof contexts are not globally composable: {composition.status.value}")
        if composition.assurance_floor is None or composition.assurance_floor.rank < required_assurance.rank:
            raise ValueError("proof-context assurance floor is below required PlanSeal assurance")
        all_debts = set(sufficiency.debt_refs)
        for component in contexts:
            all_debts.update(component.debt_refs)
        unaccepted = all_debts.difference(accepted)
        if unaccepted:
            raise ValueError(f"PlanSeal has unaccepted correctness debt: {sorted(unaccepted)!r}")
        accepted_present = tuple(sorted(all_debts.intersection(accepted)))
        status = SealStatus.SEALED_WITH_ACCEPTED_DEBT if accepted_present else SealStatus.SEALED
        context_digests = tuple(sorted(component.canonical_digest for component in contexts))
        body = {
            "seal_id": _required("seal_id", seal_id),
            "revision_id": _required("revision_id", revision_id),
            "plan_root_revision": _required("plan_root_revision", plan_root_revision),
            "mission_revision": int(mission_revision),
            "canonical_state_version": int(canonical_state_version),
            "action_closure_refs": closure,
            "sufficiency_certificate_revision": sufficiency.revision_id,
            "sufficiency_certificate_digest": sufficiency.canonical_digest,
            "proof_context_digests": context_digests,
            "composition_digest": composition.canonical_digest,
            "required_assurance": required_assurance.value,
            "assurance_floor": composition.assurance_floor.value,
            "accepted_debt_refs": accepted_present,
            "compiler_pass_manifest": passes,
            "invariant_digest": _required("invariant_digest", invariant_digest),
            "created_sequence": int(created_sequence),
            "validity_regime": _required("validity_regime", validity_regime),
            "status": status.value,
        }
        return PlanSeal(
            seal_id=body["seal_id"],
            revision_id=body["revision_id"],
            plan_root_revision=body["plan_root_revision"],
            mission_revision=body["mission_revision"],
            canonical_state_version=body["canonical_state_version"],
            action_closure_refs=closure,
            sufficiency_certificate_revision=sufficiency.revision_id,
            sufficiency_certificate_digest=sufficiency.canonical_digest,
            proof_context_digests=context_digests,
            composition_digest=composition.canonical_digest,
            required_assurance=required_assurance,
            assurance_floor=composition.assurance_floor,
            accepted_debt_refs=accepted_present,
            compiler_pass_manifest=passes,
            invariant_digest=body["invariant_digest"],
            created_sequence=body["created_sequence"],
            validity_regime=body["validity_regime"],
            status=status,
            canonical_digest=digest(body),
        )
