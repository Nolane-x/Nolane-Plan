# Wave 8 — Conformance Exhaustion Design

## Status

Implementation design for the final bounded conformance-exhaustion wave of the Nolane Plan v0.15 reference runtime.

Wave 8 starts from the released Wave-7 exact main SHA `78e44da066bd362a2ee935c06ad5902bb0872238` (`0.7.0a1`). Wave 7 is already GREEN for bounded durable-lineage/migration/replay/compaction semantics. Wave 8 does not reopen those contracts as feature work. Instead, it tries to falsify the strongest remaining claims, closes the remaining bounded normative seams called out by `docs/SPEC-COVERAGE.md`, and separates correctness evidence from benchmark/research measurement.

The chosen architecture is **Layered Falsification**: frozen coverage registry → property/metamorphic invariants → deterministic bounded chaos → differential equivalence → broader constitutional mutation → bounded reference worlds → final source-spec reconciliation.

## Source-of-truth contracts

Wave 8 is grounded in:

- `docs/SPEC-COVERAGE.md`;
- `docs/superpowers/specs/2026-08-29-nolane-plan-v015-runtime-design.md`;
- Wave 3–7 design documents and their already-frozen conformance taxonomies;
- the released runtime at `0.7.0a1`.

The remaining normative engineering surfaces assigned to Wave 8 are:

1. decision-relevant convergence guards beyond the currently declared bounded examples;
2. generalized global minimality/exclusion proof beyond the current action-local sufficiency certificate;
3. broader N-way proof-context composition without allowing unsupported context joins to become authority;
4. resource/capacity feasibility beyond the currently declared control-plane resource model;
5. dispatch fence and cancellation residual-race semantics;
6. strategic relocation ambiguity/unknown behavior under generated overlapping and changing regions;
7. broader migration contracts across supported historical schema/version paths without silent guessing;
8. property/metamorphic/chaos/differential conformance across the already-GREEN runtime surfaces;
9. broader constitutional mutation coverage;
10. final source-spec coverage reconciliation.

The following remain research or explicit product boundaries and MUST NOT be promoted to GREEN by Wave 8:

- empirical superiority over external planners;
- arbitrary production storage-engine physical-history deletion;
- distributed correctness writers / consensus;
- generic identity-provider behavior;
- generic scheduler/orchestrator-product behavior;
- generic messaging/task-marketplace behavior.

## Objective

Wave 8 must answer a harder question than “do the examples pass?”:

> Across a deterministic, reproducible family of generated valid and adversarial states, do Nolane Plan’s declared safety and authority invariants remain true under semantics-preserving transformations, restart/replay boundaries, bounded faults, migration/compaction transforms, and deliberate constitutional mutants?

A Wave-8 GREEN result means only that the bounded v0.15 reference-runtime claim survived this exhaustion surface. It is not a formal proof and is not a production/distributed safety certification.

## Design principles

### 1. Every generated test has a named oracle

No random workload may count as evidence merely because it “did not crash”. Every generated case binds:

- one or more `spec_surface_refs`;
- one or more invariant IDs;
- an exact deterministic seed;
- a generator version;
- the transformation/fault schedule;
- expected relation (`EQUAL`, `MONOTONIC_NON_PROMOTION`, `FAIL_CLOSED`, `PRESERVE_HISTORY`, etc.);
- an observed canonical summary;
- a reproducible counterexample recipe on failure.

### 2. Determinism is part of the test contract

All randomized exploration uses `random.Random(seed)` owned by the Wave-8 harness. No test may depend on wall-clock time, process scheduling luck, hash iteration order, network access, or uncontrolled global randomness.

A failed generated case must be rerunnable by a single seed + case ID. Shrinking/minimization is deterministic.

### 3. Exhaustion code has no authority

Wave-8 generators, chaos schedules, benchmark worlds, shrinkers and differential runners are test/support code. They cannot mint `ActionAuthorization`, bypass `PlanKernel`’s writer lock, mutate canonical structures out of band, or create a new correctness path.

Production changes are allowed only when a RED counterexample demonstrates a missing semantic guard in the bounded runtime.

### 4. Strong claims are relation-based

For many correctness surfaces the strongest oracle is not an expected scalar output but a relation between executions. Examples:

- permutation of set-like input refs must not change canonical digest;
- adding irrelevant evidence must not strengthen authority;
- removing support may preserve or weaken authority but never strengthen it;
- restart/replay must preserve canonical semantic state;
- representation-only compaction must preserve authority result;
- migration marked `INVALIDATED_REQUIRES_RECHECK` must never retain old current usability;
- hiding principal information cannot increase that principal’s available decision authority;
- adding an active blocker cannot make a proof more usable;
- shrinking resource capacity cannot improve strong schedulability;
- delaying a required observation cannot improve information-by-deadline feasibility.

### 5. Failure minimization is first-class

A raw failing seed is insufficient. The harness must deterministically try to shrink:

1. number of runtime mutations;
2. number of principals;
3. number of evidence/information records;
4. number of candidate actions/policy nodes;
5. number of resources/jobs;
6. number of migration dispositions;
7. number of fault-injection points.

The minimized recipe must preserve the same invariant failure ID.

## Architecture

### 1. `wave8_registry.py` — frozen exhaustion registry

Create `src/nolane_plan/wave8_registry.py`.

Core immutable types:

```text
Wave8Layer = PROPERTY | METAMORPHIC | CHAOS | DIFFERENTIAL | MUTATION | WORLD | COVERAGE
Wave8Expectation = EQUAL | MONOTONIC_NON_PROMOTION | FAIL_CLOSED | PRESERVE_HISTORY | PRESERVE_SEMANTICS | WEAKEN_OR_EQUAL
Wave8Invariant
  invariant_id
  layer
  spec_surface_refs[]
  title
  expectation
  generator_family
  required_oracle
  bounded_scope

Wave8Counterexample
  invariant_id
  case_id
  seed
  generator_version
  recipe[]
  minimized_recipe[]
  expected_relation
  observed_summary
  canonical_digest
```

Registry rules:

- invariant IDs are unique and frozen;
- every executable Wave-8 case maps to at least one registry invariant;
- every registry invariant maps to at least one `docs/SPEC-COVERAGE.md` row;
- `BOUNDARY`/`RESEARCH` rows cannot be registered as correctness invariants;
- registry serialization/digest is deterministic;
- duplicate or orphan coverage refs fail CI.

Initial invariant families are frozen as:

- `P01–P10`: property invariants;
- `M01–M12`: metamorphic relations;
- `C01–C10`: bounded chaos/restart/fault invariants;
- `D01–D10`: differential equivalence invariants;
- `X01–X12`: broader constitutional mutation targets;
- `W01–W06`: bounded reference-world invariants;
- `S01–S08`: final spec-coverage reconciliation checks.

Exact counts may only change before the first Wave-8 taxonomy GREEN commit. After that commit, changing counts/names requires an explicit taxonomy-revision commit and corresponding documentation update.

### 2. `wave8_generators.py` — deterministic semantic generators

Create `src/nolane_plan/wave8_generators.py`.

Generators produce bounded valid/adversarial inputs for existing production objects rather than inventing parallel semantics.

Generator families:

- principal/access/information histories;
- evidence/support/blocker graphs;
- action scores and candidate sets;
- DecisionEpoch / policy information partitions;
- policy-node/selection/sufficiency/seal bundles;
- control-plane resources/jobs/coexistence relations;
- handoff/liveness/stability contracts;
- dormant/resurrection branches;
- relocation candidate-region sets;
- lineage/regime revisions;
- migration manifests across declared supported schema transitions;
- replay/compaction operation sequences.

All generated values are small and bounded. Default CI budget targets hundreds of cases per family, not unbounded fuzzing.

Invalid generators intentionally violate one named precondition at a time so a failure can be attributed to a specific guard.

### 3. `wave8_properties.py` — invariant properties

Create `src/nolane_plan/wave8_properties.py`.

Minimum property set:

- **P01 canonical determinism**: same semantic input produces same canonical digest regardless of set-like ordering;
- **P02 principal anti-escalation**: reducing a principal’s observed/allowed information cannot increase decision or action authority;
- **P03 blocker monotonicity**: adding an active blocker cannot make unsupported/blocked proof usable;
- **P04 support monotonicity**: removing positive support cannot strengthen proof/seal authority;
- **P05 hard-veto monotonicity**: hard-vetoed candidates never re-enter the eligible Pareto/selection set because of score changes;
- **P06 resource monotonicity**: reducing capacity or increasing required load cannot improve a strong schedulability result;
- **P07 temporal monotonicity**: delaying required information or reducing reaction time cannot improve strong handoff/executability status;
- **P08 authority freshness**: changing any exact authority-bound semantic revision cannot leave old dispatch authority usable;
- **P09 history non-erasure**: valid restart/migration/compaction operations do not erase required immutable receipts/lineage/debt history;
- **P10 unknown non-promotion**: UNKNOWN/opaque/unlocated/inconclusive states do not spontaneously become strong positive authority without new evidence or explicit conservative rule.

### 4. `wave8_metamorphic.py` — semantics-preserving transformations

Create `src/nolane_plan/wave8_metamorphic.py`.

Required relations:

- **M01** reorder set-like refs → equal digest/result;
- **M02** rename non-semantic presentation labels → equal semantic result;
- **M03** add irrelevant evidence outside dependency/query domain → authority equal, not stronger through accidental global freshness;
- **M04** duplicate common-lineage support → independence strength unchanged;
- **M05** split an information-equivalent history into aliases → pre-reveal action choice unchanged;
- **M06** reorder mutually exclusive branch declarations → policy coherence unchanged;
- **M07** reorder resources/jobs with stable IDs → schedulability result unchanged;
- **M08** snapshot then immediate reopen → canonical semantic digest equal;
- **M09** replay equivalent supported journal suffix from same prefix → canonical semantic digest equal;
- **M10** representation-only compaction → semantic root and current authority result equal;
- **M11** deterministic legacy import repeated twice → equal imported semantic root and equal recheck requirements;
- **M12** migration manifest canonical ordering changes only → equal manifest digest/result.

Transformations that change semantics must never be mislabeled metamorphic-equivalent.

### 5. `wave8_chaos.py` — bounded deterministic fault schedules

Create `src/nolane_plan/wave8_chaos.py`.

Chaos is modeled at explicit correctness boundaries, not via nondeterministic process killing.

Fault points include:

- before and after journal append;
- before and after snapshot persistence;
- after snapshot but before suffix replay;
- before/after authorization binding;
- after durable dispatch record but before outcome observation;
- after ambiguous non-idempotent outcome before reconciliation;
- before migration root switch;
- after migration root switch during reopen/replay;
- before/after representation-only compaction commit;
- before child activation refresh in a handoff;
- cancellation request racing a modeled dispatch fence.

Required chaos invariants:

- **C01** torn/invalid snapshot fails closed;
- **C02** valid snapshot + valid suffix reconstructs exactly;
- **C03** unknown correctness-significant suffix event fails closed;
- **C04** authorization interrupted before durable binding cannot become dispatchable authority;
- **C05** durable dispatch without known non-idempotent outcome remains reconciliation-required;
- **C06** migration failure before root switch leaves source root authoritative;
- **C07** migration durable root switch replays to target root without resurrecting invalidated authority;
- **C08** compaction commit is all-or-nothing at the declared representation boundary;
- **C09** stale handoff activation fails closed after restart;
- **C10** cancellation/dispatch residual ambiguity is explicit and cannot be reported as clean cancellation or clean commit without evidence.

Wave 8 may add a bounded production primitive for C10 if RED proves the current action lifecycle/transaction protocol cannot represent the required fence state. It must reuse existing transaction/receipt authority rather than create a second executor protocol.

### 6. `wave8_differential.py` — independent execution-path equivalence

Create `src/nolane_plan/wave8_differential.py`.

Differential checks compare independent ways to reach the same declared semantic state:

- **D01** live execution state vs snapshot+reopen state;
- **D02** live state vs snapshot-prefix + replay-suffix state;
- **D03** repeated replay from same prefix;
- **D04** pre/post representation-only compaction;
- **D05** direct v7 state vs deterministic v6-imported equivalent where the legacy fixture actually contains enough semantics;
- **D06** migration execution vs replay of durable migration event;
- **D07** direct principal information computation vs reconstructed principal state after restart;
- **D08** proof/policy authority assessment before restart vs recalculated assessment after restart;
- **D09** schedulability/liveness assessment before restart vs recalculated assessment after restart;
- **D10** relocation result computed from the same canonical state/region set across ordering permutations and restart boundaries.

Differential comparison uses a bounded canonical projection. It must not compare incidental object identity, temp paths, wall-clock values or dictionary insertion order.

### 7. Remaining bounded semantic closures

Wave 8 is primarily conformance, but a RED property may expose a genuinely missing bounded primitive. These are the only pre-authorized production closure areas.

#### 7.1 Generalized bounded exclusion/minimality

Add a bounded `GlobalExclusionAssessment` only if generated counterexamples prove that current action-local `DecisionSufficiencyCertificate` can incorrectly imply a stronger global minimality claim.

The bounded implementation must:

- distinguish “sufficient for selected action” from “all relevant alternatives globally excluded”;
- require an explicit finite candidate universe or return `UNKNOWN`;
- bind candidate-universe revision/digest;
- never create action authority by itself;
- be optional to existing sealed-policy paths unless a caller claims global exclusion.

#### 7.2 Generalized N-way proof-context composition

If RED demonstrates a gap, add a bounded composability checker over explicit context constraint atoms.

It must return `COMPOSABLE`, `INCOMPATIBLE`, or `UNKNOWN`; pairwise compatibility is insufficient to claim global composition; unsupported solver/context theory returns `UNKNOWN`, never true.

#### 7.3 Extended resource feasibility

If RED demonstrates a gap, extend existing control-plane resource semantics only for declared bounded resource kinds and explicit capacity/demand windows. Unknown external scheduler behavior remains conservative/UNKNOWN.

#### 7.4 Dispatch fence / cancellation residual race

This is a mandatory Wave-8 closure target because the coverage ledger is currently PARTIAL.

The runtime must distinguish at least:

- cancellation accepted before durable dispatch;
- dispatch durably recorded, cancellation unconfirmed;
- external effect outcome unknown;
- cancellation/compensation confirmed by evidence;
- committed outcome.

A cancellation request must never erase the durable fact that dispatch might already have occurred. For non-idempotent actions, ambiguous cancellation after durable dispatch remains reconciliation-required.

#### 7.5 Strategic relocation exhaustion

Generated overlapping regions must verify:

- zero compatible regions → `UNLOCATED`;
- multiple compatible regions sharing one decision signature → `LOCATED` is allowed for decision-equivalent location;
- compatible regions with different decision signatures → `AMBIGUOUS`;
- ordering of regions never changes status/signatures;
- canonical-state mutation can change the location revision and stale dependent authority;
- ambiguity is never silently collapsed by selecting an arbitrary first region.

#### 7.6 Historical migration matrix

Wave 8 does not promise every imaginable schema pair. It must freeze the **supported historical migration matrix** for repository-owned snapshot schemas and test every declared edge.

For each supported edge:

- a fixture exists;
- changed correctness fields are explicit;
- all six dispositions retain their Wave-7 semantics;
- repeated import/migration is deterministic;
- unsupported legacy variants are explicit fail-closed cases;
- no migration path strengthens historical authority merely because later schemas know more.

### 8. `wave8_conformance.py` — frozen exhaustion runner

Create `src/nolane_plan/wave8_conformance.py`.

The runner executes the frozen registry using deterministic seed ranges and prints machine-checkable totals by layer.

Required output shape:

```text
WAVE8_PROPERTY=<passed>/<total>
WAVE8_METAMORPHIC=<passed>/<total>
WAVE8_CHAOS=<passed>/<total>
WAVE8_DIFFERENTIAL=<passed>/<total>
WAVE8_WORLDS=<passed>/<total>
WAVE8_COVERAGE=<passed>/<total>
WAVE8_CONFORMANCE=GREEN
```

On failure it prints the exact invariant ID, case ID, seed and minimized recipe and exits non-zero.

### 9. Broader constitutional mutation gate

Create `scripts/wave8_mutation_gate.py`.

At least twelve target-specific mutants must be killed:

1. principal anti-escalation bypass;
2. blocker monotonicity bypass;
3. hard-veto resurrection;
4. resource-capacity monotonicity inversion;
5. temporal-information deadline optimism;
6. replay equivalence digest bypass;
7. unknown-event fail-open;
8. migration authority resurrection;
9. compaction semantic-equivalence break;
10. cancellation after durable dispatch falsely reported clean;
11. relocation ambiguity collapsed to arbitrary region;
12. global-composition pairwise-only false positive.

The mutation gate must fail if a mutant survives or if a mutant is killed by an unrelated crash before reaching its target assertion. Each mutant therefore has an expected target invariant/case family.

### 10. Bounded reference worlds

Create `src/nolane_plan/wave8_worlds.py` and deterministic fixtures under `tests/fixtures/wave8_worlds/`.

Reference worlds are correctness/measurement scenarios, not proof of superiority.

Six bounded worlds:

- **W01 Principal Relay** — two/three principals with delayed observations and asymmetric access;
- **W02 Open-World Recovery** — residual world becomes decision-relevant and forces uncertainty/quarantine;
- **W03 Deadline Resource Contention** — concurrent reaction routes compete for worker/writer/approval capacity;
- **W04 Handoff Chain** — repeated ordinary/recovery stutter plus information-by-deadline and activation refresh;
- **W05 Migration + Ambiguous External Effect** — schema transition around a non-idempotent unknown outcome;
- **W06 Dormant Hedge + Compaction** — old unique fallback/dormant branch survives representation compaction and later revalidation.

Each world has:

- canonical initial fixture;
- finite action/event schedule;
- named safety invariants;
- deterministic expected terminal classification;
- optional measurement counters (steps, retained options, debt, reaction slack).

Measurement counters may be reported but may not gate a correctness claim unless the spec gives a hard bound.

### 11. Final spec reconciliation

Wave 8 must turn `docs/SPEC-COVERAGE.md` into a closed audited ledger for v0.15 bounded reference-runtime scope.

Create `src/nolane_plan/wave8_coverage.py` or an equivalent deterministic checker that verifies:

- every non-boundary/non-research coverage row has an implementation/test evidence reference;
- every Wave-8 registry invariant maps to a ledger row;
- no `PARTIAL` or `MISSING` row is silently rewritten to GREEN without a named test/implementation evidence reference;
- rows intentionally remaining partial have an explicit reason and are moved to `BOUNDARY` or `RESEARCH` only when the source design actually makes them non-goals;
- release claim text is generated/checked against the ledger state rather than manually overstating closure.

The final audit must preserve explicit PARTIAL status for any surface that remains genuinely unclosed.

## Test strategy

Wave 8 remains strict TDD.

For every new production semantic guard:

1. add the smallest RED unit/property counterexample;
2. run the focused test and preserve exact failure evidence;
3. implement the smallest semantic fix;
4. rerun focused tests;
5. run the affected generated family;
6. run full 408+ regression plus Wave 2–8 gates;
7. commit only after GREEN.

Generator/harness code itself also gets tests for deterministic seed replay, invariant registry completeness, failure minimization and duplicate/orphan detection.

## CI strategy

The existing Python 3.11/3.12/3.13 matrix remains mandatory.

Wave-8 CI adds:

- Wave-8 registry self-check;
- deterministic property/metamorphic suite;
- deterministic bounded chaos suite;
- differential suite;
- Wave-8 constitutional mutation gate;
- bounded reference worlds;
- final coverage checker.

Runtime budget is bounded. The default PR/push matrix must remain practical for GitHub-hosted runners. A fixed “extended seed” job may be added only if deterministic and still bounded; it cannot replace the default exact-head gates.

## Release target

Wave-8 release candidate: `0.8.0a1`.

Release requires the same exact commit to pass on Python 3.11/3.12/3.13:

- all prior tests;
- all Wave-8 unit/generated tests;
- compile all modules;
- principal projection oracle `108 -> 0`;
- Wave 2–8 adversarial/exhaustion conformance;
- Wave 3–8 constitutional mutation gates;
- bounded reference worlds;
- final coverage checker;
- end-to-end demo;
- exact release-head CI;
- PR synthetic-merge CI;
- fresh `main` race-check and non-forced fast-forward;
- fresh final-main CI on the exact release SHA.

No release merge is allowed if `main` has moved and the candidate is behind; the release process must rebase/reverify rather than force-update.

## Definition of done

Wave 8 is done only when:

1. the exhaustion registry is frozen and every invariant is mapped to a real v0.15 coverage row;
2. all property/metamorphic/chaos/differential suites are deterministic and GREEN;
3. every generated failure can be reproduced by seed/case and minimized deterministically;
4. the dispatch-fence/cancellation residual-race row is either closed with explicit semantics or remains honestly PARTIAL with a demonstrated reason — never silently promoted;
5. relocation ambiguity is exhausted over bounded generated region/state families;
6. every declared supported historical migration edge has fixtures and differential/replay checks;
7. the Wave-8 constitutional mutant set is target-specifically killed;
8. six bounded reference worlds pass their named correctness invariants;
9. the final coverage ledger contains no unjustified GREEN claims;
10. exact release-head, synthetic-merge and final-main CI are all GREEN on the same `0.8.0a1` release SHA.

## Claim boundary

The strongest permitted final claim is:

> **Nolane Plan v0.15 reference runtime is GREEN for the bounded single-writer scope explicitly enumerated in the final coverage ledger and Wave 2–8 conformance/exhaustion suites.**

This claim does not mean formal verification, arbitrary production crash safety, distributed consensus safety, universal optimality, or empirical superiority over other planning systems.
