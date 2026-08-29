from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .hashing import digest


@dataclass(frozen=True, slots=True)
class DecisionCutRevision:
    """Prefix-closed causal authority view for the serialized Plan Kernel."""

    id: str
    revision: int
    commit_frontier_sequence: int
    mission_revision: int
    canonical_state_revision: int
    strategic_location_revision: int
    source_generations: tuple[tuple[str, int], ...]

    def includes_sequence(self, sequence: int) -> bool:
        return 0 <= sequence <= self.commit_frontier_sequence

    def generation(self, domain: str) -> int | None:
        return dict(self.source_generations).get(domain)


class DecisionCutLedger:
    def __init__(self) -> None:
        self._items: dict[str, DecisionCutRevision] = {}
        self._revision = 0

    def capture(
        self,
        commit_frontier_sequence: int,
        mission_revision: int,
        canonical_state_revision: int,
        strategic_location_revision: int,
        source_generations: Mapping[str, int],
    ) -> DecisionCutRevision:
        if commit_frontier_sequence < 0:
            raise ValueError("commit frontier cannot be negative")
        self._revision += 1
        generations = tuple(sorted((str(k), int(v)) for k, v in source_generations.items()))
        body = {
            "revision": self._revision,
            "frontier": commit_frontier_sequence,
            "mission": mission_revision,
            "canonical": canonical_state_revision,
            "location": strategic_location_revision,
            "generations": generations,
        }
        cut = DecisionCutRevision(
            digest(body)[:24],
            self._revision,
            commit_frontier_sequence,
            mission_revision,
            canonical_state_revision,
            strategic_location_revision,
            generations,
        )
        self._items[cut.id] = cut
        return cut

    def get(self, cut_id: str) -> DecisionCutRevision:
        return self._items[cut_id]

    def all(self) -> tuple[DecisionCutRevision, ...]:
        return tuple(self._items.values())
