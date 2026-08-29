# Wave 3 External Trust Anchor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close v0.15 host-grounded principal identity, inter-principal delivery, dispatch attestation and reconciliation-evidence seams without expanding Nolane Plan into an identity provider or messaging platform.

**Architecture:** Add focused immutable ledgers for identity, communication and execution evidence, then integrate them into `PlanKernel` through strong-path methods while retaining weak backwards-compatible paths for reversible examples. Every authority-sensitive object is bound to exact principal/adapter/transaction revisions and freshness generations, and all new correctness state is durable/replayable.

**Tech Stack:** Python 3.11+, stdlib dataclasses/enums, existing hash journal/snapshot/freshness architecture, `unittest`, GitHub Actions matrix 3.11/3.12/3.13.

**Spec:** `docs/superpowers/specs/2026-08-29-wave3-external-trust-anchor-design.md`

## Global Constraints

- Single serialized `PlanKernel` correctness writer remains normative.
- Nolane Plan does not authenticate accounts; it consumes canonical host/platform identity evidence.
- Model prose, role labels, process IDs and worker names cannot establish strong principal identity.
- `SENT`/queued information is not recipient-available until the planning-relevant observation/reveal condition is satisfied.
- Executor-sensitive dispatch requires current identity attestation matching the exact authorized acting principal.
- Reconciliation trust is represented by evidence; callers cannot create strong trust with a boolean.
- Unknown/opaque identity at a strong assurance boundary fails closed.
- All strong-path identity/delivery/reconciliation state must survive snapshot/replay.

---

### Task 1: Canonical Host Identity Ledger

**Files:**
- Create: `src/nolane_plan/identity.py`
- Test: `tests/test_wave3_identity.py`

**Interfaces:**
- Produces `PrincipalAttestation`, `PrincipalBindingRevision`, `PrincipalIdentityLedger`.
- `PrincipalIdentityLedger.accept(attestation) -> PrincipalBindingRevision` rejects blank canonical refs, assurance outside `[0,1]`, expired-at-acceptance attestations and source-subject collisions that map to incompatible canonical refs.
- `current(principal_ref, now, minimum_assurance) -> PrincipalBindingRevision` rejects absent, revoked, expired or low-assurance identity.
- `revoke(attestation_id, revoked_at)` advances the binding revision.

- [ ] Write RED tests proving narrated labels alone are not attestations, canonical source subjects are stable, source-subject collisions fail closed, and expiry/revocation remove current strong identity.
- [ ] Run `python -m unittest tests.test_wave3_identity -v`; expected RED import/module failures.
- [ ] Implement immutable dataclasses plus ledger validation and provenance digest.
- [ ] Run focused tests; expected GREEN.
- [ ] Commit `feat: add canonical principal identity ledger`.

### Task 2: Planning-Relevant Communication Ledger

**Files:**
- Create: `src/nolane_plan/communication.py`
- Test: `tests/test_wave3_communication.py`

**Interfaces:**
- Produces `CommunicationState`, `CommunicationReceipt`, `CommunicationLedger`.
- `sent(...)` creates `SENT`.
- `delivered(receipt_id, delivered_at, evidence_ref)` requires `SENT`.
- `observed(receipt_id, observed_at, evidence_ref)` requires `DELIVERED` and returns `OBSERVED`.
- `decision_usable(receipt_id, recipient_ref, decision_time)` returns true only for the exact recipient, `OBSERVED` at/before the boundary and within validity.

- [ ] Write RED tests for `SENT != known`, wrong recipient, late delivery/observation non-retroactivity, expiry and illegal state transitions.
- [ ] Run focused tests and confirm RED.
- [ ] Implement the state machine and immutable receipts.
- [ ] Run focused tests and confirm GREEN.
- [ ] Commit `feat: add principal communication evidence ledger`.

### Task 3: Dispatch and Reconciliation Evidence

**Files:**
- Modify: `src/nolane_plan/execution.py`
- Test: `tests/test_wave3_execution_evidence.py`

**Interfaces:**
- Add `DispatchAttestation` and `ReconciliationEvidence`.
- Add `verify_dispatch_attestation(...)` binding authorization, transaction, action, adapter id/revision, exact principal, current principal binding and minimum assurance.
- Replace the strong reconciliation path with `reconcile_with_evidence(transaction_id, evidence, minimum_assurance)`; evidence must bind exact transaction/action/authorization/principal/adapter context and normalized outcome.
- Keep legacy boolean reconciliation only as an explicitly weak compatibility helper that cannot satisfy strong kernel reconciliation.

- [ ] Write RED tests for wrong principal, wrong adapter revision, wrong transaction, low assurance and boolean-trust bypass.
- [ ] Run focused tests and confirm RED.
- [ ] Implement evidence dataclasses/verifiers and ledger strong path.
- [ ] Run focused tests and confirm GREEN.
- [ ] Commit `feat: bind dispatch and reconciliation to evidence`.

### Task 4: Kernel Strong Principal/Delivery/Dispatch Path

**Files:**
- Create: `src/nolane_plan/trust_runtime.py`
- Modify: `src/nolane_plan/__init__.py`
- Test: `tests/test_wave3_kernel_trust.py`

**Interfaces:**
- `install_trust_runtime()` augments `PlanKernel` with `identities`, `communications`, `dispatch_attestations`, `reconciliation_evidence` and strong methods without duplicating the correctness writer.
- `bind_principal(attestation, allowed_tags)` creates/updates the principal profile and bumps `principal-identity:<ref>` plus principal/plan freshness.
- `transfer_information(...)` records send/delivery/observation and only calls principal observation when an `OBSERVED` communication receipt is current.
- `authorize_strong(...)` requires a current acting-principal binding when action legality is principal-sensitive/executor-sensitive.
- `dispatch_strong(...)` records the existing durable dispatch transaction before adapter execution and verifies `DispatchAttestation` before treating the executor as the intended principal.
- `reconcile_strong(...)` accepts only `ReconciliationEvidence`.

- [ ] Write RED integration tests for admin-spoof rejection, identity change after authorization, cross-principal delivery leakage, late observation, wrong-principal dispatch and wrong-transaction reconciliation.
- [ ] Run focused tests and confirm RED.
- [ ] Implement extension and bootstrap import.
- [ ] Run all tests; existing Wave-1/2 behavior must remain GREEN.
- [ ] Commit `feat: integrate host-grounded trust into PlanKernel`.

### Task 5: Snapshot/Replay and Freshness

**Files:**
- Modify: `src/nolane_plan/kernel_recovery.py`
- Test: `tests/test_wave3_replay.py`

**Interfaces:**
- Snapshot serialization includes identity bindings/attestations, communication receipts, dispatch attestations and reconciliation evidence.
- Replay reducer understands corresponding events and refuses unknown trust mutations.
- Identity/delivery changes advance freshness domains so dependent capsule/policy artifacts stale at authority time.

- [ ] Write RED crash tests: restart preserves canonical principal provenance, `SENT` remains non-usable, observed delivery remains recipient-bound, revoked identity stays revoked, and reconciliation evidence remains transaction-bound.
- [ ] Run focused tests and confirm RED.
- [ ] Extend serializer/restorer/reducer and freshness bumps.
- [ ] Run full regression + compile + base/Wave-2 conformance.
- [ ] Commit `feat: make Wave 3 trust state crash safe`.

### Task 6: Wave-3 Adversarial Conformance and Release Gate

**Files:**
- Create: `src/nolane_plan/wave3_conformance.py`
- Create: `tests/test_wave3_conformance.py`
- Modify: `.github/workflows/ci.yml`
- Modify: `README.md`
- Modify: `SECURITY.md`
- Modify: `CHANGELOG.md`
- Modify: `pyproject.toml`
- Modify: `src/nolane_plan/__init__.py`

**Interfaces:**
- `run_wave3_conformance() -> dict` returns deterministic case records and aggregate pass/fail.
- Required cases: narrated principal spoof, source-subject collision, expired identity, revoked identity, authorization→dispatch principal swap, adapter revision mismatch, wrong-transaction reconciliation, SENT-not-known, late observation non-retroactivity, recipient swap, restart provenance, identity/delivery freshness invalidation.
- CI invokes Wave-3 conformance on Python 3.11/3.12/3.13 after unit tests and Wave-2 conformance.

- [ ] Write RED conformance test before implementation module exists.
- [ ] Implement deterministic adversarial suite using real runtime APIs.
- [ ] Run full test suite, compile, base `108 -> 0`, Wave-2 `10/10`, Wave-3 all cases, demo and crash/reopen fixture.
- [ ] Create four mutation branches: bypass canonical identity, bypass dispatch attestation, treat SENT as OBSERVED, accept boolean trusted reconciliation. Confirm each branch fails focused/conformance tests.
- [ ] Bump package to `0.3.0a1`, document claim boundaries and security semantics.
- [ ] Run fresh feature-branch CI matrix; only publish after 3/3 GREEN.
- [ ] Fast-forward `main` without force after rechecking it has not changed, then require fresh `main` CI 3/3 GREEN.

## Self-review

- Spec coverage: closes v0.15 principal identity source/provenance, delivery/reveal grounding, dispatch-time principal attestation, principal-change TOCTOU, executing-principal reconciliation attribution and freshness/replay implications. Does not claim to close ProofInputEnvelope/support/policy-seal/future-lineage surfaces; those are explicitly scheduled in `docs/SPEC-COVERAGE.md` Waves 4-8.
- Placeholder scan: no TBD/TODO/"implement later" instructions are used as plan steps.
- Type consistency: strong-path evidence objects are defined before kernel integration and reuse exact authorization/transaction/adapter/principal identifiers already present in Wave 2.
