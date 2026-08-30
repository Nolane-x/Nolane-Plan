from __future__ import annotations

import ast
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Iterable

from .types import ReplayError


class ReplayEventClass(str, Enum):
    STATE_REDUCER = "STATE_REDUCER"
    DERIVED_RECOMPUTE = "DERIVED_RECOMPUTE"
    AUDIT_ONLY = "AUDIT_ONLY"
    SNAPSHOT_BOUNDARY = "SNAPSHOT_BOUNDARY"


@dataclass(frozen=True, slots=True)
class ReplayEventSpec:
    event_type: str
    classification: ReplayEventClass
    correctness_significant: bool = True
    reducer_name: str | None = None
    delegate_layer: str | None = None

    def __post_init__(self) -> None:
        if not self.event_type.strip():
            raise ValueError("replay event type must be non-empty")
        if self.classification == ReplayEventClass.STATE_REDUCER and not (
            self.reducer_name or self.delegate_layer
        ):
            raise ValueError("state reducer must declare a reducer or delegate layer")


class ReplayRegistry:
    def __init__(self, specs: Iterable[ReplayEventSpec]) -> None:
        values = tuple(specs)
        by_event: dict[str, ReplayEventSpec] = {}
        for spec in values:
            if spec.event_type in by_event:
                raise ValueError(f"duplicate replay event type: {spec.event_type}")
            by_event[spec.event_type] = spec
        self._specs = values
        self._by_event = by_event

    @property
    def specs(self) -> tuple[ReplayEventSpec, ...]:
        return self._specs

    @property
    def event_types(self) -> frozenset[str]:
        return frozenset(self._by_event)

    def require(
        self,
        event_type: str,
        *,
        correctness_significant: bool = True,
    ) -> ReplayEventSpec | None:
        spec = self._by_event.get(event_type)
        if spec is None:
            if correctness_significant:
                raise ReplayError(f"unregistered correctness-significant replay event: {event_type}")
            return None
        return spec


def discover_recorded_event_types(package_root: Path) -> frozenset[str]:
    """Statically inventory literal `_record("event", ...)` emissions.

    Correctness events are intentionally required to use literal event names. A
    dynamically constructed name would make the replay inventory incomplete by
    construction and therefore fails closed.
    """

    root = Path(package_root)
    discovered: set[str] = set()
    for path in sorted(root.rglob("*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, SyntaxError) as exc:
            raise ReplayError(f"cannot inventory replay events in {path}: {exc}") from exc
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if not (isinstance(func, ast.Attribute) and func.attr == "_record"):
                continue
            if not node.args:
                raise ReplayError(f"_record call without event type in {path}:{node.lineno}")
            event_node = node.args[0]
            if not (isinstance(event_node, ast.Constant) and isinstance(event_node.value, str)):
                raise ReplayError(
                    f"dynamic _record event type is forbidden in {path}:{node.lineno}"
                )
            discovered.add(event_node.value)
    return frozenset(discovered)


def _base(event_type: str, reducer_name: str) -> ReplayEventSpec:
    return ReplayEventSpec(event_type, ReplayEventClass.STATE_REDUCER, True, reducer_name=reducer_name)


def _delegate(event_type: str, layer: str) -> ReplayEventSpec:
    return ReplayEventSpec(event_type, ReplayEventClass.STATE_REDUCER, True, delegate_layer=layer)


_BASE_SPECS = (
    _base("mission.created", "mission_created"),
    _base("mission.revised", "mission_revised"),
    _base("freshness.bumped", "freshness_bumped"),
    _base("principal.registered", "principal_registered"),
    _base("principal.access_changed", "principal_access_changed"),
    _base("information.published", "information_published"),
    _base("information.observed", "information_observed"),
    _base("evidence.added", "evidence_added"),
    _base("future.family_added", "future_family_added"),
    _base("obligation.added", "obligation_added"),
    _base("action.proposed", "action_proposed"),
    _base("authority.grant_added", "authority_grant_added"),
    _base("adapter.registered", "adapter_registered"),
    _base("region.registered", "region_registered"),
    _base("resource.reserved", "resource_reserved"),
    _base("capsule.compiled", "capsule_compiled"),
    _base("action.authorized", "action_authorized"),
    _base("action.dispatch_recorded", "legacy_action_protocol"),
    _base("action.reconciliation_required", "legacy_action_protocol"),
    _base("action.outcome_observed", "action_outcome_observed"),
    _base("canonical.committed", "legacy_action_protocol"),
    _base("action.reconciled", "legacy_action_protocol"),
    _base("state.relocated", "state_relocated"),
    _base("recovery.model_class_uncertain", "recovery_model_class_uncertain"),
    _base("completion.verified", "completion_verified"),
    _base("model.proposal_received", "model_proposal_received"),
    ReplayEventSpec(
        "snapshot.saved",
        ReplayEventClass.SNAPSHOT_BOUNDARY,
        correctness_significant=True,
    ),
)

_TRUST_EVENTS = (
    "principal.identity_bound",
    "principal.identity_revoked",
    "communication.sent",
    "communication.delivered",
    "communication.observed",
    "capsule.identity_bound",
    "action.authorization_identity_bound",
    "action.dispatch_attested",
    "action.reconciled_evidence",
)

_PROOF_EVENTS = (
    "proof.semantic_source_registered",
    "proof.semantic_source_mutated",
    "proof.profile_refs_registered",
    "proof.query_domain_created",
    "proof.query_domain_membership_advanced",
    "proof.query_domain_member_mutated",
    "proof.input_envelope_registered",
    "proof.manifest_captured",
    "proof.support_node_registered",
    "proof.support_set_registered",
    "proof.invalidity_causes_set",
    "proof.authorization_bound",
)

_POLICY_EVENTS = (
    "policy.frontier_registered",
    "policy.partition_registered",
    "policy.epoch_registered",
    "policy.node_registered",
    "policy.selection_registered",
    "policy.sufficiency_registered",
    "policy.seal_registered",
    "policy.executability_registered",
    "policy.authorization_bound",
)

_SCHEDULABILITY_EVENTS = (
    "schedulability.resource_registered",
    "schedulability.job_registered",
    "schedulability.certificate_registered",
    "schedulability.coverage_registered",
    "schedulability.independence_registered",
    "schedulability.robust_preparedness_registered",
    "schedulability.liveness_registered",
    "schedulability.stability_registered",
    "schedulability.edge_activation_registered",
    "schedulability.authorization_bound",
)

_WAVE7_SPECS = (
    _base("semantic.regime_revised", "semantic_regime_revised"),
    _base("migration.schema_root_switched", "migration_schema_root_switched"),
    _base("compaction.representation_committed", "compaction_representation_committed"),
)


DEFAULT_REPLAY_REGISTRY = ReplayRegistry(
    (
        *_BASE_SPECS,
        *(_delegate(event, "trust") for event in _TRUST_EVENTS),
        *(_delegate(event, "proof") for event in _PROOF_EVENTS),
        *(_delegate(event, "policy") for event in _POLICY_EVENTS),
        *(_delegate(event, "schedulability") for event in _SCHEDULABILITY_EVENTS),
        *_WAVE7_SPECS,
    )
)
