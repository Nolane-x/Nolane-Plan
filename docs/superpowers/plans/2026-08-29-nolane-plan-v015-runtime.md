# Nolane Plan v0.15 Full Reference Runtime Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an executable, broad v0.15 Nolane Plan reference runtime with principal-scoped multi-agent correctness, future-space planning, evidence/freshness, temporal/recovery semantics, durable replay, conformance labs and CLI.

**Architecture:** One serialized `PlanKernel` owns correctness-critical state. Domain modules expose immutable/value-oriented contracts; speculative compilation and verification are side-effect free. External/model proposals are non-authoritative until kernel checks promote them.

**Tech Stack:** Python 3.11+, standard library, `unittest`, JSON/JSONL persistence, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-08-29-nolane-plan-v015-runtime-design.md`

## Global Constraints

- Single serialized correctness writer remains canonical.
- Runtime-global information does not automatically become principal-available information.
- Decision Capsules bind recipient principal and principal information/access scope.
- ActionAuthorization resolves an exact acting principal and dispatch rechecks principal identity where material.
- Unknown/opaque/inconclusive states fail closed for consequential operations.
- Strategic Obligations are condition-centric, not worker-owned tasks.
- Residual/null-world state is first-class.
- No distributed consensus, identity provider, generic message bus, or task marketplace is introduced.
- Standard-library-first implementation; no mandatory third-party runtime dependencies.

---

### Task 1: Contract tests and core value types
**Files:** tests for principal, evidence, mission and typed status contracts; then `types.py`, `hashing.py`, `mission.py`, `principals.py`, `evidence.py`.
**Produces:** stable IDs/digests, typed outcomes, principal-scoped information availability, versioned mission/evidence.
- [ ] Write failing tests for global-vs-principal information, access, delivery timing, mission versions and evidence lineage.
- [ ] Run tests and confirm feature-missing failures.
- [ ] Implement minimal value objects and ledgers.
- [ ] Run tests green and commit.

### Task 2: Obligations and strategic future space
**Files:** tests for obligations/future; then `obligations.py`, `future.py`, `compiler.py`.
**Produces:** condition-centric obligations, NULL_WORLD, factorized/lazy future compilation, strategic transitions and merge certificates.
- [ ] Write failing tests for obligation persistence, residual-world presence, expansion and unsafe merge rejection.
- [ ] Run RED.
- [ ] Implement minimal semantics.
- [ ] Run GREEN and commit.

### Task 3: Decision Capsules and principal-bound actions
**Files:** tests for capsules/actions; then `capsule.py`, `actions.py`.
**Produces:** principal-bound capsule compiler, scoped hydration, grants, authorizations, dispatch fences and receipts.
- [ ] Write failing swap/replay/TOCTOU tests.
- [ ] Run RED.
- [ ] Implement principal bindings and fail-closed status.
- [ ] Run GREEN and commit.

### Task 4: Temporal, selector and recovery planes
**Files:** tests for temporal/selector/recovery; then `temporal.py`, `selector.py`, `recovery.py`.
**Produces:** schedulability/handoff checks, hard-veto/Pareto assessment, model-class quarantine.
- [ ] Write failing deadline, tail-risk and ontology-break tests.
- [ ] Run RED.
- [ ] Implement minimal semantics.
- [ ] Run GREEN and commit.

### Task 5: Durable journal and replay
**Files:** persistence tests; then `persistence.py`.
**Produces:** hash-chained journal, atomic snapshots, chain verification and deterministic replay envelopes.
- [ ] Write tamper and round-trip tests.
- [ ] Run RED.
- [ ] Implement persistence.
- [ ] Run GREEN and commit.

### Task 6: PlanKernel integration
**Files:** kernel lifecycle tests; then `kernel.py`.
**Produces:** serialized writer, canonical state, invalidation, end-to-end action lifecycle and snapshot state.
- [ ] Write end-to-end tests from mission→future→capsule→authorization→dispatch→postcondition→commit.
- [ ] Run RED.
- [ ] Implement kernel orchestration.
- [ ] Run GREEN and commit.

### Task 7: v0.15 conformance laboratory
**Files:** conformance tests; then `conformance.py`, `failure_registry.py`.
**Produces:** PG01–PG40 registry and exact 108→0 principal collision oracle.
- [ ] Write exact-count failing oracle tests.
- [ ] Run RED.
- [ ] Implement bounded matrix and verifier.
- [ ] Run GREEN and commit.

### Task 8: CLI, docs, packaging and CI
**Files:** `cli.py`, `__main__.py`, package exports, README, pyproject, workflow, examples.
**Produces:** installable project and runnable demonstration.
- [ ] Write CLI smoke test.
- [ ] Run RED.
- [ ] Implement CLI/demo and packaging.
- [ ] Run all tests, conformance lab, compileall and demo.
- [ ] Commit release candidate.
