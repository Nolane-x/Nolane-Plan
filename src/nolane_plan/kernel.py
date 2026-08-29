from __future__ import annotations

import threading
from pathlib import Path
from typing import Any, Protocol

from .actions import ActionAuthorization, ActionIntent, AuthorityEngine, AuthorityGrant, ExecutionReceipt
from .capsule import CapsuleCompiler, DecisionCapsule
from .evidence import EvidenceLedger, EvidenceRecord
from .future import FutureFamily, FutureLattice
from .hashing import digest
from .mission import MissionLedger
from .obligations import ObligationLedger, StrategicObligation
from .persistence import HashJournal, SnapshotStore
from .principals import InformationItem, PrincipalRegistry
from .recovery import RecoveryController
from .types import AuthorizationError, PlanError


class ExecutionAdapter(Protocol):
    def execute(self, action: ActionIntent, principal_ref: str) -> dict[str, Any]: ...


class PlanKernel:
    """Single correctness-writer reference kernel.

    All correctness-significant mutation is serialized by `_writer_lock` and
    journaled. Speculative/model outputs are stored separately until promoted
    through typed kernel operations.
    """

    def __init__(self, root: Path, mission: MissionLedger):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._writer_lock = threading.RLock()
        self.mission = mission
        self.canonical_state: dict[str, Any] = {}
        self.canonical_version = 1
        self.plan_snapshot_version = 1
        self.principals = PrincipalRegistry()
        self.evidence = EvidenceLedger()
        self.obligations = ObligationLedger()
        self.future = FutureLattice()
        self.recovery = RecoveryController()
        self.authority = AuthorityEngine()
        self.information_items: dict[str, InformationItem] = {}
        self.actions: dict[str, ActionIntent] = {}
        self.grants: dict[str, AuthorityGrant] = {}
        self.capsules: dict[str, DecisionCapsule] = {}
        self.authorizations: dict[str, ActionAuthorization] = {}
        self.receipts: dict[str, ExecutionReceipt] = {}
        self.model_proposals: dict[str, dict[str, Any]] = {}
        self.journal = HashJournal(self.root / "journal.jsonl")
        self.snapshots = SnapshotStore(self.root / "snapshot.json")

    @classmethod
    def create(
        cls,
        root: Path,
        objective: str,
        success_conditions: tuple[str, ...] = (),
        hard_constraints: tuple[str, ...] = (),
        anti_goals: tuple[str, ...] = (),
    ) -> "PlanKernel":
        kernel = cls(Path(root), MissionLedger.create(objective, success_conditions, hard_constraints, anti_goals=anti_goals))
        kernel._record("mission.created", {"mission_version": kernel.mission.current.version, "objective": objective})
        return kernel

    def _record(self, event_type: str, payload: dict[str, Any]) -> None:
        self.journal.append(event_type, payload)

    @property
    def writer_sequence(self) -> int:
        return len(self.journal.entries())

    def register_principal(self, principal_ref: str, allowed_tags: set[str]):
        with self._writer_lock:
            profile = self.principals.register(principal_ref, allowed_tags)
            self._record("principal.registered", {"principal_ref": principal_ref, "access_revision": profile.revision})
            return profile

    def update_principal_access(self, principal_ref: str, allowed_tags: set[str]):
        with self._writer_lock:
            profile = self.principals.update_access(principal_ref, allowed_tags)
            self.plan_snapshot_version += 1
            self._record("principal.access_changed", {"principal_ref": principal_ref, "access_revision": profile.revision})
            return profile

    def publish_information(self, item: InformationItem) -> InformationItem:
        with self._writer_lock:
            self.information_items[item.id] = item
            self._record("information.published", {"item_id": item.id, "tags": sorted(item.tags), "provenance": item.provenance})
            return item

    def observe_information(self, principal_ref: str, item_id: str, observed_at: int | float):
        with self._writer_lock:
            if item_id not in self.information_items:
                raise KeyError(item_id)
            record = self.principals.observe(principal_ref, item_id, observed_at)
            self._record("information.observed", {"principal_ref": principal_ref, "item_id": item_id, "observed_at": observed_at})
            return record

    def add_evidence(self, record: EvidenceRecord) -> EvidenceRecord:
        with self._writer_lock:
            out = self.evidence.add(record)
            self._record("evidence.added", {"evidence_id": record.id, "claim": record.claim, "generation": self.evidence.generation})
            return out

    def add_future_family(self, family: FutureFamily) -> FutureFamily:
        with self._writer_lock:
            out = self.future.add_family(family)
            self.plan_snapshot_version += 1
            self._record("future.family_added", {"family_id": family.id, "residual": family.residual})
            return out

    def add_obligation(self, obligation: StrategicObligation) -> StrategicObligation:
        with self._writer_lock:
            out = self.obligations.add(obligation)
            self.plan_snapshot_version += 1
            self._record("obligation.added", {"obligation_id": obligation.id, "condition": obligation.condition})
            return out

    def propose_action(self, action: ActionIntent) -> ActionIntent:
        with self._writer_lock:
            self.actions[action.id] = action
            self._record("action.proposed", {"action_id": action.id, "family": action.family, "risk": action.risk_class.value})
            return action

    def add_grant(self, grant: AuthorityGrant) -> AuthorityGrant:
        with self._writer_lock:
            self.grants[grant.id] = grant
            self._record("authority.grant_added", {"grant_id": grant.id, "principal_ref": grant.principal_ref, "scopes": sorted(grant.scopes)})
            return grant

    def compile_capsule(self, principal_ref: str, decision_time: int | float, action_ids: tuple[str, ...]) -> DecisionCapsule:
        with self._writer_lock:
            items = tuple(self.information_items.values())
            partition = self.principals.build_partition(principal_ref, items, decision_time)
            compiler = CapsuleCompiler(self.principals)
            capsule = compiler.compile(
                principal_ref,
                partition,
                self.mission.current,
                self.canonical_version,
                action_ids,
                self.evidence.generation,
                self.plan_snapshot_version,
            )
            self.capsules[capsule.id] = capsule
            self._record("capsule.compiled", {"capsule_id": capsule.id, "principal_ref": principal_ref, "partition": partition.digest})
            return capsule

    def validate_capsule(self, capsule_id: str, principal_ref: str) -> bool:
        with self._writer_lock:
            capsule = self.capsules[capsule_id]
            partition = self.principals.build_partition(principal_ref, self.information_items.values(), capsule.decision_time)
            return CapsuleCompiler(self.principals).validate(capsule, principal_ref, partition, self.mission.current, self.canonical_version)

    def authorize(self, action_id: str, acting_principal_ref: str, grant_ids: tuple[str, ...], now: int | float) -> ActionAuthorization:
        with self._writer_lock:
            action = self.actions[action_id]
            grants = tuple(self.grants[g] for g in grant_ids)
            authorization = self.authority.authorize(action, acting_principal_ref, grants, self.mission.current.version, self.canonical_version, now)
            self.authorizations[authorization.id] = authorization
            self._record("action.authorized", {"authorization_id": authorization.id, "action_id": action_id, "acting_principal_ref": acting_principal_ref})
            return authorization

    def dispatch(
        self,
        authorization_id: str,
        presented_principal_ref: str,
        adapter: ExecutionAdapter,
        now: int | float,
        emergency_authorized: bool = False,
    ) -> ExecutionReceipt:
        with self._writer_lock:
            authorization = self.authorizations[authorization_id]
            action = self.actions[authorization.action_id]
            grants = tuple(self.grants[g] for g in authorization.grant_refs)
            if not self.authority.dispatch_eligible(authorization, presented_principal_ref, grants, self.mission.current.version, self.canonical_version, now):
                raise AuthorizationError("dispatch principal/freshness/authority check failed")
            if not self.recovery.can_execute(action.risk_class, emergency_authorized):
                raise AuthorizationError("recovery quarantine blocks consequential action")
            self._record("action.execution_started", {"authorization_id": authorization_id, "action_id": action.id, "principal_ref": presented_principal_ref})
            raw = adapter.execute(action, presented_principal_ref)
            executing = raw.get("executing_principal_ref")
            if executing != authorization.acting_principal_ref:
                raise AuthorizationError("execution receipt principal mismatch")
            transport_ok = bool(raw.get("ok"))
            verified = bool(raw.get("postconditions_verified"))
            patch = dict(raw.get("state_patch") or {})
            receipt = ExecutionReceipt(
                digest({"auth": authorization_id, "action": action.id, "principal": executing, "now": now, "patch": patch})[:24],
                action.id,
                authorization_id,
                executing,
                transport_ok,
                verified,
                patch,
                now,
            )
            self.receipts[receipt.id] = receipt
            self._record("action.outcome_observed", {"receipt_id": receipt.id, "transport_ok": transport_ok, "postconditions_verified": verified, "executing_principal_ref": executing})
            if transport_ok and verified:
                self.canonical_state.update(patch)
                self.canonical_version += 1
                self.plan_snapshot_version += 1
                self._record("canonical.committed", {"canonical_version": self.canonical_version, "state_patch": patch, "receipt_id": receipt.id})
            return receipt

    def revise_mission(self, **changes):
        with self._writer_lock:
            updated = self.mission.revise(**changes)
            self.plan_snapshot_version += 1
            self._record("mission.revised", {"mission_version": updated.version, "objective": updated.objective})
            return updated

    def submit_model_proposal(self, proposal: dict[str, Any]) -> str:
        with self._writer_lock:
            proposal_id = digest({"proposal": proposal, "sequence": self.writer_sequence + 1})[:24]
            self.model_proposals[proposal_id] = dict(proposal)
            self._record("model.proposal_received", {"proposal_id": proposal_id})
            return proposal_id

    def report_model_class_anomaly(self, reason: str, residual_weight: float):
        with self._writer_lock:
            state = self.recovery.enter_model_class_uncertain(reason, residual_weight)
            self.plan_snapshot_version += 1
            self._record("recovery.model_class_uncertain", {"reason": reason, "residual_weight": state.residual_weight, "generation": state.generation})
            return state

    def snapshot_state(self) -> dict[str, Any]:
        return {
            "mission": {"version": self.mission.current.version, "objective": self.mission.current.objective},
            "canonical_version": self.canonical_version,
            "canonical_state": self.canonical_state,
            "plan_snapshot_version": self.plan_snapshot_version,
            "journal_head": self.journal.head,
            "future_family_ids": sorted(self.future.families),
            "open_obligation_ids": sorted(o.id for o in self.obligations.open()),
            "recovery": {"mode": self.recovery.state.mode.value, "residual_weight": self.recovery.state.residual_weight},
        }

    def save_snapshot(self) -> dict[str, Any]:
        with self._writer_lock:
            state = self.snapshot_state()
            self.snapshots.save(state)
            self._record("snapshot.saved", {"snapshot_digest": digest(state)})
            return state
