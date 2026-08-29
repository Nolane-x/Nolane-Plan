from __future__ import annotations

from dataclasses import dataclass

from .decision_cut import DecisionCutRevision
from .freshness import DependencyStamp, FreshnessDomainLedger


@dataclass(frozen=True, slots=True)
class ArtifactBinding:
    id: str
    kind: str
    produced_sequence: int
    dependency_stamp: DependencyStamp
    decision_cut_id: str


class ArtifactRegistry:
    """Authority-time artifact freshness and causal visibility registry."""

    def __init__(self, freshness: FreshnessDomainLedger) -> None:
        self.freshness = freshness
        self._items: dict[str, ArtifactBinding] = {}

    def register(
        self,
        artifact_id: str,
        kind: str,
        produced_sequence: int,
        dependency_domains: tuple[str, ...],
        decision_cut_id: str,
    ) -> ArtifactBinding:
        if artifact_id in self._items:
            raise ValueError(f"artifact already registered: {artifact_id}")
        stamp = DependencyStamp.capture(self.freshness, dependency_domains)
        item = ArtifactBinding(artifact_id, kind, produced_sequence, stamp, decision_cut_id)
        self._items[artifact_id] = item
        return item

    def get(self, artifact_id: str) -> ArtifactBinding:
        return self._items[artifact_id]

    def current(self, artifact_id: str) -> bool:
        return self.get(artifact_id).dependency_stamp.current(self.freshness)

    def usable_at_cut(self, artifact_id: str, cut: DecisionCutRevision) -> bool:
        item = self.get(artifact_id)
        if not cut.includes_sequence(item.produced_sequence):
            return False
        if not item.dependency_stamp.current(self.freshness):
            return False
        for domain, generation in item.dependency_stamp.generations:
            cut_generation = cut.generation(domain)
            if cut_generation is not None and cut_generation != generation:
                return False
        return True
