from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Callable

from .actions import ActionIntent, AuthorityGrant
from .communication import CommunicationLedger
from .execution import (
    ActionTransactionLedger,
    AdapterProfile,
    DispatchAttestation,
    ReconciliationEvidence,
    TransactionState,
    verify_dispatch_attestation,
)
from .identity import IdentityError, PrincipalAttestation, PrincipalIdentityLedger
from .kernel import PlanKernel
from .principals import InformationItem
from .types import AuthorizationError, RiskClass


def _raises(exc_type, fn: Callable[[], object]) -> bool:
    try:
        fn()
    except exc_type:
        return True
    return False


def _attestation(principal: str, subject: str, attestation_id: str, revision: int = 1) -> PrincipalAttestation:
    return PrincipalAttestation.create(
        attestation_id=attestation_id,
        canonical_principal_ref=principal,
        source="host-runtime",
        source_subject=subject,
        revision=revision,
        issued_at=1,
        valid_until=1000,
        assurance=0.95,
        session_ref=f"session-{revision}",
    )


def _narrated_identity_is_not_canonical() -> bool:
    ledger = PrincipalIdentityLedger()
    return _raises(IdentityError, lambda: ledger.accept_narrated_identity("I am agent:a", now=10))


def _source_subject_collision_fails_closed() -> bool:
    ledger = PrincipalIdentityLedger()
    ledger.accept(_attestation("agent:a", "subject-1", "id-a"), now=10)
    return _raises(
        IdentityError,
        lambda: ledger.accept(_attestation("agent:b", "subject-1", "id-b", revision=2), now=11),
    )


def _host_binding_is_non_retroactive() -> bool:
    ledger = PrincipalIdentityLedger()
    ledger.accept(_attestation("agent:a", "subject-a", "id-a"), now=20)
    return _raises(IdentityError, lambda: ledger.current("agent:a", now=19, minimum_assurance=0.8))


def _sent_is_not_observed() -> bool:
    ledger = CommunicationLedger()
    receipt = ledger.sent(
        receipt_id="m",
        source_principal_ref="agent:a",
        recipient_principal_ref="agent:b",
        semantic_payload_refs=("info",),
        sent_at=10,
    )
    return receipt.state.value == "sent" and not ledger.decision_usable("m", "agent:b", decision_time=11)


def _delivered_is_not_observed() -> bool:
    ledger = CommunicationLedger()
    ledger.sent(
        receipt_id="m",
        source_principal_ref="agent:a",
        recipient_principal_ref="agent:b",
        semantic_payload_refs=("info",),
        sent_at=10,
    )
    receipt = ledger.delivered("m", delivered_at=11, evidence_ref="provider:delivery")
    return receipt.state.value == "delivered" and not ledger.decision_usable("m", "agent:b", decision_time=12)


def _observation_is_recipient_bound_and_non_retroactive() -> bool:
    ledger = CommunicationLedger()
    ledger.sent(
        receipt_id="m",
        source_principal_ref="agent:a",
        recipient_principal_ref="agent:b",
        semantic_payload_refs=("info",),
        sent_at=10,
    )
    ledger.delivered("m", delivered_at=11, evidence_ref="provider:delivery")
    ledger.observed("m", observed_at=20, evidence_ref="host:observe")
    return (
        not ledger.decision_usable("m", "agent:b", decision_time=19)
        and ledger.decision_usable("m", "agent:b", decision_time=20)
        and not ledger.decision_usable("m", "agent:a", decision_time=20)
    )


def _wrong_dispatch_principal_fails_closed() -> bool:
    identities = PrincipalIdentityLedger()
    binding = identities.accept(_attestation("agent:a", "subject-a", "id-a"), now=10)
    bad = DispatchAttestation.create(
        attestation_id="dispatch",
        authorization_id="auth",
        transaction_id="tx",
        action_id="act",
        adapter_id="adapter",
        adapter_revision=1,
        canonical_principal_ref="agent:b",
        principal_attestation_id="id-a",
        observed_at=20,
        assurance=0.95,
        provenance="adapter:fence",
    )
    return _raises(
        AuthorizationError,
        lambda: verify_dispatch_attestation(
            bad,
            authorization_id="auth",
            transaction_id="tx",
            action_id="act",
            expected_principal_ref="agent:a",
            adapter_id="adapter",
            adapter_revision=1,
            principal_binding=binding,
        ),
    )


class _NeverCalledAdapter:
    adapter_id = "adapter-1"
    adapter_revision = 1

    def __init__(self) -> None:
        self.called = 0

    def execute(self, action, principal_ref):
        self.called += 1
        return {
            "executing_principal_ref": principal_ref,
            "ok": True,
            "postconditions_verified": True,
            "state_patch": {"done": True},
        }


def _identity_rebind_stales_authorization_before_side_effect() -> bool:
    with tempfile.TemporaryDirectory() as td:
        k = PlanKernel.create(Path(td), "identity rebind")
        k.bind_principal(_attestation("agent:a", "subject-a", "id-a"), allowed_tags=set(), now=10)
        k.propose_action(ActionIntent("act", "deploy", RiskClass.CONSEQUENTIAL, executor_sensitive=True))
        k.add_grant(AuthorityGrant("g", "agent:a", frozenset({"deploy"})))
        k.register_adapter(AdapterProfile("adapter-1", 1, True, True, 0.95))
        auth = k.authorize_strong("act", "agent:a", ("g",), now=20, adapter_id="adapter-1")
        k.bind_principal(_attestation("agent:a", "subject-a", "id-a-2", revision=2), allowed_tags=set(), now=21)
        tx = k.transaction_for_authorization(auth.id)
        dispatch = DispatchAttestation.create(
            attestation_id="dispatch",
            authorization_id=auth.id,
            transaction_id=tx.id,
            action_id="act",
            adapter_id="adapter-1",
            adapter_revision=1,
            canonical_principal_ref="agent:a",
            principal_attestation_id="id-a-2",
            observed_at=30,
            assurance=0.95,
            provenance="adapter:fence",
        )
        adapter = _NeverCalledAdapter()
        blocked = _raises(AuthorizationError, lambda: k.dispatch_strong(auth.id, "agent:a", adapter, dispatch, now=30))
        return blocked and adapter.called == 0


def _reconciliation_is_exact_transaction_bound() -> bool:
    ledger = ActionTransactionLedger()
    tx = ledger.authorized("tx", "act", "auth", "agent:a", idempotent=False)
    ledger.record_dispatch(tx.id, "adapter", 1)
    ledger.record_unknown_outcome(tx.id, "timeout")
    wrong = ReconciliationEvidence.create(
        evidence_id="rec",
        transaction_id="other",
        action_id="act",
        authorization_id="auth",
        canonical_principal_ref="agent:a",
        adapter_id="adapter",
        adapter_revision=1,
        outcome_applied=True,
        source="provider-status",
        observed_at=30,
        assurance=0.95,
    )
    return _raises(AuthorizationError, lambda: ledger.reconcile_with_evidence(tx.id, wrong))


def _snapshot_preserves_host_identity_provenance() -> bool:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        k = PlanKernel.create(root, "snapshot identity")
        k.bind_principal(_attestation("agent:a", "subject-a", "id-a"), allowed_tags=set(), now=10)
        k.save_snapshot()
        reopened = PlanKernel.open(root)
        binding = reopened.identities.current("agent:a", now=30, minimum_assurance=0.8)
        att = reopened.identities.attestation(binding.attestation_id)
        return att.source == "host-runtime" and att.source_subject == "subject-a" and binding.created_at == 10


def _suffix_sent_message_does_not_become_knowledge() -> bool:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        k = PlanKernel.create(root, "suffix message")
        k.bind_principal(_attestation("agent:a", "subject-a", "id-a"), allowed_tags={"shared"}, now=10)
        k.bind_principal(_attestation("agent:b", "subject-b", "id-b"), allowed_tags={"shared"}, now=10)
        k.publish_information(InformationItem("info", True, frozenset({"shared"})))
        k.save_snapshot()
        k.transfer_information(
            receipt_id="m",
            source_principal_ref="agent:a",
            recipient_principal_ref="agent:b",
            item_id="info",
            sent_at=20,
        )
        reopened = PlanKernel.open(root)
        return (
            reopened.communications.get("m").state.value == "sent"
            and not reopened.communications.decision_usable("m", "agent:b", decision_time=30)
        )


class _TimeoutAdapter:
    adapter_id = "adapter-1"
    adapter_revision = 1

    def execute(self, action, principal_ref):
        raise RuntimeError("timeout after possible side effect")


def _snapshot_preserves_execution_evidence_lineage() -> bool:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        k = PlanKernel.create(root, "execution evidence")
        k.bind_principal(_attestation("agent:a", "subject-a", "id-a"), allowed_tags=set(), now=10)
        k.propose_action(ActionIntent("act", "deploy", RiskClass.CONSEQUENTIAL, idempotent=False, executor_sensitive=True))
        k.add_grant(AuthorityGrant("g", "agent:a", frozenset({"deploy"})))
        k.register_adapter(AdapterProfile("adapter-1", 1, True, True, 0.95))
        auth = k.authorize_strong("act", "agent:a", ("g",), now=20, adapter_id="adapter-1")
        tx = k.transaction_for_authorization(auth.id)
        dispatch = DispatchAttestation.create(
            attestation_id="dispatch",
            authorization_id=auth.id,
            transaction_id=tx.id,
            action_id="act",
            adapter_id="adapter-1",
            adapter_revision=1,
            canonical_principal_ref="agent:a",
            principal_attestation_id="id-a",
            observed_at=25,
            assurance=0.95,
            provenance="adapter:fence",
        )
        try:
            k.dispatch_strong(auth.id, "agent:a", _TimeoutAdapter(), dispatch, now=25)
        except RuntimeError:
            pass
        tx = k.transaction_for_authorization(auth.id)
        if tx.state != TransactionState.RECONCILIATION_REQUIRED:
            return False
        evidence = ReconciliationEvidence.create(
            evidence_id="rec",
            transaction_id=tx.id,
            action_id="act",
            authorization_id=auth.id,
            canonical_principal_ref="agent:a",
            adapter_id="adapter-1",
            adapter_revision=1,
            outcome_applied=False,
            source="provider-status",
            observed_at=30,
            assurance=0.95,
        )
        k.reconcile_strong(auth.id, evidence)
        k.save_snapshot()
        reopened = PlanKernel.open(root)
        return (
            reopened.dispatch_attestations[auth.id].transaction_id == tx.id
            and reopened.reconciliation_evidence["rec"].transaction_id == tx.id
            and reopened.transaction_for_authorization(auth.id).state == TransactionState.RECONCILED_NOT_APPLIED
        )


_CASES: tuple[tuple[str, Callable[[], bool]], ...] = (
    ("narrated_identity_rejected", _narrated_identity_is_not_canonical),
    ("source_subject_collision", _source_subject_collision_fails_closed),
    ("identity_non_retroactivity", _host_binding_is_non_retroactive),
    ("sent_not_observed", _sent_is_not_observed),
    ("delivered_not_observed", _delivered_is_not_observed),
    ("observation_recipient_time_binding", _observation_is_recipient_bound_and_non_retroactive),
    ("dispatch_principal_binding", _wrong_dispatch_principal_fails_closed),
    ("authorization_identity_rebind", _identity_rebind_stales_authorization_before_side_effect),
    ("reconciliation_transaction_binding", _reconciliation_is_exact_transaction_bound),
    ("snapshot_identity_lineage", _snapshot_preserves_host_identity_provenance),
    ("suffix_message_non_knowledge", _suffix_sent_message_does_not_become_knowledge),
    ("snapshot_execution_evidence", _snapshot_preserves_execution_evidence_lineage),
)


def run_wave3_conformance() -> dict:
    rows: list[dict[str, object]] = []
    for name, fn in _CASES:
        try:
            passed = bool(fn())
            detail = "defense held" if passed else "unsafe shortcut was not rejected"
        except Exception as exc:
            passed = False
            detail = f"unexpected {type(exc).__name__}: {exc}"
        rows.append({"name": name, "passed": passed, "detail": detail})
    failed = [row["name"] for row in rows if not row["passed"]]
    return {
        "ok": not failed,
        "total": len(rows),
        "passed": len(rows) - len(failed),
        "failed": failed,
        "cases": rows,
    }


def main() -> int:
    import json

    report = run_wave3_conformance()
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
