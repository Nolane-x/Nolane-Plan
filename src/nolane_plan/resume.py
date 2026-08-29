from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from .actions import ActionAuthorization, ActionIntent, AuthorityGrant
from .artifacts import ArtifactBinding
from .capsule import DecisionCapsule
from .decision_cut import DecisionCutRevision
from .evidence import EvidencePolarity, EvidenceRecord
from .execution import ActionTransaction, AdapterProfile, TransactionState
from .freshness import DependencyStamp
from .future import FutureFamily
from .hashing import digest
from .mission import MissionContract, MissionLedger
from .obligations import ObligationStatus, StrategicObligation
from .persistence import HashJournal, SnapshotStore
from .principals import AccessProfile, DeliveryRecord, InformationItem
from .recovery import RecoveryMode, RecoveryState
from .relocation import CandidateRegion, LocationStatus, StrategicLocationRevision
from .types import ReplayError, RiskClass
from .verification import BoundCompletionReport


SNAPSHOT_SCHEMA = "nolane-plan-runtime-snapshot-v2"


def _mission_to_dict(mission: MissionContract) -> dict[str, Any]:
    return {
        "version": mission.version,
        "objective": mission.objective,
        "success_conditions": list(mission.success_conditions),
        "hard_constraints": list(mission.hard_constraints),
        "soft_preferences": list(mission.soft_preferences),
        "anti_goals": list(mission.anti_goals),
        "risk_budget": mission.risk_budget,
    }


def _snapshot_state(self) -> dict[str, Any]:
    return {
        "snapshot_schema": SNAPSHOT_SCHEMA,
        "mission": _mission_to_dict(self.mission.current),
        "canonical_version": self.canonical_version,
        "canonical_state": dict(self.canonical_state),
        "plan_snapshot_version": self.plan_snapshot_version,
        "journal_head": self.journal.head,
        "principals": [
            {
                "principal_ref": p.principal_ref,
                "revision": p.revision,
                "allowed_tags": sorted(p.allowed_tags),
            }
            for p in self.principals._profiles.values()
        ],
        "deliveries": [
            {"item_id": d.item_id, "principal_ref": d.principal_ref, "observed_at": d.observed_at}
            for d in self.principals._deliveries.values()
        ],
        "partition_revision": self.principals._partition_revision,
        "information_items": [
            {
                "id": item.id,
                "payload": item.payload,
                "tags": sorted(item.tags),
                "visible_at": item.visible_at,
                "valid_until": item.valid_until,
                "provenance": item.provenance,
                "assurance": item.assurance,
            }
            for item in self.information_items.values()
        ],
        "evidence_generation": self.evidence.generation,
        "evidence": [
            {
                "id": e.id,
                "claim": e.claim,
                "polarity": e.polarity.value,
                "source_id": e.source_id,
                "lineage_root": e.lineage_root,
                "observed_at": e.observed_at,
                "valid_until": e.valid_until,
                "assurance": e.assurance,
                "revoked": e.revoked,
                "revocation_reason": e.revocation_reason,
            }
            for e in self.evidence.records.values()
        ],
        "obligations": [
            {
                "id": o.id,
                "condition": o.condition,
                "deadline": o.deadline,
                "required_capability": o.required_capability,
                "hard": o.hard,
                "status": o.status.value,
                "lineage": list(o.lineage),
            }
            for o in self.obligations._items.values()
        ],
        "unavailable_principals": sorted(self.obligations.unavailable_principals),
        "future_families": [
            {
                "id": f.id,
                "predicate": f.predicate,
                "probability": f.probability,
                "support": f.support,
                "assumptions": list(f.assumptions),
                "impact": f.impact,
                "residual": f.residual,
            }
            for f in self.future.families.values()
        ],
        "actions": [
            {
                "id": a.id,
                "family": a.family,
                "risk_class": a.risk_class.value,
                "parameters": [list(x) for x in a.parameters],
                "preconditions": list(a.preconditions),
                "required_capabilities": list(a.required_capabilities),
                "idempotent": a.idempotent,
                "executor_sensitive": a.executor_sensitive,
            }
            for a in self.actions.values()
        ],
        "grants": [
            {
                "id": g.id,
                "principal_ref": g.principal_ref,
                "scopes": sorted(g.scopes),
                "expires_at": g.expires_at,
                "revoked": g.revoked,
                "risk_classes": sorted(x.value for x in g.risk_classes),
            }
            for g in self.grants.values()
        ],
        "capsules": [asdict(c) for c in self.capsules.values()],
        "authorizations": [asdict(a) for a in self.authorizations.values()],
        "adapters": [asdict(a) for a in self.adapters.values()],
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
        "authorization_transactions": dict(self.authorization_transactions),
        "freshness_generations": dict(self.freshness.generations),
        "decision_cuts": [
            {
                "id": cut.id,
                "revision": cut.revision,
                "commit_frontier_sequence": cut.commit_frontier_sequence,
                "mission_revision": cut.mission_revision,
                "canonical_state_revision": cut.canonical_state_revision,
                "strategic_location_revision": cut.strategic_location_revision,
                "source_generations": [list(x) for x in cut.source_generations],
            }
            for cut in self.decision_cuts.all()
        ],
        "artifacts": [
            {
                "id": a.id,
                "kind": a.kind,
                "produced_sequence": a.produced_sequence,
                "dependency_generations": [list(x) for x in a.dependency_stamp.generations],
                "decision_cut_id": a.decision_cut_id,
            }
            for a in self.artifacts._items.values()
        ],
        "regions": [
            {"id": r.id, "required_facts": r.required_facts, "decision_signature": r.decision_signature}
            for r in self.regions
        ],
        "strategic_location": {
            "status": self.strategic_location.status.value,
            "region_ids": list(self.strategic_location.region_ids),
            "decision_signatures": list(self.strategic_location.decision_signatures),
            "revision": self._location_revision,
        },
        "recovery": {
            "mode": self.recovery.state.mode.value,
            "reason": self.recovery.state.reason,
            "residual_weight": self.recovery.state.residual_weight,
            "generation": self.recovery.state.generation,
        },
        "completion_reports": [asdict(r) for r in self.completion_reports.values()],
    }


def _save_snapshot(self) -> dict[str, Any]:
    with self._writer_lock:
        state = _snapshot_state(self)
        self.snapshots.save(state)
        self._record("snapshot.saved", {
            "snapshot_schema": SNAPSHOT_SCHEMA,
            "snapshot_digest": digest(state),
            "bound_journal_head": state["journal_head"],
        })
        return state


def _restore_state(kernel, state: dict[str, Any]) -> None:
    if state.get("snapshot_schema") != SNAPSHOT_SCHEMA:
        raise ReplayError("unsupported or missing snapshot schema")

    mission_doc = state["mission"]
    kernel.mission = MissionLedger(MissionContract(
        int(mission_doc["version"]),
        str(mission_doc["objective"]),
        tuple(mission_doc.get("success_conditions", ())),
        tuple(mission_doc.get("hard_constraints", ())),
        tuple(mission_doc.get("soft_preferences", ())),
        tuple(mission_doc.get("anti_goals", ())),
        mission_doc.get("risk_budget"),
    ))
    kernel.canonical_version = int(state["canonical_version"])
    kernel.canonical_state = dict(state.get("canonical_state", {}))
    kernel.plan_snapshot_version = int(state.get("plan_snapshot_version", 1))

    kernel.principals._profiles = {
        p["principal_ref"]: AccessProfile(int(p["revision"]), p["principal_ref"], frozenset(p.get("allowed_tags", ())))
        for p in state.get("principals", ())
    }
    kernel.principals._deliveries = {
        (d["principal_ref"], d["item_id"]): DeliveryRecord(d["item_id"], d["principal_ref"], d["observed_at"])
        for d in state.get("deliveries", ())
    }
    kernel.principals._partition_revision = int(state.get("partition_revision", 0))

    kernel.information_items = {
        item["id"]: InformationItem(
            item["id"], item.get("payload"), frozenset(item.get("tags", ())),
            item.get("visible_at", 0), item.get("valid_until"),
            item.get("provenance", "host"), float(item.get("assurance", 1.0)),
        )
        for item in state.get("information_items", ())
    }

    kernel.evidence.records = {
        e["id"]: EvidenceRecord(
            e["id"], e["claim"], EvidencePolarity(e["polarity"]), e["source_id"],
            e["lineage_root"], e["observed_at"], e.get("valid_until"),
            float(e.get("assurance", 0.5)), bool(e.get("revoked", False)), e.get("revocation_reason"),
        )
        for e in state.get("evidence", ())
    }
    kernel.evidence.generation = int(state.get("evidence_generation", 1))

    kernel.obligations._items = {
        o["id"]: StrategicObligation(
            o["id"], o["condition"], o.get("deadline"), o.get("required_capability"),
            bool(o.get("hard", True)), ObligationStatus(o.get("status", "open")), tuple(o.get("lineage", ())),
        )
        for o in state.get("obligations", ())
    }
    kernel.obligations.unavailable_principals = set(state.get("unavailable_principals", ()))

    kernel.future.families = {
        f["id"]: FutureFamily(
            f["id"], f["predicate"], f.get("probability"), float(f.get("support", 0.0)),
            tuple(f.get("assumptions", ())), float(f.get("impact", 1.0)), bool(f.get("residual", False)),
        )
        for f in state.get("future_families", ())
    }

    kernel.actions = {
        a["id"]: ActionIntent(
            a["id"], a["family"], RiskClass(a.get("risk_class", "reversible")),
            tuple(tuple(x) for x in a.get("parameters", ())), tuple(a.get("preconditions", ())),
            tuple(a.get("required_capabilities", ())), bool(a.get("idempotent", True)),
            bool(a.get("executor_sensitive", False)),
        )
        for a in state.get("actions", ())
    }
    kernel.grants = {
        g["id"]: AuthorityGrant(
            g["id"], g["principal_ref"], frozenset(g.get("scopes", ())), g.get("expires_at"),
            bool(g.get("revoked", False)), frozenset(RiskClass(x) for x in g.get("risk_classes", ("reversible", "consequential", "irreversible"))),
        )
        for g in state.get("grants", ())
    }
    kernel.capsules = {c["id"]: DecisionCapsule(**c) for c in state.get("capsules", ())}
    kernel.authorizations = {a["id"]: ActionAuthorization(**a) for a in state.get("authorizations", ())}
    kernel.adapters = {a["adapter_id"]: AdapterProfile(**a) for a in state.get("adapters", ())}

    kernel.transactions._items.clear()
    for tx in state.get("transactions", ()):
        kernel.transactions.restore(ActionTransaction(
            tx["id"], tx["action_id"], tx["authorization_id"], tx["principal_ref"],
            bool(tx["idempotent"]), TransactionState(tx["state"]), tx.get("adapter_id"),
            tx.get("adapter_revision"), tx.get("detail"),
        ))
    kernel.authorization_transactions = dict(state.get("authorization_transactions", {}))

    kernel.freshness.generations = {str(k): int(v) for k, v in state.get("freshness_generations", {}).items()}

    kernel.decision_cuts._items.clear()
    max_revision = 0
    for row in state.get("decision_cuts", ()):
        cut = DecisionCutRevision(
            row["id"], int(row["revision"]), int(row["commit_frontier_sequence"]),
            int(row["mission_revision"]), int(row["canonical_state_revision"]),
            int(row["strategic_location_revision"]), tuple(tuple(x) for x in row.get("source_generations", ())),
        )
        kernel.decision_cuts._items[cut.id] = cut
        max_revision = max(max_revision, cut.revision)
    kernel.decision_cuts._revision = max_revision

    kernel.artifacts._items = {
        a["id"]: ArtifactBinding(
            a["id"], a["kind"], int(a["produced_sequence"]),
            DependencyStamp(tuple(tuple(x) for x in a.get("dependency_generations", ()))),
            a["decision_cut_id"],
        )
        for a in state.get("artifacts", ())
    }

    kernel.regions = [CandidateRegion(r["id"], dict(r.get("required_facts", {})), r["decision_signature"]) for r in state.get("regions", ())]
    loc = state.get("strategic_location", {})
    kernel.strategic_location = StrategicLocationRevision(
        LocationStatus(loc.get("status", "unlocated")),
        tuple(loc.get("region_ids", ())),
        tuple(loc.get("decision_signatures", ())),
    )
    kernel._location_revision = int(loc.get("revision", 1))

    rec = state.get("recovery", {})
    kernel.recovery.state = RecoveryState(
        RecoveryMode(rec.get("mode", "normal")), rec.get("reason"),
        float(rec.get("residual_weight", 0.0)), int(rec.get("generation", 1)),
    )
    kernel.completion_reports = {
        r["artifact_id"]: BoundCompletionReport(**r) for r in state.get("completion_reports", ())
    }


def _find_snapshot_prefix(entries, journal_head: str) -> int:
    if journal_head == HashJournal.GENESIS:
        return 0
    for index, row in enumerate(entries, start=1):
        if row.entry_hash == journal_head:
            return index
    raise ReplayError("snapshot journal head is not a prefix of the current journal")


def _replay_suffix(kernel, entries) -> None:
    for entry in entries:
        event = entry.event_type
        payload = entry.payload
        if event == "snapshot.saved":
            continue
        if event == "action.dispatch_recorded":
            tx = kernel.transactions.get(payload["transaction_id"])
            if tx.state in {TransactionState.AUTHORIZED, TransactionState.RECONCILED_NOT_APPLIED}:
                kernel.transactions.record_dispatch(tx.id, payload["adapter_id"], int(payload["adapter_revision"]))
            continue
        if event == "action.reconciliation_required":
            tx = kernel.transactions.get(payload["transaction_id"])
            if tx.state == TransactionState.DISPATCH_RECORDED:
                kernel.transactions.record_unknown_outcome(tx.id, str(payload.get("reason", "unknown outcome")))
            continue
        if event == "action.reconciled":
            tx = kernel.transactions.get(payload["transaction_id"])
            if tx.state == TransactionState.RECONCILIATION_REQUIRED:
                kernel.transactions.reconcile(tx.id, bool(payload["outcome_applied"]), bool(payload.get("trusted", False)))
            continue
        if event == "canonical.committed":
            kernel.canonical_state.update(dict(payload.get("state_patch") or {}))
            kernel.canonical_version = int(payload["canonical_version"])
            tx_id = payload.get("transaction_id")
            if tx_id and tx_id in kernel.transactions._items:
                tx = kernel.transactions.get(tx_id)
                if tx.state in {TransactionState.OUTCOME_OBSERVED, TransactionState.RECONCILED_APPLIED}:
                    kernel.transactions.commit(tx_id)
            continue
        if event == "freshness.bumped":
            kernel.freshness.generations[payload["domain"]] = int(payload["generation"])
            continue
        # A replay reducer must never invent missing semantics for a mutation.
        raise ReplayError(f"unsupported post-snapshot replay event: {event}")


def _open(cls, root: Path):
    root = Path(root)
    journal = HashJournal(root / "journal.jsonl")
    journal.verify(raise_on_error=True)
    state = SnapshotStore(root / "snapshot.json").load()
    entries = journal.entries()
    prefix_length = _find_snapshot_prefix(entries, str(state.get("journal_head", "")))

    mission_doc = state.get("mission") or {}
    if not mission_doc:
        raise ReplayError("snapshot has no mission contract")
    mission = MissionLedger(MissionContract(
        int(mission_doc["version"]), str(mission_doc["objective"]),
        tuple(mission_doc.get("success_conditions", ())), tuple(mission_doc.get("hard_constraints", ())),
        tuple(mission_doc.get("soft_preferences", ())), tuple(mission_doc.get("anti_goals", ())),
        mission_doc.get("risk_budget"),
    ))
    kernel = cls(root, mission)
    _restore_state(kernel, state)
    _replay_suffix(kernel, entries[prefix_length:])
    return kernel


def install_runtime_extensions(kernel_cls) -> None:
    kernel_cls.snapshot_state = _snapshot_state
    kernel_cls.save_snapshot = _save_snapshot
    kernel_cls.open = classmethod(_open)
