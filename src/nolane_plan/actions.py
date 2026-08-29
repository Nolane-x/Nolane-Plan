from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable

from .hashing import digest
from .types import AuthorizationError, RiskClass


@dataclass(frozen=True, slots=True)
class ActionIntent:
    id: str
    family: str
    risk_class: RiskClass = RiskClass.REVERSIBLE
    parameters: tuple[tuple[str, str], ...] = ()
    preconditions: tuple[str, ...] = ()
    required_capabilities: tuple[str, ...] = ()
    idempotent: bool = True
    executor_sensitive: bool = False


@dataclass(frozen=True, slots=True)
class AuthorityGrant:
    id: str
    principal_ref: str
    scopes: frozenset[str]
    expires_at: int | float | None = None
    revoked: bool = False
    risk_classes: frozenset[RiskClass] = frozenset({RiskClass.REVERSIBLE, RiskClass.CONSEQUENTIAL, RiskClass.IRREVERSIBLE})

    def with_revoked(self, revoked: bool = True) -> "AuthorityGrant":
        return replace(self, revoked=revoked)

    def usable(self, principal_ref: str, action: ActionIntent, now: int | float) -> bool:
        return (
            not self.revoked
            and self.principal_ref == principal_ref
            and action.family in self.scopes
            and action.risk_class in self.risk_classes
            and (self.expires_at is None or now <= self.expires_at)
        )


@dataclass(frozen=True, slots=True)
class ActionAuthorization:
    id: str
    action_id: str
    action_family: str
    acting_principal_ref: str
    grant_refs: tuple[str, ...]
    mission_version: int
    canonical_version: int
    issued_at: int | float
    expires_at: int | float | None = None
    decision_cut_id: str | None = None
    capsule_id: str | None = None
    adapter_id: str | None = None
    adapter_revision: int | None = None


@dataclass(frozen=True, slots=True)
class ExecutionReceipt:
    id: str
    action_id: str
    authorization_id: str
    executing_principal_ref: str
    transport_ok: bool
    postconditions_verified: bool
    state_patch: dict
    observed_at: int | float


class AuthorityEngine:
    def authorize(
        self,
        action: ActionIntent,
        acting_principal_ref: str,
        grants: Iterable[AuthorityGrant],
        mission_version: int,
        canonical_version: int,
        now: int | float,
        expires_at: int | float | None = None,
        decision_cut_id: str | None = None,
        capsule_id: str | None = None,
        adapter_id: str | None = None,
        adapter_revision: int | None = None,
    ) -> ActionAuthorization:
        grant_list = tuple(grants)
        usable = tuple(g for g in grant_list if g.usable(acting_principal_ref, action, now))
        if not usable:
            raise AuthorizationError("no principal-compatible grant authorizes action")
        if any(g.principal_ref != acting_principal_ref for g in grant_list):
            raise AuthorizationError("grant/principal composition mismatch")
        body = {
            "action_id": action.id,
            "action_family": action.family,
            "principal": acting_principal_ref,
            "grants": tuple(g.id for g in usable),
            "mission": mission_version,
            "canonical": canonical_version,
            "issued_at": now,
            "decision_cut_id": decision_cut_id,
            "capsule_id": capsule_id,
            "adapter_id": adapter_id,
            "adapter_revision": adapter_revision,
        }
        return ActionAuthorization(
            digest(body)[:24], action.id, action.family, acting_principal_ref,
            tuple(g.id for g in usable), mission_version, canonical_version, now,
            expires_at, decision_cut_id, capsule_id, adapter_id, adapter_revision,
        )

    def dispatch_eligible(
        self,
        authorization: ActionAuthorization,
        presented_principal_ref: str,
        grants: Iterable[AuthorityGrant],
        mission_version: int,
        canonical_version: int,
        now: int | float,
        presented_adapter_id: str | None = None,
        presented_adapter_revision: int | None = None,
    ) -> bool:
        if authorization.acting_principal_ref != presented_principal_ref:
            return False
        if authorization.mission_version != mission_version or authorization.canonical_version != canonical_version:
            return False
        if authorization.expires_at is not None and now > authorization.expires_at:
            return False
        if authorization.adapter_id is not None:
            if presented_adapter_id != authorization.adapter_id:
                return False
            if presented_adapter_revision != authorization.adapter_revision:
                return False
        by_id = {g.id: g for g in grants}
        if not authorization.grant_refs:
            return False
        for gid in authorization.grant_refs:
            grant = by_id.get(gid)
            if grant is None or grant.revoked or grant.principal_ref != authorization.acting_principal_ref:
                return False
            if authorization.action_family not in grant.scopes:
                return False
            if grant.expires_at is not None and now > grant.expires_at:
                return False
        return True
