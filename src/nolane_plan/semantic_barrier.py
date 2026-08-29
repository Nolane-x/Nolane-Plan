from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any, Iterable

from .freshness import FreshnessDomainLedger
from .proof_dependencies import DependencyFreshnessVector
from .types import PlanError


class SemanticClosureError(PlanError):
    """Raised when a semantic mutation cannot be invalidated soundly."""


@dataclass(frozen=True, slots=True)
class MutationImpactProfileRevision:
    revision_id: str
    source_id: str
    affected_domains: tuple[str, ...]
    coverage_complete: bool
    conservative_fallback_domains: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.revision_id.strip() or not self.source_id.strip():
            raise SemanticClosureError("impact profile revision and source id must be non-empty")
        if not self.coverage_complete and not self.conservative_fallback_domains:
            # Such a profile can exist as evidence of opacity, but cannot authorize mutation.
            return


@dataclass(frozen=True, slots=True)
class SemanticSourceRevision:
    source_id: str
    revision_id: str
    value: Any
    linearization_sequence: int


@dataclass(frozen=True, slots=True)
class SemanticMutationReceipt:
    source_id: str
    previous_revision_id: str
    new_revision_id: str
    impact_profile_revision: str
    affected_domains: tuple[str, ...]
    before_generations: tuple[tuple[str, int], ...]
    after_generations: tuple[tuple[str, int], ...]
    linearization_sequence: int


class SemanticClosureBarrier:
    """Linearizes canonical semantic mutation and all soundly affected invalidations."""

    def __init__(
        self,
        freshness: FreshnessDomainLedger,
        writer_lock: threading.RLock | None = None,
    ) -> None:
        self.freshness = freshness
        self._lock = writer_lock or threading.RLock()
        self._sources: dict[str, SemanticSourceRevision] = {}
        self._sequence = 0

    def register_source(self, source_id: str, *, revision_id: str, value: Any) -> SemanticSourceRevision:
        if not source_id.strip() or not revision_id.strip():
            raise SemanticClosureError("source id and revision id must be non-empty")
        with self._lock:
            if source_id in self._sources:
                raise SemanticClosureError(f"semantic source already registered: {source_id}")
            self._sequence += 1
            source = SemanticSourceRevision(source_id, revision_id, value, self._sequence)
            self._sources[source_id] = source
            return source

    def read_source(self, source_id: str) -> SemanticSourceRevision:
        with self._lock:
            try:
                return self._sources[source_id]
            except KeyError as exc:
                raise SemanticClosureError(f"unknown semantic source: {source_id}") from exc

    def read_consistent(self, source_id: str, domains: Iterable[str]):
        with self._lock:
            source = self.read_source(source_id)
            generations = tuple(self.freshness.generation(domain) for domain in domains)
            if len(generations) == 1:
                return source.revision_id, generations[0]
            return source.revision_id, generations

    def mutate(
        self,
        source_id: str,
        *,
        new_revision_id: str,
        new_value: Any,
        impact_profile: MutationImpactProfileRevision,
    ) -> SemanticMutationReceipt:
        with self._lock:
            current = self.read_source(source_id)
            if impact_profile.source_id != source_id:
                raise SemanticClosureError("mutation impact profile is bound to a different source")
            if not new_revision_id.strip() or new_revision_id == current.revision_id:
                raise SemanticClosureError("semantic source revision must advance")
            if not impact_profile.coverage_complete and not impact_profile.conservative_fallback_domains:
                raise SemanticClosureError(
                    "mutation impact is incomplete and has no conservative invalidation fallback"
                )

            domains = tuple(
                sorted(
                    {
                        *(str(domain) for domain in impact_profile.affected_domains if str(domain)),
                        *(str(domain) for domain in impact_profile.conservative_fallback_domains if str(domain)),
                    }
                )
            )
            if impact_profile.coverage_complete and not domains:
                # A complete profile may explicitly prove no correctness-bearing dependencies.
                domains = ()
            before = tuple((domain, self.freshness.generation(domain)) for domain in domains)

            # Source replacement and invalidation generation advances are one critical section.
            self._sequence += 1
            self._sources[source_id] = SemanticSourceRevision(
                source_id,
                new_revision_id,
                new_value,
                self._sequence,
            )
            for domain in domains:
                self.freshness.bump(domain)
            after = tuple((domain, self.freshness.generation(domain)) for domain in domains)
            return SemanticMutationReceipt(
                source_id=source_id,
                previous_revision_id=current.revision_id,
                new_revision_id=new_revision_id,
                impact_profile_revision=impact_profile.revision_id,
                affected_domains=domains,
                before_generations=before,
                after_generations=after,
                linearization_sequence=self._sequence,
            )

    def artifact_current(
        self,
        vector: DependencyFreshnessVector,
        *,
        cached_valid: bool | None = None,
    ) -> bool:
        del cached_valid
        with self._lock:
            return vector.current(self.freshness)
