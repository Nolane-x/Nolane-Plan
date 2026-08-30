# Nolane Plan v0.15 Implementation Coverage Ledger

This ledger tracks the strongest normative runtime contracts in `NOLANE-PLAN-RUNTIME-ARCHITECTURE-V0.15-PRINCIPAL-SCOPED-MULTI-AGENT-CLOSURE-SPEC.md` against the reference implementation. It deliberately separates **implemented semantics**, **partial reference semantics**, **planned closure**, and **research/non-goal claims**.

Legend: `GREEN` = on a tested correctness path for the stated bounded scope; `GREEN/PARTIAL` = a strong bounded primitive exists but a wider spec surface remains open; `PARTIAL` = primitive exists but the complete contract is not yet closed; `MISSING` = not implemented; `BOUNDARY` = explicitly outside the v0.15 reference-runtime goal.

| Spec surface | Current state | Closure wave |
|---|---|---|
| Mission revision / anti-goals / hard constraints | GREEN | existing |
| Canonical state outranks plan narrative | GREEN | existing |
| `NULL_WORLD` / residual unknown-world representation | GREEN | existing |
| Future families, bounded factorized compiler | GREEN/PARTIAL — bounded family lattice remains implemented; broader lineage remains | existing/W7 |
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
| Authority-time dependency freshness | GREEN | W2/W4 |
| `ProofInputEnvelopeRevision` | GREEN | W4 |
| Dependency-capture assurance / hidden-read defense | GREEN | W4 |
| `ProofDependencyManifestRevision` | GREEN | W4 |
| Query-domain membership/result-sensitivity revision for absence/universal claims | GREEN | W4 |
| SupportAlternativeSet / conjunctive clauses / grounded support | GREEN | W4 |
| Blocking-invalidity vs positive-support distinction | GREEN | W4 |
| Semantic closure barrier (source mutation + generation advance) | GREEN | W4 |
| Replay-derived proof support/freshness reconstruction | GREEN for Wave-4 proof lineage / PARTIAL globally | W4/W7 |
| `DecisionEpoch` principal/access/partition/action-space/temporal binding | GREEN | W5 |
| Direct `DecisionEpoch` binding to every causal/policy lineage dimension | PARTIAL | W7 |
| Reveal events / principal-relative observation frontier | GREEN | W5 |
| Principal-relative non-anticipativity checking | GREEN | W5 |
| `PolicyNodeRevision` contingent policy graph | GREEN | W5 |
| Policy-level branch/resource coherence | GREEN | W5 |
| Frozen `SelectionTransaction` / advisory `SelectionRecord` | GREEN | W5 |
| Selection hard-veto monotonicity and dependency freshness | GREEN | W5 |
| `DecisionSufficiencyCertificate` exact action-local closure | GREEN | W5 |
| Generalized global minimality/exclusion proof beyond declared closure | PARTIAL | W7/W8 |
| PlanSeal / immutable proof-bearing decision seal | GREEN | W5 |
| Monotonic seal invalidation / no revival | GREEN | W5 |
| N-way proof-context composition | GREEN for bounded finite-world theory / PARTIAL generally | W5/W7 |
| Recursive decision-recall certificate | GREEN for bounded signature horizon | W5 |
| Policy outcome totality / residual-handler certificate | GREEN for bounded explicit outcomes | W5 |
| Transition/observation-model adequacy distinct from modeled-support totality | GREEN for bounded explicit residual model | W6 |
| Parent→child policy-edge stitch certificate | GREEN for explicit refinement contracts | W5 |
| Decision reaction envelope and IA0–IA4 classification | GREEN for bounded single-route timing | W5 |
| Canonical control-plane resource revisions | GREEN | W6 |
| Reaction resource-demand/job contracts | GREEN | W6 |
| Joint control-plane schedulability certificate | GREEN for bounded deterministic/scenario analysis | W6 |
| Coexistence/mutual-exclusion aware joint reaction analysis | GREEN | W6 |
| Resource/regime freshness of schedulability authority | GREEN | W6 |
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
| Proof-carrying `ActionAuthorization` bundle | GREEN for sealed-policy path | W4/W5 |
| Sealed-policy authority recheck under exact kernel writer lock | GREEN | W5 |
| Wave-6 schedulability/liveness prerequisites under exact kernel writer | GREEN | W6 |
| Wave-6 objects cannot mint independent authorization/dispatch authority | GREEN | W6 |
| SharedCommitment exclusive-resource conflict | GREEN | existing + W5 |
| Resource/capacity feasibility beyond simple exclusive overlap | GREEN for declared control-plane resource model / PARTIAL generally | W6/W7 |
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
| Dispatch fence contract / cancellation residual race semantics | PARTIAL | W7 |
| Strategic relocation `LOCATED/AMBIGUOUS/UNLOCATED` | GREEN/PARTIAL | existing/W7 |
| Completion verifier bound to current mission/cut/freshness | GREEN | existing/W2 |
| Immutable lineage fields across all strategic objects | PARTIAL | W7 |
| Schema/world-model/environment-regime versioning | PARTIAL | W7 |
| Snapshot/journal integrity and prefix binding | GREEN | W2 |
| Trust-bearing snapshot/replay semantics | GREEN | W3 |
| Proof-bearing snapshot/replay semantics | GREEN | W4 |
| Policy-bearing snapshot/replay semantics | GREEN | W5 |
| Wave-6 resource/schedulability/liveness/stability snapshot/replay semantics | GREEN | W6 |
| Wave-6 internal canonical-digest verification | GREEN | W6 |
| Historical Wave-6 revisions separated from current logical pointers | GREEN | W6 |
| Bounded v5→v6 migration with empty Wave-6 state | GREEN | W6 |
| Stale Wave-6 resource state cannot resurrect old certificate on restart | GREEN | W6 |
| Full semantic replay coverage for every strategic object/event | PARTIAL | W7 |
| General migration contracts across all schema versions | PARTIAL | W7 |
| Graph compaction lineage | MISSING | W7 |
| PG01-PG40 registry | GREEN | existing |
| I-65..I-72 v0.6 schedulability/liveness invariants | GREEN for bounded reference-runtime scope | W6 |
| I-245..I-260 principal-scoped closure | GREEN/PARTIAL — tested principal scope; wider durable lineage remains | W3-W7 |
| v0.14 projection collision oracle `108 -> 0` | GREEN | existing |
| Wave-2 adversarial conformance | GREEN — 10/10 | W2 |
| Wave-3 adversarial conformance + constitutional mutations | GREEN — 12/12 + 4/4 | W3 |
| Wave-4 adversarial conformance + constitutional mutations | GREEN — 14/14 + 7/7 | W4 |
| Wave-5 adversarial conformance + constitutional mutations | GREEN — 29/29 + 13/13 | W5 |
| Wave-6 exact failure-taxonomy conformance + constitutional mutations | GREEN — 43/43 + 12/12 | W6 |
| Python 3.11/3.12/3.13 Wave-6 matrix | GREEN on pre-release gate — 334 tests + all gates | W6 |
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
4. **Wave 6 — Schedulability/Liveness & Future-Temporal-Resource Closure — GREEN for bounded reference-runtime scope pending exact release/main integration**: joint control-plane schedulability, protected reaction capacity, repeated handoff liveness, activation-time edge stability, modeled-totality/adequacy separation, option independence, dormant-branch resurrection, kernel authority integration, snapshot-v6 replay/migration, 43-case taxonomy oracle and 12-mutation constitutional gate.
5. **Wave 7 — Durable Lineage & Migration Closure — NEXT**: common immutable lineage schema, environment/world/schema versions, full replay reducers, generalized migrations and compaction lineage.
6. **Wave 8 — Conformance Exhaustion**: property/metamorphic/chaos/differential tests, broader constitutional mutation coverage, benchmark worlds and final spec-to-code audit.

## Wave 6 verification surface

Wave 6 is GREEN only for the bounded schedulability/liveness/future-temporal-resource scope exercised by repository gates:

- local reaction feasibility does not imply a joint guarantee; concurrently reachable jobs are checked against declared shared resource capacity;
- mutually exclusive jobs can be excluded from simultaneous demand only when coexistence semantics are known; UNKNOWN remains explicit debt;
- resource identity includes revision/regime/capacity semantics and certificate reuse binds exact current job/resource digests;
- verifier/model/rate-limit/human/kernel-writer contracts can be finite control-plane resources rather than hidden unlimited infrastructure;
- deadline-critical planning capacity is protected from speculative work and oversubscription fails closed;
- repeated `SAFE_HANDOFF` is bounded by handoff count, total deferral, ordinary/recovery stutter, recursive feasibility, information timing and a grounded absolute refinement deadline;
- semantic renaming/equivalent debt does not create progress, and executable-horizon advance is suppressed when critical debt or synthesis workload regresses;
- edge activation rechecks mutable generations, permissions, reservations/locks, external writer assumptions and open side effects; opacity remains UNKNOWN;
- modeled-support totality is reported separately from transition/observation-model adequacy and residual/open-world closure;
- OR/K-of-N robustness requires a declared failure-set-relative independence certificate and co-activation feasibility; shared credentials/network/evidence/control dependencies collapse robust uplift;
- dormant protected futures are not probability-pruned and resurrection requires current revalidation of all declared semantic lineage dimensions;
- `authorize_schedulable_policy(...)` runs under the canonical writer and delegates through Wave-5 sealed-policy authority, preserving proof and identity lineage;
- snapshot schema v6 canonically persists/replays Wave-6 state, verifies internal digests, keeps historical revisions distinct from current pointers, migrates v5 with empty Wave-6 state and fails closed on unknown correctness-significant suffix events;
- the exact v0.6 failure taxonomy passes `43/43`; twelve deliberate constitutional mutants are killed;
- the pre-release matrix passes 334 unit/integration tests, compile, the original `108 -> 0` oracle, all Wave 2–6 conformance/mutation gates and the end-to-end demo on Python 3.11, 3.12 and 3.13.

## Remaining normative engineering surface

Wave 6 intentionally does **not** promote the following to GREEN:

- one common immutable lineage schema across every strategic object;
- complete environment/world-model/schema/profile versioning across all objects;
- semantic replay reducers for every correctness-significant object/event in the full architecture;
- generalized migration contracts across every historical schema pair;
- graph-compaction lineage and proofs that compaction preserves authority semantics;
- global minimality/exclusion beyond the currently declared bounded closure;
- generalized proof-context composition outside implemented bounded theories;
- property/metamorphic/chaos/differential exhaustion and benchmark-world evidence.

## Claim boundary

`GREEN` means a tested reference implementation for the stated bounded scope. It does not mean formal proof, production hardening, distributed multi-writer safety or empirical superiority. A final claim of full **reference-runtime normative coverage** remains unavailable until the remaining Wave 7/8 `PARTIAL`/`MISSING` surfaces are either implemented and verified or explicitly classified as a spec-supported research/non-goal boundary.
