# Nolane Plan v0.15 Implementation Coverage Ledger

This ledger tracks the strongest normative runtime contracts in `NOLANE-PLAN-RUNTIME-ARCHITECTURE-V0.15-PRINCIPAL-SCOPED-MULTI-AGENT-CLOSURE-SPEC.md` against the reference implementation. It deliberately separates **implemented semantics**, **partial reference semantics**, **planned closure**, and **research/non-goal claims**.

Legend: `GREEN` = on a tested correctness path; `PARTIAL` = primitive exists but the complete spec contract is not yet on the kernel authority path; `W3+` = scheduled closure wave; `BOUNDARY` = explicitly not required by v0.15.

| Spec surface | Current state | Closure wave |
|---|---|---|
| Mission revision / anti-goals / hard constraints | GREEN | existing |
| Canonical state outranks plan narrative | GREEN | existing |
| `NULL_WORLD` / residual unknown-world representation | GREEN | existing |
| Future families, bounded factorized compiler | GREEN/PARTIAL | W6 deeper policy integration |
| Decision-relevant convergence guards | GREEN/PARTIAL | W6 |
| Condition-centric Strategic Obligations | GREEN | existing |
| Evidence polarity, revocation, common-lineage independence | GREEN | existing |
| Principal-scoped access profiles and information partitions | GREEN | existing |
| Decision Capsule recipient/partition/access binding | GREEN | existing |
| Capsule hydration anti-escalation | GREEN | existing |
| Exact acting-principal authorization and presented-principal match | GREEN | existing |
| Canonical host/platform principal identity binding | PARTIAL | W3 |
| Principal identity provenance across restart/replay | PARTIAL | W3 |
| Inter-principal delivery/reveal/ack evidence | PARTIAL | W3 |
| Dispatch-time principal attestation object | PARTIAL | W3 |
| Executing-principal reconciliation evidence | PARTIAL | W3 |
| `DecisionCutRevision` causal/knowledge frontier | GREEN/PARTIAL | W4 expands full cut dimensions |
| Knowledge-time / no retroactive artifact injection | GREEN | existing |
| Authority-time dependency freshness | GREEN | existing |
| `ProofInputEnvelopeRevision` | MISSING | W4 |
| Dependency-capture assurance / hidden-read defense | MISSING | W4 |
| `ProofDependencyManifestRevision` | PARTIAL (`DependencyManifest`) | W4 |
| Query-domain membership revision for absence/universal claims | PARTIAL | W4 |
| SupportAlternativeSet / conjunctive clauses / grounded support | MISSING | W4 |
| Blocking-invalidity vs positive-support distinction | MISSING | W4 |
| Semantic closure barrier (source mutation + generation advance) | PARTIAL | W4 |
| Replay-derived support/freshness reconstruction | PARTIAL | W4/W7 |
| `DecisionEpoch` full principal/cut/policy binding | PARTIAL | W5 |
| Reveal events / principal-relative observation frontier | PARTIAL | W5 |
| `PolicyNodeRevision` contingent policy graph | PARTIAL | W5 |
| `SelectionRecord` with admissibility/Pareto/risk/debt refs | MISSING | W5 |
| PlanSeal / immutable proof-bearing decision seal | MISSING | W5 |
| Proof-carrying `ActionAuthorization` bundle | PARTIAL | W5 |
| Decision sufficiency / capsule exclusion certificates | MISSING | W5 |
| Preparedness levels and irreversible-horizon floor | GREEN/PARTIAL | W5/W6 |
| Reaction-window schedulability | GREEN | existing |
| Handoff liveness and principal change revalidation | PARTIAL | W3/W6 |
| SharedCommitment exclusive-resource conflict | GREEN | existing |
| Resource/capacity feasibility beyond simple exclusive overlap | PARTIAL | W6 |
| Safe pruning / dormant branch / resurrection | GREEN/PARTIAL | W6 |
| Probability-only catastrophic pruning prohibition | PARTIAL | W6 |
| Planning budget mandatory-work preservation | GREEN/PARTIAL | W6 |
| Action lifecycle postcondition-before-commit | GREEN | existing |
| Durable dispatch-before-side-effect linearization | GREEN | existing |
| Unknown non-idempotent outcome -> reconciliation | GREEN | existing |
| Adapter capability revision binding | GREEN | existing |
| Dispatch fence contract / cancellation residual race semantics | PARTIAL | W3/W6 |
| Strategic relocation `LOCATED/AMBIGUOUS/UNLOCATED` | GREEN/PARTIAL | W6 |
| Completion verifier bound to current mission/cut/freshness | GREEN | existing |
| Immutable lineage fields across all strategic objects | PARTIAL | W7 |
| Schema/world-model/environment-regime versioning | PARTIAL | W7 |
| Snapshot/journal integrity and prefix binding | GREEN | existing |
| Full semantic replay coverage | PARTIAL | W7 |
| Migration contracts across schema versions | MISSING | W7 |
| Graph compaction lineage | MISSING | W7 |
| PG01-PG40 registry | GREEN | existing |
| I-245..I-260 principal-scoped closure | GREEN/PARTIAL | W3 closes grounding seams |
| v0.14 projection collision oracle `108 -> 0` | GREEN | existing |
| Wave-2 adversarial conformance | GREEN | existing |
| Property/metamorphic/chaos/differential conformance | PARTIAL | W8 |
| Real benchmark worlds / empirical superiority | RESEARCH | W8 measurement only |
| Distributed correctness writers / consensus | BOUNDARY | not v0.15 |
| Generic identity provider | BOUNDARY | not v0.15 |
| Generic messaging/task marketplace/orchestration platform | BOUNDARY | not v0.15 |

## Exhaustion order

1. **Wave 3 — External Trust Anchor Closure**: canonical principal attestations, communication receipts, dispatch attestation, reconciliation evidence, replay/freshness integration.
2. **Wave 4 — Proof Dependency & Support Closure**: proof input envelopes, capture assurance, query membership, support alternatives, semantic closure barrier.
3. **Wave 5 — Sealed Contingent Policy Closure**: full decision epochs, reveal/observation frontiers, policy nodes, SelectionRecord, PlanSeal, proof-carrying authorization and capsule sufficiency/exclusion.
4. **Wave 6 — Future/Temporal/Resource Closure**: survival/convergence metrics, branch dormancy/resurrection, handoff liveness, richer resource capacity, integrated budgets and relocation.
5. **Wave 7 — Durable Lineage & Migration Closure**: common immutable lineage schema, environment/world/schema versions, full replay reducers, migrations and compaction lineage.
6. **Wave 8 — Conformance Exhaustion**: property/metamorphic/chaos/differential tests, mutation gates per constitutional seam, benchmark worlds and final spec-to-code audit.

## Claim boundary

`GREEN` means a tested reference implementation for the stated scope. It does not mean formal proof, production hardening, distributed multi-writer safety or empirical superiority. The final exhaustion gate may only claim full **reference-runtime normative coverage** after every `PARTIAL`/`MISSING` row above is either GREEN or explicitly classified as a documented research/non-goal boundary with spec support.
