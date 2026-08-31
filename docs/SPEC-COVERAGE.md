# Nolane Plan v0.15 Implementation Coverage Ledger

This ledger tracks the strongest normative runtime contracts in `NOLANE-PLAN-RUNTIME-ARCHITECTURE-V0.15-PRINCIPAL-SCOPED-MULTI-AGENT-CLOSURE-SPEC.md` against the reference implementation. It deliberately separates **implemented semantics**, **partial reference semantics**, **planned closure**, and **research/non-goal claims**.

Legend: `GREEN` = on a tested correctness path for the stated bounded scope; `GREEN/PARTIAL` = a strong bounded primitive exists but a wider spec surface remains open; `PARTIAL` = primitive exists but the complete contract is not yet closed; `MISSING` = not implemented; `BOUNDARY` = explicitly outside the v0.15 reference-runtime goal.

| Spec surface | Current state | Closure wave |
|---|---|---|
| Mission revision / anti-goals / hard constraints | GREEN | existing |
| Canonical state outranks plan narrative | GREEN | existing |
| `NULL_WORLD` / residual unknown-world representation | GREEN | existing |
| Future families, bounded factorized compiler | GREEN — declared runtime families now also carry immutable Wave-7 lineage | existing/W7 |
| Decision-relevant convergence guards | GREEN/PARTIAL | existing/W7 |
| Condition-centric Strategic Obligations | GREEN | existing |
| Evidence polarity, revocation, common-lineage independence | GREEN | existing |
| Principal-scoped access profiles and information partitions | GREEN | existing + W5 |
| Decision Capsule recipient/partition/access binding | GREEN | existing |
| Capsule hydration anti-escalation | GREEN | existing |
| Exact acting-principal authorization and presented-principal match | GREEN | existing |
| Canonical host/platform principal identity binding | GREEN | W3 |
| Principal identity provenance across restart/replay | GREEN | W3 |
| Inter-principal planning-relevant delivery/observation evidence | GREEN | W3 |
| Dispatch-time principal attestation object | GREEN | W3 |
| Executing-principal reconciliation evidence | GREEN | W3 |
| `DecisionCutRevision` causal/knowledge frontier | GREEN | W2 |
| Knowledge-time / no retroactive artifact injection | GREEN | W2/W3 |
| Authority-time dependency freshness | GREEN | W2/W4/W7 |
| `ProofInputEnvelopeRevision` | GREEN | W4 |
| Dependency-capture assurance / hidden-read defense | GREEN | W4 |
| `ProofDependencyManifestRevision` | GREEN | W4 |
| Query-domain membership/result-sensitivity revision for absence/universal claims | GREEN | W4 |
| SupportAlternativeSet / conjunctive clauses / grounded support | GREEN | W4 |
| Blocking-invalidity vs positive-support distinction | GREEN | W4 |
| Semantic closure barrier (source mutation + generation advance) | GREEN | W4 |
| Replay-derived proof support/freshness reconstruction | GREEN for every declared Wave-4/Wave-7 runtime replay path; broader architecture remains bounded | W4/W7 |
| `DecisionEpoch` principal/access/partition/action-space/temporal binding | GREEN | W5 |
| Direct `DecisionEpoch` binding to mission/canonical/location/information/semantic-regime lineage | GREEN for declared runtime sidecar | W7 |
| Reveal events / principal-relative observation frontier | GREEN | W5 |
| Principal-relative non-anticipativity checking | GREEN | W5 |
| `PolicyNodeRevision` contingent policy graph | GREEN | W5 |
| Policy-level branch/resource coherence | GREEN | W5 |
| Frozen `SelectionTransaction` / advisory `SelectionRecord` | GREEN | W5 |
| Selection hard-veto monotonicity and dependency freshness | GREEN | W5 |
| `DecisionSufficiencyCertificate` exact action-local closure | GREEN | W5 |
| Generalized global minimality/exclusion proof beyond declared closure | PARTIAL | W8 |
| PlanSeal / immutable proof-bearing decision seal | GREEN | W5 |
| Monotonic seal invalidation / no revival | GREEN | W5 |
| N-way proof-context composition | GREEN for bounded finite-world theory / PARTIAL generally | W5/W8 |
| Recursive decision-recall certificate | GREEN for bounded signature horizon | W5 |
| Policy outcome totality / residual-handler certificate | GREEN for bounded explicit outcomes | W5 |
| Transition/observation-model adequacy distinct from modeled-support totality | GREEN for bounded explicit residual model | W6 |
| Parent→child policy-edge stitch certificate | GREEN for explicit refinement contracts | W5 |
| Decision reaction envelope and IA0–IA4 classification | GREEN for bounded single-route timing | W5 |
| Canonical control-plane resource revisions | GREEN | W6 |
| Reaction resource-demand/job contracts | GREEN | W6 |
| Joint control-plane schedulability certificate | GREEN for bounded deterministic/scenario analysis | W6 |
| Coexistence/mutual-exclusion aware joint reaction analysis | GREEN | W6 |
| Resource/regime freshness of schedulability authority | GREEN | W6/W7 |
| Human approval / kernel-writer / rate-limit resources in reaction feasibility | GREEN for declared resource contracts | W6 |
| Structure-aware preparedness aggregation | GREEN for bounded structures | W5/W6 |
| Failure-set-relative option independence / common-mode resistance | GREEN | W6 |
| Nominal vs robust-independent preparedness reporting | GREEN | W6 |
| Information-capability preservation / self-induced blindness check | GREEN | W5 |
| Continuation contract / terminal semantics / horizon cap | GREEN | W5 |
| Repeated handoff liveness certificate | GREEN | W6 |
| Grounded handoff deadline revision | GREEN | W6 |
| Bounded ordinary/recovery stutter and deferral budgets | GREEN | W6 |
| Handoff progress rank rejects semantic/debt churn | GREEN | W6 |
| Horizon advance cannot launder critical-debt/workload regression | GREEN | W6 |
| Recursive feasibility and information-by-deadline requirement for `SAFE_HANDOFF` | GREEN for bounded certificate inputs | W6 |
| Activation-time edge stability contract | GREEN | W6 |
| Mutable generation/permission/reservation/writer refresh at child activation | GREEN | W6 |
| Open asynchronous parent effect blocks child activation until resolved | GREEN | W6 |
| Edge opacity remains UNKNOWN rather than assumed stable | GREEN | W6 |
| Exact-scope policy executability `EXEC_*` assessment | GREEN | W5 |
| Proof-carrying `ActionAuthorization` bundle | GREEN for sealed-policy path | W4/W5/W7 |
| Sealed-policy authority recheck under exact kernel writer lock | GREEN | W5/W7 |
| Wave-6 schedulability/liveness prerequisites under exact kernel writer | GREEN | W6/W7 |
| Exact proof/policy/schedulability/action semantic lineage bound into authorization | GREEN for declared authority pipeline | W7 |
| Wave-6 objects cannot mint independent authorization/dispatch authority | GREEN | W6 |
| SharedCommitment exclusive-resource conflict | GREEN | existing + W5 |
| Resource/capacity feasibility beyond simple exclusive overlap | GREEN for declared control-plane resource model / PARTIAL generally | W6/W8 |
| Protected deadline-critical planning capacity | GREEN | W6 |
| Multiple required protections fail closed on oversubscription | GREEN | W6 |
| Safe pruning / dormant branch / resurrection | GREEN for revisioned bounded revalidation | W6 |
| Probability-only catastrophic/sole-route/unique-hedge/information-rich pruning prohibition | GREEN for declared protected classes | W6 |
| Resurrection requires mission/evidence/transition/temporal/resource/capability/authority/risk revalidation | GREEN | W6 |
| Planning budget mandatory-work preservation | GREEN | existing/W6 |
| Action lifecycle postcondition-before-commit | GREEN | existing |
| Durable dispatch-before-side-effect linearization | GREEN | W2/W3 |
| Unknown non-idempotent outcome -> evidence-bound reconciliation | GREEN | W2/W3 |
| Adapter capability revision binding | GREEN | W2 |
| Dispatch fence contract / cancellation residual race semantics | PARTIAL | W8 |
| Strategic relocation `LOCATED/AMBIGUOUS/UNLOCATED` | GREEN/PARTIAL | existing/W8 |
| Completion verifier bound to current mission/cut/freshness | GREEN | existing/W2 |
| Common immutable lineage schema for declared strategic runtime families | GREEN | W7 |
| Immutable historical revision identity / parent DAG / no-rebind semantics | GREEN | W7 |
| Schema/world-model/environment/canonicalization/semantic-profile regime versioning | GREEN for explicit bounded runtime regimes | W7 |
| Snapshot/journal integrity and prefix binding | GREEN | W2 |
| Trust-bearing snapshot/replay semantics | GREEN | W3 |
| Proof-bearing snapshot/replay semantics | GREEN | W4 |
| Policy-bearing snapshot/replay semantics | GREEN | W5 |
| Wave-6 resource/schedulability/liveness/stability snapshot/replay semantics | GREEN | W6 |
| Wave-6 internal canonical-digest verification | GREEN | W6 |
| Historical Wave-6 revisions separated from current logical pointers | GREEN | W6 |
| Bounded v5→v6 migration with empty Wave-6 state | GREEN | W6 |
| Stale Wave-6 resource state cannot resurrect old certificate on restart | GREEN | W6 |
| Snapshot v7 persists lineage/regimes/migration/compaction/replay registry and authority closure | GREEN | W7 |
| Conservative deterministic v6→v7 import without invented strong ancestry | GREEN | W7 |
| Replay coverage for every correctness-significant event emitted by the bounded runtime | GREEN | W7 |
| Unknown correctness-significant replay event fails closed | GREEN | W7 |
| Same supported snapshot+journal produces same bounded canonical semantic digest | GREEN | W7 |
| Typed semantic migration with exact six dispositions and explicit debt/identity mappings | GREEN for bounded migration contract | W7 |
| General migration contracts across every historical schema/version pair | PARTIAL | W8 |
| Migration cannot silently preserve authority or reinterpret ambiguous external effects | GREEN for declared runtime migration path | W7 |
| Reversible representation-only graph compaction with read-only archive/reconstruction | GREEN for bounded reference runtime | W7 |
| Compaction retains active authority, dormant/resurrection, proof/evidence/debt and unique-fallback lineage | GREEN | W7 |
| Production physical history deletion/general storage-engine compaction | BOUNDARY/PARTIAL — reference runtime intentionally archives instead of proving arbitrary destructive storage rewrites | W8/non-goal review |
| PG01-PG40 registry | GREEN | existing |
| I-65..I-72 v0.6 schedulability/liveness invariants | GREEN for bounded reference-runtime scope | W6 |
| I-245..I-260 principal-scoped closure | GREEN for declared principal/authority lineage paths / PARTIAL wider architectural exhaustion | W3-W8 |
| v0.14 projection collision oracle `108 -> 0` | GREEN | existing |
| Wave-2 adversarial conformance | GREEN — 10/10 | W2 |
| Wave-3 adversarial conformance + constitutional mutations | GREEN — 12/12 + 4/4 | W3 |
| Wave-4 adversarial conformance + constitutional mutations | GREEN — 14/14 + 7/7 | W4 |
| Wave-5 adversarial conformance + constitutional mutations | GREEN — 29/29 + 13/13 | W5 |
| Wave-6 exact failure-taxonomy conformance + constitutional mutations | GREEN — 43/43 + 12/12 | W6 |
| Wave-7 durable-lineage/migration/replay/compaction conformance + constitutional mutations | GREEN — 32/32 + 12/12 | W7 |
| Python 3.11/3.12/3.13 Wave-7 pre-release matrix | GREEN — 408 tests + compile/oracle/Wave2–7 gates/demo at Task-8 exact head | W7 |
| Property/metamorphic/chaos/differential conformance | PARTIAL | W8 |
| Real benchmark worlds / empirical superiority | RESEARCH | W8 measurement only |
| Distributed correctness writers / consensus | BOUNDARY | not v0.15 |
| Generic identity provider | BOUNDARY | not v0.15 |
| Generic scheduler/orchestrator product | BOUNDARY | not v0.15 |
| Generic messaging/task marketplace/orchestration platform | BOUNDARY | not v0.15 |

## Exhaustion order

1. **Wave 3 — External Trust Anchor Closure — GREEN for reference-runtime scope**: canonical principal attestations, communication receipts, dispatch attestation, reconciliation evidence, trust snapshot/replay/freshness integration.
2. **Wave 4 — Proof Dependency & Support Closure — GREEN for reference-runtime scope**: proof input envelopes, capture assurance, query membership/result-sensitivity revisions, proof dependency manifests, bounded-DNF support alternatives, blocking-invalidity separation, semantic closure barrier, proof-carrying kernel authority, proof snapshot/replay and adversarial/mutation gates.
3. **Wave 5 — Executable Policy Closure — GREEN for bounded reference-runtime scope**: principal-relative decision information, contingent policy IR, frozen advisory selection, decision sufficiency, PlanSeal, recursive recall, totality, edge stitching, reaction/readiness, information capability, continuation, exact-scope executability, sealed-policy kernel authority, snapshot-v5 replay and adversarial/mutation gates.
4. **Wave 6 — Schedulability/Liveness & Future-Temporal-Resource Closure — GREEN and released for bounded reference-runtime scope**: joint control-plane schedulability, protected reaction capacity, repeated handoff liveness, activation-time edge stability, modeled-totality/adequacy separation, option independence, dormant-branch resurrection, kernel authority integration, snapshot-v6 replay/migration, 43-case taxonomy oracle and 12-mutation constitutional gate.
5. **Wave 7 — Durable Lineage & Migration Closure — implementation GREEN, release integration in progress**: common immutable lineage, typed semantic regimes, explicit authority lineage, frozen replay registry/base reducers, snapshot-v7/conservative-v6 import, six-disposition migration, reversible compaction, 32-case adversarial taxonomy and 12 constitutional mutants.
6. **Wave 8 — Conformance Exhaustion — NEXT after Wave-7 release/main verification**: property/metamorphic/chaos/differential tests, broader constitutional mutation coverage, benchmark worlds and final source-spec coverage reconciliation.

## Wave 7 verification surface

Wave 7 is GREEN only for the bounded durable-lineage/migration/replay/compaction scope exercised by repository gates:

- canonical sidecars give declared runtime strategic objects stable logical identity, immutable revision identity, causal writer sequence, parent/provenance/debt lineage and deterministic semantic digests;
- schema, world-model, environment, canonicalization and semantic-profile regimes are explicit immutable revisions and authority binds their exact current revisions;
- DecisionEpoch sidecars and proof/policy/schedulability/action authority closure bind exact lineage revisions rather than logical IDs alone;
- semantic-regime or bound artifact drift blocks old authority before dispatch, while representation-only compaction does not spuriously invalidate an equivalent authorization;
- migration uses the exact six dispositions, forbids silent defaults/debt loss/implicit identity remapping, conservatively invalidates authority and rejects ambiguous external-action migration without verified bridge evidence;
- snapshot v7 persists and verifies lineage, regimes, migration, compaction, replay-registry and authority-closure state; v6 import is deterministic and marks authority recheck-required when exact ancestry is unavailable;
- the replay registry covers every `_record(...)` event emitted by the bounded runtime, delegates existing Wave 3–6 reducers, reconstructs missing base events, uses journal sequence rather than wall time and fails closed on unknown correctness-significant events;
- representation-only compaction retains or archives all canonical lineage needed by active authority, dormant resurrection, proof/evidence/debt and unique fallback semantics, and reconstruction reproduces the certified source semantic root;
- the frozen Wave-7 taxonomy passes `32/32`, and twelve deliberate constitutional mutants are killed target-specifically;
- Task-8 exact head `5f58455d3161ed08cefcde7407e086279c8582ff` passed 408 unit/integration tests, compile, the `108 -> 0` oracle, Wave 2–7 conformance/mutation gates and the end-to-end demo on Python 3.11, 3.12 and 3.13 in CI run `33343969251`.

## Remaining normative engineering surface

Wave 7 intentionally does **not** promote the following to global/full-architecture GREEN:

- generalized global minimality/exclusion beyond the currently declared bounded closure;
- generalized proof-context composition outside implemented bounded theories;
- every hypothetical or historical schema-to-schema migration pair;
- arbitrary destructive physical compaction across production storage engines;
- distributed/multi-writer consensus semantics;
- property/metamorphic/chaos/differential exhaustion;
- benchmark-world or empirical planning-superiority claims;
- final source-spec coverage reconciliation across all remaining PARTIAL rows.

Those remaining surfaces belong to Wave 8, explicit research measurement, or the stated product boundaries.

## Claim boundary

`GREEN` means a tested reference implementation for the stated bounded scope. It does not mean formal proof, production hardening, distributed multi-writer safety or empirical superiority. Before the Wave-7 release commit, PR synthetic-merge and final `main` evidence are complete, the strongest valid Wave-7 statement is: **implementation GREEN for the bounded durable-lineage/migration/replay/compaction reference-runtime scope; release integration still pending**.
