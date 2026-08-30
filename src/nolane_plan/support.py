from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Mapping

from .hashing import digest


class SupportStatus(str, Enum):
    SUPPORTED = "supported"
    UNSUPPORTED = "unsupported"
    SUPPORT_INCONCLUSIVE = "support_inconclusive"
    SUPPORT_CONFLICTED = "support_conflicted"
    SUPPORT_STALE = "support_stale"
    SUPPORT_UNSUPPORTED_FORMULA = "support_unsupported_formula"


@dataclass(frozen=True, slots=True)
class SupportNode:
    ref: str
    current: bool
    direct_grounding_roots: frozenset[str]
    support_refs: tuple[str, ...]
    scope: str
    assumption_basis: frozenset[str]
    proof_kind: str
    validity_regime: str
    context_tags: frozenset[str]


@dataclass(frozen=True, slots=True)
class SupportClause:
    clause_id: str
    required_support_refs: tuple[str, ...]
    scope: str
    assumption_basis: frozenset[str]
    proof_kind: str
    grounding_root_requirements: frozenset[str]
    validity_regime: str
    context_tags: frozenset[str]
    minimum_independent_roots: int = 1

    def __post_init__(self) -> None:
        if not self.clause_id.strip():
            raise ValueError("support clause id must be non-empty")
        if self.minimum_independent_roots < 1:
            raise ValueError("minimum independent grounding roots must be positive")


@dataclass(frozen=True, slots=True)
class SupportAlternativeSetRevision:
    support_set_id: str
    revision_id: str
    subject_artifact_revision: str
    clauses: tuple[SupportClause, ...]
    scope: str
    assumption_context_rules: tuple[str, ...]
    proof_kind: str
    grounding_policy: str
    support_evaluation_profile: str
    created_sequence: int
    canonical_digest: str

    @classmethod
    def create(
        cls,
        *,
        support_set_id: str,
        revision_id: str,
        subject_artifact_revision: str,
        clauses: Iterable[SupportClause],
        scope: str,
        assumption_context_rules: Iterable[str],
        proof_kind: str,
        grounding_policy: str,
        support_evaluation_profile: str,
        created_sequence: int,
    ) -> "SupportAlternativeSetRevision":
        required = {
            "support_set_id": support_set_id,
            "revision_id": revision_id,
            "subject_artifact_revision": subject_artifact_revision,
            "scope": scope,
            "proof_kind": proof_kind,
            "grounding_policy": grounding_policy,
            "support_evaluation_profile": support_evaluation_profile,
        }
        for name, value in required.items():
            if not str(value).strip():
                raise ValueError(f"{name} must be non-empty")
        if created_sequence < 0:
            raise ValueError("created sequence cannot be negative")
        clause_tuple = tuple(clauses)
        clause_ids = tuple(clause.clause_id for clause in clause_tuple)
        if len(clause_ids) != len(set(clause_ids)):
            raise ValueError("support clause ids must be unique")
        rules = tuple(sorted({str(value) for value in assumption_context_rules if str(value)}))
        body = {
            "support_set_id": support_set_id,
            "revision_id": revision_id,
            "subject_artifact_revision": subject_artifact_revision,
            "clauses": tuple(
                {
                    "clause_id": clause.clause_id,
                    "required_support_refs": tuple(clause.required_support_refs),
                    "scope": clause.scope,
                    "assumption_basis": tuple(sorted(clause.assumption_basis)),
                    "proof_kind": clause.proof_kind,
                    "grounding_root_requirements": tuple(sorted(clause.grounding_root_requirements)),
                    "validity_regime": clause.validity_regime,
                    "context_tags": tuple(sorted(clause.context_tags)),
                    "minimum_independent_roots": clause.minimum_independent_roots,
                }
                for clause in clause_tuple
            ),
            "scope": scope,
            "assumption_context_rules": rules,
            "proof_kind": proof_kind,
            "grounding_policy": grounding_policy,
            "support_evaluation_profile": support_evaluation_profile,
            "created_sequence": created_sequence,
        }
        return cls(
            support_set_id=support_set_id,
            revision_id=revision_id,
            subject_artifact_revision=subject_artifact_revision,
            clauses=clause_tuple,
            scope=scope,
            assumption_context_rules=rules,
            proof_kind=proof_kind,
            grounding_policy=grounding_policy,
            support_evaluation_profile=support_evaluation_profile,
            created_sequence=created_sequence,
            canonical_digest=digest(body),
        )


@dataclass(frozen=True, slots=True)
class SupportAssessment:
    support_set_revision: str
    subject_artifact_revision: str
    status: SupportStatus
    surviving_clause_refs: tuple[str, ...]
    grounding_roots: tuple[str, ...]
    evaluated_at_cut: str
    generation: int
    assessment_digest: str


@dataclass(frozen=True, slots=True)
class InvalidityCause:
    cause_id: str
    code: str
    active: bool
    blocking: bool
    detail: str | None = None


@dataclass(frozen=True, slots=True)
class ArtifactAuthorityAssessment:
    support: SupportAssessment
    invalidity_causes: tuple[InvalidityCause, ...]

    @property
    def current_usable(self) -> bool:
        return (
            self.support.status == SupportStatus.SUPPORTED
            and not any(cause.active and cause.blocking for cause in self.invalidity_causes)
        )


class SupportEvaluator:
    """Bounded DNF support evaluator with grounded-root and cycle semantics."""

    @staticmethod
    def _resolve_roots(
        ref: str,
        nodes: Mapping[str, SupportNode],
        *,
        active_context: frozenset[str],
        visiting: frozenset[str],
        memo: dict[str, frozenset[str] | None],
    ) -> frozenset[str] | None:
        if ref in memo:
            return memo[ref]
        if ref in visiting:
            memo[ref] = None
            return None
        node = nodes.get(ref)
        if node is None or not node.current:
            memo[ref] = None
            return None
        if active_context and not active_context.issubset(node.context_tags):
            memo[ref] = None
            return None

        roots = set(node.direct_grounding_roots)
        next_visiting = visiting | {ref}
        for dependency_ref in node.support_refs:
            dependency_roots = SupportEvaluator._resolve_roots(
                dependency_ref,
                nodes,
                active_context=active_context,
                visiting=next_visiting,
                memo=memo,
            )
            if not dependency_roots:
                memo[ref] = None
                return None
            roots.update(dependency_roots)
        if not roots:
            memo[ref] = None
            return None
        resolved = frozenset(roots)
        memo[ref] = resolved
        return resolved

    @classmethod
    def evaluate(
        cls,
        support_set: SupportAlternativeSetRevision,
        nodes: Mapping[str, SupportNode],
        *,
        active_context: Iterable[str],
        evaluated_at_cut: str,
        generation: int,
    ) -> SupportAssessment:
        context = frozenset(str(value) for value in active_context)
        surviving: list[str] = []
        all_roots: set[str] = set()
        memo: dict[str, frozenset[str] | None] = {}

        for clause in support_set.clauses:
            # Empty ALL_OF is mathematically vacuous but does not create a grounding root.
            if not clause.required_support_refs:
                continue
            if clause.scope != support_set.scope or clause.proof_kind != support_set.proof_kind:
                continue
            if context and not context.issubset(clause.context_tags):
                continue

            clause_roots: set[str] = set()
            clause_valid = True
            for ref in clause.required_support_refs:
                node = nodes.get(ref)
                if node is None:
                    clause_valid = False
                    break
                if node.scope != clause.scope or node.proof_kind != clause.proof_kind:
                    clause_valid = False
                    break
                if node.assumption_basis != clause.assumption_basis:
                    clause_valid = False
                    break
                if node.validity_regime != clause.validity_regime:
                    clause_valid = False
                    break
                roots = cls._resolve_roots(
                    ref,
                    nodes,
                    active_context=context,
                    visiting=frozenset(),
                    memo=memo,
                )
                if not roots:
                    clause_valid = False
                    break
                clause_roots.update(roots)

            if not clause_valid:
                continue
            if not clause.grounding_root_requirements.issubset(clause_roots):
                continue
            if len(clause_roots) < clause.minimum_independent_roots:
                continue
            surviving.append(clause.clause_id)
            all_roots.update(clause_roots)

        status = SupportStatus.SUPPORTED if surviving else SupportStatus.UNSUPPORTED
        body = {
            "support_set_revision": support_set.revision_id,
            "subject_artifact_revision": support_set.subject_artifact_revision,
            "status": status.value,
            "surviving_clause_refs": tuple(surviving),
            "grounding_roots": tuple(sorted(all_roots)),
            "evaluated_at_cut": evaluated_at_cut,
            "generation": generation,
        }
        return SupportAssessment(
            support_set_revision=support_set.revision_id,
            subject_artifact_revision=support_set.subject_artifact_revision,
            status=status,
            surviving_clause_refs=tuple(surviving),
            grounding_roots=tuple(sorted(all_roots)),
            evaluated_at_cut=evaluated_at_cut,
            generation=generation,
            assessment_digest=digest(body),
        )
