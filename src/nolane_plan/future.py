from __future__ import annotations

from dataclasses import dataclass, field

from .types import InvariantViolation, RiskClass

NULL_WORLD_ID = "NULL_WORLD"


@dataclass(frozen=True, slots=True)
class FutureFamily:
    id: str
    predicate: str
    probability: float | None = None
    support: float = 0.0
    assumptions: tuple[str, ...] = ()
    impact: float = 1.0
    residual: bool = False


@dataclass(frozen=True, slots=True)
class StrategicState:
    id: str
    mission_version: int
    obligations: frozenset[str] = frozenset()
    anti_goal_status: frozenset[str] = frozenset()
    irreversible_facts: frozenset[str] = frozenset()
    resources: frozenset[str] = frozenset()
    verification_debt: frozenset[str] = frozenset()


@dataclass(frozen=True, slots=True)
class StrategicTransition:
    id: str
    source_state_id: str
    destination_state_id: str
    action_family: str
    guard: str = "true"
    required_authority: tuple[str, ...] = ()
    risk_class: RiskClass = RiskClass.REVERSIBLE
    rollback: str | None = None


@dataclass(frozen=True, slots=True)
class ConvergenceCertificate:
    source_state_ids: tuple[str, ...]
    target_state_id: str
    same_mission_version: bool = True
    obligations_compatible: bool = True
    anti_goals_compatible: bool = True
    irreversible_facts_compatible: bool = True
    resources_compatible: bool = True
    temporal_compatible: bool = True
    side_effects_resolved: bool = True
    downstream_action_equivalent: bool = True
    belief_difference_irrelevant: bool = True
    actor_regime_compatible: bool = True
    verification_debt_preserved: bool = True
    provenance_preserved: bool = True

    @property
    def valid(self) -> bool:
        return all((
            self.same_mission_version,
            self.obligations_compatible,
            self.anti_goals_compatible,
            self.irreversible_facts_compatible,
            self.resources_compatible,
            self.temporal_compatible,
            self.side_effects_resolved,
            self.downstream_action_equivalent,
            self.belief_difference_irrelevant,
            self.actor_regime_compatible,
            self.verification_debt_preserved,
            self.provenance_preserved,
        ))


class FutureLattice:
    def __init__(self) -> None:
        self.families: dict[str, FutureFamily] = {
            NULL_WORLD_ID: FutureFamily(NULL_WORLD_ID, "none of the enumerated model families adequately explains reality", residual=True, impact=1.0)
        }
        self.states: dict[str, StrategicState] = {}
        self.transitions: dict[str, StrategicTransition] = {}
        self.merge_lineage: dict[str, tuple[str, ...]] = {}

    def add_family(self, family: FutureFamily) -> FutureFamily:
        if family.id == NULL_WORLD_ID and not family.residual:
            raise InvariantViolation("NULL_WORLD must remain residual")
        self.families[family.id] = family
        return family

    def add_state(self, state: StrategicState) -> StrategicState:
        self.states[state.id] = state
        return state

    def add_transition(self, transition: StrategicTransition) -> StrategicTransition:
        if transition.source_state_id not in self.states or transition.destination_state_id not in self.states:
            raise InvariantViolation("transition endpoints must exist")
        self.transitions[transition.id] = transition
        return transition

    def merge(self, certificate: ConvergenceCertificate) -> None:
        if not certificate.valid:
            raise InvariantViolation("unsafe convergence certificate")
        if certificate.target_state_id not in self.states:
            raise InvariantViolation("merge target missing")
        if any(source not in self.states for source in certificate.source_state_ids):
            raise InvariantViolation("merge source missing")
        mission_versions = {self.states[s].mission_version for s in certificate.source_state_ids + (certificate.target_state_id,)}
        if len(mission_versions) != 1:
            raise InvariantViolation("mission versions differ")
        self.merge_lineage[certificate.target_state_id] = certificate.source_state_ids
