from __future__ import annotations

import threading
from pathlib import Path
from typing import Any, Protocol

from .actions import ActionAuthorization, ActionIntent, AuthorityEngine, AuthorityGrant, ExecutionReceipt
from .artifacts import ArtifactRegistry
from .capsule import CapsuleCompiler, DecisionCapsule
from .decision_cut import DecisionCutLedger, DecisionCutRevision
from .evidence import EvidenceLedger, EvidenceRecord
from .execution import ActionTransaction, ActionTransactionLedger, AdapterProfile, TransactionState
from .freshness import FreshnessDomainLedger
from .future import FutureFamily, FutureLattice
from .hashing import digest
from .mission import MissionLedger
from .obligations import ObligationLedger, StrategicObligation
from .persistence import HashJournal, SnapshotStore
from .preparedness import PreparednessLevel, PreparednessProfile
from .principals import InformationItem, PrincipalRegistry
from .query import QuerySnapshotCompletenessReceipt, strong_universal_current
from .recovery import RecoveryController
from .relocation import CandidateRegion, LocationStatus, StateRelocator, StrategicLocationRevision
from .resources import ReservationLedger, SharedCommitment
from .temporal import ReactionWindow
from .types import AuthorizationError, CapsuleError, PlanError, RiskClass
from .verification import BoundCompletionReport, CompletionVerifier


class ExecutionAdapter(Protocol):
    def execute(self, action: ActionIntent, principal_ref: str) -> dict[str, Any]: ...


class PlanKernel:
    """Single correctness-writer reference kernel.

    Wave 2 integrates causal Decision Cuts, authority-time artifact freshness,
    adapter capability binding, durable action transactions, reconciliation,
    strategic relocation and completion-proof freshness into the canonical path.
    """

    _CORE_DOMAINS = ("mission", "canonical", "plan", "evidence", "obligations", "location")

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

        self.freshness = FreshnessDomainLedger()
        for domain in self._CORE_DOMAINS:
            self.freshness.ensure(domain)
        self.decision_cuts = DecisionCutLedger()
        self.artifacts = ArtifactRegistry(self.freshness)
        self.transactions = ActionTransactionLedger()
        self.authorization_transactions: dict[str, str] = {}
        self.adapters: dict[str, AdapterProfile] = {}
        self.reservations = ReservationLedger()
        self.regions: list[CandidateRegion] = []
        self._location_revision = 1
        self.strategic_location = StrategicLocationRevision(LocationStatus.UNLOCATED, (), ())
        self.completion_reports: dict[str, BoundCompletionReport] = {}

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

    def _record(self, event_type: str, payload: dict[str, Any]):
        return self.journal.append(event_type, payload)

    def _bump(self, *domains: str) -> None:
        for domain in domains:
            self.freshness.bump(domain)

    @property
    def writer_sequence(self) -> int:
        return len(self.journal.entries())

    def bump_freshness(self, domain: str) -> int:
        with self._writer_lock:
            generation = self.freshness.bump(domain)
            self._record("freshness.bumped", {"domain": domain, "generation": generation})
            return generation

    def current_cut(self) -> DecisionCutRevision:
        return self.decision_cuts.capture(
            self.writer_sequence,
            self.mission.current.version,
            self.canonical_version,
            self._location_revision,
            self.freshness.generations,
        )

    def register_principal(self, principal_ref: str, allowed_tags: set[str]):
        with self._writer_lock:
            profile = self.principals.register(principal_ref, allowed_tags)
            domain = f"principal:{principal_ref}"
            self.freshness.ensure(domain)
            self._bump(domain, "plan")
            self._record("principal.registered", {"principal_ref": principal_ref, "access_revision": profile.revision})
            return profile

    def update_principal_access(self, principal_ref: str, allowed_tags: set[str]):
        with self._writer_lock:
            profile = self.principals.update_access(principal_ref, allowed_tags)
            self.plan_snapshot_version += 1
            self._bump(f"principal:{principal_ref}", "plan")
            self._record("principal.access_changed", {"principal_ref": principal_ref, "access_revision": profile.revision})
            return profile

    def publish_information(self, item: InformationItem) -> InformationItem:
        with self._writer_lock:
            self.information_items[item.id] = item
            self._bump("plan")
            self._record("information.published", {"item_id": item.id, "tags": sorted(item.tags), "provenance": item.provenance})
            return item

    def observe_information(self, principal_ref: str, item_id: str, observed_at: int | float):
        with self._writer_lock:
            if item_id not in self.information_items:
                raise KeyError(item_id)
            record = self.principals.observe(principal_ref, item_id, observed_at)
            self._bump(f"principal:{principal_ref}")
            self._record("information.observed", {"principal_ref": principal_ref, "item_id": item_id, "observed_at": observed_at})
            return record

    def add_evidence(self, record: EvidenceRecord) -> EvidenceRecord:
        with self._writer_lock:
            out = self.evidence.add(record)
            self._bump("evidence")
            self._record("evidence.added", {"evidence_id": record.id, "claim": record.claim, "generation": self.evidence.generation})
            return out

    def add_future_family(self, family: FutureFamily) -> FutureFamily:
        with self._writer_lock:
            out = self.future.add_family(family)
            self.plan_snapshot_version += 1
            self._bump("plan")
            self._record("future.family_added", {"family_id": family.id, "residual": family.residual})
            return out

    def add_obligation(self, obligation: StrategicObligation) -> StrategicObligation:
        with self._writer_lock:
            out = self.obligations.add(obligation)
            self.plan_snapshot_version += 1
            self._bump("obligations", "plan")
            self._record("obligation.added", {"obligation_id": obligation.id, "condition": obligation.condition})
            return out

    def propose_action(self, action: ActionIntent) -> ActionIntent:
        with self._writer_lock:
            self.actions[action.id] = action
            self._record("action.proposed", {
                "action_id": action.id,
                "family": action.family,
                "risk": action.risk_class.value,
                "idempotent": action.idempotent,
                "executor_sensitive": action.executor_sensitive,
            })
            return action

    def add_grant(self, grant: AuthorityGrant) -> AuthorityGrant:
        with self._writer_lock:
            self.grants[grant.id] = grant
            self._record("authority.grant_added", {"grant_id": grant.id, "principal_ref": grant.principal_ref, "scopes": sorted(grant.scopes)})
            return grant

    def register_adapter(self, profile: AdapterProfile) -> AdapterProfile:
        with self._writer_lock:
            current = self.adapters.get(profile.adapter_id)
            if current is not None and profile.revision <= current.revision:
                raise ValueError("adapter revision must increase")
            self.adapters[profile.adapter_id] = profile
            domain = f"adapter:{profile.adapter_id}"
            self.freshness.ensure(domain)
            if current is not None:
                self._bump(domain)
            self._record("adapter.registered", {
                "adapter_id": profile.adapter_id,
                "revision": profile.revision,
                "capability_digest": profile.capability_digest,
            })
            return profile

    def register_region(self, region: CandidateRegion) -> CandidateRegion:
        with self._writer_lock:
            if any(existing.id == region.id for existing in self.regions):
                raise ValueError(region.id)
            self.regions.append(region)
            self._location_revision += 1
            self._bump("location", "plan")
            self._record("region.registered", {"region_id": region.id, "decision_signature": region.decision_signature})
            return region

    def reserve(self, commitment: SharedCommitment) -> SharedCommitment:
        with self._writer_lock:
            out = self.reservations.reserve(commitment)
            self._record("resource.reserved", {
                "resource_id": commitment.resource_id,
                "principal_ref": commitment.principal_ref,
                "start": commitment.start,
                "end": commitment.end,
                "exclusive": commitment.exclusive,
            })
            return out

    def compile_capsule(self, principal_ref: str, decision_time: int | float, action_ids: tuple[str, ...]) -> DecisionCapsule:
        with self._writer_lock:
            items = tuple(self.information_items.values())
            partition = self.principals.build_partition(principal_ref, items, decision_time)
            cut = self.current_cut()
            compiler = CapsuleCompiler(self.principals)
            capsule = compiler.compile(
                principal_ref,
                partition,
                self.mission.current,
                self.canonical_version,
                action_ids,
                self.evidence.generation,
                self.plan_snapshot_version,
                decision_cut_id=cut.id,
            )
            self.capsules[capsule.id] = capsule
            principal_domain = f"principal:{principal_ref}"
            self.freshness.ensure(principal_domain)
            self.artifacts.register(
                capsule.id,
                "decision_capsule",
                cut.commit_frontier_sequence,
                ("mission", "canonical", "plan", "evidence", principal_domain),
                cut.id,
            )
            self._record("capsule.compiled", {
                "capsule_id": capsule.id,
                "principal_ref": principal_ref,
                "partition": partition.digest,
                "decision_cut_id": cut.id,
            })
            return capsule

    def validate_capsule(self, capsule_id: str, principal_ref: str) -> bool:
        with self._writer_lock:
            capsule = self.capsules[capsule_id]
            partition = self.principals.build_partition(principal_ref, self.information_items.values(), capsule.decision_time)
            CapsuleCompiler(self.principals).validate(
                capsule,
                principal_ref,
                partition,
                self.mission.current,
                self.canonical_version,
            )
            cut = self.decision_cuts.get(capsule.decision_cut_id)
            if not self.artifacts.usable_at_cut(capsule.id, cut):
                raise CapsuleError("capsule dependency/cut authority is stale")
            return True

    def _assert_policy_gate(
        self,
        action: ActionIntent,
        query_receipts: tuple[QuerySnapshotCompletenessReceipt, ...],
        preparedness: PreparednessProfile | None,
        reaction_window: ReactionWindow | None,
    ) -> None:
        for receipt in query_receipts:
            if not strong_universal_current(receipt, self.freshness, 0.8):
                raise AuthorizationError("universal/absence proof is incomplete or stale")
        if preparedness is not None:
            required = PreparednessLevel.EXECUTABLE if action.risk_class != RiskClass.REVERSIBLE else PreparednessLevel.SCHEMA
            if not preparedness.satisfies(required):
                raise AuthorizationError("preparedness floor not satisfied")
        if reaction_window is not None and not reaction_window.schedulable():
            raise AuthorizationError("reaction window is not schedulable")

    def _assert_no_unresolved_duplicate(self, action: ActionIntent, acting_principal_ref: str) -> None:
        if action.idempotent:
            return
        for tx in self.transactions.all():
            if tx.action_id == action.id and tx.principal_ref == acting_principal_ref and tx.state == TransactionState.RECONCILIATION_REQUIRED:
                raise AuthorizationError("non-idempotent action has unresolved prior dispatch")

    def authorize(
        self,
        action_id: str,
        acting_principal_ref: str,
        grant_ids: tuple[str, ...],
        now: int | float,
        *,
        capsule_id: str | None = None,
        adapter_id: str | None = None,
        query_receipts: tuple[QuerySnapshotCompletenessReceipt, ...] = (),
        preparedness: PreparednessProfile | None = None,
        reaction_window: ReactionWindow | None = None,
    ) -> ActionAuthorization:
        with self._writer_lock:
            action = self.actions[action_id]
            self._assert_no_unresolved_duplicate(action, acting_principal_ref)
            self._assert_policy_gate(action, query_receipts, preparedness, reaction_window)

            if capsule_id is not None:
                self.validate_capsule(capsule_id, acting_principal_ref)
                capsule = self.capsules[capsule_id]
                if action_id not in capsule.action_ids:
                    raise AuthorizationError("action is not projected into the decision capsule")
                cut = self.decision_cuts.get(capsule.decision_cut_id)
            else:
                cut = self.current_cut()

            adapter_revision = None
            if adapter_id is not None:
                profile = self.adapters.get(adapter_id)
                if profile is None:
                    raise AuthorizationError("unknown adapter profile")
                profile.require_for(action.risk_class, executor_sensitive=action.executor_sensitive)
                adapter_revision = profile.revision
            elif action.executor_sensitive:
                raise AuthorizationError("executor-sensitive action requires adapter binding")

            grants = tuple(self.grants[g] for g in grant_ids)
            authorization = self.authority.authorize(
                action,
                acting_principal_ref,
                grants,
                self.mission.current.version,
                self.canonical_version,
                now,
                decision_cut_id=cut.id,
                capsule_id=capsule_id,
                adapter_id=adapter_id,
                adapter_revision=adapter_revision,
            )
            self.authorizations[authorization.id] = authorization
            tx_id = digest({"authorization_id": authorization.id, "action_id": action.id, "principal": acting_principal_ref})[:24]
            tx = self.transactions.authorized(tx_id, action.id, authorization.id, acting_principal_ref, action.idempotent)
            self.authorization_transactions[authorization.id] = tx.id
            self._record("action.authorized", {
                "authorization_id": authorization.id,
                "action_id": action_id,
                "acting_principal_ref": acting_principal_ref,
                "decision_cut_id": cut.id,
                "capsule_id": capsule_id,
                "adapter_id": adapter_id,
                "adapter_revision": adapter_revision,
                "transaction_id": tx.id,
            })
            return authorization

    def transaction_for_authorization(self, authorization_id: str) -> ActionTransaction:
        return self.transactions.get(self.authorization_transactions[authorization_id])

    def _adapter_identity(self, adapter: ExecutionAdapter, authorization: ActionAuthorization) -> tuple[str | None, int | None]:
        adapter_id = getattr(adapter, "adapter_id", None)
        adapter_revision = getattr(adapter, "adapter_revision", None)
        if authorization.adapter_id is None:
            return adapter_id, adapter_revision
        if adapter_id is None:
            adapter_id = authorization.adapter_id
        if adapter_revision is None:
            adapter_revision = authorization.adapter_revision
        return adapter_id, adapter_revision

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
            adapter_id, adapter_revision = self._adapter_identity(adapter, authorization)
            if not self.authority.dispatch_eligible(
                authorization,
                presented_principal_ref,
                grants,
                self.mission.current.version,
                self.canonical_version,
                now,
                adapter_id,
                adapter_revision,
            ):
                raise AuthorizationError("dispatch principal/freshness/authority/adapter check failed")
            if authorization.adapter_id is not None:
                current_profile = self.adapters.get(authorization.adapter_id)
                if current_profile is None or current_profile.revision != authorization.adapter_revision:
                    raise AuthorizationError("adapter capability revision is stale")
                current_profile.require_for(action.risk_class, executor_sensitive=action.executor_sensitive)
            if not self.recovery.can_execute(action.risk_class, emergency_authorized):
                raise AuthorizationError("recovery quarantine blocks consequential action")

            tx = self.transaction_for_authorization(authorization_id)
            self.transactions.assert_retry_allowed(tx.id)
            effective_adapter_id = adapter_id or "unbound-adapter"
            effective_adapter_revision = adapter_revision or 0
            self.transactions.record_dispatch(tx.id, effective_adapter_id, effective_adapter_revision)
            self._record("action.dispatch_recorded", {
                "transaction_id": tx.id,
                "authorization_id": authorization_id,
                "action_id": action.id,
                "principal_ref": presented_principal_ref,
                "adapter_id": effective_adapter_id,
                "adapter_revision": effective_adapter_revision,
            })

            try:
                raw = adapter.execute(action, presented_principal_ref)
            except Exception as exc:
                self.transactions.record_unknown_outcome(tx.id, str(exc))
                self._record("action.reconciliation_required", {
                    "transaction_id": tx.id,
                    "reason": str(exc),
                    "non_idempotent": not action.idempotent,
                })
                raise

            executing = raw.get("executing_principal_ref")
            if executing != authorization.acting_principal_ref:
                self.transactions.record_unknown_outcome(tx.id, "execution receipt principal mismatch")
                self._record("action.reconciliation_required", {
                    "transaction_id": tx.id,
                    "reason": "execution receipt principal mismatch",
                    "non_idempotent": not action.idempotent,
                })
                raise AuthorizationError("execution receipt principal mismatch")
            if raw.get("outcome_known", True) is False:
                self.transactions.record_unknown_outcome(tx.id, "adapter reported unknown outcome")
                self._record("action.reconciliation_required", {"transaction_id": tx.id, "reason": "adapter reported unknown outcome"})
                raise PlanError("external action outcome is unknown; reconciliation required")

            self.transactions.record_outcome(tx.id)
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
            self._record("action.outcome_observed", {"receipt_id": receipt.id, "transport_ok": transport_ok, "postconditions_verified": verified, "executing_principal_ref": executing, "transaction_id": tx.id})
            if transport_ok and verified:
                self._commit_action_patch(tx.id, patch, receipt.id)
            return receipt

    def _commit_action_patch(self, transaction_id: str, patch: dict[str, Any], receipt_id: str | None = None) -> None:
        self.canonical_state.update(patch)
        self.canonical_version += 1
        self.plan_snapshot_version += 1
        self._bump("canonical", "plan")
        self.transactions.commit(transaction_id)
        self._record("canonical.committed", {
            "canonical_version": self.canonical_version,
            "state_patch": patch,
            "receipt_id": receipt_id,
            "transaction_id": transaction_id,
        })
        self._relocate_after_commit()

    def reconcile_action(
        self,
        authorization_id: str,
        *,
        outcome_applied: bool,
        state_patch: dict[str, Any] | None = None,
        trusted: bool,
    ) -> ActionTransaction:
        with self._writer_lock:
            tx = self.transaction_for_authorization(authorization_id)
            reconciled = self.transactions.reconcile(tx.id, outcome_applied, trusted)
            self._record("action.reconciled", {
                "transaction_id": tx.id,
                "outcome_applied": outcome_applied,
                "trusted": trusted,
            })
            if outcome_applied:
                self._commit_action_patch(tx.id, dict(state_patch or {}), None)
            return self.transactions.get(tx.id)

    def _relocate_after_commit(self) -> StrategicLocationRevision:
        if not self.regions:
            return self.strategic_location
        location = StateRelocator(self.regions).locate(self.canonical_state)
        self.strategic_location = location
        self._location_revision += 1
        self._bump("location")
        self._record("state.relocated", {
            "status": location.status.value,
            "region_ids": list(location.region_ids),
            "decision_signatures": list(location.decision_signatures),
        })
        if location.status == LocationStatus.UNLOCATED:
            state = self.recovery.enter_model_class_uncertain("canonical state is outside registered strategic regions", 1.0)
            self._record("recovery.model_class_uncertain", {
                "reason": state.reason,
                "residual_weight": state.residual_weight,
                "generation": state.generation,
            })
        return location

    def verify_completion(self, anti_goal_violations: tuple[str, ...]) -> BoundCompletionReport:
        with self._writer_lock:
            base = CompletionVerifier().verify(self.mission.current, self.canonical_state, self.obligations, anti_goal_violations)
            cut = self.current_cut()
            artifact_id = digest({
                "kind": "completion",
                "cut": cut.id,
                "complete": base.complete,
                "missing": base.missing_success_conditions,
                "open_hard": base.open_hard_obligations,
                "violations": base.anti_goal_violations,
            })[:24]
            report = BoundCompletionReport(
                base.complete,
                base.missing_success_conditions,
                base.open_hard_obligations,
                base.anti_goal_violations,
                artifact_id,
                cut.id,
            )
            self.artifacts.register(
                artifact_id,
                "completion_report",
                cut.commit_frontier_sequence,
                ("mission", "canonical", "obligations"),
                cut.id,
            )
            self.completion_reports[artifact_id] = report
            self._record("completion.verified", {"artifact_id": artifact_id, "decision_cut_id": cut.id, "complete": report.complete})
            return report

    def revise_mission(self, **changes):
        with self._writer_lock:
            updated = self.mission.revise(**changes)
            self.plan_snapshot_version += 1
            self._bump("mission", "plan")
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
            "strategic_location": {
                "status": self.strategic_location.status.value,
                "region_ids": list(self.strategic_location.region_ids),
                "decision_signatures": list(self.strategic_location.decision_signatures),
                "revision": self._location_revision,
            },
            "freshness_generations": dict(self.freshness.generations),
            "transactions": [
                {
                    "id": tx.id,
                    "action_id": tx.action_id,
                    "authorization_id": tx.authorization_id,
                    "principal_ref": tx.principal_ref,
                    "idempotent": tx.idempotent,
                    "state": tx.state.value,
                    "adapter_id": tx.adapter_id,
                    "adapter_revision": tx.adapter_revision,
                    "detail": tx.detail,
                }
                for tx in self.transactions.all()
            ],
        }

    def save_snapshot(self) -> dict[str, Any]:
        with self._writer_lock:
            state = self.snapshot_state()
            self.snapshots.save(state)
            self._record("snapshot.saved", {"snapshot_digest": digest(state)})
            return state
