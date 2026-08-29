from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
from typing import Any

from .hashing import digest
from .types import PlanError


class QueryDomainError(PlanError):
    """Raised when a query domain cannot support its claimed completeness semantics."""


class QueryDomainStatus(str, Enum):
    COMPLETE = "complete"
    INCOMPLETE = "incomplete"
    OPAQUE = "opaque"
    INCONCLUSIVE = "inconclusive"


@dataclass(frozen=True, slots=True)
class QueryDomainRevision:
    query_domain_id: str
    revision_id: str
    scope_revision: str
    membership_generation: int
    result_sensitivity_generation: int
    index_schema_revision: str
    completeness_contract: str
    filter_predicate_revision: str
    alias_equivalence_regime: str
    visibility_permission_regime: str
    mutation_impact_profile_revision: str
    query_snapshot_id: str
    snapshot_complete: bool
    opaque: bool
    visibility_assurance: float
    created_sequence: int
    canonical_digest: str

    def status(self, minimum_assurance: float) -> QueryDomainStatus:
        if self.opaque:
            return QueryDomainStatus.OPAQUE
        if not self.snapshot_complete or not self.query_snapshot_id:
            return QueryDomainStatus.INCOMPLETE
        if self.visibility_assurance < minimum_assurance:
            return QueryDomainStatus.INCONCLUSIVE
        return QueryDomainStatus.COMPLETE

    @property
    def semantic_identity(self) -> tuple[Any, ...]:
        return (
            self.query_domain_id,
            self.scope_revision,
            self.membership_generation,
            self.result_sensitivity_generation,
            self.index_schema_revision,
            self.completeness_contract,
            self.filter_predicate_revision,
            self.alias_equivalence_regime,
            self.visibility_permission_regime,
            self.mutation_impact_profile_revision,
            self.query_snapshot_id,
            self.snapshot_complete,
            self.opaque,
            self.visibility_assurance,
        )


class QueryDomainLedger:
    """Canonical bounded query-domain history for negative/universal dependencies."""

    def __init__(self) -> None:
        self._history: dict[str, list[QueryDomainRevision]] = {}

    @staticmethod
    def _validate_fields(**fields: Any) -> None:
        nonempty = (
            "query_domain_id",
            "scope_revision",
            "index_schema_revision",
            "completeness_contract",
            "filter_predicate_revision",
            "alias_equivalence_regime",
            "visibility_permission_regime",
            "mutation_impact_profile_revision",
        )
        for name in nonempty:
            if not str(fields[name]).strip():
                raise QueryDomainError(f"{name} must be non-empty")
        assurance = float(fields["visibility_assurance"])
        if not 0.0 <= assurance <= 1.0:
            raise QueryDomainError("visibility assurance must be within [0, 1]")
        if int(fields["created_sequence"]) < 0:
            raise QueryDomainError("created sequence cannot be negative")

    @staticmethod
    def _digest(row: dict[str, Any]) -> str:
        body = dict(row)
        body.pop("canonical_digest", None)
        return digest(body)

    def create(
        self,
        *,
        query_domain_id: str,
        scope_revision: str,
        index_schema_revision: str,
        completeness_contract: str,
        filter_predicate_revision: str,
        alias_equivalence_regime: str,
        visibility_permission_regime: str,
        mutation_impact_profile_revision: str,
        query_snapshot_id: str,
        snapshot_complete: bool,
        opaque: bool,
        visibility_assurance: float,
        created_sequence: int,
    ) -> QueryDomainRevision:
        if query_domain_id in self._history:
            raise QueryDomainError(f"query domain already exists: {query_domain_id}")
        fields = dict(
            query_domain_id=query_domain_id,
            scope_revision=scope_revision,
            index_schema_revision=index_schema_revision,
            completeness_contract=completeness_contract,
            filter_predicate_revision=filter_predicate_revision,
            alias_equivalence_regime=alias_equivalence_regime,
            visibility_permission_regime=visibility_permission_regime,
            mutation_impact_profile_revision=mutation_impact_profile_revision,
            query_snapshot_id=query_snapshot_id,
            snapshot_complete=snapshot_complete,
            opaque=opaque,
            visibility_assurance=visibility_assurance,
            created_sequence=created_sequence,
        )
        self._validate_fields(**fields)
        row = {
            **fields,
            "revision_id": f"{query_domain_id}@1",
            "membership_generation": 1,
            "result_sensitivity_generation": 1,
        }
        revision = QueryDomainRevision(**row, canonical_digest=self._digest(row))
        self._history[query_domain_id] = [revision]
        return revision

    def latest(self, query_domain_id: str) -> QueryDomainRevision:
        history = self._history.get(query_domain_id)
        if not history:
            raise QueryDomainError(f"unknown query domain: {query_domain_id}")
        return history[-1]

    def _next(self, query_domain_id: str, **changes: Any) -> QueryDomainRevision:
        previous = self.latest(query_domain_id)
        revision_number = len(self._history[query_domain_id]) + 1
        candidate = replace(
            previous,
            revision_id=f"{query_domain_id}@{revision_number}",
            **changes,
            canonical_digest="",
        )
        fields = {
            "query_domain_id": candidate.query_domain_id,
            "scope_revision": candidate.scope_revision,
            "index_schema_revision": candidate.index_schema_revision,
            "completeness_contract": candidate.completeness_contract,
            "filter_predicate_revision": candidate.filter_predicate_revision,
            "alias_equivalence_regime": candidate.alias_equivalence_regime,
            "visibility_permission_regime": candidate.visibility_permission_regime,
            "mutation_impact_profile_revision": candidate.mutation_impact_profile_revision,
            "query_snapshot_id": candidate.query_snapshot_id,
            "snapshot_complete": candidate.snapshot_complete,
            "opaque": candidate.opaque,
            "visibility_assurance": candidate.visibility_assurance,
            "created_sequence": candidate.created_sequence,
        }
        self._validate_fields(**fields)
        body = {
            "query_domain_id": candidate.query_domain_id,
            "revision_id": candidate.revision_id,
            "scope_revision": candidate.scope_revision,
            "membership_generation": candidate.membership_generation,
            "result_sensitivity_generation": candidate.result_sensitivity_generation,
            "index_schema_revision": candidate.index_schema_revision,
            "completeness_contract": candidate.completeness_contract,
            "filter_predicate_revision": candidate.filter_predicate_revision,
            "alias_equivalence_regime": candidate.alias_equivalence_regime,
            "visibility_permission_regime": candidate.visibility_permission_regime,
            "mutation_impact_profile_revision": candidate.mutation_impact_profile_revision,
            "query_snapshot_id": candidate.query_snapshot_id,
            "snapshot_complete": candidate.snapshot_complete,
            "opaque": candidate.opaque,
            "visibility_assurance": candidate.visibility_assurance,
            "created_sequence": candidate.created_sequence,
        }
        candidate = replace(candidate, canonical_digest=self._digest(body))
        self._history[query_domain_id].append(candidate)
        return candidate

    def revise(self, query_domain_id: str, **changes: Any) -> QueryDomainRevision:
        allowed = {
            "scope_revision",
            "index_schema_revision",
            "completeness_contract",
            "filter_predicate_revision",
            "alias_equivalence_regime",
            "visibility_permission_regime",
            "mutation_impact_profile_revision",
            "query_snapshot_id",
            "snapshot_complete",
            "opaque",
            "visibility_assurance",
            "created_sequence",
        }
        unknown = set(changes).difference(allowed)
        if unknown:
            raise QueryDomainError(f"unsupported query-domain changes: {sorted(unknown)!r}")
        return self._next(query_domain_id, **changes)

    def advance_membership(
        self,
        query_domain_id: str,
        *,
        query_snapshot_id: str,
        created_sequence: int | None = None,
    ) -> QueryDomainRevision:
        previous = self.latest(query_domain_id)
        changes: dict[str, Any] = {
            "membership_generation": previous.membership_generation + 1,
            "result_sensitivity_generation": previous.result_sensitivity_generation + 1,
            "query_snapshot_id": query_snapshot_id,
        }
        if created_sequence is not None:
            changes["created_sequence"] = created_sequence
        return self._next(query_domain_id, **changes)

    def record_member_mutation(
        self,
        query_domain_id: str,
        *,
        predicate_result_may_change: bool,
        query_snapshot_id: str,
        created_sequence: int | None = None,
    ) -> QueryDomainRevision:
        previous = self.latest(query_domain_id)
        if not predicate_result_may_change:
            return previous
        changes: dict[str, Any] = {
            "result_sensitivity_generation": previous.result_sensitivity_generation + 1,
            "query_snapshot_id": query_snapshot_id,
        }
        if created_sequence is not None:
            changes["created_sequence"] = created_sequence
        return self._next(query_domain_id, **changes)

    def current(self, bound_revision: QueryDomainRevision) -> bool:
        try:
            latest = self.latest(bound_revision.query_domain_id)
        except QueryDomainError:
            return False
        return latest.canonical_digest == bound_revision.canonical_digest

    def can_prove_absence(
        self,
        bound_revision: QueryDomainRevision,
        *,
        returned_match_count: int,
        minimum_assurance: float,
    ) -> bool:
        if returned_match_count != 0:
            return False
        if not self.current(bound_revision):
            return False
        return bound_revision.status(minimum_assurance) == QueryDomainStatus.COMPLETE
