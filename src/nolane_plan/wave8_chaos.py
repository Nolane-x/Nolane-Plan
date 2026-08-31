from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import tempfile
from typing import Callable, Iterable

from .actions import ActionIntent, AuthorityGrant
from .handoff_stability import EdgeActivationStatus, HandoffStabilityContract, HandoffStabilityEvaluator
from .hashing import digest
from .lineage import SemanticRegimeKind
from .lineage_recovery import canonical_semantic_digest
from .migration import FieldMigrationDisposition, MigrationDisposition, MigrationError, MigrationManifest
from .types import AuthorizationError, ReplayError
from .wave8_registry import WAVE8_INVARIANTS, Wave8Counterexample


CHAOS_IDS = tuple(f"C{index:02d}" for index in range(1, 11))
_CHAOS_ROWS = {row.invariant_id: row for row in WAVE8_INVARIANTS if row.invariant_id in CHAOS_IDS}


@dataclass(frozen=True, slots=True)
class Wave8FaultSchedule:
    invariant_id: str
    seed: int
    operations: tuple[str, ...]
    canonical_digest: str


_FAULT_OPERATIONS = {
    "C01": ("snapshot.save", "fault:corrupt_outer_snapshot_digest", "restart:open"),
    "C02": ("snapshot.save", "suffix:mission_revision", "restart:open", "compare:semantic_digest"),
    "C03": ("snapshot.save", "fault:append_unknown_correctness_event", "restart:open"),
    "C04": ("authorize", "fault:drop_authority_lineage_binding", "dispatch"),
    "C05": ("snapshot.save", "dispatch:durable", "fault:adapter_exception", "restart:open", "retry"),
    "C06": ("authorize", "fault:leave_dispatch_recorded", "migration:attempt_without_bridge"),
    "C07": ("snapshot.save", "migration:root_switch", "restart:open", "authority:recheck"),
    "C08": ("snapshot.save", "compaction:durable_commit", "fault:restart_after_commit", "reconstruct"),
    "C09": ("handoff:register_stability", "snapshot.save", "restart:open", "fault:generation_drift"),
    "C10": ("snapshot.save", "dispatch:durable", "cancel", "restart:open", "retry"),
}


class _FailingAdapter:
    def __init__(self) -> None:
        self.calls = 0

    def execute(self, action, principal_ref):
        self.calls += 1
        raise RuntimeError("wave8 injected adapter interruption")


class _CountingAdapter:
    def __init__(self) -> None:
        self.calls = 0

    def execute(self, action, principal_ref):
        self.calls += 1
        return {
            "ok": True,
            "postconditions_verified": True,
            "executing_principal_ref": principal_ref,
            "state_patch": {"done": True},
        }


def build_chaos_schedule(invariant_id: str, seed: int) -> Wave8FaultSchedule:
    invariant = str(invariant_id).strip().upper()
    if invariant not in _FAULT_OPERATIONS:
        raise ValueError(f"unknown Wave-8 chaos invariant: {invariant_id}")
    seed_value = int(seed)
    operations = _FAULT_OPERATIONS[invariant]
    body = {"invariant_id": invariant, "seed": seed_value, "operations": operations}
    return Wave8FaultSchedule(invariant, seed_value, operations, digest(body))


def _kernel(seed: int, root: Path):
    from . import PlanKernel

    return PlanKernel.create(
        root,
        f"wave8 chaos mission {seed}",
        ("done",),
        ("preserve history",),
    )


def _authorized_kernel(seed: int, root: Path, *, idempotent: bool = True):
    kernel = _kernel(seed, root)
    action_id = f"action:{seed}"
    grant_id = f"grant:{seed}"
    principal = f"agent:{seed}"
    kernel.propose_action(ActionIntent(action_id, "deploy", idempotent=idempotent))
    kernel.add_grant(AuthorityGrant(grant_id, principal, frozenset({"deploy"})))
    authorization = kernel.authorize(action_id, principal, (grant_id,), 1)
    return kernel, authorization, principal


def _manifest(kernel, seed: int) -> MigrationManifest:
    source = kernel.lineage.current_regime(SemanticRegimeKind.SCHEMA).revision_id
    target = f"schema:nolane-plan:v7-wave8-chaos-{seed}"
    return MigrationManifest.create(
        manifest_id=f"wave8-chaos-migration:{seed}",
        source_schema_revision=source,
        target_schema_revision=target,
        target_schema_semantic_digest=digest({"wave8-chaos-target": seed}),
        changed_correctness_fields=(("PolicyNodeRevision", "guard_semantics"),),
        field_dispositions=(
            FieldMigrationDisposition(
                "PolicyNodeRevision",
                "guard_semantics",
                MigrationDisposition.INVALIDATED_REQUIRES_RECHECK,
            ),
        ),
        identity_mappings=(),
        checked_invariants=("no_authority_promotion",),
        revoked_certificate_refs=(),
        revoked_authorization_refs=(),
        new_debt_refs=(),
        replay_fixture_digests=(f"wave8-chaos:{seed}",),
        rollback_procedure_ref="rollback:wave8-chaos",
        backup_ref="backup:wave8-chaos",
        unsupported_legacy_cases=("opaque-legacy",),
        external_effect_history_refs=(),
        provenance_refs=("wave8:chaos",),
    )


def _c01(schedule: Wave8FaultSchedule) -> tuple[bool, str]:
    with tempfile.TemporaryDirectory(prefix="nolane-wave8-c01-") as temp:
        root = Path(temp)
        kernel = _kernel(schedule.seed, root)
        kernel.save_snapshot()
        path = root / "snapshot.json"
        document = json.loads(path.read_text(encoding="utf-8"))
        document["digest"] = "0" * 64
        path.write_text(json.dumps(document, sort_keys=True), encoding="utf-8")
        from . import PlanKernel

        try:
            PlanKernel.open(root)
        except ReplayError:
            return True, "corrupt snapshot rejected before trusted restore"
        return False, "corrupt snapshot was accepted"


def _c02(schedule: Wave8FaultSchedule) -> tuple[bool, str]:
    with tempfile.TemporaryDirectory(prefix="nolane-wave8-c02-") as temp:
        root = Path(temp)
        kernel = _kernel(schedule.seed, root)
        kernel.save_snapshot()
        kernel.revise_mission(objective=f"wave8-chaos-suffix:{schedule.seed}")
        live = canonical_semantic_digest(kernel)
        from . import PlanKernel

        restored = PlanKernel.open(root)
        replayed = canonical_semantic_digest(restored)
        holds = live == replayed and restored.mission.current.objective == f"wave8-chaos-suffix:{schedule.seed}"
        return holds, f"live={live} replayed={replayed}"


def _c03(schedule: Wave8FaultSchedule) -> tuple[bool, str]:
    with tempfile.TemporaryDirectory(prefix="nolane-wave8-c03-") as temp:
        root = Path(temp)
        kernel = _kernel(schedule.seed, root)
        kernel.save_snapshot()
        kernel._record(
            "proof.unknown_wave8_correctness_event",
            {"seed": schedule.seed, "correctness_significant": True},
        )
        from . import PlanKernel

        try:
            PlanKernel.open(root)
        except ReplayError:
            return True, "unknown correctness-significant event rejected"
        return False, "unknown correctness-significant event replayed"


def _c04(schedule: Wave8FaultSchedule) -> tuple[bool, str]:
    with tempfile.TemporaryDirectory(prefix="nolane-wave8-c04-") as temp:
        kernel, authorization, principal = _authorized_kernel(schedule.seed, Path(temp))
        kernel.authorization_lineage_bindings.pop(authorization.id, None)
        adapter = _CountingAdapter()
        blocked = False
        try:
            kernel.dispatch(authorization.id, principal, adapter, 2)
        except (AuthorizationError, KeyError):
            blocked = True
        return blocked and adapter.calls == 0, f"blocked={blocked} adapter_calls={adapter.calls}"


def _c05(schedule: Wave8FaultSchedule) -> tuple[bool, str]:
    with tempfile.TemporaryDirectory(prefix="nolane-wave8-c05-") as temp:
        root = Path(temp)
        kernel, authorization, principal = _authorized_kernel(schedule.seed, root, idempotent=False)
        kernel.save_snapshot()
        adapter = _FailingAdapter()
        interrupted = False
        try:
            kernel.dispatch(authorization.id, principal, adapter, 2)
        except RuntimeError:
            interrupted = True
        tx = kernel.transaction_for_authorization(authorization.id)
        from .execution import TransactionState

        live_pending = tx.state is TransactionState.RECONCILIATION_REQUIRED
        from . import PlanKernel

        restored = PlanKernel.open(root)
        replayed = restored.transaction_for_authorization(authorization.id)
        retry_blocked = False
        try:
            restored.transactions.assert_retry_allowed(replayed.id)
        except AuthorizationError:
            retry_blocked = True
        holds = (
            interrupted
            and adapter.calls == 1
            and live_pending
            and replayed.state is TransactionState.RECONCILIATION_REQUIRED
            and retry_blocked
        )
        return holds, f"live={tx.state.value} replayed={replayed.state.value} retry_blocked={retry_blocked}"


def _c06(schedule: Wave8FaultSchedule) -> tuple[bool, str]:
    with tempfile.TemporaryDirectory(prefix="nolane-wave8-c06-") as temp:
        kernel, authorization, _ = _authorized_kernel(schedule.seed, Path(temp), idempotent=False)
        tx = kernel.transaction_for_authorization(authorization.id)
        kernel.transactions.record_dispatch(tx.id, "adapter:wave8", 1)
        source = kernel.lineage.current_regime(SemanticRegimeKind.SCHEMA).revision_id
        blocked = False
        try:
            kernel.apply_semantic_migration(_manifest(kernel, schedule.seed), now=2)
        except MigrationError:
            blocked = True
        current = kernel.lineage.current_regime(SemanticRegimeKind.SCHEMA).revision_id
        holds = blocked and current == source and authorization.id not in kernel.migration_recheck_required_authorizations
        return holds, f"blocked={blocked} source={source} current={current}"


def _c07(schedule: Wave8FaultSchedule) -> tuple[bool, str]:
    with tempfile.TemporaryDirectory(prefix="nolane-wave8-c07-") as temp:
        root = Path(temp)
        kernel, authorization, _ = _authorized_kernel(schedule.seed, root)
        kernel.save_snapshot()
        manifest = _manifest(kernel, schedule.seed)
        result = kernel.apply_semantic_migration(manifest, now=2)
        live = (
            kernel.lineage.current_regime(SemanticRegimeKind.SCHEMA).revision_id,
            tuple(sorted(kernel.migration_recheck_required_authorizations)),
            canonical_semantic_digest(kernel),
        )
        from . import PlanKernel

        restored = PlanKernel.open(root)
        replayed = (
            restored.lineage.current_regime(SemanticRegimeKind.SCHEMA).revision_id,
            tuple(sorted(restored.migration_recheck_required_authorizations)),
            canonical_semantic_digest(restored),
        )
        holds = (
            live == replayed
            and result.target_schema_revision == manifest.target_schema_revision
            and authorization.id in restored.migration_recheck_required_authorizations
        )
        return holds, f"live={live!r} replayed={replayed!r}"


def _c08(schedule: Wave8FaultSchedule) -> tuple[bool, str]:
    with tempfile.TemporaryDirectory(prefix="nolane-wave8-c08-") as temp:
        root = Path(temp)
        kernel, authorization, _ = _authorized_kernel(schedule.seed, root)
        kernel.save_snapshot()
        before = canonical_semantic_digest(kernel)
        manifest_id = f"wave8-chaos-compaction:{schedule.seed}"
        result = kernel.compact_lineage(manifest_id)
        after = canonical_semantic_digest(kernel)
        from . import PlanKernel

        restored = PlanKernel.open(root)
        rebuilt = restored.reconstruct_compacted_lineage(manifest_id)
        replayed = canonical_semantic_digest(restored)
        restored._assert_authorization_lineage_current(authorization.id)
        holds = (
            before == after == replayed
            and result.source_semantic_root_digest == result.target_semantic_root_digest
            and rebuilt.semantic_root_digest() == restored.lineage.semantic_root_digest()
        )
        return holds, f"before={before} after={after} replayed={replayed}"


def _stability_contract(seed: int) -> HandoffStabilityContract:
    return HandoffStabilityContract.create(
        contract_id=f"wave8-stability:{seed}",
        revision_id=f"wave8-stability:{seed}@1",
        policy_edge_ref=f"edge:{seed}",
        protected_predicate_refs=("inventory-ok", "permission-ok"),
        protected_generation_bindings=(("inventory", 7), ("permission", 3)),
        lock_or_reservation_refs=(f"lock:{seed}",),
        stability_start=0.0,
        stability_end=100.0,
        external_writer_assumption_refs=(f"writer:{seed}",),
        refresh_required_predicate_refs=("inventory-ok", "permission-ok"),
        authorization_time_precondition_refs=("inventory-ok", "permission-ok"),
        invalidating_event_refs=("permission.revoked",),
        open_side_effect_refs=(),
        fallback_on_instability=f"fallback:{seed}",
        opacity_debt_refs=(),
        validity_regime="ACTIVE",
    )


def _c09(schedule: Wave8FaultSchedule) -> tuple[bool, str]:
    with tempfile.TemporaryDirectory(prefix="nolane-wave8-c09-") as temp:
        root = Path(temp)
        kernel = _kernel(schedule.seed, root)
        contract = _stability_contract(schedule.seed)
        kernel.register_handoff_stability_contract(contract)
        kernel.save_snapshot()
        from . import PlanKernel

        restored = PlanKernel.open(root)
        restored_contract = restored.handoff_stability_contracts[contract.revision_id]
        assessment = HandoffStabilityEvaluator.assess(
            contract=restored_contract,
            current_generations={"inventory": 8, "permission": 3},
            refreshed_predicates=(),
            active_lock_or_reservation_refs=(f"lock:{schedule.seed}",),
            observed_invalidating_events=(),
            resolved_side_effect_refs=(),
            current_external_writer_assumption_refs=(f"writer:{schedule.seed}",),
            now=20.0,
        )
        holds = assessment.status is EdgeActivationStatus.REFRESH_REQUIRED and not assessment.supports_activation
        return holds, f"status={assessment.status.value} blockers={assessment.blocker_refs!r}"


def _c10(schedule: Wave8FaultSchedule) -> tuple[bool, str]:
    with tempfile.TemporaryDirectory(prefix="nolane-wave8-c10-") as temp:
        root = Path(temp)
        kernel, authorization, principal = _authorized_kernel(schedule.seed, root, idempotent=False)
        kernel.save_snapshot()
        tx = kernel.transaction_for_authorization(authorization.id)
        kernel.transactions.record_dispatch(tx.id, "adapter:wave8", 1)
        kernel._record(
            "action.dispatch_recorded",
            {
                "transaction_id": tx.id,
                "authorization_id": authorization.id,
                "action_id": authorization.action_id,
                "principal_ref": principal,
                "adapter_id": "adapter:wave8",
                "adapter_revision": 1,
            },
        )
        live = kernel.cancel_authorized_action(authorization.id, reason="wave8-race")
        from .execution import TransactionState
        from . import PlanKernel

        restored = PlanKernel.open(root)
        replayed = restored.transaction_for_authorization(authorization.id)
        retry_blocked = False
        try:
            restored.transactions.assert_retry_allowed(replayed.id)
        except AuthorizationError:
            retry_blocked = True
        holds = (
            live.state is TransactionState.CANCELLATION_PENDING
            and replayed.state is TransactionState.CANCELLATION_PENDING
            and retry_blocked
        )
        return holds, f"live={live.state.value} replayed={replayed.state.value} retry_blocked={retry_blocked}"


_CHAOS_EVALUATORS: dict[str, Callable[[Wave8FaultSchedule], tuple[bool, str]]] = {
    "C01": _c01,
    "C02": _c02,
    "C03": _c03,
    "C04": _c04,
    "C05": _c05,
    "C06": _c06,
    "C07": _c07,
    "C08": _c08,
    "C09": _c09,
    "C10": _c10,
}


def _evaluate(invariant_id: str, schedule: Wave8FaultSchedule) -> tuple[bool, str]:
    try:
        return _CHAOS_EVALUATORS[invariant_id](schedule)
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"


def _counterexample(invariant_id: str, schedule: Wave8FaultSchedule, summary: str) -> Wave8Counterexample:
    row = _CHAOS_ROWS[invariant_id]
    return Wave8Counterexample.create(
        invariant_id=invariant_id,
        case_id=f"{invariant_id}:{schedule.seed}",
        seed=schedule.seed,
        generator_version="wave8-chaos-v1",
        recipe=schedule.operations,
        minimized_recipe=schedule.operations,
        expected_relation=row.expectation,
        observed_summary=summary,
    )


def run_wave8_chaos_invariant(
    invariant_id: str,
    seeds: Iterable[int],
) -> tuple[Wave8Counterexample, ...]:
    invariant = str(invariant_id).strip().upper()
    if invariant not in _CHAOS_EVALUATORS:
        raise ValueError(f"unknown Wave-8 chaos invariant: {invariant_id}")
    failures: list[Wave8Counterexample] = []
    for seed in sorted({int(value) for value in seeds}):
        schedule = build_chaos_schedule(invariant, seed)
        holds, summary = _evaluate(invariant, schedule)
        if not holds:
            failures.append(_counterexample(invariant, schedule, summary))
    return tuple(failures)


def run_wave8_chaos(seeds: Iterable[int]) -> tuple[Wave8Counterexample, ...]:
    seed_tuple = tuple(sorted({int(value) for value in seeds}))
    failures = [
        counterexample
        for invariant_id in CHAOS_IDS
        for counterexample in run_wave8_chaos_invariant(invariant_id, seed_tuple)
    ]
    return tuple(sorted(failures, key=lambda row: (row.invariant_id, row.seed, row.case_id)))
