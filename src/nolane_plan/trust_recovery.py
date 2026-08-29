from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any, Callable

from .communication import CommunicationReceipt, CommunicationState
from .execution import DispatchAttestation, ReconciliationEvidence, TransactionState
from .hashing import digest
from .identity import PrincipalAttestation
from .mission import MissionContract, MissionLedger
from .persistence import HashJournal, SnapshotStore
from .resume import SNAPSHOT_SCHEMA as BASE_SNAPSHOT_SCHEMA
from .resume import _find_snapshot_prefix, _replay_suffix, _restore_state
from .types import ReplayError


TRUST_SNAPSHOT_SCHEMA = "nolane-plan-runtime-snapshot-v3"


def _attestation_doc(attestation: PrincipalAttestation) -> dict[str, Any]:
    return {
        "attestation_id": attestation.attestation_id,
        "canonical_principal_ref": attestation.canonical_principal_ref,
        "source": attestation.source,
        "source_subject": attestation.source_subject,
        "revision": attestation.revision,
        "issued_at": attestation.issued_at,
        "valid_until": attestation.valid_until,
        "assurance": attestation.assurance,
        "session_ref": attestation.session_ref,
        "provenance_digest": attestation.provenance_digest,
    }


def _attestation_from_doc(row: dict[str, Any]) -> PrincipalAttestation:
    attestation = PrincipalAttestation.create(
        attestation_id=str(row["attestation_id"]),
        canonical_principal_ref=str(row["canonical_principal_ref"]),
        source=str(row["source"]),
        source_subject=str(row["source_subject"]),
        revision=int(row["revision"]),
        issued_at=row["issued_at"],
        valid_until=row.get("valid_until"),
        assurance=float(row["assurance"]),
        session_ref=row.get("session_ref"),
    )
    recorded = str(row.get("provenance_digest", attestation.provenance_digest))
    if attestation.provenance_digest != recorded:
        raise ReplayError("principal attestation provenance digest mismatch")
    return attestation


def _dispatch_from_doc(row: dict[str, Any]) -> DispatchAttestation:
    attestation = DispatchAttestation.create(
        attestation_id=str(row["attestation_id"]),
        authorization_id=str(row["authorization_id"]),
        transaction_id=str(row["transaction_id"]),
        action_id=str(row["action_id"]),
        adapter_id=str(row["adapter_id"]),
        adapter_revision=int(row["adapter_revision"]),
        canonical_principal_ref=str(row["canonical_principal_ref"]),
        principal_attestation_id=str(row["principal_attestation_id"]),
        observed_at=row["observed_at"],
        assurance=float(row["assurance"]),
        provenance=str(row["provenance"]),
    )
    recorded = str(row.get("provenance_digest", attestation.provenance_digest))
    if attestation.provenance_digest != recorded:
        raise ReplayError("dispatch attestation provenance digest mismatch")
    return attestation


def _reconciliation_from_doc(row: dict[str, Any]) -> ReconciliationEvidence:
    evidence = ReconciliationEvidence.create(
        evidence_id=str(row["evidence_id"]),
        transaction_id=str(row["transaction_id"]),
        action_id=str(row["action_id"]),
        authorization_id=str(row["authorization_id"]),
        canonical_principal_ref=str(row["canonical_principal_ref"]),
        adapter_id=str(row["adapter_id"]),
        adapter_revision=int(row["adapter_revision"]),
        outcome_applied=bool(row["outcome_applied"]),
        source=str(row["source"]),
        observed_at=row["observed_at"],
        assurance=float(row["assurance"]),
    )
    recorded = str(row.get("provenance_digest", evidence.provenance_digest))
    if evidence.provenance_digest != recorded:
        raise ReplayError("reconciliation evidence provenance digest mismatch")
    return evidence


def _communication_doc(receipt: CommunicationReceipt) -> dict[str, Any]:
    return {
        "id": receipt.id,
        "source_principal_ref": receipt.source_principal_ref,
        "recipient_principal_ref": receipt.recipient_principal_ref,
        "semantic_payload_refs": list(receipt.semantic_payload_refs),
        "semantic_payload_digest": receipt.semantic_payload_digest,
        "state": receipt.state.value,
        "sent_at": receipt.sent_at,
        "delivered_at": receipt.delivered_at,
        "observed_at": receipt.observed_at,
        "valid_until": receipt.valid_until,
        "access_condition": receipt.access_condition,
        "provenance": receipt.provenance,
        "delivery_evidence_ref": receipt.delivery_evidence_ref,
        "observation_evidence_ref": receipt.observation_evidence_ref,
    }


def _trust_state(self) -> dict[str, Any]:
    bindings = []
    for binding in self.identities.all_bindings():
        attestation = self.identities.attestation(binding.attestation_id)
        bindings.append({
            "binding_id": binding.binding_id,
            "binding_revision": binding.binding_revision,
            "created_at": binding.created_at,
            "provenance_digest": binding.provenance_digest,
            "attestation": _attestation_doc(attestation),
            "revoked_at": self.identities.revoked_at(binding.attestation_id),
        })
    return {
        "identity_bindings": bindings,
        "communications": [_communication_doc(receipt) for receipt in self.communications.all()],
        "authorization_identity_bindings": dict(self.authorization_identity_bindings),
        "authorization_identity_attestations": dict(self.authorization_identity_attestations),
        "dispatch_attestations": [asdict(value) for value in self.dispatch_attestations.values()],
        "reconciliation_evidence": [asdict(value) for value in self.reconciliation_evidence.values()],
    }


def _snapshot_state(self, base_snapshot_state: Callable[[Any], dict[str, Any]]) -> dict[str, Any]:
    state = dict(base_snapshot_state(self))
    state["snapshot_schema"] = TRUST_SNAPSHOT_SCHEMA
    state["trust"] = _trust_state(self)
    return state


def _restore_trust_state(kernel, trust: dict[str, Any]) -> None:
    kernel.identities = type(kernel.identities)()
    kernel.communications = type(kernel.communications)()
    kernel.authorization_identity_bindings = {}
    kernel.authorization_identity_attestations = {}
    kernel.dispatch_attestations = {}
    kernel.reconciliation_evidence = {}

    bindings = sorted(
        trust.get("identity_bindings", ()),
        key=lambda row: (str(row["attestation"]["canonical_principal_ref"]), int(row["binding_revision"])),
    )
    for row in bindings:
        attestation = _attestation_from_doc(dict(row["attestation"]))
        binding = kernel.identities.accept(attestation, now=row["created_at"])
        if binding.binding_id != row["binding_id"]:
            raise ReplayError("principal binding id mismatch during snapshot restore")
        if binding.binding_revision != int(row["binding_revision"]):
            raise ReplayError("principal binding revision mismatch during snapshot restore")
        if binding.provenance_digest != row["provenance_digest"]:
            raise ReplayError("principal binding provenance mismatch during snapshot restore")
        if row.get("revoked_at") is not None:
            kernel.identities.revoke(attestation.attestation_id, revoked_at=row["revoked_at"])

    for row in trust.get("communications", ()):
        receipt = CommunicationReceipt(
            id=str(row["id"]),
            source_principal_ref=str(row["source_principal_ref"]),
            recipient_principal_ref=str(row["recipient_principal_ref"]),
            semantic_payload_refs=tuple(row.get("semantic_payload_refs", ())),
            semantic_payload_digest=str(row["semantic_payload_digest"]),
            state=CommunicationState(str(row["state"])),
            sent_at=row["sent_at"],
            delivered_at=row.get("delivered_at"),
            observed_at=row.get("observed_at"),
            valid_until=row.get("valid_until"),
            access_condition=row.get("access_condition"),
            provenance=str(row["provenance"]),
            delivery_evidence_ref=row.get("delivery_evidence_ref"),
            observation_evidence_ref=row.get("observation_evidence_ref"),
        )
        if digest(receipt.semantic_payload_refs) != receipt.semantic_payload_digest:
            raise ReplayError("communication semantic payload digest mismatch")
        if receipt.id in kernel.communications._receipts:
            raise ReplayError("duplicate communication receipt in snapshot")
        kernel.communications._receipts[receipt.id] = receipt

    kernel.authorization_identity_bindings = {
        str(k): str(v) for k, v in trust.get("authorization_identity_bindings", {}).items()
    }
    kernel.authorization_identity_attestations = {
        str(k): str(v) for k, v in trust.get("authorization_identity_attestations", {}).items()
    }
    for row in trust.get("dispatch_attestations", ()):
        value = _dispatch_from_doc(dict(row))
        kernel.dispatch_attestations[value.authorization_id] = value
    for row in trust.get("reconciliation_evidence", ()):
        value = _reconciliation_from_doc(dict(row))
        kernel.reconciliation_evidence[value.evidence_id] = value


def _apply_freshness_generations(kernel, payload: dict[str, Any]) -> None:
    for domain, generation in payload.get("freshness_generations", {}).items():
        kernel.freshness.generations[str(domain)] = int(generation)


def _replay_identity_bound(kernel, payload: dict[str, Any]) -> None:
    attestation = _attestation_from_doc(dict(payload["attestation"]))
    binding = kernel.identities.accept(attestation, now=payload["binding_created_at"])
    if binding.binding_id != payload["binding_id"] or binding.binding_revision != int(payload["binding_revision"]):
        raise ReplayError("identity binding event does not reproduce canonical binding")
    principal_ref = binding.canonical_principal_ref
    allowed_tags = frozenset(payload.get("allowed_tags", ()))
    profile = kernel.principals._profiles.get(principal_ref)
    if profile is None:
        profile = kernel.principals.register(principal_ref, allowed_tags)
    elif profile.allowed_tags != allowed_tags:
        profile = kernel.principals.update_access(principal_ref, allowed_tags)
    if profile.revision != int(payload["access_revision"]):
        raise ReplayError("identity binding access revision mismatch")
    kernel.freshness.ensure(f"communication:{principal_ref}")
    _apply_freshness_generations(kernel, payload)
    kernel.plan_snapshot_version += 1


def _replay_identity_revoked(kernel, payload: dict[str, Any]) -> None:
    kernel.identities.revoke(str(payload["attestation_id"]), revoked_at=payload["revoked_at"])
    _apply_freshness_generations(kernel, payload)
    kernel.plan_snapshot_version += 1


def _replay_communication_sent(kernel, payload: dict[str, Any]) -> None:
    receipt = kernel.communications.sent(
        receipt_id=str(payload["receipt_id"]),
        source_principal_ref=str(payload["source_principal_ref"]),
        recipient_principal_ref=str(payload["recipient_principal_ref"]),
        semantic_payload_refs=tuple(payload.get("semantic_payload_refs", ())),
        sent_at=payload["sent_at"],
        valid_until=payload.get("valid_until"),
        access_condition=payload.get("access_condition"),
        provenance=str(payload.get("provenance", "host")),
    )
    if receipt.semantic_payload_digest != payload["semantic_payload_digest"]:
        raise ReplayError("communication sent event payload digest mismatch")


def _replay_communication_delivered(kernel, payload: dict[str, Any]) -> None:
    kernel.communications.delivered(
        str(payload["receipt_id"]),
        delivered_at=payload["delivered_at"],
        evidence_ref=str(payload["evidence_ref"]),
    )


def _replay_communication_observed(kernel, payload: dict[str, Any]) -> None:
    receipt = kernel.communications.observed(
        str(payload["receipt_id"]),
        observed_at=payload["observed_at"],
        evidence_ref=str(payload["evidence_ref"]),
    )
    principal_ref = str(payload["recipient_principal_ref"])
    if receipt.recipient_principal_ref != principal_ref:
        raise ReplayError("communication observation recipient mismatch")
    kernel.principals.observe(principal_ref, str(payload["item_id"]), payload["observed_at"])
    _apply_freshness_generations(kernel, payload)


def _replay_authorization_identity_bound(kernel, payload: dict[str, Any]) -> None:
    authorization_id = str(payload["authorization_id"])
    if authorization_id not in kernel.authorizations:
        raise ReplayError("identity-bound authorization is absent during replay")
    kernel.authorization_identity_bindings[authorization_id] = str(payload["principal_binding_id"])
    kernel.authorization_identity_attestations[authorization_id] = str(payload["principal_attestation_id"])


def _replay_dispatch_attested(kernel, payload: dict[str, Any]) -> None:
    value = _dispatch_from_doc({
        "attestation_id": payload["dispatch_attestation_id"],
        "authorization_id": payload["authorization_id"],
        "transaction_id": payload["transaction_id"],
        "action_id": payload["action_id"],
        "adapter_id": payload["adapter_id"],
        "adapter_revision": payload["adapter_revision"],
        "canonical_principal_ref": payload["principal_ref"],
        "principal_attestation_id": payload["principal_attestation_id"],
        "observed_at": payload["observed_at"],
        "assurance": payload["assurance"],
        "provenance": payload["provenance"],
        "provenance_digest": payload["provenance_digest"],
    })
    kernel.dispatch_attestations[value.authorization_id] = value


def _replay_reconciliation_evidence(kernel, payload: dict[str, Any]) -> None:
    evidence = _reconciliation_from_doc({
        "evidence_id": payload["evidence_id"],
        "transaction_id": payload["transaction_id"],
        "action_id": payload["action_id"],
        "authorization_id": payload["authorization_id"],
        "canonical_principal_ref": payload["principal_ref"],
        "adapter_id": payload["adapter_id"],
        "adapter_revision": payload["adapter_revision"],
        "outcome_applied": payload["outcome_applied"],
        "source": payload["source"],
        "observed_at": payload["observed_at"],
        "assurance": payload["assurance"],
        "provenance_digest": payload["provenance_digest"],
    })
    if evidence.evidence_id in kernel.reconciliation_evidence:
        raise ReplayError("duplicate reconciliation evidence during replay")
    tx = kernel.transactions.get(evidence.transaction_id)
    if tx.state != TransactionState.RECONCILIATION_REQUIRED:
        raise ReplayError("reconciliation evidence replay has invalid transaction state")
    kernel.transactions.reconcile_with_evidence(tx.id, evidence, minimum_assurance=0.0)
    kernel.reconciliation_evidence[evidence.evidence_id] = evidence


def _replay_entry(kernel, entry) -> None:
    event = entry.event_type
    payload = entry.payload
    if event == "principal.identity_bound":
        _replay_identity_bound(kernel, payload)
        return
    if event == "principal.identity_revoked":
        _replay_identity_revoked(kernel, payload)
        return
    if event == "communication.sent":
        _replay_communication_sent(kernel, payload)
        return
    if event == "communication.delivered":
        _replay_communication_delivered(kernel, payload)
        return
    if event == "communication.observed":
        _replay_communication_observed(kernel, payload)
        return
    if event == "action.authorization_identity_bound":
        _replay_authorization_identity_bound(kernel, payload)
        return
    if event == "action.dispatch_attested":
        _replay_dispatch_attested(kernel, payload)
        return
    if event == "action.reconciled_evidence":
        _replay_reconciliation_evidence(kernel, payload)
        return
    _replay_suffix(kernel, (entry,))


def _open(cls, root: Path):
    root = Path(root)
    journal = HashJournal(root / "journal.jsonl")
    journal.verify(raise_on_error=True)
    state = SnapshotStore(root / "snapshot.json").load()
    schema = state.get("snapshot_schema")
    if schema not in {BASE_SNAPSHOT_SCHEMA, TRUST_SNAPSHOT_SCHEMA}:
        raise ReplayError("unsupported or missing snapshot schema")
    entries = journal.entries()
    prefix_length = _find_snapshot_prefix(entries, str(state.get("journal_head", "")))

    mission_doc = state.get("mission") or {}
    if not mission_doc:
        raise ReplayError("snapshot has no mission contract")
    mission = MissionLedger(MissionContract(
        int(mission_doc["version"]),
        str(mission_doc["objective"]),
        tuple(mission_doc.get("success_conditions", ())),
        tuple(mission_doc.get("hard_constraints", ())),
        tuple(mission_doc.get("soft_preferences", ())),
        tuple(mission_doc.get("anti_goals", ())),
        mission_doc.get("risk_budget"),
    ))
    kernel = cls(root, mission)
    core_state = dict(state)
    core_state["snapshot_schema"] = BASE_SNAPSHOT_SCHEMA
    core_state.pop("trust", None)
    _restore_state(kernel, core_state)
    if schema == TRUST_SNAPSHOT_SCHEMA:
        _restore_trust_state(kernel, dict(state.get("trust") or {}))
    for entry in entries[prefix_length:]:
        _replay_entry(kernel, entry)
    return kernel


def install_trust_recovery(kernel_cls) -> None:
    if getattr(kernel_cls, "_wave3_trust_recovery_installed", False):
        return
    base_snapshot_state = kernel_cls.snapshot_state

    def snapshot_state(self):
        return _snapshot_state(self, base_snapshot_state)

    def save_snapshot(self):
        with self._writer_lock:
            state = snapshot_state(self)
            self.snapshots.save(state)
            self._record("snapshot.saved", {
                "snapshot_schema": TRUST_SNAPSHOT_SCHEMA,
                "snapshot_digest": digest(state),
                "bound_journal_head": state["journal_head"],
            })
            return state

    kernel_cls.snapshot_state = snapshot_state
    kernel_cls.save_snapshot = save_snapshot
    kernel_cls.open = classmethod(_open)
    kernel_cls._wave3_trust_recovery_installed = True
