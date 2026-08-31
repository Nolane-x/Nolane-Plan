# Wave 8 Conformance Exhaustion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Falsify and close the remaining bounded v0.15 reference-runtime correctness surfaces with deterministic property/metamorphic/chaos/differential testing, explicit cancellation-fence semantics, bounded migration/relocation exhaustion, constitutional mutation testing, reference worlds, and final source-spec reconciliation.

**Architecture:** Build a test-owned Layered Falsification harness around the released `0.7.0a1` runtime. Harness code never creates authority; production code changes only where a focused RED counterexample proves a missing bounded semantic guard. Keep every generated failure seed-replayable and deterministically minimizable, then finish with one frozen Wave-8 runner and exact release-head/synthetic-merge/final-main verification.

**Tech Stack:** Python 3.11/3.12/3.13, standard library `unittest`, `random.Random`, existing Nolane Plan hash journal/snapshot/replay runtime, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-08-31-wave8-conformance-exhaustion-design.md`

## Global Constraints

- Start from Wave-7 release SHA `78e44da066bd362a2ee935c06ad5902bb0872238`; do not rewrite `main` history.
- One serialized correctness writer remains `PlanKernel`.
- Wave-8 harness code cannot mint authorization or mutate canonical runtime state out of band.
- Random exploration must be deterministic from explicit seeds; no wall-clock/network/scheduler randomness.
- Generated failures must print invariant ID, case ID, seed and deterministic minimized recipe.
- `BOUNDARY` and `RESEARCH` coverage rows cannot be promoted to correctness GREEN.
- Unknown/opaque/inconclusive semantics remain fail-closed or UNKNOWN; no optimistic promotion.
- Existing Wave 2–7 conformance and mutation gates remain mandatory.
- Release target is `0.8.0a1` only after exact-head, PR synthetic-merge and final-main CI all pass on the same release SHA.

---

### Task 1: Freeze the Wave-8 invariant registry

**Files:**
- Create: `src/nolane_plan/wave8_registry.py`
- Create: `tests/test_wave8_registry.py`

**Interfaces:**
- Produces: `Wave8Layer`, `Wave8Expectation`, `Wave8Invariant`, `Wave8Counterexample`, `WAVE8_INVARIANTS`, `wave8_registry_digest()`.
- Consumes later: all Wave-8 runners/generators/mutation/coverage checks.

- [ ] **Step 1: Write RED registry tests**

Create tests that assert the exact family counts and ID ranges from the design:

```python
EXPECTED = {
    "P": 10,
    "M": 12,
    "C": 10,
    "D": 10,
    "X": 12,
    "W": 6,
    "S": 8,
}


def test_wave8_registry_is_unique_and_frozen():
    ids = [row.invariant_id for row in WAVE8_INVARIANTS]
    assert len(ids) == len(set(ids)) == 68
    for prefix, count in EXPECTED.items():
        assert sum(value.startswith(prefix) for value in ids) == count


def test_every_invariant_has_real_coverage_ref_and_bounded_scope():
    for row in WAVE8_INVARIANTS:
        assert row.spec_surface_refs
        assert row.bounded_scope.strip()
        assert row.required_oracle.strip()


def test_registry_digest_is_order_stable():
    assert wave8_registry_digest(WAVE8_INVARIANTS) == wave8_registry_digest(tuple(reversed(WAVE8_INVARIANTS)))
```

- [ ] **Step 2: Run focused RED**

Run:

```bash
python -m unittest discover -s tests -p 'test_wave8_registry.py' -v
```

Expected: import failure for `nolane_plan.wave8_registry` and no unrelated failures.

- [ ] **Step 3: Implement immutable registry types and all 68 rows**

Use frozen/slots dataclasses. Canonicalize all set-like refs. Validate prefix/layer consistency (`P* -> PROPERTY`, etc.), non-empty scope/oracle and unique IDs. `Wave8Counterexample.create(...)` hashes the exact reproduction envelope.

- [ ] **Step 4: GREEN focused + full regression**

```bash
python -m unittest discover -s tests -p 'test_wave8_registry.py' -v
python -m unittest discover -s tests -v
python -m compileall -q src
```

Expected: registry tests GREEN and existing 408 tests remain GREEN.

- [ ] **Step 5: Commit**

```bash
git add src/nolane_plan/wave8_registry.py tests/test_wave8_registry.py
git commit -m "test: freeze Wave 8 invariant registry"
```

### Task 2: Deterministic generators and counterexample minimizer

**Files:**
- Create: `src/nolane_plan/wave8_generators.py`
- Create: `tests/test_wave8_generators.py`

**Interfaces:**
- Produces: `Wave8CaseRecipe`, `DeterministicCaseGenerator`, `generate_case(family, seed)`, `minimize_recipe(recipe, predicate)`.
- Consumes: existing production dataclasses only; does not write journal/canonical state directly.

- [ ] **Step 1: Write RED determinism/bounds tests**

Test that `generate_case("principal_information", 17)` is byte-for-byte canonical-equal on repeated runs; that all counts stay inside explicit limits (`principals <= 3`, `items <= 8`, `actions <= 6`, `resources <= 5`, `fault_points <= 8`); and that minimization removes recipe operations in stable lexical/index order while preserving the supplied failure predicate.

- [ ] **Step 2: Run RED**

```bash
python -m unittest discover -s tests -p 'test_wave8_generators.py' -v
```

Expected: missing generator module.

- [ ] **Step 3: Implement seed-owned generator families**

Use only `rng = random.Random(int(seed))`. Create small canonical recipe payloads for:

```text
principal_information
evidence_support
selector_candidates
policy_information
policy_bundle
resource_jobs
handoff
resurrection
relocation
lineage_regime
migration
replay_compaction
```

`minimize_recipe` must repeatedly try removing one operation at a time, restart from the beginning after every successful reduction, and stop at a fixed point.

- [ ] **Step 4: GREEN and determinism double-run**

```bash
python -m unittest discover -s tests -p 'test_wave8_generators.py' -v
python -m unittest discover -s tests -p 'test_wave8_generators.py' -v
```

Expected: identical outputs/failure ordering on both runs.

- [ ] **Step 5: Commit**

```bash
git add src/nolane_plan/wave8_generators.py tests/test_wave8_generators.py
git commit -m "test: add deterministic Wave 8 generators"
```

### Task 3: Property invariants P01–P10

**Files:**
- Create: `src/nolane_plan/wave8_properties.py`
- Create: `tests/test_wave8_properties.py`

**Interfaces:**
- Produces: `run_wave8_properties(seeds: range | tuple[int, ...]) -> tuple[Wave8Counterexample, ...]` with empty tuple meaning GREEN.
- Uses: `selector.pareto_front`, principal/proof/policy/schedulability/lineage/replay APIs and deterministic recipes.

- [ ] **Step 1: Write focused property tests for every P invariant**

Each test iterates seeds `0..31` and asserts no counterexample for:

```text
P01 canonical ordering determinism
P02 principal anti-escalation
P03 blocker monotonicity
P04 support removal cannot strengthen
P05 hard-veto monotonicity
P06 resource capacity/load monotonicity
P07 deadline/observation monotonicity
P08 authority revision freshness
P09 history non-erasure
P10 UNKNOWN/opaque/unlocated non-promotion
```

The test runner must report the first exact failing seed and minimized recipe.

- [ ] **Step 2: Run RED and classify failures**

```bash
python -m unittest discover -s tests -p 'test_wave8_properties.py' -v
```

Expected: initially RED because the property runner does not exist. After the runner shell exists, any semantic failures must be kept as RED evidence and fixed one invariant at a time; do not weaken the oracle.

- [ ] **Step 3: Implement property runner using public/current production semantics**

Do not add production code if an invariant already holds. For any actual semantic RED, add a dedicated focused unit test in the owner module’s Wave test before changing production code.

- [ ] **Step 4: GREEN P01–P10 + regression**

```bash
python -m unittest discover -s tests -p 'test_wave8_properties.py' -v
python -m unittest discover -s tests -v
```

- [ ] **Step 5: Commit**

```bash
git add src/nolane_plan/wave8_properties.py tests/test_wave8_properties.py
git commit -m "test: add Wave 8 property falsification"
```

### Task 4: Metamorphic relations M01–M12

**Files:**
- Create: `src/nolane_plan/wave8_metamorphic.py`
- Create: `tests/test_wave8_metamorphic.py`

**Interfaces:**
- Produces: `run_wave8_metamorphic(seeds) -> tuple[Wave8Counterexample, ...]`.

- [ ] **Step 1: Write RED relation tests**

For seeds `0..31`, assert exact relation preservation for M01–M12 from the design. The comparison projection must explicitly exclude temp paths, wall-clock fields and in-memory object identity.

- [ ] **Step 2: Run RED**

```bash
python -m unittest discover -s tests -p 'test_wave8_metamorphic.py' -v
```

- [ ] **Step 3: Implement canonical projections and transformations**

Provide dedicated transformation functions such as:

```python
permute_set_like_refs(recipe, seed)
add_irrelevant_evidence(recipe)
duplicate_common_lineage_support(recipe)
permute_resource_jobs(recipe, seed)
snapshot_reopen_projection(kernel)
compact_projection(kernel)
```

Each transformation declares the invariant ID it is valid for; transformations may not be reused under a different semantic relation implicitly.

- [ ] **Step 4: GREEN + repeat with reversed seed order**

```bash
python -m unittest discover -s tests -p 'test_wave8_metamorphic.py' -v
```

Also run the same runner with seeds reversed and require identical per-seed results.

- [ ] **Step 5: Commit**

```bash
git add src/nolane_plan/wave8_metamorphic.py tests/test_wave8_metamorphic.py
git commit -m "test: add Wave 8 metamorphic relations"
```

### Task 5: Close dispatch-fence cancellation residual races

**Files:**
- Modify: `src/nolane_plan/execution.py`
- Modify: `src/nolane_plan/kernel.py`
- Modify: `src/nolane_plan/replay_registry.py`
- Modify: replay/snapshot reducer file that currently owns `action.dispatch_recorded` / `action.reconciliation_required` restoration (verify exact owner before edit)
- Create: `tests/test_wave8_cancellation_fence.py`

**Interfaces:**
- Extend `TransactionState` with:
  - `CANCELLED_PRE_DISPATCH`
  - `CANCELLATION_PENDING`
- Add ledger methods:
  - `cancel_before_dispatch(transaction_id: str, detail: str) -> ActionTransaction`
  - `request_cancellation_after_dispatch(transaction_id: str, detail: str) -> ActionTransaction`
- Add kernel method:
  - `cancel_authorized_action(authorization_id: str, *, detail: str) -> ActionTransaction`
- Reuse `reconcile_with_evidence(...)` for post-dispatch proof of applied/not-applied outcome; do not add a caller-supplied trust boolean to the strong path.

- [ ] **Step 1: Write semantic RED tests**

Required tests:

```text
cancel before dispatch -> CANCELLED_PRE_DISPATCH and dispatch is impossible
cancel after DISPATCH_RECORDED -> CANCELLATION_PENDING, never clean cancelled
non-idempotent CANCELLATION_PENDING blocks retry
trusted reconciliation outcome_applied=False -> RECONCILED_NOT_APPLIED
trusted reconciliation outcome_applied=True -> RECONCILED_APPLIED/commit path
snapshot/restart preserves pending cancellation
post-snapshot cancellation event replays exactly
unknown/tampered cancellation event fails closed
```

- [ ] **Step 2: Run focused RED**

```bash
python -m unittest discover -s tests -p 'test_wave8_cancellation_fence.py' -v
```

Expected: failures specifically show absent states/API/replay event.

- [ ] **Step 3: Implement transaction-state semantics**

Rules:

```text
AUTHORIZED -> CANCELLED_PRE_DISPATCH
DISPATCH_RECORDED -> CANCELLATION_PENDING
CANCELLATION_PENDING -> reconciliation only
CANCELLED_PRE_DISPATCH -> terminal, never dispatch
CANCELLATION_PENDING non-idempotent -> retry forbidden
```

Extend `assert_retry_allowed()` accordingly. Extend `reconcile_with_evidence()` to accept `CANCELLATION_PENDING` as a reconciliation-required state while preserving exact transaction/action/authorization/principal/adapter binding.

- [ ] **Step 4: Journal and replay cancellation**

`PlanKernel.cancel_authorized_action(...)` records one correctness-significant `action.cancellation_recorded` event containing transaction ID, authorization ID, resulting state and detail. Add it to the frozen replay registry as a `STATE_REDUCER`. Reducer verifies legal source state and exact resulting state; it must not overwrite a committed/reconciled-applied transaction.

- [ ] **Step 5: GREEN focused + Wave2/3 regression**

```bash
python -m unittest discover -s tests -p 'test_wave8_cancellation_fence.py' -v
python -m unittest discover -s tests -p 'test_wave2_execution_recovery.py' -v
python -m unittest discover -s tests -p 'test_wave3_replay.py' -v
python -m unittest discover -s tests -v
```

- [ ] **Step 6: Commit**

```bash
git add src/nolane_plan/execution.py src/nolane_plan/kernel.py src/nolane_plan/replay_registry.py src/nolane_plan/*recovery*.py tests/test_wave8_cancellation_fence.py
git commit -m "feat: close cancellation dispatch fence semantics"
```

### Task 6: Exhaust strategic relocation and stale dependent authority

**Files:**
- Modify only if RED requires: `src/nolane_plan/relocation.py`, `src/nolane_plan/kernel.py`, lineage/authority integration owner
- Create: `tests/test_wave8_relocation.py`

**Interfaces:**
- Existing `StateRelocator.locate()` remains the authority-free location classifier.

- [ ] **Step 1: Write generated RED/characterization tests**

Cover all bounded region sets generated from 1–5 regions:

```text
no compatible regions -> UNLOCATED
same decision signature across multiple compatible regions -> LOCATED
multiple decision signatures -> AMBIGUOUS
region ordering cannot change status/region_ids/signatures
canonical commit changes location revision when location recomputes
old location-bound authorization/DecisionEpoch is stale after decision-relevant relocation change
```

- [ ] **Step 2: Run focused suite**

```bash
python -m unittest discover -s tests -p 'test_wave8_relocation.py' -v
```

If existing behavior already passes a case, keep it as conformance evidence and make no production edit. Any failing stale-authority case gets a focused RED before the minimal owner-module fix.

- [ ] **Step 3: GREEN and commit**

```bash
python -m unittest discover -s tests -p 'test_wave8_relocation.py' -v
python -m unittest discover -s tests -v
git add tests/test_wave8_relocation.py src/nolane_plan/relocation.py src/nolane_plan/kernel.py src/nolane_plan/*lineage*.py
git commit -m "test: exhaust bounded strategic relocation"
```

### Task 7: Freeze and exhaust the supported historical migration matrix

**Files:**
- Create: `src/nolane_plan/wave8_migration_matrix.py`
- Create: `tests/test_wave8_migration_matrix.py`
- Create: deterministic fixture documents under `tests/fixtures/wave8_migrations/`
- Modify only if RED requires: `src/nolane_plan/migration.py`, `src/nolane_plan/migration_runtime.py`, snapshot import owners.

**Interfaces:**
- Produces `HistoricalMigrationEdge(source_schema, target_schema, fixture_ref, expected_dispositions, unsupported_cases)` and `SUPPORTED_MIGRATION_EDGES`.

- [ ] **Step 1: Enumerate repository-owned snapshot schema edges from recovery code**

The matrix must include only paths the repository can actually parse/import. Do not invent fixtures for unknown historical formats. Each declared edge stores exact source/target schema IDs and fixture digest.

- [ ] **Step 2: Write RED matrix tests**

For every declared edge assert:

```text
fixture digest is stable
repeat import/migration gives same canonical semantic digest
all changed correctness fields have exactly one Wave-7 disposition
old authority is preserved only when exact semantics/lineage permit it; otherwise recheck required
unsupported variants fail closed
migration live result == replayed migration result projection
```

- [ ] **Step 3: Run RED and make minimal fixes**

```bash
python -m unittest discover -s tests -p 'test_wave8_migration_matrix.py' -v
```

No schema pair may be added just to increase coverage count.

- [ ] **Step 4: GREEN and commit**

```bash
python -m unittest discover -s tests -p 'test_wave8_migration_matrix.py' -v
python -m unittest discover -s tests -p 'test_wave7_migration.py' -v
python -m unittest discover -s tests -p 'test_wave7_snapshot.py' -v
git add src/nolane_plan/wave8_migration_matrix.py tests/test_wave8_migration_matrix.py tests/fixtures/wave8_migrations src/nolane_plan/migration.py src/nolane_plan/migration_runtime.py src/nolane_plan/*snapshot*.py
git commit -m "test: exhaust supported migration matrix"
```

### Task 8: Close bounded global exclusion, N-way composition, and extended resource monotonicity

**Files:**
- Create if RED requires: `src/nolane_plan/global_exclusion.py`
- Create if RED requires: `src/nolane_plan/context_composition.py`
- Modify if RED requires: existing Wave-6 resource/schedulability owner modules
- Create: `tests/test_wave8_remaining_closure.py`

**Interfaces if needed:**

```text
GlobalExclusionStatus = EXCLUDED | NOT_EXCLUDED | UNKNOWN
GlobalExclusionAssessment.create(candidate_universe_revision, candidate_refs, surviving_refs, completeness_assurance)
ContextCompositionStatus = COMPOSABLE | INCOMPATIBLE | UNKNOWN
assess_context_composition(contexts, theory) -> ContextCompositionStatus
```

- [ ] **Step 1: Write RED tests that distinguish bounded claims**

Tests must prove:

```text
action-local sufficiency never implies global exclusion by itself
finite complete candidate universe can support bounded exclusion
missing/opaque universe -> UNKNOWN
pairwise-compatible but globally inconsistent contexts -> INCOMPATIBLE/UNKNOWN, never COMPOSABLE
unsupported context theory -> UNKNOWN
resource capacity decrease/load increase cannot improve strong schedulability across generated bounded cohorts
```

- [ ] **Step 2: Run focused RED/characterization**

```bash
python -m unittest discover -s tests -p 'test_wave8_remaining_closure.py' -v
```

Where existing Wave-5/6 APIs already satisfy the contract, keep tests only. Create the new bounded types only for genuinely absent semantics demonstrated by RED.

- [ ] **Step 3: GREEN and commit**

```bash
python -m unittest discover -s tests -p 'test_wave8_remaining_closure.py' -v
python -m unittest discover -s tests -v
git add tests/test_wave8_remaining_closure.py src/nolane_plan/global_exclusion.py src/nolane_plan/context_composition.py src/nolane_plan/*schedulability*.py src/nolane_plan/*resource*.py
git commit -m "feat: close remaining bounded Wave 8 semantics"
```

### Task 9: Bounded chaos C01–C10 and differential D01–D10

**Files:**
- Create: `src/nolane_plan/wave8_chaos.py`
- Create: `src/nolane_plan/wave8_differential.py`
- Create: `tests/test_wave8_chaos.py`
- Create: `tests/test_wave8_differential.py`

**Interfaces:**
- Produces `run_wave8_chaos(seeds)` and `run_wave8_differential(seeds)`.

- [ ] **Step 1: Write deterministic chaos RED tests**

Implement fault schedules as explicit operation recipes, not process kills. Test C01–C10 with seeds `0..15`; each fault point must reproduce identically on rerun.

- [ ] **Step 2: Write differential RED tests**

Implement D01–D10 canonical projections and assert exact equivalence/relation where the design declares it.

- [ ] **Step 3: Run both RED suites**

```bash
python -m unittest discover -s tests -p 'test_wave8_chaos.py' -v
python -m unittest discover -s tests -p 'test_wave8_differential.py' -v
```

- [ ] **Step 4: Implement runners; fix production only from focused RED**

Every mismatch first becomes a single focused regression test before production edits.

- [ ] **Step 5: GREEN twice**

```bash
python -m unittest discover -s tests -p 'test_wave8_chaos.py' -v
python -m unittest discover -s tests -p 'test_wave8_differential.py' -v
python -m unittest discover -s tests -p 'test_wave8_chaos.py' -v
python -m unittest discover -s tests -p 'test_wave8_differential.py' -v
```

- [ ] **Step 6: Commit**

```bash
git add src/nolane_plan/wave8_chaos.py src/nolane_plan/wave8_differential.py tests/test_wave8_chaos.py tests/test_wave8_differential.py
git commit -m "test: add deterministic chaos and differential gates"
```

### Task 10: Six bounded reference worlds and Wave-8 mutation gate

**Files:**
- Create: `src/nolane_plan/wave8_worlds.py`
- Create: `tests/test_wave8_worlds.py`
- Create: `tests/fixtures/wave8_worlds/*.json`
- Create: `scripts/wave8_mutation_gate.py`
- Create: `tests/test_wave8_mutation_gate.py`

**Interfaces:**
- Produces `run_reference_worlds()` and mutation-gate CLI output `WAVE8_MUTATIONS_CAUGHT=12/12`.

- [ ] **Step 1: Encode W01–W06 fixtures and terminal invariants**

Each fixture contains initial state, finite event schedule, exact named invariant IDs and expected terminal classification. Measurement counters are separate from correctness assertions.

- [ ] **Step 2: Write reference-world RED tests**

```bash
python -m unittest discover -s tests -p 'test_wave8_worlds.py' -v
```

- [ ] **Step 3: Implement exactly twelve target-specific mutants X01–X12**

Each mutant declares `target_invariant_id`; the gate rejects a mutant kill caused only by setup/import/syntax failure. A kill is valid only when the targeted Wave-8 assertion fails under the mutant.

- [ ] **Step 4: Run mutation gate and worlds**

```bash
python scripts/wave8_mutation_gate.py
python -m unittest discover -s tests -p 'test_wave8_worlds.py' -v
```

Expected: `WAVE8_MUTATIONS_CAUGHT=12/12` and all six worlds GREEN.

- [ ] **Step 5: Commit**

```bash
git add src/nolane_plan/wave8_worlds.py tests/test_wave8_worlds.py tests/fixtures/wave8_worlds scripts/wave8_mutation_gate.py tests/test_wave8_mutation_gate.py
git commit -m "test: add Wave 8 worlds and mutation gate"
```

### Task 11: Frozen Wave-8 runner, final coverage checker, CI and release

**Files:**
- Create: `src/nolane_plan/wave8_conformance.py`
- Create: `src/nolane_plan/wave8_coverage.py`
- Create: `tests/test_wave8_conformance.py`
- Create: `tests/test_wave8_coverage.py`
- Modify: `.github/workflows/ci.yml`
- Modify: `docs/SPEC-COVERAGE.md`
- Modify: `CONFORMANCE.md`, `README.md`, `CHANGELOG.md`, `SECURITY.md` only where release evidence/claim text requires it
- Modify: `src/nolane_plan/__init__.py`, `pyproject.toml` for `0.8.0a1` only after all implementation gates are GREEN.

**Interfaces:**
- `python -m nolane_plan.wave8_conformance` prints layer totals and `WAVE8_CONFORMANCE=GREEN`.
- `python -m nolane_plan.wave8_coverage` exits non-zero on orphan/unjustified coverage claims.

- [ ] **Step 1: Write runner/coverage RED tests**

Assert exact registry count `68`, exact layer counts, stable registry digest, all executable layers GREEN, no correctness invariant mapped to `BOUNDARY`/`RESEARCH`, and every remaining `PARTIAL` row has an explicit reason/evidence classification.

- [ ] **Step 2: Implement runner and coverage checker**

The conformance runner calls property/metamorphic/chaos/differential/world/coverage layers with frozen CI seed ranges and emits exact machine-readable totals. It exits non-zero on any counterexample.

- [ ] **Step 3: Update CI but keep version at `0.7.0a1` during proof**

Add after Wave-7 gates:

```yaml
- name: Wave 8 conformance exhaustion
  run: python -m nolane_plan.wave8_conformance
- name: Wave 8 constitutional mutation gate
  run: python scripts/wave8_mutation_gate.py
- name: Wave 8 final coverage audit
  run: python -m nolane_plan.wave8_coverage
```

- [ ] **Step 4: Run exact pre-release full surface**

```bash
python -m unittest discover -s tests -v
python -m compileall -q src
python -m nolane_plan conformance
python -m nolane_plan.wave2_conformance
python -m nolane_plan.wave3_conformance
python scripts/wave3_mutation_gate.py
python -m nolane_plan.wave4_conformance
python scripts/wave4_mutation_gate.py
python -m nolane_plan.wave5_conformance
python scripts/wave5_mutation_gate.py
python -m nolane_plan.wave6_conformance
python scripts/wave6_mutation_gate.py
python -m nolane_plan.wave7_conformance
python scripts/wave7_mutation_gate.py
python -m nolane_plan.wave8_conformance
python scripts/wave8_mutation_gate.py
python -m nolane_plan.wave8_coverage
python -m nolane_plan demo --root .ci-demo-wave8
```

- [ ] **Step 5: Require GitHub CI GREEN on Python 3.11/3.12/3.13**

Do not bump release version until the implementation exact head is 3/3 GREEN.

- [ ] **Step 6: Final coverage reconciliation**

Update `docs/SPEC-COVERAGE.md` with exact test/run evidence. Do not force all rows GREEN: retain explicit `PARTIAL`, `RESEARCH` or `BOUNDARY` when the Wave-8 evidence does not close them. Correct the stale Wave-7 text to record final-main run `33350465557` and exact release SHA `78e44da066bd362a2ee935c06ad5902bb0872238`.

- [ ] **Step 7: Bump release to `0.8.0a1` and run exact release-head CI**

Change package/version metadata and release docs in one release commit. The exact release SHA must pass every matrix/gate above.

- [ ] **Step 8: PR synthetic-merge verification**

Open the release PR only after release-head CI is GREEN. Require PR synthetic-merge CI 3/3 GREEN; verify checkout is the synthetic merge SHA from job logs.

- [ ] **Step 9: Race-check and non-forced fast-forward**

Immediately before integration verify:

```text
current main SHA == PR base SHA
compare(main, release_head).status == ahead
behind_by == 0
PR mergeable == true
```

Then update `main` to exact release SHA with `force=false` only.

- [ ] **Step 10: Fresh final-main verification**

Require a new `push` CI run on `main` at the exact release SHA with Python 3.11/3.12/3.13 all completed/success. Read at least one full job log to verify checkout SHA, package version, full tests, Wave-8 totals, mutation `12/12`, coverage audit and demo journal validity.

- [ ] **Step 11: Completion claim**

Only after Step 10 may the repository claim:

```text
Nolane Plan v0.15 reference runtime is GREEN for the bounded single-writer
scope explicitly enumerated in the final coverage ledger and Wave 2–8
conformance/exhaustion suites.
```

Do not claim formal verification, arbitrary production crash safety, distributed consensus safety, universal optimality or empirical superiority.
