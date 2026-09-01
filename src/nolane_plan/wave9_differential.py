from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .hashing import digest
from .multiwriter import MultiWriterCoordinator, WriteIntent, WriterIdentity
from .production_store import InMemoryProductionStore, StorageCapabilityProfile

WAVE9_DIFFERENTIAL_CASE_IDS = (
    "DF-LIVE-REOPEN",
    "DF-LIVE-SUFFIX-REPLAY",
    "DF-SINGLE-WRITER-PROJECTION",
    "DF-DESTRUCTIVE-COMPACTION",
)

@dataclass(frozen=True, slots=True)
class Wave9DifferentialResult:
    case_id: str
    relation: str
    left_digest: str
    right_digest: str
    passed: bool
    observed_summary: str
    canonical_digest: str

    @classmethod
    def create(cls, *, case_id: str, relation: str, left_digest: str, right_digest: str, observed_summary: str) -> "Wave9DifferentialResult":
        left = str(left_digest)
        right = str(right_digest)
        body = {"case_id": str(case_id), "relation": str(relation), "left_digest": left, "right_digest": right, "passed": left == right, "observed_summary": str(observed_summary)}
        return cls(**body, canonical_digest=digest(body))

@dataclass(frozen=True, slots=True)
class Wave9DifferentialReport:
    results: tuple[Wave9DifferentialResult, ...]
    case_count: int
    passed_count: int
    failed_count: int
    canonical_digest: str

    @classmethod
    def create(cls, results: tuple[Wave9DifferentialResult, ...]) -> "Wave9DifferentialReport":
        count = len(results)
        passed = sum(1 for row in results if row.passed)
        body = {"results": tuple(row.canonical_digest for row in results), "case_count": count, "passed_count": passed, "failed_count": count - passed}
        return cls(results, count, passed, count - passed, digest(body))

def _strong_store(backend_id: str) -> InMemoryProductionStore:
    return InMemoryProductionStore(StorageCapabilityProfile.create(backend_id=backend_id, revision=1, atomic_replace=True, durable_acknowledgement=True, compare_and_swap=True, fencing_tokens=True, transactional_batch=True, destructive_delete=True, crash_recovery_durable=True), require_strong_multiwriter=True)

def _writer(writer_id: str) -> WriterIdentity:
    return WriterIdentity.create(writer_id=writer_id, principal_ref="agent", process_instance_ref=f"process:{writer_id}:1")

def _kernel_wave9_projection(kernel) -> str:
    latest = kernel.latest_observed_authority_epoch
    body = {
        "execution_contracts": tuple((key, value.canonical_digest) for key, value in sorted(kernel.execution_contracts.items())),
        "execution_bindings": tuple(sorted(kernel.authorization_execution_contract_bindings.items())),
        "remote_cancellation_acknowledgements": tuple((key, value.canonical_digest) for key, value in sorted(kernel.remote_cancellation_acknowledgements.items())),
        "compensation_records": tuple((key, value.canonical_digest) for key, value in sorted(kernel.compensation_records.items())),
        "destructive_compaction_observations": tuple((key, value.canonical_digest) for key, value in sorted(kernel.destructive_compaction_observations.items())),
        "observed_authority_epochs": tuple((key, value.canonical_digest) for key, value in sorted(kernel.observed_authority_epochs.items())),
        "latest_epoch_digest": None if latest is None else latest.epoch.canonical_digest,
        "multiwriter_commit_observations": tuple((key, value.canonical_digest) for key, value in sorted(kernel.multiwriter_commit_observations.items())),
        "authorization_epoch_bindings": tuple((key, value.canonical_digest) for key, value in sorted(kernel.authorization_authority_epoch_bindings.items())),
    }
    return digest(body)

def _live_vs_reopen() -> tuple[str, str, str]:
    from . import PlanKernel
    with tempfile.TemporaryDirectory() as root:
        path = Path(root)
        kernel = PlanKernel.create(path, "Wave 9 differential live reopen")
        store = _strong_store("diff-live-reopen")
        coordinator = MultiWriterCoordinator(store)
        kernel.acquire_authority_epoch(coordinator, _writer("w1"), None)
        kernel.save_snapshot()
        left = _kernel_wave9_projection(kernel)
        right = _kernel_wave9_projection(PlanKernel.open(path))
        return left, right, "snapshot reopen preserved Wave-9 durable sidecar projection"

def _live_vs_suffix_replay() -> tuple[str, str, str]:
    from . import PlanKernel
    with tempfile.TemporaryDirectory() as root:
        path = Path(root)
        kernel = PlanKernel.create(path, "Wave 9 differential suffix replay")
        store = _strong_store("diff-suffix")
        coordinator = MultiWriterCoordinator(store)
        lease1 = kernel.acquire_authority_epoch(coordinator, _writer("w1"), None)
        kernel.save_snapshot()
        kernel.acquire_authority_epoch(coordinator, _writer("w2"), lease1.epoch.epoch)
        left = _kernel_wave9_projection(kernel)
        right = _kernel_wave9_projection(PlanKernel.open(path))
        return left, right, "snapshot plus epoch suffix replay matched live projection"

def _single_writer_projection() -> tuple[str, str, str]:
    store = _strong_store("diff-single-writer")
    coordinator = MultiWriterCoordinator(store)
    lease = coordinator.acquire(_writer("w1"), None)
    intent = WriteIntent.create(intent_id="intent:single", writer_id="w1", operation_kind="canonical_update", payload={"value": 1}, idempotent=True, idempotency_key="single:1", conflict_scope="canonical:single", external_effect_possible=False)
    reference = digest({"operation_kind": "canonical_update", "payload": {"value": 1}, "idempotent": True, "idempotency_key": "single:1", "conflict_scope": "canonical:single", "external_effect_possible": False})
    coordinator.commit(intent, lease, expected_revision=0)
    projection = coordinator.reconstruct()
    if len(projection.committed_intents) != 1:
        raise AssertionError("single-writer strong projection did not contain exactly one commit")
    return reference, projection.committed_intents[0].semantic_digest, "strong multi-writer single-writer projection preserved reference intent semantics"

def _pre_post_destructive_compaction() -> tuple[str, str, str]:
    from . import PlanKernel
    with tempfile.TemporaryDirectory() as root:
        kernel = PlanKernel.create(Path(root), "Wave 9 differential destructive compaction")
        store = _strong_store("diff-compaction")
        epoch = store.acquire_epoch("compactor", None)
        kernel.prepare_destructive_compaction(store, epoch, compaction_id="dc:diff", source_representation_id="source:r1", target_representation_id="target:r1")
        kernel.verify_compaction_shadow(store, epoch, "dc:diff")
        kernel.commit_compaction_switch(store, epoch, "dc:diff")
        kernel.retire_compaction_source(store, epoch, "dc:diff")
        verified = kernel.verify_destructive_compaction(store, epoch, "dc:diff")
        return verified.source_canonical_semantic_digest, verified.target_canonical_semantic_digest, "verified destructive compaction preserved canonical semantic projection"

_CASES: tuple[tuple[str, str, Callable[[], tuple[str, str, str]]], ...] = (
    (WAVE9_DIFFERENTIAL_CASE_IDS[0], "live_vs_reopen", _live_vs_reopen),
    (WAVE9_DIFFERENTIAL_CASE_IDS[1], "live_vs_suffix_replay", _live_vs_suffix_replay),
    (WAVE9_DIFFERENTIAL_CASE_IDS[2], "single_writer_vs_strong_multiwriter_projection", _single_writer_projection),
    (WAVE9_DIFFERENTIAL_CASE_IDS[3], "pre_vs_post_destructive_compaction", _pre_post_destructive_compaction),
)

def run_wave9_differential() -> Wave9DifferentialReport:
    results: list[Wave9DifferentialResult] = []
    for case_id, relation, runner in _CASES:
        try:
            left, right, summary = runner()
        except Exception as exc:
            left = digest({"case_id": case_id, "failure_side": "left", "exception": type(exc).__name__})
            right = digest({"case_id": case_id, "failure_side": "right", "message": str(exc)})
            results.append(Wave9DifferentialResult.create(case_id=case_id, relation=relation, left_digest=left, right_digest=right, observed_summary=f"{type(exc).__name__}: {exc}"))
        else:
            results.append(Wave9DifferentialResult.create(case_id=case_id, relation=relation, left_digest=left, right_digest=right, observed_summary=summary))
    return Wave9DifferentialReport.create(tuple(results))

def main() -> int:
    report = run_wave9_differential()
    for row in report.results:
        print(f"{row.case_id} {row.relation}: {'PASS' if row.passed else 'FAIL'} — {row.observed_summary}")
    print(f"Wave 9 differential: {report.passed_count}/{report.case_count} passed; digest={report.canonical_digest}")
    return 0 if report.failed_count == 0 else 1

if __name__ == "__main__":
    raise SystemExit(main())
