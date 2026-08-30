# Wave 6 Schedulability & Liveness Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the bounded v0.6 reference-runtime schedulability/liveness/future-temporal-resource semantics without adding a second correctness writer or a general scheduler.

**Architecture:** Add immutable canonical Wave-6 certificate modules around the existing Wave-5 policy runtime, then integrate them as additional fail-closed prerequisites under `PlanKernel._writer_lock`. Persistence remains layered: snapshot v6 wraps v5 policy recovery and replays only known Wave-6 correctness events.

**Tech Stack:** Python 3.11–3.13, stdlib `dataclasses`, `Enum`, `unittest`, existing `nolane_plan.hashing.digest`, GitHub Actions matrix.

**Spec:** `docs/superpowers/specs/2026-08-30-wave6-schedulability-liveness-closure-design.md`

## Global Constraints

- Retain exactly one serialized correctness writer: `PlanKernel._writer_lock`.
- No new object may mint dispatch authority; Wave-6 authority gates must delegate through `authorize_sealed_policy()`.
- RS1 never supports a strong joint policy timing guarantee when concurrent jobs are possible.
- Unsupported/UNKNOWN solver, correlation, capacity, freshness or liveness semantics fail closed; never optimistic-default to success.
- Scenario stress is not exact proof.
- Handoff deadlines cannot advance solely from a new planning object.
- `PolicyEdgeCertificate` does not suppress activation-time freshness checks.
- Totality over modeled support never implies open-world completeness without explicit closed-domain proof.
- Robust OR/K-of-N uplift requires failure-set-relative independence plus co-activation feasibility.
- Every new persistent object must have canonical codec, internal digest verification, replay and v5→v6 migration semantics before release.
- Wave 6 must not become a generic real-time scheduler/orchestration product.
- Release target: `0.6.0a1`.

---

## File map

- Create `src/nolane_plan/control_plane.py`: control resource, demand, job and reservation contracts.
- Create `src/nolane_plan/schedulability.py`: RS0–RS4 certificate and bounded joint evaluator.
- Modify `src/nolane_plan/budget.py`: protected certified reaction capacity.
- Create `src/nolane_plan/handoff_liveness.py`: progress rank/policy/liveness certificate.
- Create `src/nolane_plan/handoff_stability.py`: activation-time stability/refresh contract.
- Create `src/nolane_plan/policy_coverage.py`: modeled-totality vs adequacy/residual assessment.
- Create `src/nolane_plan/option_independence.py`: failure-set-relative route independence and robust readiness result.
- Modify `src/nolane_plan/policy_readiness.py`: robust preparedness composition consumes independence certificate.
- Create `src/nolane_plan/future_resurrection.py`: revisioned dormant branch and resurrection assessment.
- Create `src/nolane_plan/schedulability_runtime.py`: kernel registries/rechecks under writer lock.
- Create `src/nolane_plan/schedulability_codec.py`: canonical JSON-compatible representation for Wave-6 persistent objects.
- Create `src/nolane_plan/schedulability_recovery.py`: snapshot v6 / migration / suffix replay.
- Modify `src/nolane_plan/__init__.py`: install Wave-6 runtime and recovery in order.
- Create `src/nolane_plan/wave6_conformance.py`: deterministic adversarial oracle.
- Create `scripts/wave6_mutation_gate.py`: constitutional mutation gate.
- Modify `.github/workflows/ci.yml`: require Wave-6 conformance/mutation gates.
- Tests are split by task under `tests/test_wave6_*.py`.

---

### Task 1: Canonical control-plane resource and reaction-job contracts

**Files:**
- Create: `src/nolane_plan/control_plane.py`
- Test: `tests/test_wave6_control_plane.py`

**Interfaces:**
- Produces: `ControlPlaneResourceRevision`, `ReactionResourceDemand`, `ReactionJobContract`, `ControlPlaneReservation`, `ControlPlaneResourceError`.
- Consumed by: Tasks 2, 3, 8, 9.

- [ ] **Step 1: Write failing contract tests**

Tests must assert:

```python
resource = ControlPlaneResourceRevision.create(
    resource_id="verifier",
    revision_id="verifier-r1",
    resource_kind="CONCURRENCY",
    capacity_units=2.0,
    concurrency_limit=2,
    service_rate_per_second=2.0,
    rate_window_seconds=1.0,
    availability_interval=(0.0, 100.0),
    priority_policy_ref="priority-v1",
    reservation_policy_ref="reservation-v1",
    regime_ref="verifier-regime-1",
    assurance_profile="bounded-worst-case",
    opaque_dimensions=(),
    validity_regime="mission-1",
)
assert resource.concurrency_limit == 2
```

Also cover invalid negative capacity, zero/negative rate window, inverted availability, unsupported resource kind, opaque strong resource without conservative bound, demand with negative service, job deadline before release, empty demand for a strong job, deterministic digest ordering, and reservation interval/service validation.

- [ ] **Step 2: Run RED**

Run:

```bash
python -m unittest tests.test_wave6_control_plane -v
```

Expected: import failure because `nolane_plan.control_plane` does not exist; all pre-existing tests remain green in full discovery.

- [ ] **Step 3: Implement minimal canonical contracts**

Use frozen/slotted dataclasses, explicit enum/string validation, sorted canonical tuples, and `digest(body)`. No scheduler logic belongs here.

- [ ] **Step 4: Run focused GREEN and full regression**

```bash
python -m unittest tests.test_wave6_control_plane -v
python -m unittest discover -s tests -v
python -m compileall -q src
```

- [ ] **Step 5: Commit**

```text
feat: add Wave 6 control-plane contracts
```

---

### Task 2: Bounded joint reaction schedulability

**Files:**
- Create: `src/nolane_plan/schedulability.py`
- Test: `tests/test_wave6_schedulability.py`

**Interfaces:**
- Consumes: Task-1 contracts.
- Produces: `ReactionSchedulabilityLevel`, `SchedulabilityAnalysisMode`, `OverloadWitness`, `ReactionSchedulabilityCertificate`, `ReactionSchedulabilityEvaluator`.

- [ ] **Step 1: Write RED tests for I-65/I-66**

Required scenarios:

```python
# Each job individually fits a one-unit verifier, but both are co-reachable
# in the same [0, 1] window and jointly require two units.
certificate = ReactionSchedulabilityEvaluator.evaluate(...)
assert certificate.level == ReactionSchedulabilityLevel.RS1_EACH_JOB_INDIVIDUALLY_FEASIBLE
assert certificate.overload_witnesses[0].resource_ref == "verifier"
```

Tests also require:
- mutually exclusive jobs are not summed;
- unknown coexistence never becomes exclusivity;
- rate-limit and serial/kernel-writer resources can bind feasibility;
- `SCENARIO_STRESS` cannot produce RS4/strong exact proof;
- unsupported model yields RS0/UNKNOWN debt;
- resource revision or job digest drift invalidates reuse;
- explicit closed-subdomain proof is required for RS4.

- [ ] **Step 2: Run RED**

```bash
python -m unittest tests.test_wave6_schedulability -v
```

Expected: missing module/API only.

- [ ] **Step 3: Implement finite-window conservative evaluator**

Use endpoints from release/deadline windows. For each resource and relevant window, compute co-reachable jobs and conservative required service/concurrency versus available service. Emit exact overload witnesses; never solve arbitrary scheduling problems.

- [ ] **Step 4: Run GREEN + regression**

```bash
python -m unittest tests.test_wave6_schedulability -v
python -m unittest discover -s tests -v
python -m compileall -q src
```

- [ ] **Step 5: Commit**

```text
feat: add joint reaction schedulability certificates
```

---

### Task 3: Protected reaction reservations and planning budget

**Files:**
- Modify: `src/nolane_plan/budget.py`
- Test: `tests/test_wave6_resource_governor.py`

**Interfaces:**
- Consumes: `ControlPlaneReservation`.
- Produces: `ProtectedBudgetDemand`, expanded `PlanningBudgetGovernor.allocate(..., protected_demands=())` while preserving legacy calls.

- [ ] **Step 1: Write RED tests**

Cover:
- background work cannot consume a deadline-critical protected slice;
- mandatory + protected demand above budget raises `InvariantViolation` rather than silently pruning;
- unused protected capacity may not be assumed available before its release policy permits it;
- legacy `allocate(units)` behavior remains unchanged;
- reservation starvation of a separately marked higher-value required route is explicit infeasibility/debt, not hidden success.

- [ ] **Step 2: Run RED focused test**

- [ ] **Step 3: Add backward-compatible protected-capacity path**

Do not turn the governor into a task scheduler. It only accounts for planning budget reserved by already-certified reaction-critical work.

- [ ] **Step 4: Run full regression**

- [ ] **Step 5: Commit**

```text
feat: protect certified reaction capacity
```

---

### Task 4: Progress-bounded SAFE_HANDOFF liveness

**Files:**
- Create: `src/nolane_plan/handoff_liveness.py`
- Test: `tests/test_wave6_handoff_liveness.py`

**Interfaces:**
- Produces: `ContinuationProgressRank`, `HandoffProgressPolicy`, `HandoffProgressStatus`, `HandoffLivenessCertificate`, `HandoffLivenessEvaluator`.

- [ ] **Step 1: Write RED tests for HL01–HL12 bounded semantics**

At minimum:
- eight semantically identical handoffs with positive local slack exhaust bounded stutter and become `NO_PROGRESS`;
- debt reduction is `STRICT_PROGRESS`;
- executable horizon advance is progress only when absolute horizon does not shrink/rebase;
- equivalent debt renamed under a new ID is not progress when equivalence lineage is supplied;
- `RECOVERY_STUTTER` is distinct from ordinary stutter;
- a new plan revision cannot extend `absolute_latest_safe_refinement_time` without grounded temporal authority;
- recursive feasibility false/unknown blocks `SAFE_HANDOFF`;
- handoff budget and total deferral are enforced;
- information needed after the deadline yields UNKNOWN/NO_PROGRESS rather than feasible handoff.

- [ ] **Step 2: Run RED**

- [ ] **Step 3: Implement canonical rank/policy/evaluator**

The progress relation is bounded and policy-declared; no universal distance-to-goal scalar is introduced.

- [ ] **Step 4: Run GREEN + full regression**

- [ ] **Step 5: Commit**

```text
feat: add bounded handoff liveness certificates
```

---

### Task 5: Activation-time edge stability

**Files:**
- Create: `src/nolane_plan/handoff_stability.py`
- Test: `tests/test_wave6_handoff_stability.py`

**Interfaces:**
- Produces: `HandoffStabilityContract`, `EdgeActivationAssessment`, `EdgeActivationStatus`, `HandoffStabilityEvaluator`.

- [ ] **Step 1: Write RED tests for EF semantics**

Cover external generation drift, expired reservation, permission/capability revision drift, open asynchronous side effect, protected stable predicate, explicitly refreshed predicate, opacity debt, and fallback-on-instability.

The core assertion is:

```python
assert HandoffStabilityEvaluator.assess(
    contract=contract,
    current_generations={"inventory": 8},
    refreshed_predicates=(),
    now=20,
).status == EdgeActivationStatus.REFRESH_REQUIRED
```

when the edge was certified at generation 7.

- [ ] **Step 2: Run RED**
- [ ] **Step 3: Implement activation evaluator**
- [ ] **Step 4: Run GREEN + regression**
- [ ] **Step 5: Commit**

```text
feat: enforce activation-time edge freshness
```

---

### Task 6: Two-axis totality/adequacy and robust option independence

**Files:**
- Create: `src/nolane_plan/policy_coverage.py`
- Create: `src/nolane_plan/option_independence.py`
- Modify: `src/nolane_plan/policy_readiness.py`
- Test: `tests/test_wave6_policy_adequacy.py`
- Test: `tests/test_wave6_option_independence.py`

**Interfaces:**
- Produces: `ModelAdequacyLevel`, `ResidualOpenWorldStatus`, `ExecutablePolicyCoverageAssessment`, `OptionIndependenceStatus`, `OptionIndependenceCertificate`, `RobustPreparednessAssessment`.

- [ ] **Step 1: RED totality/adequacy tests**

A Wave-5 totality certificate can remain TOTAL while model adequacy is DEGRADED and residual debt ACTIVE. The combined assessment must remain qualified and `open_world_complete` false unless a closed-domain proof ref exists.

- [ ] **Step 2: RED independence tests**

Two P4 routes sharing `credential:prod` under failure set `credential-loss` must report nominal P4 but robust-independent readiness at the conservative non-uplift floor. Distinct routes with independently verified dependencies and coactivation can receive robust uplift.

- [ ] **Step 3: Implement both canonical modules and readiness integration**

Legacy `PreparednessProfile.aggregate()` stays available. Add a new strong aggregation API that consumes `OptionIndependenceCertificate`; do not silently reinterpret existing callers.

- [ ] **Step 4: Run focused + full GREEN**

- [ ] **Step 5: Commit**

```text
feat: separate model adequacy and robust option independence
```

---

### Task 7: Dormant branch resurrection closure

**Files:**
- Create: `src/nolane_plan/future_resurrection.py`
- Modify: `src/nolane_plan/pruning.py` only for a backward-compatible strong adapter method if needed.
- Test: `tests/test_wave6_future_resurrection.py`

**Interfaces:**
- Produces: `DormantBranchRevision`, `ResurrectionStatus`, `BranchResurrectionAssessment`, `BranchResurrectionEvaluator`.

- [ ] **Step 1: Write RED tests**

A dormant branch cannot resurrect when mission revision, evidence/assumptions, transition model, temporal feasibility, resource/capability/authority revision or risk classification is stale. Current revalidation of every bound dimension permits resurrection. Catastrophic/sole-route/unique-hedge/information-rich branches remain protected from probability-only pruning.

- [ ] **Step 2: Run RED**
- [ ] **Step 3: Implement revisioned dormant/resurrection semantics**
- [ ] **Step 4: Run GREEN + regression**
- [ ] **Step 5: Commit**

```text
feat: harden dormant branch resurrection
```

---

### Task 8: Kernel authority integration under the single writer

**Files:**
- Create: `src/nolane_plan/schedulability_runtime.py`
- Modify: `src/nolane_plan/__init__.py`
- Test: `tests/test_wave6_kernel_authority.py`

**Interfaces:**
- Consumes: Tasks 1–7 plus existing `authorize_sealed_policy()`.
- Produces kernel methods for registration/evaluation and `authorize_schedulable_policy(...)`.

- [ ] **Step 1: Write RED integration tests**

Required assertions:
- runtime uses exact `PlanKernel._writer_lock`;
- valid path preserves identity + proof + policy authorization bindings and adds Wave-6 certificate bindings;
- RS1 cannot authorize when concurrent reactions are possible;
- resource revision drift blocks authority before authorization count increases;
- exhausted handoff liveness blocks `SAFE_HANDOFF` authority;
- stale edge activation blocks child authorization until refreshed;
- totality with degraded/open residual cannot be laundered into closed-world strong claim;
- nominal-only independence blocks a robust redundancy claim;
- no Wave-6 object has a dispatch method or independent authorization constructor.

- [ ] **Step 2: Run RED**
- [ ] **Step 3: Implement registries/rechecks and delegate to `authorize_sealed_policy()`**
- [ ] **Step 4: Run GREEN + regression**
- [ ] **Step 5: Commit**

```text
feat: bind Wave 6 closure into kernel authority
```

---

### Task 9: Snapshot v6, canonical codecs and fail-closed replay

**Files:**
- Create: `src/nolane_plan/schedulability_codec.py`
- Create: `src/nolane_plan/schedulability_recovery.py`
- Modify: `src/nolane_plan/__init__.py`
- Test: `tests/test_wave6_replay.py`

**Interfaces:**
- Wraps existing v5 policy recovery.
- Produces snapshot schema `nolane-plan-runtime-snapshot-v6`.

- [ ] **Step 1: Write RED recovery tests**

Cover:
- exact v6 round trip of all Wave-6 registries and digests;
- v5 snapshot opens with empty Wave-6 state, never invented certificates;
- resource/job/certificate drift state does not resurrect as current after restart;
- stale handoff and edge stability stay stale;
- post-snapshot Wave-6 registration/invalidation suffix events replay exactly;
- tampered internal digest fails closed even if outer snapshot digest is recomputed;
- unknown correctness-significant Wave-6 event fails closed.

- [ ] **Step 2: Run RED**
- [ ] **Step 3: Implement codec/recovery wrapper**

Restore via canonical constructors and compare canonical digest. Replay mutates internal registries directly without writing duplicate journal events.

- [ ] **Step 4: Run GREEN + full regression**
- [ ] **Step 5: Commit**

```text
feat: make Wave 6 state replay complete
```

---

### Task 10: Wave-6 adversarial oracle and constitutional mutation gate

**Files:**
- Create: `src/nolane_plan/wave6_conformance.py`
- Create: `tests/test_wave6_conformance.py`
- Create: `scripts/wave6_mutation_gate.py`
- Modify: `.github/workflows/ci.yml`

**Interfaces:**
- Produces deterministic release gates.

- [ ] **Step 1: RED conformance-module test**

Require unique case names and all cases passed. The first RED should fail only because `wave6_conformance` does not exist.

- [ ] **Step 2: Implement deterministic oracle**

Minimum cases include all five spec discriminators plus bounded cases for CP01–12/HL01–12/EF/OI/adequacy seams representable by the runtime. Target at least 30 non-duplicate adversarial cases.

- [ ] **Step 3: Add mutation runner**

Minimum mutations:

```text
rs1_joint_guarantee_bypass
coexistence_bypass
resource_regime_freshness_bypass
protected_capacity_bypass
stutter_budget_bypass
deadline_self_extension_bypass
equivalent_debt_progress_bypass
edge_activation_refresh_bypass
totality_open_world_laundering
common_mode_independence_bypass
replay_internal_digest_bypass
stale_wave6_restart_resurrection
```

Each mutant must be killed by a focused existing test; mutation-runner success requires all killed.

- [ ] **Step 4: Wire CI and run full 3-version matrix**

Add:

```bash
python -m nolane_plan.wave6_conformance
python scripts/wave6_mutation_gate.py
```

- [ ] **Step 5: Commit**

```text
feat: enforce Wave 6 conformance gates
```

---

### Task 11: Release `0.6.0a1` and integrate exact verified main

**Files:**
- Modify: `pyproject.toml`
- Modify: `src/nolane_plan/__init__.py`
- Modify: `CHANGELOG.md`
- Modify: `README.md`
- Modify: `CONFORMANCE.md`
- Modify: `docs/SPEC-COVERAGE.md`

**Interfaces:**
- Produces the Wave-6 release candidate and evidence trail.

- [ ] **Step 1: Audit coverage ledger line by line**

Promote only Wave-6 rows actually demonstrated by Tasks 1–10. Keep Wave-7 lineage/migration exhaustion and Wave-8 property/chaos/empirical boundaries non-GREEN.

- [ ] **Step 2: Atomically align release-facing metadata to `0.6.0a1`**

- [ ] **Step 3: Fresh release-head verification**

Require Python 3.11/3.12/3.13 success, full unit suite, compile, principal oracle, Wave2–6 conformance/mutations and demo.

- [ ] **Step 4: Diff/ancestry audit and PR**

Verify branch is ahead of current `main`, behind 0 and contains no unrelated changes. Open PR and require a separate PR-triggered 3-version GREEN run.

- [ ] **Step 5: Integrate with race guard**

Re-read `main`; if unchanged, fast-forward with `force=false` to the exact verified release SHA. Do not force-update.

- [ ] **Step 6: Fresh exact-main verification**

Require new `main` push CI GREEN on Python 3.11/3.12/3.13. Capture exact test/oracle/mutation counts from logs.

- [ ] **Step 7: Nolane World scoped verification**

Run core invariants and record exact-main release evidence. Claim only `GREEN_FOR_WAVE6_BOUNDED_REFERENCE_RUNTIME_SCOPE` if the repo gates pass. Do not claim full World convergence unless its own convergence court passes.

- [ ] **Step 8: Final checkpoint**

Wave 6 may be called closed only after exact-main evidence exists. Then move to Wave 7 durable lineage/migration closure.

---

## Plan self-review

- Spec coverage: Tasks 1–10 cover I-65–I-72 and all 12 v0.6 acceptance additions; Task 7 also closes the Wave-6 dormant/resurrection seam in the coverage ledger; Task 3 closes protected reaction budget semantics.
- Placeholder scan: no TBD/TODO/“similar to” placeholders; each task has concrete interfaces and test obligations.
- Type consistency: kernel/recovery tasks consume the exact Task-1–7 object names defined above; release schema is consistently v6; strong authority consistently delegates through `authorize_sealed_policy()`.
- Scope check: scheduling remains bounded planning-certificate analysis and does not expose a general scheduler/executor.