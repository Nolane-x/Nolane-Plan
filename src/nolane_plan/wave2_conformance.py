from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Callable

from .actions import ActionIntent, AuthorityGrant
from .artifacts import ArtifactRegistry
from .decision_cut import DecisionCutLedger
from .execution import ActionTransactionLedger, AdapterProfile, TransactionState
from .freshness import FreshnessDomainLedger
from .kernel import PlanKernel
from .query import QuerySnapshotCompletenessReceipt, strong_universal_current
from .resources import ReservationConflict, ReservationLedger, SharedCommitment
from .temporal import ReactionWindow
from .types import AuthorizationError, ReplayError, RiskClass


def _raises(exc_type, fn: Callable[[], object]) -> bool:
    try:
        fn()
    except exc_type:
        return True
    return False


def _future_artifact_cannot_leak_into_historical_cut() -> bool:
    freshness = FreshnessDomainLedger()
    cuts = DecisionCutLedger()
    registry = ArtifactRegistry(freshness)
    cut = cuts.capture(2, 1, 1, 1, freshness.generations)
    registry.register("future-proof", "proof", 3, (), cut.id)
    return not registry.usable_at_cut("future-proof", cut)


def _freshness_mutation_stales_authority_immediately() -> bool:
    freshness = FreshnessDomainLedger()
    freshness.ensure("state")
    cuts = DecisionCutLedger()
    registry = ArtifactRegistry(freshness)
    cut = cuts.capture(1, 1, 1, 1, freshness.generations)
    registry.register("proof", "proof", 1, ("state",), cut.id)
    before = registry.usable_at_cut("proof", cut)
    freshness.bump("state")
    after = registry.usable_at_cut("proof", cut)
    return before and not after


def _opaque_adapter_cannot_execute_executor_sensitive_action() -> bool:
    profile = AdapterProfile("opaque", 1, False, False, 1.0)
    return _raises(AuthorizationError, lambda: profile.require_for(RiskClass.CONSEQUENTIAL, executor_sensitive=True))


def _non_idempotent_ambiguous_outcome_cannot_blind_retry() -> bool:
    ledger = ActionTransactionLedger()
    tx = ledger.authorized("tx", "charge", "auth", "agent:p0", idempotent=False)
    ledger.record_dispatch(tx.id, "payments", 1)
    ledger.record_unknown_outcome(tx.id, "timeout after possible side effect")
    return ledger.get(tx.id).state == TransactionState.RECONCILIATION_REQUIRED and _raises(
        AuthorizationError, lambda: ledger.assert_retry_allowed(tx.id)
    )


def _incomplete_universal_query_cannot_prove_absence() -> bool:
    freshness = FreshnessDomainLedger()
    freshness.ensure("inventory")
    receipt = QuerySnapshotCompletenessReceipt.capture(freshness, "inventory", "snapshot", False, 1.0)
    return not strong_universal_current(receipt, freshness, 0.8)


def _reaction_deadline_miss_is_unschedulable() -> bool:
    return not ReactionWindow(0, 3, 2, 2, 1).schedulable()


def _exclusive_resource_overlap_is_rejected() -> bool:
    ledger = ReservationLedger()
    ledger.reserve(SharedCommitment("gpu", "agent:a", 0, 10, True))
    return _raises(ReservationConflict, lambda: ledger.reserve(SharedCommitment("gpu", "agent:b", 5, 8, True)))


def _unlocated_commit_enters_model_class_uncertainty() -> bool:
    from .execution import AdapterProfile
    from .relocation import CandidateRegion

    class Adapter:
        adapter_id = "deploy-api"
        adapter_revision = 1

        def execute(self, action, principal_ref):
            return {
                "ok": True,
                "postconditions_verified": True,
                "state_patch": {"deployed": True},
                "executing_principal_ref": principal_ref,
            }

    with tempfile.TemporaryDirectory() as td:
        k = PlanKernel.create(Path(td), "deploy")
        k.register_principal("agent:p0", {"public"})
        k.register_region(CandidateRegion("before", {"deployed": False}, "stay"))
        action = ActionIntent("deploy", "deploy", RiskClass.CONSEQUENTIAL)
        k.propose_action(action)
        k.add_grant(AuthorityGrant("g", "agent:p0", frozenset({"deploy"}), expires_at=100))
        k.register_adapter(AdapterProfile("deploy-api", 1, True, True, 1.0))
        auth = k.authorize("deploy", "agent:p0", ("g",), 1, adapter_id="deploy-api")
        k.dispatch(auth.id, "agent:p0", Adapter(), 2)
        return k.strategic_location.status.value == "unlocated" and k.recovery.state.mode.value == "model_class_uncertain"


def _completion_proof_stales_after_mission_revision() -> bool:
    with tempfile.TemporaryDirectory() as td:
        k = PlanKernel.create(Path(td), "ship", success_conditions=("done",))
        k.canonical_state["done"] = True
        report = k.verify_completion(())
        before = report.complete and k.artifacts.current(report.artifact_id)
        k.revise_mission(objective="ship v2")
        return before and not k.artifacts.current(report.artifact_id)


def _snapshot_must_bind_real_journal_prefix() -> bool:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        k = PlanKernel.create(root, "x")
        state = k.save_snapshot()
        forged = dict(state)
        forged["journal_head"] = "f" * 64
        k.snapshots.save(forged)
        return _raises(ReplayError, lambda: PlanKernel.open(root))


_CASES: tuple[tuple[str, Callable[[], bool]], ...] = (
    ("future_artifact_historical_cut", _future_artifact_cannot_leak_into_historical_cut),
    ("authority_time_freshness", _freshness_mutation_stales_authority_immediately),
    ("adapter_principal_assurance", _opaque_adapter_cannot_execute_executor_sensitive_action),
    ("non_idempotent_reconciliation", _non_idempotent_ambiguous_outcome_cannot_blind_retry),
    ("universal_query_completeness", _incomplete_universal_query_cannot_prove_absence),
    ("reaction_window_schedulability", _reaction_deadline_miss_is_unschedulable),
    ("exclusive_resource_conflict", _exclusive_resource_overlap_is_rejected),
    ("unlocated_unknown_world", _unlocated_commit_enters_model_class_uncertainty),
    ("completion_proof_freshness", _completion_proof_stales_after_mission_revision),
    ("snapshot_journal_prefix_binding", _snapshot_must_bind_real_journal_prefix),
)


def run_wave2_conformance() -> dict:
    rows: list[dict[str, object]] = []
    for name, fn in _CASES:
        try:
            passed = bool(fn())
            detail = "defense held" if passed else "unsafe shortcut was not rejected"
        except Exception as exc:  # a conformance case crashing is not a pass
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

    report = run_wave2_conformance()
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
