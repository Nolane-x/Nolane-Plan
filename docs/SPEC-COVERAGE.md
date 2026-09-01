# Nolane Plan v0.15 Implementation Coverage Ledger

This ledger tracks the strongest normative runtime contracts in `NOLANE-PLAN-RUNTIME-ARCHITECTURE-V0.15-PRINCIPAL-SCOPED-MULTI-AGENT-CLOSURE-SPEC.md` against the reference implementation. It deliberately separates **implemented semantics**, **partial reference semantics**, **research claims**, and **explicit product boundaries**.

Release line: `0.8.0a1` (Wave 8) is final-main verified at `8f0288ee2119a05a83923ae16e0ec56b7cbad1c8` in CI run `33367224457`. Wave 9 Production Correctness & Distributed Authority is an implementation candidate on its dedicated branch and remains unreleased until its exact release-head, synthetic-merge and final-main gates are reproduced. `GREEN` below always means the tested bounded scope stated by the row, not global formal correctness.

Legend: `GREEN` = on a tested correctness path for the stated bounded scope; `GREEN ... / PARTIAL — ...` = a bounded primitive is closed while a wider explicitly named surface remains open; `PARTIAL — ...` = the complete contract remains open for the stated reason; `MISSING` = not implemented; `RESEARCH` = measurement only and never correctness evidence; `BOUNDARY` = explicitly outside the v0.15 reference-runtime goal.

| Spec surface | Current state | Closure wave |
|---|---|---|
| Mission revision / anti-goals / hard constraints | GREEN | existing |
| Canonical state outranks plan narrative | GREEN | existing |
| `NULL_WORLD` / residual unknown-world representation | GREEN | existing |
| Future families, bounded factorized compiler | GREEN — declared runtime families carry immutable Wave-7 lineage | existing/W7 |
| Decision-relevant convergence guards | GREEN for declared decision guards / PARTIAL — generalized convergence optimality remains outside the bounded reference runtime | existing/W7 |
| Condition-centric Strategic Obligations | GREEN | existing |
| Evidence polarity, revocation, common-lineage independence | GREEN | existing |
| Principal-scoped access profiles and information partitions | GREEN | existing + W5/W8 |
| Decision Capsule recipient/partition/access binding | GREEN | existing |
| Capsule hydration anti-escalation | GREEN | existing |
| Exact acting-principal authorization and presented-principal match | GREEN | existing |
| Canonical host/platform principal identity binding | GREEN | W3 |
| Principal identity provenance across restart/replay | GREEN | W3/W8 |
| Inter-principal planning-relevant delivery/observation evidence | GREEN | W3/W8 |
| Dispatch-time principal attestation object | GREEN | W3 |
| Executing-principal reconciliation evidence | GREEN | W3 |
| `DecisionCutRevision` causal/knowledge frontier | GREEN | W2 |
| Knowledge-time / no retroactive artifact injection | GREEN | W2/W3 |
| Authority-time dependency freshness | GREEN | W2/W4/W7/W8 |
| `ProofInputEnvelopeRevision` | GREEN | W4 |
| Dependency-capture assurance / hidden-read defense | GREEN | W4 |
| `ProofDependencyManifestRevision` | GREEN | W4 |
| Query-domain membership/result-sensitivity revision for absence/universal claims | GREEN | W4 |
| SupportAlternativeSet / conjunctive clauses / grounded support | GREEN | W4/W8 |
| Blocking-invalidity vs positive-support distinction | GREEN | W4/W8 |
| Semantic closure barrier (source mutation + generation advance) | GREEN | W4 |
| Replay-derived proof support/freshness reconstruction | GREEN for declared runtime paths | W4/W7/W8 |
| `DecisionEpoch` principal/access/partition/action-space/temporal binding | GREEN | W5 |
| Direct `DecisionEpoch` binding to mission/canonical/location/information/semantic-regime lineage | GREEN for declared runtime sidecar | W7 |
| Reveal events / principal-relative observation frontier | GREEN | W5 |
| Principal-relative non-anticipativity checking | GREEN | W5/W8 |
| `PolicyNodeRevision` contingent policy graph | GREEN | W5 |
| Policy-level branch/resource coherence | GREEN | W5/W8 |
| Frozen `SelectionTransaction` / advisory `SelectionRecord` | GREEN | W5 |
| Selection hard-veto monotonicity and dependency freshness | GREEN | W5/W8 |
| `DecisionSufficiencyCertificate` exact action-local closure | GREEN | W5 |
| Generalized global minimality/exclusion proof beyond declared closure | GREEN for bounded finite complete candidate universes / PARTIAL — generalized open or opaque candidate universes remain outside proved closure | W8 |
| PlanSeal / immutable proof-bearing decision seal | GREEN | W5 |
| Monotonic seal invalidation / no revival | GREEN | W5 |
| N-way proof-context composition | GREEN for bounded finite-world theory / PARTIAL — generalized or opaque constraint theories remain unsupported | W5/W8 |
| Recursive decision-recall certificate | GREEN for bounded signature horizon | W5 |
| Policy outcome totality / residual-handler certificate | GREEN for bounded explicit outcomes | W5 |
| Transition/observation-model adequacy distinct from modeled-support totality | GREEN for bounded explicit residual model | W6 |
| Parent→child policy-edge stitch certificate | GREEN for explicit refinement contracts | W5 |
| Decision reaction envelope and IA0–IA4 classification | GREEN for bounded single-route timing | W5 |
| Canonical control-plane resource revisions | GREEN | W6 |
| Reaction resource-demand/job contracts | GREEN | W6 |
| Joint control-plane schedulability certificate | GREEN for bounded deterministic/scenario analysis | W6/W8 |
| Coexistence/mutual-exclusion aware joint reaction analysis | GREEN | W6 |
| Resource/regime freshness of schedulability authority | GREEN | W6/W7 |
| Human approval / kernel-writer / rate-limit resources in reaction feasibility | GREEN for declared resource contracts | W6 |
| Structure-aware preparedness aggregation | GREEN for bounded structures | W5/W6 |
| Failure-set-relative option independence / common-mode resistance | GREEN | W6 |
| Nominal vs robust-independent preparedness reporting | GREEN | W6 |
| Information-capability preservation / self-induced blindness check | GREEN | W5 |
| Continuation contract / terminal semantics / horizon cap | GREEN | W5 |
| Repeated handoff liveness certificate | GREEN | W6/W8 |
| Grounded handoff deadline revision | GREEN | W6 |
| Bounded ordinary/recovery stutter and deferral budgets | GREEN | W6 |
| Handoff progress rank rejects semantic/debt churn | GREEN | W6 |
| Horizon advance cannot launder critical-debt/workload regression | GREEN | W6 |
| Recursive feasibility and information-by-deadline requirement for `SAFE_HANDOFF` | GREEN for bounded certificate inputs | W6/W8 |
| Activation-time edge stability contract | GREEN | W6 |
| Mutable generation/permission/reservation/writer refresh at child activation | GREEN | W6/W8 |
| Open asynchronous parent effect blocks child activation until resolved | GREEN | W6 |
| Edge opacity remains UNKNOWN rather than assumed stable | GREEN | W6 |
| Exact-scope policy executability `EXEC_*` assessment | GREEN | W5 |
| Proof-carrying `ActionAuthorization` bundle | GREEN for sealed-policy path | W4/W5/W7/W8 |
| Sealed-policy authority recheck under exact kernel writer lock | GREEN | W5/W7 |
| Wave-6 schedulability/liveness prerequisites under exact kernel writer | GREEN | W6/W7/W8 |
| Exact proof/policy/schedulability/action semantic lineage bound into authorization | GREEN for declared authority pipeline | W7/W8 |
| Wave-6 objects cannot mint independent authorization/dispatch authority | GREEN | W6 |
| SharedCommitment exclusive-resource conflict | GREEN | existing + W5 |
| Resource/capacity feasibility beyond simple exclusive overlap | GREEN for declared control-plane resource model / PARTIAL — arbitrary external resource models and schedulers remain outside the bounded runtime | W6/W8 |
| Protected deadline-critical planning capacity | GREEN | W6 |
| Multiple required protections fail closed on oversubscription | GREEN | W6 |
| Safe pruning / dormant branch / resurrection | GREEN for revisioned bounded revalidation | W6 |
| Probability-only catastrophic/sole-route/unique-hedge/information-rich pruning prohibition | GREEN for declared protected classes | W6 |
| Resurrection requires mission/evidence/transition/temporal/resource/capability/authority/risk revalidation | GREEN | W6 |
| Planning budget mandatory-work preservation | GREEN | existing/W6 |
| Action lifecycle postcondition-before-commit | GREEN | existing |
| Durable dispatch-before-side-effect linearization | GREEN | W2/W3 |
| Unknown non-idempotent outcome -> evidence-bound reconciliation | GREEN | W2/W3/W8/W9 |
| Adapter capability revision binding | GREEN | W2/W9 |
| Dispatch fence contract / cancellation residual race semantics | GREEN for the declared Wave-9 adapter capability contract / PARTIAL — adapter-specific physical cancellation mechanisms remain external | W8/W9 |
| Strategic relocation `LOCATED/AMBIGUOUS/UNLOCATED` | GREEN for bounded canonical states and finite region sets / PARTIAL — generalized geometric or continuous location semantics are outside this classifier | existing/W8 |
| Completion verifier bound to current mission/cut/freshness | GREEN | existing/W2 |
| Common immutable lineage schema for declared strategic runtime families | GREEN | W7/W8 |
| Immutable historical revision identity / parent DAG / no-rebind semantics | GREEN | W7 |
| Schema/world-model/environment/canonicalization/semantic-profile regime versioning | GREEN for explicit bounded runtime regimes | W7 |
| Snapshot/journal integrity and prefix binding | GREEN | W2/W8/W9 |
| Trust-bearing snapshot/replay semantics | GREEN | W3 |
| Proof-bearing snapshot/replay semantics | GREEN | W4/W8 |
| Policy-bearing snapshot/replay semantics | GREEN | W5/W8 |
| Wave-6 resource/schedulability/liveness/stability snapshot/replay semantics | GREEN | W6/W8 |
| Snapshot v7 persists lineage/regimes/migration/compaction/replay registry and authority closure | GREEN | W7/W8 |
| Conservative deterministic v6→v7 import without invented strong ancestry | GREEN | W7/W8 |
| Replay coverage for every correctness-significant event emitted by the bounded runtime | GREEN | W7/W8/W9 |
| Unknown correctness-significant replay event fails closed | GREEN | W7/W8/W9 |
| Same supported snapshot+journal produces same bounded canonical semantic digest | GREEN | W7/W8/W9 |
| Typed semantic migration with exact six dispositions and explicit debt/identity mappings | GREEN for bounded migration contract | W7/W8 |
| General migration contracts across every historical schema/version pair | PARTIAL — repository-owned v2-v6 to v7 edges are exhausted; arbitrary external/historical schema pairs remain unsupported | W8 |
| Migration cannot silently preserve authority or reinterpret ambiguous external effects | GREEN for declared runtime migration path | W7/W8 |
| Reversible representation-only graph compaction with read-only archive/reconstruction | GREEN for bounded reference runtime | W7/W8 |
| Compaction retains active authority, dormant/resurrection, proof/evidence/debt and unique-fallback lineage | GREEN | W7/W8/W9 |
| Production physical history deletion/general storage-engine compaction | GREEN for the Wave-9 bounded production-store destructive-compaction contract / PARTIAL — arbitrary storage-engine compaction remains outside the reference runtime | W9 |
| PG01-PG40 registry | GREEN | existing |
| I-65..I-72 v0.6 schedulability/liveness invariants | GREEN for bounded reference-runtime scope | W6 |
| I-245..I-260 principal-scoped closure | GREEN for declared principal/authority paths / PARTIAL — wider source-spec claims outside the enumerated runtime remain unpromoted | W3-W9 |
| v0.14 projection collision oracle `108 -> 0` | GREEN | existing |
| Wave-2 adversarial conformance | GREEN — 10/10 | W2 |
| Wave-3 adversarial conformance + constitutional mutations | GREEN — 12/12 + 4/4 | W3 |
| Wave-4 adversarial conformance + constitutional mutations | GREEN — 14/14 + 7/7 | W4 |
| Wave-5 adversarial conformance + constitutional mutations | GREEN — 29/29 + 13/13 | W5 |
| Wave-6 exact failure-taxonomy conformance + constitutional mutations | GREEN — 43/43 + 12/12 | W6 |
| Wave-7 durable-lineage/migration/replay/compaction conformance + constitutional mutations | GREEN — 32/32 + 12/12 | W7 |
| Python 3.11/3.12/3.13 Wave-7 implementation matrix | GREEN — final release SHA `78e44da066bd362a2ee935c06ad5902bb0872238`; final-main CI `33350465557`; 408 tests + compile/oracle/Wave2–7 gates/demo | W7 |
| Property/metamorphic/chaos/differential conformance | GREEN — frozen Wave-8 P01–P10, M01–M12, C01–C10 and D01–D10 executable suites with deterministic seeded runners | W8 |
| Python 3.11/3.12/3.13 Wave-8 implementation matrix | GREEN — final release SHA `8f0288ee2119a05a83923ae16e0ec56b7cbad1c8`; final-main CI `33367224457`; 464 tests + compile/oracle/Wave2–8 gates/demo | W8 |
| Bounded destructive production-store compaction | GREEN for source→shadow→CAS switch→retire→verify under declared production-store capabilities | W9 |
| Bounded external execution capability/cancellation/compensation contract | GREEN for exact adapter-revision/authority-epoch evidence paths | W9 |
| Bounded multi-writer correctness authority | GREEN for backends proving CAS + fencing + durable acknowledgement; consensus remains outside scope | W9 |
| Real benchmark worlds / empirical superiority | RESEARCH | W8 measurement only |
| Distributed correctness writers / consensus | GREEN for the Wave-9 bounded CAS/fencing authority protocol / BOUNDARY — generic consensus, replication and distributed transaction protocols remain out of scope | W9 |
| Generic identity provider | BOUNDARY | not v0.15 |
| Generic scheduler/orchestrator product | BOUNDARY | not v0.15 |
| Generic messaging/task marketplace/orchestration platform | BOUNDARY | not v0.15 |

## Exhaustion order

1. **Wave 3 — External Trust Anchor Closure — GREEN for reference-runtime scope**.
2. **Wave 4 — Proof Dependency & Support Closure — GREEN for reference-runtime scope**.
3. **Wave 5 — Executable Policy Closure — GREEN for bounded reference-runtime scope**.
4. **Wave 6 — Schedulability/Liveness & Future-Temporal-Resource Closure — GREEN and released for bounded reference-runtime scope**.
5. **Wave 7 — Durable Lineage & Migration Closure — RELEASED and final-main verified** at exact SHA `78e44da066bd362a2ee935c06ad5902bb0872238`, CI `33350465557`.
6. **Wave 8 — Conformance Exhaustion — RELEASED and final-main verified** at exact SHA `8f0288ee2119a05a83923ae16e0ec56b7cbad1c8`, CI `33367224457`: frozen 68-invariant registry; deterministic property/metamorphic/chaos/differential suites; bounded global-exclusion/composition/resource closure; W01–W06 reference worlds; target-specific X01–X12 mutation falsification; final source-spec coverage reconciliation.
7. **Wave 9 — Production Correctness & Distributed Authority — implementation closure candidate**: bounded destructive production-store compaction; explicit execution capability/cancellation/compensation semantics; bounded CAS/fencing multi-writer authority; v9 snapshot/replay closure; deterministic production-fault and differential runners; target-specific X01–X12 mutation gate; exact coverage ledger below. Release remains conditional on exact release-head/PR/final-main CI.

## Wave 7 final verification surface

Wave 7 is GREEN only for the bounded durable-lineage/migration/replay/compaction scope exercised by repository gates:

- declared strategic runtime objects use canonical sidecars with stable logical identity, immutable revision identity, causal sequence and parent/provenance/debt lineage;
- schema, world-model, environment, canonicalization and semantic-profile regimes are explicit immutable revisions;
- DecisionEpoch and proof/policy/schedulability/action authority bind exact lineage revisions and current semantic regimes;
- semantic drift blocks old authority before dispatch while representation-only compaction preserves an otherwise-current authorization result;
- migration uses exactly six dispositions, forbids silent defaults/debt loss/implicit identity remapping, invalidates authority conservatively and rejects ambiguous external-action migration without verified bridge evidence;
- snapshot v7 persists/verifies lineage, regimes, migration, compaction, replay registry and authority closure; v6 import is deterministic and conservative;
- the replay registry covers every correctness-significant event emitted by the bounded runtime, is sequence-driven and fails closed on unknown correctness-significant events;
- representation-only compaction retains or archives every protected lineage class exercised by the reference runtime and reconstructs the certified semantic root;
- the frozen Wave-7 taxonomy passes `32/32`, and twelve deliberate constitutional mutants are killed;
- exact release SHA `78e44da066bd362a2ee935c06ad5902bb0872238` passed the final `main` Python 3.11/3.12/3.13 matrix in CI run `33350465557`.

## Wave 8 bounded evidence surface

Wave 8 adds falsification depth without widening the product claim beyond evidence:

- the frozen registry contains exactly 68 IDs: P01–P10, M01–M12, C01–C10, D01–D10, X01–X12, W01–W06 and S01–S08;
- seeded property, metamorphic, chaos and differential runners are deterministic and fail by producing explicit counterexamples rather than silently skipping exceptions;
- cancellation after durable dispatch remains `CANCELLATION_PENDING` until exact evidence-bound reconciliation, while pre-dispatch cancellation is terminal;
- relocation preserves `UNLOCATED` and decision-signature ambiguity rather than selecting arbitrary regions;
- repository-owned historical snapshot edges v2 through v6 are imported conservatively into v7 without inventing newer authority layers;
- bounded finite candidate universes support explicit global exclusion while opaque/open universes remain unknown;
- N-way finite-world proof-context composition uses global intersection, not pairwise-only compatibility;
- W01–W06 are correctness fixtures; any timing/benchmark measurements emitted alongside them are research observations only;
- X01–X12 are target-specific constitutional mutants: setup/import/syntax/timeout or non-target failures are invalid kills rather than mutation successes;
- S01–S08 reconcile the final coverage ledger, exact Wave-7 release evidence and bounded claim boundary deterministically;
- exact release SHA `8f0288ee2119a05a83923ae16e0ec56b7cbad1c8` passed the final `main` Python 3.11/3.12/3.13 matrix in CI run `33367224457`.

## Wave 9 bounded evidence surface

The table below is the machine-audited Wave-9 closure surface. A `GREEN` row must name implementation evidence, executable unit/integration evidence, a production-fault/differential/replay oracle, and either a direct constitutional mutant or an explicit statement that the minimum mutation set has no direct mutant for that row.

| Wave 9 invariant | State | Implementation evidence | Unit/integration evidence | Chaos/differential/replay evidence | Mutation evidence |
| --- | --- | --- | --- | --- | --- |
| DC01 | GREEN | `destructive_compaction.py` retention closure | `test_wave9_destructive_compaction.py` | `wave9_chaos.py` compaction frontier + `wave9_differential.py` | `X04` active-lineage deletion |
| DC02 | GREEN | `destructive_compaction.py` dormant/resurrection retention | `test_wave9_destructive_compaction.py` | `wave9_chaos.py` compaction frontier + `test_wave9_replay_restart.py` | N/A — no direct minimum mutant; retention frontier is directly tested |
| DC03 | GREEN | `destructive_compaction.py` proof/evidence/debt/fallback retention | `test_wave9_destructive_compaction.py` | `wave9_chaos.py` compaction frontier + `test_wave9_replay_restart.py` | N/A — no direct minimum mutant; retention frontier is directly tested |
| DC04 | GREEN | `destructive_compaction.py` shadow semantic-root verification | `test_wave9_destructive_compaction.py` | `wave9_differential.py` pre/post compaction relation | N/A — no direct minimum mutant; semantic equivalence is differential-tested |
| DC05 | GREEN | `destructive_compaction.py` switch receipt + `production_store.py` CAS | `test_wave9_destructive_compaction.py` | `wave9_chaos.py` switch fault schedules | N/A — CAS semantics are mutation-covered by `X03` on shared storage primitive |
| DC06 | GREEN | `destructive_compaction.py` separate SWITCH_COMMITTED/SOURCE_RETIRED phases | `test_wave9_destructive_compaction.py` | `wave9_chaos.py` pre/post switch crash schedules | `X05` source deletion before switch durability |
| DC07 | GREEN | `destructive_compaction.py` durable phase machine | `test_wave9_destructive_compaction.py` | `CH-DC07-CRASH-BEFORE-SWITCH` | N/A — deterministic crash oracle is the direct falsifier |
| DC08 | GREEN | `destructive_compaction.py` recovery pointer coherence | `test_wave9_destructive_compaction.py` | `CH-DC08-CRASH-AFTER-SWITCH` | `X06` mixed-representation recovery |
| DC09 | GREEN | `destructive_compaction.py` exact retirement manifest/idempotence | `test_wave9_destructive_compaction.py` | `wave9_chaos.py` compaction frontier | N/A — no direct minimum mutant; exact manifest/idempotence has direct tests |
| DC10 | GREEN | `destructive_compaction.py` manifest digest validation | `test_wave9_destructive_compaction.py` | `test_wave9_replay_restart.py` tamper/reopen path | N/A — no direct minimum mutant; tamper oracle is direct |
| DC11 | GREEN | `production_store.py` epoch fencing + compaction retire CAS | `test_wave9_destructive_compaction.py` | `CH-DC11-STALE-RETIRE` | `X02` stale-writer primitive on shared storage fence |
| DC12 | GREEN | `destructive_compaction_runtime.py` + `wave9_snapshot.py` | `test_wave9_replay_restart.py` | `DF-DESTRUCTIVE-COMPACTION` + live/reopen replay | N/A — differential/replay equivalence is the direct falsifier |
| EX01 | GREEN | `execution_contract.py` revision/digest-bound contract | `test_wave9_execution_contract.py` | `test_wave9_replay_restart.py` execution sidecar restore | N/A — no direct minimum mutant; exact binding has direct tests |
| EX02 | GREEN | `execution_contract_runtime.py` current-contract check | `test_wave9_execution_contract.py` | `test_wave9_replay_restart.py` | N/A — no direct minimum mutant; adapter-revision drift has direct tests |
| EX03 | GREEN | `execution_contract.py` exact cancellation acknowledgement binding | `test_wave9_execution_contract.py` | `wave9_chaos.py` cancellation frontier | N/A — EX11 mutant shares exact acknowledgement validation path |
| EX04 | GREEN | `execution_contract.py` cancellation-class gate | `test_wave9_execution_contract.py` | `CH-EX04-BEST-EFFORT-AMBIGUITY` | `X07` best-effort cancellation falsely clean |
| EX05 | GREEN | `execution_contract.py` fenced-effect stale-effect exclusion | `test_wave9_execution_contract.py` | `wave9_chaos.py` execution frontier | N/A — fenced-effect evidence has a direct negative/positive test |
| EX06 | GREEN | `execution_contract_runtime.py` reconciliation-required ambiguity | `test_wave9_execution_contract.py` + transaction tests | `test_wave9_replay_restart.py` ambiguity persistence | N/A — no direct minimum mutant; retry-blocking state is integration-tested |
| EX07 | GREEN | `execution_contract.py` distinct compensation record/effect | `test_wave9_execution_contract.py` | `test_wave9_replay_restart.py` execution state restore | N/A — no direct minimum mutant; distinct transaction identity has direct tests |
| EX08 | GREEN | `execution_contract.py` compensation transition preserves original outcome | `test_wave9_execution_contract.py` | `test_wave9_replay_restart.py` | `X09` compensation erases original applied outcome |
| EX09 | GREEN | `execution_contract_runtime.py` adapter revision freshness | `test_wave9_execution_contract.py` | `test_wave9_replay_restart.py` | N/A — adapter revision drift is directly tested |
| EX10 | GREEN | `wave9_snapshot.py` execution/cancellation/compensation sidecars | `test_wave9_replay_restart.py` | live/reopen and suffix replay paths | N/A — restart equivalence is the direct falsifier |
| EX11 | GREEN | `execution_contract.py` authority-epoch acknowledgement check | `test_wave9_execution_contract.py` | `CH-EX11-WRONG-EPOCH-ACK` | `X08` wrong-epoch cancellation acknowledgement |
| EX12 | GREEN | `execution_contract.py` explicit UNSUPPORTED cancellation class | `test_wave9_execution_contract.py` | `CH-EX12-UNSUPPORTED-CANCEL` | N/A — unsupported capability has direct chaos/test rejection |
| MW01 | GREEN | `production_store.py` immediate-predecessor epoch rule | `test_wave9_multiwriter.py` | `wave9_chaos.py` epoch takeover | `X01` epoch monotonicity bypass |
| MW02 | GREEN | `production_store.py` current-epoch fence | `test_wave9_multiwriter.py` | `CH-MW02-EPOCH-TAKEOVER` | `X02` stale-writer authoritative commit |
| MW03 | GREEN | `production_store.py` exact revision CAS | `test_wave9_multiwriter.py` | `CH-MW03-CAS-RACE` | `X03` CAS replaced by last-writer-wins |
| MW04 | GREEN | `multiwriter.py` idempotency semantic convergence | `test_wave9_multiwriter.py` | `CH-MW04-IDEMPOTENT-DUPLICATE` | N/A — duplicate convergence has direct deterministic chaos oracle |
| MW05 | GREEN | `multiwriter.py` explicit conflict/reconciliation record | `test_wave9_multiwriter.py` | `CH-MW05-NONIDEMPOTENT-CONFLICT` | N/A — non-idempotent conflict has direct deterministic chaos oracle |
| MW06 | GREEN | `multiwriter.py` lease-expiry ambiguity assessment | `test_wave9_multiwriter.py` | `CH-MW06-LEASE-EXPIRY` | N/A — lease-expiry ambiguity has direct chaos oracle |
| MW07 | GREEN | `production_store.py` + `multiwriter.py` writer identity digests | `test_wave9_multiwriter.py` | `wave9_chaos.py` multi-writer frontier | N/A — writer/receipt digest binding has direct tests |
| MW08 | GREEN | `multiwriter_runtime.py` + `wave9_snapshot.py` epoch sidecars | `test_wave9_replay_restart.py` | `DF-LIVE-REOPEN` | N/A — restart equivalence is the direct falsifier |
| MW09 | GREEN | `multiwriter_runtime.py` replay reducers + `wave9_snapshot.py` | `test_wave9_replay_restart.py` | `DF-LIVE-SUFFIX-REPLAY` | `X12` unknown Wave-9 replay event fail-closed guards replay authority |
| MW10 | GREEN | `production_store.py` CAS/fencing canonical-successor rule | `test_wave9_multiwriter.py` | `CH-MW03-CAS-RACE` + split-brain projection | `X03` CAS last-writer-wins |
| MW11 | GREEN | `production_store.py` capability proof + `multiwriter.py` constructor gate | `test_wave9_multiwriter.py` | `CH-MW11-UNSUPPORTED-BACKEND` | `X10` unsupported backend promoted to strong multi-writer |
| MW12 | GREEN | `multiwriter_runtime.py` authorization-epoch freshness check | Wave-9 authority integration tests + `test_wave9_replay_restart.py` | epoch takeover + replay/reopen frontier | `X11` old-epoch authorization resurrection |

## Remaining normative engineering surface

Wave 9 deliberately stops at the bounded production-store protocol defined by its design. It does **not** promote generalized open/opaque candidate-universe minimality, generalized proof-context theories, arbitrary external/historical schema migration pairs, generic distributed consensus/replication, generic two-phase commit, arbitrary storage-engine compaction, generic identity/scheduler/messaging platforms, or benchmark superiority to GREEN. Those remain explicit partial scopes, research measurement or product boundaries. No Wave 10+ objective is part of the Wave-9 release closure.

## Claim boundary

`GREEN` means a tested reference implementation for the stated bounded scope. It does not mean formal proof, arbitrary distributed consensus, universal optimality or empirical superiority. Wave 8 / `0.8.0a1` is final-main verified. Wave 9 / `0.9.0a1` remains an unreleased candidate until the exact Wave-9 release head, PR synthetic merge and final `main` each reproduce the mandatory Python 3.11/3.12/3.13 and Wave-2-through-Wave-9 gate surface.
