# Wave 5 Executable Policy Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a model-free sealed contingent-policy kernel whose strong policy claims are principal-information-feasible, recall-sufficient, outcome-total, edge-stitchable, reaction-controllable, proof-context-consistent and horizon-closed before they can gate consequential authorization.

**Architecture:** Add focused immutable policy/certificate modules and one `policy_runtime` extension over the existing single-writer `PlanKernel`. Snapshot v5 wraps Wave-4 recovery. Policy/selection/seal objects never bypass the Action Binder; they only provide current proof-bearing prerequisites for existing strong/proof-carrying authorization.

**Tech Stack:** Python 3.11–3.13, dataclasses/enums, existing hash journal/snapshot store, `unittest`, deterministic bounded oracle worlds, no new third-party runtime dependency.

**Spec:** `docs/superpowers/specs/2026-08-30-wave5-executable-policy-closure-design.md`

## Global Constraints

- One serialized correctness writer remains the normative root.
- Runtime-global information never substitutes for principal-available information.
- `DecisionEpoch`, `PolicyNodeRevision`, `SelectionRecord`, certificates and seals have no independent dispatch authority.
- `SelectionRecord` status is only ADVISORY/STALE/SUPERSEDED.
- Solver UNKNOWN/unsupported results never become proofs.
- Strong policy claims are exact-scope and exact-revision bound.
- No self-promotion from model prose to strong assurance.
- Snapshot/replay must fail closed and must not append journal entries during replay.
- Wave 6 retains joint control-plane schedulability, repeated handoff liveness and activation-time edge stability.

---

### Task 1: Principal-Scoped Information Structure and Non-Anticipativity

**Files:**
- Create: `src/nolane_plan/policy_information.py`
- Test: `tests/test_wave5_policy_information.py`

**Interfaces:**
- Produces `InformationPartitionRevision`, `DecisionEpoch`, `RevealEvent`, `ObservationFrontierRevision`, `NonAnticipativityAssessment`, `NonAnticipativityValidator`.
- Consumes immutable principal/access/canonical version identifiers only; kernel integration is deferred.

- [ ] Write failing tests proving: principal scope is part of partition identity; same information class cannot choose distinct action semantics before reveal; a grounded reveal permits a split only at/after availability; global-only observation cannot refine another principal; ambiguous/late reveal yields debt/failure; epoch has no authorization state.
- [ ] Run `python -m unittest tests.test_wave5_policy_information -v` and confirm failures are only missing Wave-5 semantics.
- [ ] Implement immutable canonical digests, partition/class validation, reveal availability checks and symbolic class-level non-anticipativity evaluation.
- [ ] Re-run focused tests, then full `python -m unittest discover -s tests -q`.
- [ ] Commit `feat: add principal-scoped policy information semantics`.

### Task 2: Contingent Policy IR and Coherence Certificate

**Files:**
- Create: `src/nolane_plan/policy_ir.py`
- Test: `tests/test_wave5_policy_ir.py`

**Interfaces:**
- Consumes Task-1 epoch/partition/frontier IDs and existing action/shared-commitment refs.
- Produces `PolicyNodeRevision`, `PolicySuccessorRoute`, `ContingentPolicyCertificate`, `PolicyCoherenceAssessment`.

- [ ] Write RED tests for exact revision binding, successor mapping, execution-principal requirements, unsealed-node non-authority, branchwise-vs-policy viability, shared-resource incompatibility and non-anticipativity certificate dependency.
- [ ] Verify RED.
- [ ] Implement immutable node schema and policy-level coherence checker. No action dispatch or grant mutation is allowed in this module.
- [ ] Verify focused + full suite.
- [ ] Commit `feat: add contingent policy IR and coherence`.

### Task 3: Frozen Selection Transactions

**Files:**
- Create: `src/nolane_plan/selection.py`
- Test: `tests/test_wave5_selection.py`

**Interfaces:**
- Produces `SelectionTransaction`, `CandidateAdmissibility`, `SelectionRecord`, `SelectionStatus`, deterministic selection evaluator.
- Later Task 8 binds the record to kernel authority; this task cannot issue authorization.

- [ ] Write RED tests for frozen snapshot/candidate digest, hard-admissibility-before-ranking, no rejected-candidate resurrection, deterministic tie rule, principal/information binding, stale dependency status and structural impossibility of `AUTHORIZED`.
- [ ] Verify RED.
- [ ] Implement selection transaction + hard-stage monotonic evaluator + deterministic stable-ID tie fallback.
- [ ] Verify focused + full suite.
- [ ] Commit `feat: add advisory frozen selection records`.

### Task 4: Decision Sufficiency, PlanSeal and N-Way Composition

**Files:**
- Create: `src/nolane_plan/seals.py`
- Test: `tests/test_wave5_seals.py`

**Interfaces:**
- Produces `ArtifactAssurance`, `DecisionSufficiencyCertificate`, `ProofContextComponent`, `GlobalCompositionResult`, `CompositionStatus`, `PlanSeal`, `SealStatus`, `SealCompiler`.
- Consumes exact proof/certificate revision digests from Waves 2–4 and Tasks 1–3.

- [ ] Write RED tests for no self-promotion, exact action-closure sealing, unrelated far-future draft not blocking local seal, dependent mutation invalidation, accepted debt remaining explicit, pairwise-compatible/global-conflict fixture, conservative guarantee/assurance meet and `COMPOSITION_UNKNOWN` fail-closed behavior.
- [ ] Verify RED.
- [ ] Implement bounded N-way composition with explicit simple constraint predicates for oracle worlds; unsupported theory returns typed UNKNOWN/UNSUPPORTED rather than guessing.
- [ ] Implement seal compiler requiring declared compiler-pass manifest and invariant digest.
- [ ] Verify focused + full suite.
- [ ] Commit `feat: add decision sufficiency and PlanSeal compiler`.

### Task 5: Recall, Totality and Policy-Edge Certificates

**Files:**
- Create: `src/nolane_plan/policy_certificates.py`
- Test: `tests/test_wave5_policy_certificates.py`

**Interfaces:**
- Produces `DecisionRecallCertificate`, `RecallLevel`, `MissingSuccessorCounterexample`, `PolicyTotalityCertificate`, `TotalityMode`, `PolicyEdgeCertificate`, `PolicyStitchCounterexample`.

- [ ] Write RED tests reproducing O11/O12/O18/O21/O22/O25: same current signal but different downstream semantics fails recall; supported residual/TIMEOUT without handler fails totality; legitimate residual handler closes only declared residual support; generic continue-primary catch-all rejected; parent post-support violating child entry yields stitch witness; UNKNOWN solver result does not pass.
- [ ] Verify RED.
- [ ] Implement bounded symbolic-set/reference-world checkers with explicit counterexample objects and revision-bound certificate digests.
- [ ] Verify focused + full suite.
- [ ] Commit `feat: add recall totality and edge certificates`.

### Task 6: Reaction, Preparedness, Information Capability and Continuation

**Files:**
- Create: `src/nolane_plan/policy_readiness.py`
- Test: `tests/test_wave5_policy_readiness.py`

**Interfaces:**
- Produces `DecisionReactionEnvelope`, `ReactionControllabilityClass`, `PreparednessProfile`, structure-aware preparedness aggregation, `InformationCapabilityRevision`, `ContinuationContract`, `TerminalSemantics`.

- [ ] Write RED tests for full reveal-to-dispatch latency, IA1-vs-IA2 distinction, NOT_APPLICABLE stage handling, AND/OR/K-of-N/contingency preparedness, non-monotonic downgrade, self-induced blindness, explicit terminal semantics, deferred-continuation horizon cap and SAFE_HANDOFF lead-time/fallback requirements.
- [ ] Verify RED.
- [ ] Implement interval/bounded reaction arithmetic and multi-axis preparedness without pretending Wave-6 joint schedulability is solved.
- [ ] Implement information-capability/continuation contracts and validation.
- [ ] Verify focused + full suite.
- [ ] Commit `feat: add policy reaction readiness and continuation semantics`.

### Task 7: Bounded Policy Executability Assessment

**Files:**
- Create: `src/nolane_plan/policy_executability.py`
- Test: `tests/test_wave5_policy_executability.py`

**Interfaces:**
- Produces `ExecutabilityStatus`, `ExecutabilityClosureManifest`, `PolicyExecutabilityAssessment`, `PolicyExecutabilityEvaluator`.
- Consumes current outputs of Tasks 1–6 and existing route/authority/freshness status.

- [ ] Write RED tests that `EXEC_BOUNDED` is impossible with known recall debt, totality hole, stitch failure, insufficient reaction class, globally noncomposable context, deferred continuation beyond horizon, stale seal or mixed snapshot; accepted debt gets a qualified status only with explicit acceptance.
- [ ] Verify RED.
- [ ] Implement exact-scope hard closure manifest and fail-closed evaluator. No scoring/confidence input can promote status.
- [ ] Verify focused + full suite.
- [ ] Commit `feat: add bounded policy executability assessment`.

### Task 8: PlanKernel Sealed Policy Authority Integration

**Files:**
- Create: `src/nolane_plan/policy_runtime.py`
- Modify: `src/nolane_plan/__init__.py`
- Test: `tests/test_wave5_kernel_policy_authority.py`

**Interfaces:**
- Adds kernel registration/evaluation methods for Tasks 1–7 and `authorize_sealed_policy(...)`.
- `authorize_sealed_policy` ultimately delegates to existing `authorize_proof_carrying`/`authorize_strong`; it never constructs dispatch authority independently.

- [ ] Write RED integration tests for exact `_writer_lock` sharing, decision-principal partition compatibility, stale reveal/access/epoch rejection, advisory selection binding, valid sufficiency + seal + executability prerequisites, unsealed consequential-action rejection and proof/identity continuity through the existing binder.
- [ ] Verify RED.
- [ ] Implement kernel state registries and journal payloads with sufficient exact replay provenance.
- [ ] Implement one critical-section evaluation→authorization path.
- [ ] Verify focused + full suite and prior Wave 2–4 conformance.
- [ ] Commit `feat: integrate sealed policy authority into PlanKernel`.

### Task 9: Snapshot v5 and Policy Replay

**Files:**
- Create: `src/nolane_plan/policy_recovery.py`
- Modify: `src/nolane_plan/__init__.py`
- Test: `tests/test_wave5_replay.py`

**Interfaces:**
- Wraps Wave-4 `PlanKernel.open`/snapshot behavior; schema becomes `nolane-plan-runtime-snapshot-v5`.

- [ ] Write RED crash/replay tests for current sealed policy survival, stale seal remaining stale, post-snapshot reveal/partition/policy/certificate mutation replay, identical executability assessment after restart, authorization-policy binding preservation and internal digest tamper failure.
- [ ] Verify RED.
- [ ] Serialize/restore policy/certificate state with internal digests; replay `policy.*` suffix events using direct reducers.
- [ ] Reuse v4 restore for lower layers; never fork Wave 1–4 core restoration.
- [ ] Verify focused + full suite.
- [ ] Commit `feat: add Wave 5 policy snapshot and replay`.

### Task 10: Wave-5 Adversarial Oracle, Mutations and Release

**Files:**
- Create: `src/nolane_plan/wave5_conformance.py`
- Create: `scripts/wave5_mutation_gate.py`
- Create: `tests/test_wave5_conformance.py`
- Modify: `.github/workflows/ci.yml`
- Modify: `CHANGELOG.md`
- Modify: `docs/SPEC-COVERAGE.md`
- Modify: `pyproject.toml`
- Modify: `src/nolane_plan/__init__.py`

**Interfaces:**
- Release target `0.5.0a1`.

- [ ] Add RED conformance contract requiring at least 18 unique deterministic cases spanning non-anticipativity, recall, totality, stitchability, reaction timing, preparedness, global composition, information capability, continuation, selection/seal authority and replay.
- [ ] Implement oracle and require all cases to pass.
- [ ] Add at least 9 constitutional mutations: anticipatory split, SelectionRecord authority leak, self-seal promotion, pairwise-only composition, residual catch-all laundering, recall current-action-only shortcut, totality UNKNOWN→pass, reaction-stage omission, executability confidence promotion/replay-integrity bypass.
- [ ] Add Wave-5 oracle/mutation steps to Python 3.11/3.12/3.13 CI.
- [ ] Bump `0.5.0a1`; update changelog/coverage only for actually GREEN semantics.
- [ ] Run fresh exact release-head push CI; open PR; require PR CI; merge with expected-head SHA; require exact main CI.
- [ ] Only after exact main CI succeeds, mark Wave 5 GREEN for bounded reference-runtime scope and begin Wave 6.

## Self-review result

The plan covers the v0.4 policy objects and the v0.5 stronger executable-policy primitives through Section 160. It intentionally does not absorb v0.6 `ReactionSchedulabilityCertificate`, `HandoffLivenessCertificate`, `HandoffStabilityContract` or `OptionIndependenceCertificate`; those are explicitly the next closure wave. No task grants independent execution authority to policy/selection/certificate objects, and persistent policy state is not released before replay coverage exists.
