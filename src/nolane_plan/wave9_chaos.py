from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .destructive_compaction import DestructiveCompactionCoordinator, DestructiveCompactionPhase, InjectedCompactionFault
from .execution_contract import CancellationClass, DispatchAcknowledgementClass, ExecutionContract, IdempotencyGuaranteeClass, OutcomeFinalityClass, RemoteCancellationAcknowledgement, validate_remote_cancellation_acknowledgement
from .hashing import digest
from .multiwriter import CommitDecisionStatus, MultiWriterCoordinator, WriteIntent, WriterIdentity
from .production_store import InMemoryProductionStore, StorageCapabilityProfile, StorageConflict, UnsupportedStorageCapability
from .types import AuthorizationError

WAVE9_CHAOS_CASE_IDS = (
    "CH-DC07-CRASH-BEFORE-SWITCH", "CH-DC08-CRASH-AFTER-SWITCH", "CH-DC11-STALE-RETIRE",
    "CH-EX04-BEST-EFFORT-AMBIGUITY", "CH-EX11-WRONG-EPOCH-ACK", "CH-EX12-UNSUPPORTED-CANCEL",
    "CH-MW02-EPOCH-TAKEOVER", "CH-MW03-CAS-RACE", "CH-MW04-IDEMPOTENT-DUPLICATE",
    "CH-MW05-NONIDEMPOTENT-CONFLICT", "CH-MW06-LEASE-EXPIRY", "CH-MW11-UNSUPPORTED-BACKEND",
)

@dataclass(frozen=True, slots=True)
class Wave9ChaosCaseResult:
    case_id: str
    invariant_id: str
    passed: bool
    observed_summary: str
    canonical_digest: str

    @classmethod
    def create(cls, *, case_id: str, invariant_id: str, passed: bool, observed_summary: str) -> "Wave9ChaosCaseResult":
        body = {"case_id": str(case_id), "invariant_id": str(invariant_id), "passed": bool(passed), "observed_summary": str(observed_summary)}
        return cls(**body, canonical_digest=digest(body))

@dataclass(frozen=True, slots=True)
class Wave9ChaosReport:
    results: tuple[Wave9ChaosCaseResult, ...]
    case_count: int
    passed_count: int
    failed_count: int
    canonical_digest: str

    @classmethod
    def create(cls, results: tuple[Wave9ChaosCaseResult, ...]) -> "Wave9ChaosReport":
        count = len(results)
        passed = sum(1 for row in results if row.passed)
        body = {"results": tuple(row.canonical_digest for row in results), "case_count": count, "passed_count": passed, "failed_count": count - passed}
        return cls(results, count, passed, count - passed, digest(body))

def _strong_store(backend_id: str) -> InMemoryProductionStore:
    return InMemoryProductionStore(StorageCapabilityProfile.create(backend_id=backend_id, revision=1, atomic_replace=True, durable_acknowledgement=True, compare_and_swap=True, fencing_tokens=True, transactional_batch=True, destructive_delete=True, crash_recovery_durable=True), require_strong_multiwriter=True)

def _writer(writer_id: str) -> WriterIdentity:
    return WriterIdentity.create(writer_id=writer_id, principal_ref="agent", process_instance_ref=f"process:{writer_id}:1")

def _intent(intent_id: str, writer_id: str, *, payload_value: int, idempotent: bool, idempotency_key: str | None, conflict_scope: str, external_effect_possible: bool = False) -> WriteIntent:
    return WriteIntent.create(intent_id=intent_id, writer_id=writer_id, operation_kind="canonical_update", payload={"value": payload_value}, idempotent=idempotent, idempotency_key=idempotency_key, conflict_scope=conflict_scope, external_effect_possible=external_effect_possible)

def _execution_contract(cancellation_class: CancellationClass) -> ExecutionContract:
    acknowledged = cancellation_class in {CancellationClass.REMOTE_ACKNOWLEDGED, CancellationClass.FENCED_EFFECT}
    return ExecutionContract.create(adapter_id="remote", adapter_revision=1, dispatch_acknowledgement=DispatchAcknowledgementClass.DURABLE_REMOTE if acknowledged else DispatchAcknowledgementClass.TRANSPORT_ONLY, idempotency_guarantee=IdempotencyGuaranteeClass.NONE, deduplication_keys=False, remote_fencing_tokens=cancellation_class == CancellationClass.FENCED_EFFECT, cancellation_class=cancellation_class, cancellation_ack_assurance=0.9 if acknowledged else 0.0, compensation_supported=False, reconciliation_observable=True, outcome_finality=OutcomeFinalityClass.OBSERVABLE)

def _ack(*, authority_epoch: int) -> RemoteCancellationAcknowledgement:
    return RemoteCancellationAcknowledgement.create(acknowledgement_id=f"ack:{authority_epoch}", transaction_id="tx:1", action_id="action:1", authorization_id="auth:1", canonical_principal_ref="agent", adapter_id="remote", adapter_revision=1, authority_epoch=authority_epoch, effect_prevented=True, fence_excludes_stale_effect=True, observed_at=1, assurance=0.9, provenance="wave9-chaos")

def _case_dc07() -> str:
    from . import PlanKernel
    with tempfile.TemporaryDirectory() as root:
        kernel = PlanKernel.create(Path(root), "Wave 9 chaos DC07")
        store = _strong_store("chaos-dc07")
        epoch = store.acquire_epoch("compactor", None)
        kernel.prepare_destructive_compaction(store, epoch, compaction_id="dc:chaos", source_representation_id="source:r1", target_representation_id="target:r1")
        try:
            kernel.verify_compaction_shadow(store, epoch, "dc:chaos", fault_after=DestructiveCompactionPhase.SHADOW_WRITTEN)
        except InjectedCompactionFault:
            pass
        else:
            raise AssertionError("shadow fault was not injected")
        reopened = DestructiveCompactionCoordinator(store)
        state = reopened.recover("dc:chaos")
        if state.phase != DestructiveCompactionPhase.SHADOW_WRITTEN or reopened.production_pointer() != "source:r1":
            raise AssertionError("pre-switch crash did not reopen source authority")
        return "shadow fault recovered source pointer"

def _case_dc08() -> str:
    from . import PlanKernel
    with tempfile.TemporaryDirectory() as root:
        kernel = PlanKernel.create(Path(root), "Wave 9 chaos DC08")
        store = _strong_store("chaos-dc08")
        epoch = store.acquire_epoch("compactor", None)
        kernel.prepare_destructive_compaction(store, epoch, compaction_id="dc:chaos", source_representation_id="source:r1", target_representation_id="target:r1")
        kernel.verify_compaction_shadow(store, epoch, "dc:chaos")
        try:
            kernel.commit_compaction_switch(store, epoch, "dc:chaos", fault_after=DestructiveCompactionPhase.SWITCH_COMMITTED)
        except InjectedCompactionFault:
            pass
        else:
            raise AssertionError("switch fault was not injected")
        reopened = DestructiveCompactionCoordinator(store)
        state = reopened.recover("dc:chaos")
        if state.phase != DestructiveCompactionPhase.SWITCH_COMMITTED or reopened.production_pointer() != "target:r1":
            raise AssertionError("post-switch crash did not reopen target authority")
        if set(reopened.representation_ids()) != {"source:r1", "target:r1"}:
            raise AssertionError("post-switch recovery produced incoherent representation state")
        return "switch fault recovered one target-authoritative pointer"

def _case_dc11() -> str:
    from . import PlanKernel
    with tempfile.TemporaryDirectory() as root:
        kernel = PlanKernel.create(Path(root), "Wave 9 chaos DC11")
        store = _strong_store("chaos-dc11")
        epoch1 = store.acquire_epoch("compactor-a", None)
        kernel.prepare_destructive_compaction(store, epoch1, compaction_id="dc:chaos", source_representation_id="source:r1", target_representation_id="target:r1")
        kernel.verify_compaction_shadow(store, epoch1, "dc:chaos")
        kernel.commit_compaction_switch(store, epoch1, "dc:chaos")
        store.acquire_epoch("writer-b", epoch1.epoch)
        try:
            kernel.retire_compaction_source(store, epoch1, "dc:chaos")
        except StorageConflict:
            return "new epoch fenced stale retirement"
        raise AssertionError("stale compactor retired storage")

def _case_ex04() -> str:
    try:
        validate_remote_cancellation_acknowledgement(_ack(authority_epoch=1), _execution_contract(CancellationClass.REMOTE_BEST_EFFORT), transaction_id="tx:1", action_id="action:1", authorization_id="auth:1", principal_ref="agent", authority_epoch=1)
    except AuthorizationError:
        return "best-effort cancellation remained non-clean"
    raise AssertionError("best-effort cancellation was promoted to clean")

def _case_ex11() -> str:
    try:
        validate_remote_cancellation_acknowledgement(_ack(authority_epoch=2), _execution_contract(CancellationClass.REMOTE_ACKNOWLEDGED), transaction_id="tx:1", action_id="action:1", authorization_id="auth:1", principal_ref="agent", authority_epoch=1)
    except AuthorizationError:
        return "wrong-epoch acknowledgement rejected"
    raise AssertionError("wrong-epoch acknowledgement closed cancellation")

def _case_ex12() -> str:
    try:
        validate_remote_cancellation_acknowledgement(_ack(authority_epoch=1), _execution_contract(CancellationClass.UNSUPPORTED), transaction_id="tx:1", action_id="action:1", authorization_id="auth:1", principal_ref="agent", authority_epoch=1)
    except AuthorizationError:
        return "unsupported cancellation stayed fail-closed"
    raise AssertionError("unsupported cancellation produced clean acknowledgement")

def _case_mw02() -> str:
    store = _strong_store("chaos-mw02")
    coordinator = MultiWriterCoordinator(store)
    lease1 = coordinator.acquire(_writer("w1"), None)
    coordinator.acquire(_writer("w2"), lease1.epoch.epoch)
    try:
        coordinator.commit(_intent("intent:stale", "w1", payload_value=1, idempotent=True, idempotency_key="stale:1", conflict_scope="scope:stale"), lease1, expected_revision=0)
    except StorageConflict:
        return "epoch takeover fenced stale commit"
    raise AssertionError("stale epoch committed authoritative state")

def _case_mw03() -> str:
    store = _strong_store("chaos-mw03")
    epoch = store.acquire_epoch("w1", None)
    first = store.conditional_commit(epoch, expected_revision=0, payload={"winner": "a"})
    try:
        store.conditional_commit(epoch, expected_revision=0, payload={"winner": "b"})
    except StorageConflict:
        if store.current_revision() != first.committed_revision:
            raise AssertionError("losing CAS changed canonical revision")
        return "same-predecessor CAS admitted one successor"
    raise AssertionError("two commits won same predecessor CAS")

def _case_mw04() -> str:
    store = _strong_store("chaos-mw04")
    coordinator = MultiWriterCoordinator(store)
    lease1 = coordinator.acquire(_writer("w1"), None)
    first = coordinator.commit(_intent("intent:1", "w1", payload_value=1, idempotent=True, idempotency_key="idem:1", conflict_scope="scope:idem"), lease1, expected_revision=0)
    lease2 = coordinator.acquire(_writer("w2"), lease1.epoch.epoch)
    second = coordinator.commit(_intent("intent:2", "w2", payload_value=1, idempotent=True, idempotency_key="idem:1", conflict_scope="scope:idem"), lease2, expected_revision=first.storage_revision)
    if second.status != CommitDecisionStatus.DUPLICATE_CONVERGED or second.authoritative_intent_digest != first.authoritative_intent_digest:
        raise AssertionError("duplicate idempotent intent minted second authority")
    return "duplicate intent converged on incumbent authority"

def _case_mw05() -> str:
    store = _strong_store("chaos-mw05")
    coordinator = MultiWriterCoordinator(store)
    lease1 = coordinator.acquire(_writer("w1"), None)
    first = coordinator.commit(_intent("intent:1", "w1", payload_value=1, idempotent=False, idempotency_key=None, conflict_scope="scope:nonidem", external_effect_possible=True), lease1, expected_revision=0)
    lease2 = coordinator.acquire(_writer("w2"), lease1.epoch.epoch)
    second = coordinator.commit(_intent("intent:2", "w2", payload_value=2, idempotent=False, idempotency_key=None, conflict_scope="scope:nonidem", external_effect_possible=True), lease2, expected_revision=first.storage_revision)
    if second.status != CommitDecisionStatus.CONFLICT_RECONCILIATION_REQUIRED or second.conflict is None:
        raise AssertionError("non-idempotent conflict did not require reconciliation")
    return "non-idempotent conflict persisted reconciliation state"

def _case_mw06() -> str:
    store = _strong_store("chaos-mw06")
    coordinator = MultiWriterCoordinator(store)
    lease = coordinator.acquire(_writer("w1"), None, valid_until=1)
    coordinator.commit(_intent("intent:effect", "w1", payload_value=1, idempotent=False, idempotency_key=None, conflict_scope="scope:effect", external_effect_possible=True), lease, expected_revision=0, now=1)
    assessment = coordinator.assess_expired_lease(lease, now=2)
    if not assessment.expired or not assessment.reconciliation_required or assessment.external_effect_absence_proven:
        raise AssertionError("lease expiry lost external-effect ambiguity")
    return "expired lease preserved external-effect ambiguity"

def _case_mw11() -> str:
    weak = InMemoryProductionStore(StorageCapabilityProfile.create(backend_id="chaos-mw11", revision=1, atomic_replace=True, durable_acknowledgement=True, compare_and_swap=False, fencing_tokens=False, transactional_batch=False, destructive_delete=False, crash_recovery_durable=True))
    try:
        MultiWriterCoordinator(weak)
    except UnsupportedStorageCapability:
        return "backend without CAS/fencing stayed unsupported"
    raise AssertionError("weak backend was promoted to strong multi-writer")

_CASES: tuple[tuple[str, str, Callable[[], str]], ...] = (
    (WAVE9_CHAOS_CASE_IDS[0], "DC07", _case_dc07), (WAVE9_CHAOS_CASE_IDS[1], "DC08", _case_dc08), (WAVE9_CHAOS_CASE_IDS[2], "DC11", _case_dc11),
    (WAVE9_CHAOS_CASE_IDS[3], "EX04", _case_ex04), (WAVE9_CHAOS_CASE_IDS[4], "EX11", _case_ex11), (WAVE9_CHAOS_CASE_IDS[5], "EX12", _case_ex12),
    (WAVE9_CHAOS_CASE_IDS[6], "MW02", _case_mw02), (WAVE9_CHAOS_CASE_IDS[7], "MW03", _case_mw03), (WAVE9_CHAOS_CASE_IDS[8], "MW04", _case_mw04),
    (WAVE9_CHAOS_CASE_IDS[9], "MW05", _case_mw05), (WAVE9_CHAOS_CASE_IDS[10], "MW06", _case_mw06), (WAVE9_CHAOS_CASE_IDS[11], "MW11", _case_mw11),
)

def run_wave9_chaos() -> Wave9ChaosReport:
    results: list[Wave9ChaosCaseResult] = []
    for case_id, invariant_id, runner in _CASES:
        try:
            summary = runner()
        except Exception as exc:
            results.append(Wave9ChaosCaseResult.create(case_id=case_id, invariant_id=invariant_id, passed=False, observed_summary=f"{type(exc).__name__}: {exc}"))
        else:
            results.append(Wave9ChaosCaseResult.create(case_id=case_id, invariant_id=invariant_id, passed=True, observed_summary=summary))
    return Wave9ChaosReport.create(tuple(results))

def main() -> int:
    report = run_wave9_chaos()
    for row in report.results:
        print(f"{row.case_id} {row.invariant_id}: {'PASS' if row.passed else 'FAIL'} — {row.observed_summary}")
    print(f"Wave 9 chaos: {report.passed_count}/{report.case_count} passed; digest={report.canonical_digest}")
    return 0 if report.failed_count == 0 else 1

if __name__ == "__main__":
    raise SystemExit(main())
