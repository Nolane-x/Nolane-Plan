from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src" / "nolane_plan"


class ProbeOutcome(str, Enum):
    KILLED = "KILLED"
    SURVIVED = "SURVIVED"
    INVALID = "INVALID"


@dataclass(frozen=True, slots=True)
class Mutation:
    mutant_id: str
    name: str
    path: str
    replacements: tuple[tuple[str, str], ...]
    target_invariant_id: str


def _one(mutant_id: str, name: str, path: str, old: str, new: str, target: str) -> Mutation:
    return Mutation(mutant_id, name, path, ((old, new),), target)


MUTATIONS = (
    _one(
        "X01", "epoch_monotonicity", "production_store.py",
        '        elif predecessor != epoch_value - 1:\n            raise ValueError("authority epoch predecessor must be the immediately prior epoch")',
        '        elif False and predecessor != epoch_value - 1:\n            raise ValueError("authority epoch predecessor must be the immediately prior epoch")',
        "MW01",
    ),
    _one(
        "X02", "stale_writer_commit", "production_store.py",
        '        if epoch.canonical_digest != current.canonical_digest:\n            raise StorageConflict(',
        '        if False and epoch.canonical_digest != current.canonical_digest:\n            raise StorageConflict(',
        "MW02",
    ),
    _one(
        "X03", "cas_last_writer_wins", "production_store.py",
        '            if expected != self._revision:\n                raise StorageConflict(',
        '            if False and expected != self._revision:\n                raise StorageConflict(',
        "MW03",
    ),
    _one(
        "X04", "active_lineage_deletion", "destructive_compaction.py",
        '        retained = _canon((*active, *dormant, *proof, *fallback))',
        '        retained = _canon((*dormant, *proof, *fallback))',
        "DC01",
    ),
    _one(
        "X05", "source_deletion_before_switch_durability", "destructive_compaction.py",
        '        payload["production_pointer"] = state.intent.target_representation_id\n        compactions[state.intent.compaction_id] = next_state.canonical_payload()',
        '        payload["production_pointer"] = state.intent.target_representation_id\n        representations.pop(state.intent.source_representation_id, None)\n        compactions[state.intent.compaction_id] = next_state.canonical_payload()',
        "DC06",
    ),
    _one(
        "X06", "mixed_representation_recovery", "destructive_compaction.py",
        '            if pointer != intent.target_representation_id:\n                raise DestructiveCompactionError("post-switch phase is not bound to the target production pointer")',
        '            if False and pointer != intent.target_representation_id:\n                raise DestructiveCompactionError("post-switch phase is not bound to the target production pointer")',
        "DC08",
    ),
    _one(
        "X07", "best_effort_cancel_clean", "execution_contract.py",
        '    if contract.cancellation_class not in {CancellationClass.REMOTE_ACKNOWLEDGED, CancellationClass.FENCED_EFFECT}:',
        '    if contract.cancellation_class not in {CancellationClass.REMOTE_BEST_EFFORT, CancellationClass.REMOTE_ACKNOWLEDGED, CancellationClass.FENCED_EFFECT}:',
        "EX04",
    ),
    _one(
        "X08", "wrong_epoch_cancellation_ack", "execution_contract.py",
        '    if acknowledgement.authority_epoch != int(authority_epoch):\n        raise AuthorizationError("remote cancellation authority epoch mismatch")',
        '    if False and acknowledgement.authority_epoch != int(authority_epoch):\n        raise AuthorizationError("remote cancellation authority epoch mismatch")',
        "EX11",
    ),
    _one(
        "X09", "compensation_erases_original_outcome", "execution_contract.py",
        '            original_outcome_applied=self.original_outcome_applied,',
        '            original_outcome_applied=False,',
        "EX08",
    ),
    _one(
        "X10", "unsupported_backend_promoted", "production_store.py",
        '        if self.support != StorageSupport.STRONG_MULTI_WRITER:\n            raise UnsupportedStorageCapability(',
        '        if False and self.support != StorageSupport.STRONG_MULTI_WRITER:\n            raise UnsupportedStorageCapability(',
        "MW11",
    ),
    _one(
        "X11", "old_epoch_authorization_resurrection", "multiwriter_runtime.py",
        '    if (\n        current.backend_id != binding.storage_backend_id',
        '    if False and (\n        current.backend_id != binding.storage_backend_id',
        "MW12",
    ),
    _one(
        "X12", "unknown_wave9_replay_event", "lineage_recovery.py",
        '    spec = DEFAULT_REPLAY_REGISTRY.require(entry.event_type, correctness_significant=True)\n    if spec is None:\n        raise ReplayError(f"missing replay registry entry: {entry.event_type}")',
        '    try:\n        spec = DEFAULT_REPLAY_REGISTRY.require(entry.event_type, correctness_significant=True)\n    except ReplayError:\n        return\n    if spec is None:\n        return',
        "X12",
    ),
)


def classify_probe_result(returncode: int, output: str, target_invariant_id: str) -> ProbeOutcome:
    target = str(target_invariant_id).strip().upper()
    reached = f"TARGET_ASSERTION_REACHED:{target}" in output
    failed = f"TARGET_ASSERTION_FAILED:{target}" in output
    passed = f"TARGET_ASSERTION_PASSED:{target}" in output
    error = f"TARGET_ASSERTION_ERROR:{target}:" in output
    if reached and failed and not passed and not error and returncode != 0:
        return ProbeOutcome.KILLED
    if reached and passed and not failed and not error and returncode == 0:
        return ProbeOutcome.SURVIVED
    return ProbeOutcome.INVALID


def _strong_store(backend_id: str):
    from nolane_plan.production_store import InMemoryProductionStore, StorageCapabilityProfile
    return InMemoryProductionStore(
        StorageCapabilityProfile.create(
            backend_id=backend_id,
            revision=1,
            atomic_replace=True,
            durable_acknowledgement=True,
            compare_and_swap=True,
            fencing_tokens=True,
            transactional_batch=True,
            destructive_delete=True,
            crash_recovery_durable=True,
        ),
        require_strong_multiwriter=True,
    )


def _writer(writer_id: str, principal: str = "agent"):
    from nolane_plan.multiwriter import WriterIdentity
    return WriterIdentity.create(
        writer_id=writer_id,
        principal_ref=principal,
        process_instance_ref=f"process:{writer_id}:1",
    )


def _contract(cancellation_class):
    from nolane_plan.execution_contract import (
        CancellationClass,
        DispatchAcknowledgementClass,
        ExecutionContract,
        IdempotencyGuaranteeClass,
        OutcomeFinalityClass,
    )
    acknowledged = cancellation_class in {CancellationClass.REMOTE_ACKNOWLEDGED, CancellationClass.FENCED_EFFECT}
    return ExecutionContract.create(
        adapter_id="remote",
        adapter_revision=1,
        dispatch_acknowledgement=(DispatchAcknowledgementClass.DURABLE_REMOTE if acknowledged else DispatchAcknowledgementClass.TRANSPORT_ONLY),
        idempotency_guarantee=IdempotencyGuaranteeClass.NONE,
        deduplication_keys=False,
        remote_fencing_tokens=cancellation_class == CancellationClass.FENCED_EFFECT,
        cancellation_class=cancellation_class,
        cancellation_ack_assurance=0.9 if acknowledged else 0.0,
        compensation_supported=True,
        reconciliation_observable=True,
        outcome_finality=OutcomeFinalityClass.OBSERVABLE,
    )


def _ack(authority_epoch: int):
    from nolane_plan.execution_contract import RemoteCancellationAcknowledgement
    return RemoteCancellationAcknowledgement.create(
        acknowledgement_id=f"ack:{authority_epoch}",
        transaction_id="tx:1",
        action_id="effect",
        authorization_id="auth:1",
        canonical_principal_ref="agent",
        adapter_id="remote",
        adapter_revision=1,
        authority_epoch=authority_epoch,
        effect_prevented=True,
        fence_excludes_stale_effect=True,
        observed_at=1,
        assurance=0.9,
        provenance="wave9-mutation-probe",
    )


def _probe_mw01() -> bool:
    from nolane_plan.production_store import AuthorityEpoch
    try:
        AuthorityEpoch.create(
            backend_id="probe",
            backend_revision=1,
            epoch=3,
            predecessor_epoch=1,
            writer_id="w",
            writer_identity_digest="writer-digest",
            acquisition_revision=0,
        )
    except ValueError:
        return True
    return False


def _probe_mw02() -> bool:
    from nolane_plan.production_store import StorageConflict
    store = _strong_store("probe-mw02")
    first = store.acquire_epoch("w1", None, writer_identity_digest="writer:1")
    store.acquire_epoch("w2", first.epoch, writer_identity_digest="writer:2")
    try:
        store.conditional_commit(first, expected_revision=0, payload={"value": 1})
    except StorageConflict:
        return True
    return False


def _probe_mw03() -> bool:
    from nolane_plan.production_store import StorageConflict
    store = _strong_store("probe-mw03")
    epoch = store.acquire_epoch("w1", None, writer_identity_digest="writer:1")
    store.conditional_commit(epoch, expected_revision=0, payload={"value": 1})
    try:
        store.conditional_commit(epoch, expected_revision=0, payload={"value": 2})
    except StorageConflict:
        return store.current_revision() == 1
    return False


def _probe_dc01() -> bool:
    from nolane_plan.destructive_compaction import DestructiveCompactionIntent
    intent = DestructiveCompactionIntent.create(
        compaction_id="dc:probe",
        source_representation_id="source:r1",
        target_representation_id="target:r1",
        source_archive_digest="archive",
        source_semantic_root_digest="semantic-root",
        source_canonical_semantic_digest="canonical-root",
        active_authority_refs=("authority:active",),
        dormant_resurrection_refs=(),
        proof_evidence_debt_refs=(),
        unique_fallback_refs=(),
        prepared_epoch_digest="epoch",
    )
    return "authority:active" in intent.retained_refs


def _prepare_compaction(backend_id: str):
    from pathlib import Path
    import tempfile
    from nolane_plan import PlanKernel
    holder = tempfile.TemporaryDirectory(prefix="wave9-mut-compaction-")
    kernel = PlanKernel.create(Path(holder.name), "Wave 9 mutation compaction")
    store = _strong_store(backend_id)
    epoch = store.acquire_epoch("compactor", None)
    kernel.prepare_destructive_compaction(
        store,
        epoch,
        compaction_id="dc:probe",
        source_representation_id="source:r1",
        target_representation_id="target:r1",
    )
    kernel.verify_compaction_shadow(store, epoch, "dc:probe")
    return holder, kernel, store, epoch


def _probe_dc06() -> bool:
    from nolane_plan.destructive_compaction import DestructiveCompactionCoordinator
    holder, kernel, store, epoch = _prepare_compaction("probe-dc06")
    try:
        try:
            kernel.commit_compaction_switch(store, epoch, "dc:probe")
        except ValueError:
            ids = set(DestructiveCompactionCoordinator(store).representation_ids())
            if ids == {"target:r1"}:
                return False
            raise
        ids = set(DestructiveCompactionCoordinator(store).representation_ids())
        return ids == {"source:r1", "target:r1"}
    finally:
        holder.cleanup()


def _probe_dc08() -> bool:
    from nolane_plan.destructive_compaction import DestructiveCompactionCoordinator, DestructiveCompactionError
    holder, kernel, store, epoch = _prepare_compaction("probe-dc08")
    try:
        kernel.commit_compaction_switch(store, epoch, "dc:probe")
        payload = store.read_payload()
        payload["production_pointer"] = "source:r1"
        store.conditional_commit(epoch, expected_revision=store.current_revision(), payload=payload)
        try:
            DestructiveCompactionCoordinator(store).recover("dc:probe")
        except DestructiveCompactionError:
            return True
        return False
    finally:
        holder.cleanup()


def _probe_ex04() -> bool:
    from nolane_plan.execution_contract import CancellationClass, validate_remote_cancellation_acknowledgement
    from nolane_plan.types import AuthorizationError
    try:
        validate_remote_cancellation_acknowledgement(
            _ack(1),
            _contract(CancellationClass.REMOTE_BEST_EFFORT),
            transaction_id="tx:1",
            action_id="effect",
            authorization_id="auth:1",
            principal_ref="agent",
            authority_epoch=1,
        )
    except AuthorizationError:
        return True
    return False


def _probe_ex11() -> bool:
    from nolane_plan.execution_contract import CancellationClass, validate_remote_cancellation_acknowledgement
    from nolane_plan.types import AuthorizationError
    try:
        validate_remote_cancellation_acknowledgement(
            _ack(2),
            _contract(CancellationClass.REMOTE_ACKNOWLEDGED),
            transaction_id="tx:1",
            action_id="effect",
            authorization_id="auth:1",
            principal_ref="agent",
            authority_epoch=1,
        )
    except AuthorizationError:
        return True
    return False


def _probe_ex08() -> bool:
    from nolane_plan.execution_contract import CompensationRecord, CompensationStatus
    record = CompensationRecord.create(
        record_id="comp:1",
        original_transaction_id="tx:original",
        compensation_transaction_id="tx:comp",
        compensation_authorization_id="auth:comp",
        original_outcome_applied=True,
    )
    transitioned = record.transition(CompensationStatus.FAILED, evidence_ref="evidence:failed")
    return transitioned.original_outcome_applied is True


def _probe_mw11() -> bool:
    from nolane_plan.production_store import StorageCapabilityProfile, UnsupportedStorageCapability
    profile = StorageCapabilityProfile.create(
        backend_id="weak",
        revision=1,
        atomic_replace=True,
        durable_acknowledgement=True,
        compare_and_swap=False,
        fencing_tokens=False,
        transactional_batch=True,
        destructive_delete=False,
        crash_recovery_durable=True,
    )
    try:
        profile.require_strong_multiwriter()
    except UnsupportedStorageCapability:
        return True
    return False


def _probe_mw12() -> bool:
    from pathlib import Path
    import tempfile
    from nolane_plan import PlanKernel
    from nolane_plan.actions import ActionIntent, AuthorityGrant
    from nolane_plan.execution import AdapterProfile
    from nolane_plan.execution_contract import CancellationClass
    from nolane_plan.multiwriter import MultiWriterCoordinator
    from nolane_plan.types import AuthorizationError, RiskClass
    with tempfile.TemporaryDirectory(prefix="wave9-mut-mw12-") as root:
        kernel = PlanKernel.create(Path(root), "Wave 9 mutation MW12")
        kernel.register_adapter(AdapterProfile("remote", 1, False, False, 1.0))
        kernel.register_execution_contract(_contract(CancellationClass.FENCED_EFFECT))
        kernel.propose_action(ActionIntent("effect", "effect", RiskClass.REVERSIBLE, idempotent=False))
        kernel.add_grant(AuthorityGrant("grant", "agent", frozenset({"effect"})))
        authorization = kernel.authorize("effect", "agent", ("grant",), 1, adapter_id="remote")
        kernel.bind_authorization_execution_contract(authorization.id)
        store = _strong_store("probe-mw12")
        coordinator = MultiWriterCoordinator(store)
        lease1 = kernel.acquire_authority_epoch(coordinator, _writer("w1"), None)
        kernel.bind_authorization_authority_epoch(authorization.id, lease1)
        kernel.acquire_authority_epoch(coordinator, _writer("w2"), lease1.epoch.epoch)
        try:
            kernel.assert_authorization_authority_epoch_current(authorization.id, store)
        except AuthorizationError:
            return True
        return False


def _probe_x12() -> bool:
    from types import SimpleNamespace
    from nolane_plan import lineage_recovery
    from nolane_plan.types import ReplayError
    entry = SimpleNamespace(event_type="writer.wave9_unknown_correctness_event", payload={}, sequence=1)
    try:
        lineage_recovery._replay_entry(object(), entry)
    except ReplayError:
        return True
    return False


_PROBES = {
    "MW01": _probe_mw01,
    "MW02": _probe_mw02,
    "MW03": _probe_mw03,
    "DC01": _probe_dc01,
    "DC06": _probe_dc06,
    "DC08": _probe_dc08,
    "EX04": _probe_ex04,
    "EX11": _probe_ex11,
    "EX08": _probe_ex08,
    "MW11": _probe_mw11,
    "MW12": _probe_mw12,
    "X12": _probe_x12,
}


def _probe_target(target: str) -> int:
    target = str(target).strip().upper()
    print(f"TARGET_ASSERTION_REACHED:{target}")
    probe = _PROBES.get(target)
    if probe is None:
        print(f"TARGET_ASSERTION_ERROR:{target}:unknown_target")
        return 2
    try:
        passed = bool(probe())
    except Exception as exc:
        print(f"TARGET_ASSERTION_ERROR:{target}:{type(exc).__name__}:{exc}")
        return 2
    if passed:
        print(f"TARGET_ASSERTION_PASSED:{target}")
        return 0
    print(f"TARGET_ASSERTION_FAILED:{target}")
    return 1


def run_mutation(mutation: Mutation) -> tuple[ProbeOutcome, str]:
    with tempfile.TemporaryDirectory(prefix=f"nolane-wave9-mut-{mutation.mutant_id.lower()}-") as temp_dir:
        temp = Path(temp_dir)
        package_root = temp / "src" / "nolane_plan"
        shutil.copytree(SOURCE, package_root)
        target = package_root / mutation.path
        mutated = target.read_text(encoding="utf-8")
        for old, new in mutation.replacements:
            count = mutated.count(old)
            if count != 1:
                return ProbeOutcome.INVALID, f"mutation target count={count}, expected 1 in {mutation.path}"
            mutated = mutated.replace(old, new, 1)
        target.write_text(mutated, encoding="utf-8")

        env = os.environ.copy()
        env["PYTHONPATH"] = str(temp / "src")
        try:
            proc = subprocess.run(
                [sys.executable, str(Path(__file__).resolve()), "--probe", mutation.target_invariant_id],
                cwd=ROOT,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=120,
            )
        except subprocess.TimeoutExpired as exc:
            return ProbeOutcome.INVALID, f"timeout: {exc}"
        outcome = classify_probe_result(proc.returncode, proc.stdout, mutation.target_invariant_id)
        return outcome, proc.stdout


def main() -> int:
    if len(sys.argv) >= 2 and sys.argv[1] == "--probe":
        if len(sys.argv) != 3:
            print("probe usage: --probe TARGET")
            return 2
        return _probe_target(sys.argv[2])

    killed = 0
    invalid = 0
    for mutation in MUTATIONS:
        outcome, detail = run_mutation(mutation)
        if outcome is ProbeOutcome.KILLED:
            killed += 1
            print(f"KILLED {mutation.mutant_id} {mutation.name} target={mutation.target_invariant_id}")
        elif outcome is ProbeOutcome.SURVIVED:
            print(f"SURVIVED {mutation.mutant_id} {mutation.name} target={mutation.target_invariant_id}")
        else:
            invalid += 1
            tail = "\n".join(detail.splitlines()[-8:])
            print(f"INVALID {mutation.mutant_id} {mutation.name} target={mutation.target_invariant_id}: {tail}")
    print(f"WAVE9_MUTATIONS_CAUGHT={killed}/{len(MUTATIONS)}")
    print(f"WAVE9_MUTATIONS_INVALID={invalid}")
    return 0 if killed == len(MUTATIONS) and invalid == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())