# Nolane Plan v0.15 Implementation Coverage Ledger

This ledger tracks the strongest normative runtime contracts in `NOLANE-PLAN-RUNTIME-ARCHITECTURE-V0.15-PRINCIPAL-SCOPED-MULTI-AGENT-CLOSURE-SPEC.md` against the reference implementation. It deliberately separates **implemented semantics**, **partial reference semantics**, **planned closure**, and **research/non-goal claims**.

Legend: `GREEN` = on a tested correctness path for the stated bounded scope; `GREEN/PARTIAL` = a strong bounded primitive exists but a wider spec surface remains open; `PARTIAL` = primitive exists but the complete contract is not yet closed; `MISSING` = not implemented; `BOUNDARY` = explicitly outside the v0.15 reference-runtime goal.

| Spec surface | Current state | Closure wave |
|---|---|---|
| Mission revision / anti-goals / hard constraints | GREEN | existing |
| Canonical state outranks plan narrative | GREEN | existing |
| `NULL_WORLD` / residual unknown-world representation | GREEN | existing |
| Future families, bounded factorized compiler | GREEN/PARTIAL | W6 deeper policy integration |
| Decision-relevant convergence guards | GREEN/PARTIAL | W6 |
| Condition-centric Strategic Obligations | GREEN | existing |
| Evidence polarity, revocation, common-lineage independence | GREEN | existing |
| Principal-scoped access profiles and information partitions | GREEN | existing + W5 policy partition |
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
| Direct `DecisionEpoch` binding to every causal/policy lineage dimension | PARTIAL | W6/W7 |
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
| N-way proof-context composition | GREEN for bounded finite-world theory / PARTIAL generally | W5/W6 |
| Recursive decision-recall certificate | GREEN for bounded signature horizon | W5 |
| Policy outcome totality / residual-handler certificate | GREEN for bounded explicit outcomes | W5 |
| Parent→child policy-edge stitch certificate | GREEN for explicit refinement contracts | W5 |
| Decision reaction envelope and IA0–IA4 classification | GREEN for bounded single-route timing | W5 |
| Joint control-plane schedulability certificate | MISSING | W6 |
| Structure-aware preparedness aggregation | GREEN/PARTIAL | W5/W6 |
| Information-capability preservation / self-induced blindness check | GREEN | W5 |
| Continuation contract / terminal semantics / horizon cap | GREEN | W5 |
| Exact-scope policy executability `EXEC_*` assessment | GREEN | W5 |
| Proof-carrying `ActionAuthorization` bundle | GREEN for sealed-policy path | W4/W5 |
| Sealed-policy authority recheck under exact kernel writer lock | GREEN | W5 |
| Handoff liveness and principal-change revalidation | PARTIAL | W6 |
| Repeated handoff liveness certificate | MISSING | W6 |
| Activation-time edge stability | MISSING | W6 |
| SharedCommitment exclusive-resource conflict | GREEN | existing + W5 policy coherence |
| Resource/capacity feasibility beyond simple exclusive overlap | PARTIAL | W6 |
| Safe pruning / dormant branch / resurrection | GREEN/PARTIAL | W6 |
| Probability-only catastrophic pruning prohibition | PARTIAL | W6 |
| Planning budget mandatory-work preservation | GREEN/PARTIAL | W6 |
| Action lifecycle postcondition-before-commit | GREEN | existing |
| Durable dispatch-before-side-effect linearization | GREEN | W2/W3 |
| Unknown non-idempotent outcome -> evidence-bound reconciliation | GREEN | W2/W3 |
| Adapter capability revision binding | GREEN | W2 |
| Dispatch fence contract / cancellation residual race semantics | PARTIAL | W6 |
| Strategic relocation `LOCATED/AMBIGUOUS/UNLOCATED` | GREEN/PARTIAL | W6 |
| Completion verifier bound to current mission/cut/freshness | GREEN | existing/W2 |
| Immutable lineage fields across all strategic objects | PARTIAL | W7 |
| Schema/world-model/environment-regime versioning | PARTIAL | W7 |
| Snapshot/journal integrity and prefix binding | GREEN | W2 |
| Trust-bearing snapshot/replay semantics | GREEN | W3 |
| Proof-bearing snapshot/replay semantics | GREEN | W4 |
| Policy-bearing snapshot/replay semantics | GREEN | W5 |
| Policy internal canonical-digest verification | GREEN | W5 |
| Bounded v4→v5 migration with empty policy state | GREEN | W5 |
| Full semantic replay coverage for every strategic object/event | PARTIAL | W7 |
| General migration contracts across all schema versions | PARTIAL | W5/W7 |
| Graph compaction lineage | MISSING | W7 |
| PG01-PG40 registry | GREEN | existing |
| I-245..I-260 principal-scoped closure | GREEN/PARTIAL | W5/W6 remaining schedulability/handoff seams |
| v0.14 projection collision oracle `108 -> 0` | GREEN | existing |
| Wave-2 adversarial conformance | GREEN — 10/10 | W2 |
| Wave-3 adversarial conformance + constitutional mutations | GREEN — 12/12 + 4/4 | W3 |
| Wave-4 adversarial conformance + constitutional mutations | GREEN — 14/14 + 7/7 | W4 |
| Wave-5 adversarial conformance + constitutional mutations | GREEN — 29/29 + 13/13 | W5 |
| Python 3.11/3.12/3.13 release matrix | GREEN for current Wave-5 release head | W5 |
| Property/metamorphic/chaos/differential conformance | PARTIAL | W8 |
| Real benchmark worlds / empirical superiority | RESEARCH | W8 measurement only |
| Distributed correctness writers / consensus | BOUNDARY | not v0.15 |
| Generic identity provider | BOUNDARY | not v0.15 |
| Generic messaging/task marketplace/orchestration platform | BOUNDARY | not v0.15 |

## Exhaustion order

1. **Wave 3 — External Trust Anchor Closure — GREEN for reference-runtime scope**: canonical principal attestations, communication receipts, dispatch attestation, reconciliation evidence, trust snapshot/replay/freshness integration.
2. **Wave 4 — Proof Dependency & Support Closure — GREEN for reference-runtime scope**: proof input envelopes, capture assurance, query membership/result-sensitivity revisions, proof dependency manifests, bounded-DNF support alternatives, blocking-invalidity separation, semantic closure barrier, proof-carrying kernel authority, proof snapshot/replay and Wave-4 adversarial/mutation gates.
3. **Wave 5 — Executable Policy Closure — GREEN for bounded reference-runtime scope**: principal-relative decision information, contingent policy IR, frozen advisory selection, decision sufficiency, PlanSeal, recursive recall, totality, edge stitching, reaction/readiness, information capability, continuation, exact-scope executability, sealed-policy kernel authority, snapshot-v5 replay and Wave-5 adversarial/mutation gates.
4. **Wave 6 — Schedulability/Liveness & Future-Temporal-Resource Closure — NEXT**: joint control-plane schedulability, repeated handoff liveness, activation-time edge stability/option independence and deeper future/resource integration.
5. **Wave 7 — Durable Lineage & Migration Closure**: common immutable lineage schema, environment/world/schema versions, full replay reducers, migrations and compaction lineage.
6. **Wave 8 — Conformance Exhaustion**: property/metamorphic/chaos/differential tests, mutation gates per constitutional seam, benchmark worlds and final spec-to-code audit.

## Wave 3 verification surface

Wave 3 is GREEN only for the bounded reference-runtime scope exercised by repository gates:

- host-grounded identity binding rejects narration, collisions, weak/stale/revoked and retroactively unavailable identity evidence;
- communication distinguishes `SENT`, `DELIVERED` and `OBSERVED`, with exact recipient/time binding;
- strong dispatch binds authorization, transaction, action, adapter revision and current principal binding before external execution;
- strong reconciliation consumes exact transaction/principal/adapter evidence instead of caller trust flags;
- snapshot schema v3 preserves trust provenance and execution evidence and replays supported post-snapshot trust events fail-closed;
- 12 deterministic adversarial cases pass and four deliberate constitutional mutations are killed.

## Wave 4 verification surface

Wave 4 is GREEN only for the bounded proof-dependency/support reference-runtime scope exercised by repository gates:

- strong artifacts bind an explicit proof input envelope and capture-assurance floor; self-report/opacity cannot silently become strong completeness;
- absence/universal dependencies bind canonical query-domain revisions with both membership and result-sensitivity generations;
- manifests bind exact revisions, freshness domains, query digests and semantic/trust/execution profiles; capture gaps block strong reuse;
- support is bounded DNF with conjunctive leaves, alternatives, grounding-root/cycle checks and independent-root floors;
- positive support and blocking invalidity remain distinct authority dimensions;
- semantic-source mutation and affected freshness generations share the exact kernel correctness-writer lock;
- proof-carrying authorization rechecks manifest freshness/support before authority is created;
- snapshot schema v4 preserves proof lineage with internal digest verification and fail-closed suffix replay;
- 14 deterministic adversarial cases pass and seven deliberate constitutional mutations are killed.

## Wave 5 verification surface

Wave 5 is GREEN only for the bounded executable-policy reference-runtime scope exercised by repository gates:

- principal information partitions, decision epochs and observation frontiers prevent runtime-global or other-principal state from silently refining a decision;
- non-anticipativity rejects distinct actions across information-equivalent histories until a grounded principal-available reveal exists;
- contingent policy coherence checks required branch viability and conflicting shared commitments;
- frozen selection applies hard admissibility before ranking, binds principal/information/action-space/dependency generations and remains advisory only;
- decision sufficiency and PlanSeal bind exact action-local closure; assurance cannot self-promote, unaccepted debt is not hidden, bounded global proof-context inconsistency fails closed, and invalidated seals cannot revive;
- recursive recall compares downstream signatures, totality requires supported outcomes to have exact valid handlers, and policy-edge stitching checks explicit refinement contracts;
- reaction timing distinguishes possible IA1 timing from bounded IA2-or-stronger guarantees; preparedness aggregation requires declared independence/coexistence for OR/K-of-N uplift;
- information-capability preservation detects self-induced blindness and continuation contracts do not extend executable coverage beyond certified terminal/handoff semantics;
- `PolicyExecutabilityAssessment` cannot become bounded when known blockers, unresolved recall, stale seal, mixed snapshot, inadequate reaction class, information loss or unaccepted debt remain;
- `authorize_sealed_policy` rechecks the current policy bundle under the exact kernel writer lock and then delegates through existing proof/identity authorization rather than minting independent authority;
- snapshot schema v5 canonically restores policy state, verifies internal digests, replays supported `policy.*` suffix events fail-closed, and does not resurrect stale selection/seal/partial executability state;
- 29 deterministic adversarial Wave-5 cases pass and 13 deliberate constitutional mutations are killed;
- the release matrix exercises Python 3.11, 3.12 and 3.13.

Wave 5 intentionally does **not** promote joint control-plane schedulability, repeated handoff liveness, activation-time edge stability, full migration/replay exhaustion or distributed correctness to GREEN.

## Claim boundary

`GREEN` means a tested reference implementation for the stated bounded scope. It does not mean formal proof, production hardening, distributed multi-writer safety or empirical superiority. The final exhaustion gate may claim full **reference-runtime normative coverage** only after every remaining `PARTIAL`/`MISSING` row is either GREEN or explicitly classified as a documented research/non-goal boundary with spec support.
