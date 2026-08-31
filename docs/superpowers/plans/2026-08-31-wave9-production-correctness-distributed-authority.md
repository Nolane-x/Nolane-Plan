# Wave 9 Production Correctness & Distributed Authority Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend Nolane Plan from a single-correctness-writer reference runtime to bounded production correctness for destructive compaction, external execution capability semantics, and multi-writer authority on storage backends that prove atomic CAS/fencing guarantees.

**Architecture:** Preserve `PlanKernel`, the Wave 7 lineage system, the existing replay registry, and Wave 8 conformance as the semantic core. Add a persistence-backed Authority Epoch and conditional-write contract, then make destructive compaction and external execution consume that contract; finally integrate bounded multi-writer conflict handling, restart/replay, chaos, mutation, coverage, and release gates.

**Tech Stack:** Python >=3.11, stdlib dataclasses/enums/protocols, JSON/hash-linked journal, deterministic unittest suites, GitHub Actions 3.11/3.12/3.13.

**Spec:** `docs/superpowers/specs/2026-08-31-wave9-production-correctness-distributed-authority-design.md`

## Global Constraints

- Base release is exactly `0.8.0a1` at `8f0288ee2119a05a83923ae16e0ec56b7cbad1c8`.
- Target release is `0.9.0a1` only after all Wave 9 release gates pass.
- Existing single-writer filesystem behavior remains supported.
- Existing replay registry remains the only replay authority; no second replay engine.
- Existing `_writer_lock` remains in-process serialization and is supplemented, not replaced, by storage fencing.
- Backends without atomic compare-and-swap/fencing cannot be promoted to strong multi-writer status.
- External cancellation guarantees may never be stronger than the registered adapter contract.
- Wave 8 conformance, mutation, coverage, and all historical gates remain mandatory regression evidence.
- RESEARCH/BOUNDARY surfaces remain explicitly outside bounded correctness closure.

---

### Task 1: Storage capability and Authority Epoch primitives

**Files:**
- Create: `src/nolane_plan/production_store.py`
- Create: `tests/test_wave9_production_store.py`

**Interfaces:**
- Produces `StorageSupport`, `StorageCapabilityProfile`, `AuthorityEpoch`, `ConditionalWriteReceipt`, `StorageConflict`, `UnsupportedStorageCapability`, `InMemoryProductionStore`.
- `InMemoryProductionStore.acquire_epoch(writer_id: str, expected_epoch: int | None) -> AuthorityEpoch`
- `InMemoryProductionStore.conditional_commit(epoch: AuthorityEpoch, expected_revision: int, payload: dict[str, object]) -> ConditionalWriteReceipt`
- `InMemoryProductionStore.current_epoch() -> AuthorityEpoch | None`
- `InMemoryProductionStore.current_revision() -> int`
- `InMemoryProductionStore.read_payload() -> dict[str, object]`

- [ ] **Step 1: Write RED tests for capability validation and unsupported strong mode**

Test that strong multi-writer support requires atomic CAS + fencing + durable acknowledgement; profiles without the set are classified unsupported and cannot acquire a strong epoch.

- [ ] **Step 2: Run focused RED**

Run: `python -m unittest tests.test_wave9_production_store -v`
Expected: import failure for `nolane_plan.production_store`.

- [ ] **Step 3: Implement immutable capability/epoch/receipt types**

Each canonical digest must bind all correctness-relevant fields and reject empty writer IDs, negative revisions, non-monotonic epochs, and malformed predecessor bindings.

- [ ] **Step 4: Implement deterministic in-memory CAS/fencing backend**

The backend must provide a bounded reference implementation used by tests; it is not a network consensus claim.

- [ ] **Step 5: Run focused GREEN twice**

Run the focused test module twice and require identical epoch/receipt digests.

- [ ] **Step 6: Run full regression and commit**

Run `python -m unittest discover -s tests -v` plus `python -m compileall -q src`.

---

### Task 2: External execution capability contract

**Files:**
- Create: `src/nolane_plan/execution_contract.py`
- Modify: `src/nolane_plan/execution.py`
- Modify: `src/nolane_plan/kernel.py` or the existing runtime patch module that owns adapter registration
- Modify: `src/nolane_plan/__init__.py`
- Create: `tests/test_wave9_execution_contract.py`

**Interfaces:**
- Produces `DispatchAcknowledgementClass`, `IdempotencyGuaranteeClass`, `CancellationClass`, `OutcomeFinalityClass`, `ExecutionContract`, `RemoteCancellationAcknowledgement`, `CompensationRecord`.
- `ExecutionContract.require_for_strong_dispatch(...) -> bool`
- `RemoteCancellationAcknowledgement.create(...)`
- Kernel registration must bind contract revision/digest to adapter identity.

- [ ] **Step 1: RED EX01/EX02/EX09/EX12**

Tests must reject capability downgrade, adapter revision mismatch, and unsupported cancellation promotion.

- [ ] **Step 2: RED EX03–EX08/EX10/EX11**

Tests must prove exact transaction/action/adapter/principal/epoch binding, best-effort cancellation ambiguity, compensation non-erasure, restart preservation, and wrong-epoch evidence rejection.

- [ ] **Step 3: Implement contract types and conservative defaults**

Existing `AdapterProfile` callers remain compatible; missing Wave 9 capability data means conservative/unsupported strong behavior rather than invented guarantees.

- [ ] **Step 4: Integrate cancellation and compensation transitions**

Reuse the Wave 8 cancellation ledger and replay path. Do not add a separate transaction state machine.

- [ ] **Step 5: GREEN focused + historical cancellation regression**

Run `tests.test_wave9_execution_contract` and `tests.test_wave8_cancellation_fence` twice.

- [ ] **Step 6: Commit**

---

### Task 3: Destructive compaction protocol

**Files:**
- Create: `src/nolane_plan/destructive_compaction.py`
- Create: `src/nolane_plan/destructive_compaction_runtime.py`
- Reuse/modify: `src/nolane_plan/compaction.py`
- Reuse/modify: `src/nolane_plan/compaction_runtime.py`
- Modify: `src/nolane_plan/__init__.py`
- Create: `tests/test_wave9_destructive_compaction.py`

**Interfaces:**
- Produces `DestructiveCompactionPhase`, `DestructiveCompactionIntent`, `ShadowVerificationReceipt`, `ProductionSwitchReceipt`, `RetirementManifest`, `DestructiveCompactionResult`.
- Kernel methods: `prepare_destructive_compaction`, `verify_compaction_shadow`, `commit_compaction_switch`, `retire_compaction_source`, `verify_destructive_compaction`.
- Every method consumes the current `AuthorityEpoch` and rejects stale epochs.

- [ ] **Step 1: RED DC01–DC06**

Prove exact retention closure, semantic reconstruction, epoch/revision conditional switch, and no source deletion before durable switch.

- [ ] **Step 2: RED DC07–DC12 with deterministic fault points**

Inject fault tokens at every protocol phase and reopen from storage. No sleeps or race timing.

- [ ] **Step 3: Implement PREPARED and SHADOW_WRITTEN**

Reuse Wave 7 archive/reconstruction logic to compute retention closure and semantic equivalence.

- [ ] **Step 4: Implement SWITCH_COMMITTED via storage CAS**

The production pointer moves only under exact expected storage revision and current authority epoch.

- [ ] **Step 5: Implement exact idempotent retirement**

Deletion set is manifest-bound; repeated retirement cannot broaden it.

- [ ] **Step 6: Implement replay/snapshot reducers in the existing registry**

Unknown or tampered destructive-compaction events fail closed.

- [ ] **Step 7: Focused GREEN twice + Wave 7 compaction regression**

Run both Wave 9 destructive compaction and Wave 7 compaction/replay tests.

- [ ] **Step 8: Commit**

---

### Task 4: Multi-writer authority and conflict model

**Files:**
- Create: `src/nolane_plan/multiwriter.py`
- Create: `src/nolane_plan/multiwriter_runtime.py`
- Modify: `src/nolane_plan/__init__.py`
- Create: `tests/test_wave9_multiwriter.py`

**Interfaces:**
- Produces `WriterIdentity`, `WriterLease`, `WriteIntent`, `WriteConflict`, `EpochFenceReceipt`, `CommitDecision`, `MultiWriterCoordinator`.
- `MultiWriterCoordinator.acquire(writer: WriterIdentity, expected_epoch: int | None) -> WriterLease`
- `MultiWriterCoordinator.commit(intent: WriteIntent, lease: WriterLease, expected_revision: int) -> CommitDecision`
- `MultiWriterCoordinator.reconstruct(...)` from durable epoch/receipts.

- [ ] **Step 1: RED MW01–MW03/MW07/MW11**

Monotonic epoch, stale-writer rejection, single canonical CAS successor, writer-bound receipts, unsupported backend rejection.

- [ ] **Step 2: RED MW04–MW06**

Duplicate idempotent intents converge; conflicting non-idempotent intents become reconciliation state; lease expiry alone never proves absent external effect.

- [ ] **Step 3: RED MW08–MW12**

Restart reconstruction, live/replay equivalence, split-brain bounded simulation, unsupported backend classification, and old-epoch authority invalidation.

- [ ] **Step 4: Implement coordinator on `ProductionStore`**

Do not implement consensus; require a backend capability proof for strong mode.

- [ ] **Step 5: Bind kernel strong authority to current epoch**

Authorizations that can reach strong external dispatch receive an epoch sidecar/binding. Epoch transition makes the old binding unusable until explicit revalidation.

- [ ] **Step 6: GREEN deterministic schedule matrix twice**

Run schedules in forward/reverse writer order and assert the same canonical result or same explicit conflict classification.

- [ ] **Step 7: Commit**

---

### Task 5: Snapshot/replay and restart closure

**Files:**
- Modify: existing Wave 7 lineage/snapshot runtime modules only at their extension seams
- Modify: Wave 9 runtime modules from Tasks 2–4
- Create: `tests/test_wave9_replay_restart.py`

**Interfaces:**
- Snapshot persists current authority epoch, storage revision binding, multi-writer outstanding intents/conflicts, external execution contracts, pending cancellation/compensation state, and destructive compaction phase records.
- Replay reducers reconstruct exact durable state and recompute current usability rather than resurrect authority.

- [ ] **Step 1: RED snapshot round-trip**

Create states in every nonterminal Wave 9 phase and reopen; compare canonical projections.

- [ ] **Step 2: RED snapshot + suffix replay**

Snapshot at epoch N, append epoch N+1 and compaction/execution suffix events, then reopen and require exact equivalence.

- [ ] **Step 3: RED tamper/unknown-event fail-closed**

Recomputed outer snapshot digest must not hide invalid Wave 9 internal digests.

- [ ] **Step 4: Implement serialization/restoration through existing snapshot/replay registry**

- [ ] **Step 5: GREEN twice and commit**

---

### Task 6: Wave 9 deterministic chaos and differential schedules

**Files:**
- Create: `src/nolane_plan/wave9_registry.py`
- Create: `src/nolane_plan/wave9_chaos.py`
- Create: `src/nolane_plan/wave9_differential.py`
- Create: `tests/test_wave9_registry.py`
- Create: `tests/test_wave9_chaos.py`
- Create: `tests/test_wave9_differential.py`

**Interfaces:**
- Frozen invariant registry contains DC01–DC12, EX01–EX12, MW01–MW12 plus coverage/mutation bookkeeping invariants.
- Chaos runner uses deterministic fault schedules only.
- Differential runner compares live vs reopen, live vs suffix replay, single-writer reference vs strong multi-writer single-writer projection, and pre/post destructive compaction canonical projections.

- [ ] **Step 1: RED frozen registry and exact counts**

- [ ] **Step 2: RED deterministic chaos schedules**

- [ ] **Step 3: RED differential equivalence projections**

- [ ] **Step 4: Implement runners using production APIs only**

- [ ] **Step 5: Run each runner twice and commit**

---

### Task 7: Target-specific Wave 9 mutation gate and coverage reconciliation

**Files:**
- Create: `scripts/wave9_mutation_gate.py`
- Create: `src/nolane_plan/wave9_coverage.py`
- Create: `tests/test_wave9_mutation_gate.py`
- Create: `tests/test_wave9_coverage.py`
- Modify: `docs/specs/SPEC-COVERAGE.md`
- Modify: `.github/workflows/ci.yml`

**Interfaces:**
- At least 12 declared constitutional mutants targeting the spec’s mutation list.
- A kill is valid only when the declared target assertion fails.
- Coverage report has no orphan Wave 9 invariant, no evidence-free GREEN row, and preserves explicit RESEARCH/BOUNDARY rows.

- [ ] **Step 1: RED mutation manifest and invalid-kill rejection**

- [ ] **Step 2: Add mutants one by one and require target-specific kills**

If a mutant survives, strengthen the oracle or retarget a weak mutant; never count syntax/import/setup failure as a kill.

- [ ] **Step 3: RED coverage audit**

- [ ] **Step 4: Reconcile coverage ledger conservatively**

- [ ] **Step 5: Add CI gates**

Run Wave 9 conformance/coverage on 3.11/3.12/3.13; run subprocess mutation gate on 3.11 only while unit mutation semantics remain cross-version tested.

- [ ] **Step 6: Full exact-head GREEN and commit**

---

### Task 8: Release `0.9.0a1`

**Files:**
- Modify: `pyproject.toml`
- Modify: `src/nolane_plan/__init__.py`
- Modify: `README.md`
- Modify: `CHANGELOG.md`
- Modify: `CONFORMANCE.md`
- Modify: `SECURITY.md`
- Modify: Wave 9 registry test to freeze exact registry digest.

- [ ] **Step 1: Verify pre-release implementation head GREEN 3/3**

- [ ] **Step 2: Freeze registry/conformance/coverage digests**

- [ ] **Step 3: Bump only to `0.9.0a1` and update bounded claims**

- [ ] **Step 4: Release-head CI GREEN 3/3**

- [ ] **Step 5: Open PR and verify synthetic merge CI GREEN 3/3**

- [ ] **Step 6: Check reviews/threads and base/head race**

- [ ] **Step 7: Non-forced fast-forward `main` when graph permits**

- [ ] **Step 8: Fresh final-main CI GREEN 3/3**

The release is complete only when the fresh final-main push run succeeds on all three Python versions and the exact `main` SHA still equals the tested release SHA.