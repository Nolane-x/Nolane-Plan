from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from .hashing import digest
from .lineage import (
    CanonicalLineageRevision,
    LineageError,
    LineageRegistry,
    SemanticRegimeKind,
    SemanticRegimeRevision,
)
from .types import AuthorizationError


_SCHEMA_LOGICAL_ID = "schema:nolane-plan"
_DEFAULT_REGIME_PROVENANCE = ("runtime:wave7-bootstrap",)


@dataclass(frozen=True, slots=True)
class AuthorizationLineageBinding:
    authorization_id: str
    mission_revision_id: str
    canonical_state_revision_id: str
    action_revision_id: str
    grant_revision_ids: tuple[str, ...]
    regime_revisions: tuple[tuple[str, str], ...]
    created_sequence: int
    canonical_digest: str

    @classmethod
    def create(
        cls,
        *,
        authorization_id: str,
        mission_revision_id: str,
        canonical_state_revision_id: str,
        action_revision_id: str,
        grant_revision_ids: Iterable[str],
        regime_revisions: Iterable[tuple[str, str]],
        created_sequence: int,
    ) -> "AuthorizationLineageBinding":
        grants = tuple(sorted({str(ref) for ref in grant_revision_ids if str(ref)}))
        regimes = tuple(sorted((str(kind), str(ref)) for kind, ref in regime_revisions))
        body = {
            "authorization_id": authorization_id,
            "mission_revision_id": mission_revision_id,
            "canonical_state_revision_id": canonical_state_revision_id,
            "action_revision_id": action_revision_id,
            "grant_revision_ids": grants,
            "regime_revisions": regimes,
            "created_sequence": int(created_sequence),
        }
        return cls(
            authorization_id=authorization_id,
            mission_revision_id=mission_revision_id,
            canonical_state_revision_id=canonical_state_revision_id,
            action_revision_id=action_revision_id,
            grant_revision_ids=grants,
            regime_revisions=regimes,
            created_sequence=int(created_sequence),
            canonical_digest=digest(body),
        )


def _mission_payload(self) -> dict[str, Any]:
    mission = self.mission.current
    return {
        "version": mission.version,
        "objective": mission.objective,
        "success_conditions": list(mission.success_conditions),
        "hard_constraints": list(mission.hard_constraints),
        "anti_goals": list(mission.anti_goals),
        "soft_preferences": list(mission.soft_preferences),
        "risk_budget": mission.risk_budget,
    }


def _mission_semantic_digest(self) -> str:
    return digest(_mission_payload(self))


def _canonical_state_semantic_digest(self) -> str:
    return digest(
        {
            "canonical_version": self.canonical_version,
            "canonical_state": self.canonical_state,
        }
    )


def _regime_defaults() -> tuple[tuple[SemanticRegimeKind, str, str, str], ...]:
    return (
        (
            SemanticRegimeKind.SCHEMA,
            _SCHEMA_LOGICAL_ID,
            "schema:nolane-plan:v7",
            digest({"schema": "nolane-plan-runtime", "lineage_contract": 7}),
        ),
        (
            SemanticRegimeKind.WORLD_MODEL,
            "world-model:default",
            "world-model:default:r1",
            digest({"world_model": "explicit-default", "assurance": "host-declared"}),
        ),
        (
            SemanticRegimeKind.ENVIRONMENT,
            "environment:default",
            "environment:default:r1",
            digest({"environment": "explicit-default", "assurance": "host-declared"}),
        ),
        (
            SemanticRegimeKind.CANONICALIZATION,
            "canonicalization:default",
            "canonicalization:default:r1",
            digest({"canonicalization": "nolane-plan-default", "revision": 1}),
        ),
        (
            SemanticRegimeKind.SEMANTIC_PROFILE,
            "semantic-profile:default",
            "semantic-profile:default:r1",
            digest({"semantic_profile": "nolane-plan-default", "revision": 1}),
        ),
    )


def _current_regime_id(self, kind: SemanticRegimeKind) -> str:
    return self.lineage.current_regime(kind).revision_id


def _bootstrap_regimes(self) -> None:
    for kind, logical_id, revision_id, semantic_digest in _regime_defaults():
        revision = SemanticRegimeRevision.create(
            regime_kind=kind,
            logical_id=logical_id,
            revision_id=revision_id,
            created_sequence=0,
            parent_revision_id=None,
            semantic_digest=semantic_digest,
            provenance_refs=_DEFAULT_REGIME_PROVENANCE,
        )
        self.lineage.register_regime(revision)
        self.semantic_regimes[kind] = revision.revision_id
        self.freshness.ensure(f"semantic-regime:{kind.value}")


def _new_revision_id(
    self,
    object_family: str,
    logical_id: str,
    semantic_digest: str,
    created_sequence: int,
) -> str:
    token = digest(
        {
            "family": object_family,
            "logical_id": logical_id,
            "semantic_digest": semantic_digest,
            "created_sequence": created_sequence,
        }
    )[:16]
    return f"{object_family}:{logical_id}:r{created_sequence}:{token}"


def _register_lineage(
    self,
    *,
    object_family: str,
    logical_id: str,
    semantic_payload: Any | None = None,
    semantic_digest: str | None = None,
    provenance_refs: Iterable[str] = (),
    debt_refs: Iterable[str] = (),
    validity_regime: str = "ACTIVE",
    parent_revision_ids: Iterable[str] | None = None,
    supersedes_revision_id: str | None = None,
    created_sequence: int | None = None,
    mission_dependency: bool = True,
) -> CanonicalLineageRevision:
    if semantic_digest is None:
        semantic_digest = digest(semantic_payload)
    sequence = self.writer_sequence if created_sequence is None else int(created_sequence)
    try:
        current = self.lineage.current(object_family, logical_id)
    except LineageError:
        current = None
    if current is not None and current.semantic_digest == semantic_digest:
        return current
    if current is not None:
        if parent_revision_ids is None:
            parent_revision_ids = (current.revision_id,)
        if supersedes_revision_id is None:
            supersedes_revision_id = current.revision_id
    elif parent_revision_ids is None:
        parent_revision_ids = ()

    mission_ref = None
    if mission_dependency and object_family != "MissionRevision":
        try:
            mission_ref = self.lineage.current("MissionRevision", "mission").revision_id
        except LineageError:
            mission_ref = None

    revision = CanonicalLineageRevision.create(
        object_family=object_family,
        logical_id=logical_id,
        revision_id=_new_revision_id(self, object_family, logical_id, semantic_digest, sequence),
        schema_version=_current_regime_id(self, SemanticRegimeKind.SCHEMA),
        created_sequence=sequence,
        created_at_wall_time=None,
        mission_revision_dependency=mission_ref,
        plan_revision=max(1, int(self.plan_snapshot_version)),
        world_model_revision=_current_regime_id(self, SemanticRegimeKind.WORLD_MODEL),
        environment_regime_revision=_current_regime_id(self, SemanticRegimeKind.ENVIRONMENT),
        validity_regime=validity_regime,
        parent_revision_ids=tuple(parent_revision_ids),
        provenance_refs=tuple(provenance_refs),
        assurance_profile="KERNEL_ACCEPTED",
        debt_refs=tuple(debt_refs),
        supersedes_revision_id=supersedes_revision_id,
        semantic_digest=semantic_digest,
    )
    return self.lineage.register(revision)


def _bootstrap_lineage(self) -> None:
    _register_lineage(
        self,
        object_family="MissionRevision",
        logical_id="mission",
        semantic_digest=_mission_semantic_digest(self),
        provenance_refs=("kernel:mission-ledger",),
        created_sequence=0,
        mission_dependency=False,
    )
    _register_lineage(
        self,
        object_family="CanonicalState",
        logical_id="canonical-state",
        semantic_digest=_canonical_state_semantic_digest(self),
        provenance_refs=("kernel:canonical-state",),
        created_sequence=0,
    )


def _install_state(self) -> None:
    self.lineage = LineageRegistry()
    self.semantic_regimes: dict[SemanticRegimeKind, str] = {}
    self.authorization_lineage_bindings: dict[str, AuthorizationLineageBinding] = {}
    _bootstrap_regimes(self)
    _bootstrap_lineage(self)


def _action_payload(action) -> dict[str, Any]:
    return {
        "id": action.id,
        "family": action.family,
        "risk_class": action.risk_class.value,
        "parameters": list(action.parameters),
        "preconditions": list(action.preconditions),
        "required_capabilities": list(action.required_capabilities),
        "idempotent": action.idempotent,
        "executor_sensitive": action.executor_sensitive,
    }


def _grant_payload(grant) -> dict[str, Any]:
    return {
        "id": grant.id,
        "principal_ref": grant.principal_ref,
        "scopes": sorted(grant.scopes),
        "expires_at": grant.expires_at,
        "revoked": grant.revoked,
        "risk_classes": sorted(risk.value for risk in grant.risk_classes),
    }


def _future_payload(family) -> dict[str, Any]:
    return {
        "id": family.id,
        "predicate": family.predicate,
        "probability": family.probability,
        "impact": family.impact,
        "residual": family.residual,
        "assumptions": sorted(family.assumptions),
        "support": family.support,
    }


def _obligation_payload(obligation) -> dict[str, Any]:
    return {
        "id": obligation.id,
        "condition": obligation.condition,
        "hard": obligation.hard,
        "deadline": obligation.deadline,
        "required_capability": obligation.required_capability,
        "status": obligation.status.value,
        "lineage": list(obligation.lineage),
    }


def _bind_authorization_lineage(self, authorization) -> AuthorizationLineageBinding:
    # Pre-v7 snapshots restore canonical objects directly rather than through the
    # Wave-7 mutation wrappers. A new authorization after such a restore
    # materializes exact roots from those restored objects. It does not invent
    # historical parents and does not promote an old authorization.
    mission_lineage = _register_lineage(
        self,
        object_family="MissionRevision",
        logical_id="mission",
        semantic_digest=_mission_semantic_digest(self),
        provenance_refs=("snapshot-legacy-materialization", "kernel:mission-ledger"),
        mission_dependency=False,
    )
    canonical_lineage = _register_lineage(
        self,
        object_family="CanonicalState",
        logical_id="canonical-state",
        semantic_digest=_canonical_state_semantic_digest(self),
        provenance_refs=("snapshot-legacy-materialization", "kernel:canonical-state"),
    )
    action = self.actions[authorization.action_id]
    action_lineage = _register_lineage(
        self,
        object_family="ActionIntent",
        logical_id=action.id,
        semantic_payload=_action_payload(action),
        provenance_refs=("snapshot-legacy-materialization", "kernel:action-registry"),
    )
    grant_lineages = tuple(
        _register_lineage(
            self,
            object_family="AuthorityGrant",
            logical_id=grant_id,
            semantic_payload=_grant_payload(self.grants[grant_id]),
            provenance_refs=("snapshot-legacy-materialization", "kernel:authority-registry"),
        ).revision_id
        for grant_id in authorization.grant_refs
    )
    binding = AuthorizationLineageBinding.create(
        authorization_id=authorization.id,
        mission_revision_id=mission_lineage.revision_id,
        canonical_state_revision_id=canonical_lineage.revision_id,
        action_revision_id=action_lineage.revision_id,
        grant_revision_ids=grant_lineages,
        regime_revisions=(
            (kind.value, self.lineage.current_regime(kind).revision_id)
            for kind in SemanticRegimeKind
        ),
        created_sequence=self.writer_sequence,
    )
    self.authorization_lineage_bindings[authorization.id] = binding
    return binding


def _assert_authorization_lineage_current(self, authorization_id: str) -> None:
    binding = self.authorization_lineage_bindings.get(authorization_id)
    if binding is None:
        # v6 snapshot compatibility remains readable until the v7 migration
        # layer classifies historical authority explicitly in Task 5.
        return
    current_regimes = {
        kind.value: self.lineage.current_regime(kind).revision_id
        for kind in SemanticRegimeKind
    }
    if dict(binding.regime_revisions) != current_regimes:
        raise AuthorizationError("authorization semantic-regime lineage is stale")
    if self.lineage.current("MissionRevision", "mission").revision_id != binding.mission_revision_id:
        raise AuthorizationError("authorization mission lineage is stale")
    if self.lineage.current("CanonicalState", "canonical-state").revision_id != binding.canonical_state_revision_id:
        raise AuthorizationError("authorization canonical-state lineage is stale")
    authorization = self.authorizations[authorization_id]
    if self.lineage.current("ActionIntent", authorization.action_id).revision_id != binding.action_revision_id:
        raise AuthorizationError("authorization action lineage is stale")
    current_grants = tuple(
        sorted(
            self.lineage.current("AuthorityGrant", grant_id).revision_id
            for grant_id in authorization.grant_refs
        )
    )
    if current_grants != binding.grant_revision_ids:
        raise AuthorizationError("authorization grant lineage is stale")


def _revise_semantic_regime(
    self,
    kind: str | SemanticRegimeKind,
    *,
    semantic_digest: str,
    provenance_refs: Iterable[str],
) -> SemanticRegimeRevision:
    parsed = SemanticRegimeKind.parse(kind)
    with self._writer_lock:
        current = self.lineage.current_regime(parsed)
        sequence = self.writer_sequence + 1
        revision_id = f"{current.logical_id}:r{sequence}:{digest({'kind': parsed.value, 'semantic': semantic_digest, 'sequence': sequence})[:16]}"
        revision = SemanticRegimeRevision.create(
            regime_kind=parsed,
            logical_id=current.logical_id,
            revision_id=revision_id,
            created_sequence=sequence,
            parent_revision_id=current.revision_id,
            semantic_digest=semantic_digest,
            provenance_refs=tuple(provenance_refs),
        )
        self.lineage.register_regime(revision)
        self.semantic_regimes[parsed] = revision.revision_id
        domain = f"semantic-regime:{parsed.value}"
        generation = self.freshness.bump(domain)
        plan_generation = self.freshness.bump("plan")
        self.plan_snapshot_version += 1
        self._record(
            "semantic.regime_revised",
            {
                "regime_kind": parsed.value,
                "logical_id": revision.logical_id,
                "revision_id": revision.revision_id,
                "parent_revision_id": revision.parent_revision_id,
                "created_sequence": revision.created_sequence,
                "semantic_digest": revision.semantic_digest,
                "provenance_refs": list(revision.provenance_refs),
                "canonical_digest": revision.canonical_digest,
                "freshness_generation": generation,
                "plan_generation": plan_generation,
            },
        )
        return revision


def install_lineage_runtime(kernel_cls) -> None:
    """Install Wave-7 lineage metadata on the existing single-writer kernel."""
    if getattr(kernel_cls, "_wave7_lineage_runtime_installed", False):
        return

    original_init = kernel_cls.__init__
    original_add_future_family = kernel_cls.add_future_family
    original_add_obligation = kernel_cls.add_obligation
    original_propose_action = kernel_cls.propose_action
    original_add_grant = kernel_cls.add_grant
    original_revise_mission = kernel_cls.revise_mission
    original_commit_action_patch = kernel_cls._commit_action_patch
    original_authorize = kernel_cls.authorize
    original_dispatch = kernel_cls.dispatch

    def __init__(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        _install_state(self)

    def add_future_family(self, family):
        with self._writer_lock:
            out = original_add_future_family(self, family)
            _register_lineage(
                self,
                object_family="FutureFamily",
                logical_id=family.id,
                semantic_payload=_future_payload(family),
                provenance_refs=("kernel:future-lattice",),
            )
            return out

    def add_obligation(self, obligation):
        with self._writer_lock:
            out = original_add_obligation(self, obligation)
            _register_lineage(
                self,
                object_family="StrategicObligation",
                logical_id=obligation.id,
                semantic_payload=_obligation_payload(obligation),
                provenance_refs=("kernel:obligation-ledger",),
            )
            return out

    def propose_action(self, action):
        with self._writer_lock:
            out = original_propose_action(self, action)
            _register_lineage(
                self,
                object_family="ActionIntent",
                logical_id=action.id,
                semantic_payload=_action_payload(action),
                provenance_refs=("kernel:action-registry",),
            )
            return out

    def add_grant(self, grant):
        with self._writer_lock:
            out = original_add_grant(self, grant)
            _register_lineage(
                self,
                object_family="AuthorityGrant",
                logical_id=grant.id,
                semantic_payload=_grant_payload(grant),
                provenance_refs=("kernel:authority-registry",),
            )
            return out

    def revise_mission(self, **changes):
        with self._writer_lock:
            previous = self.lineage.current("MissionRevision", "mission")
            out = original_revise_mission(self, **changes)
            _register_lineage(
                self,
                object_family="MissionRevision",
                logical_id="mission",
                semantic_digest=_mission_semantic_digest(self),
                provenance_refs=("kernel:mission-ledger",),
                parent_revision_ids=(previous.revision_id,),
                supersedes_revision_id=previous.revision_id,
                mission_dependency=False,
            )
            return out

    def _commit_action_patch(self, transaction_id, patch, receipt_id=None):
        with self._writer_lock:
            previous = self.lineage.current("CanonicalState", "canonical-state")
            out = original_commit_action_patch(self, transaction_id, patch, receipt_id)
            _register_lineage(
                self,
                object_family="CanonicalState",
                logical_id="canonical-state",
                semantic_digest=_canonical_state_semantic_digest(self),
                provenance_refs=tuple(ref for ref in (receipt_id, transaction_id) if ref),
                parent_revision_ids=(previous.revision_id,),
                supersedes_revision_id=previous.revision_id,
            )
            return out

    def authorize(self, *args, **kwargs):
        with self._writer_lock:
            authorization = original_authorize(self, *args, **kwargs)
            _bind_authorization_lineage(self, authorization)
            return authorization

    def dispatch(self, authorization_id, *args, **kwargs):
        with self._writer_lock:
            _assert_authorization_lineage_current(self, authorization_id)
            return original_dispatch(self, authorization_id, *args, **kwargs)

    kernel_cls.__init__ = __init__
    kernel_cls.add_future_family = add_future_family
    kernel_cls.add_obligation = add_obligation
    kernel_cls.propose_action = propose_action
    kernel_cls.add_grant = add_grant
    kernel_cls.revise_mission = revise_mission
    kernel_cls._commit_action_patch = _commit_action_patch
    kernel_cls.authorize = authorize
    kernel_cls.dispatch = dispatch
    kernel_cls.revise_semantic_regime = _revise_semantic_regime
    kernel_cls._mission_semantic_digest = _mission_semantic_digest
    kernel_cls._canonical_state_semantic_digest = _canonical_state_semantic_digest
    kernel_cls._register_lineage = _register_lineage
    kernel_cls._assert_authorization_lineage_current = _assert_authorization_lineage_current
    kernel_cls._wave7_lineage_runtime_installed = True
