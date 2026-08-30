# Nolane Plan Conformance

This document records the executable bounded conformance surface for the `0.6.0a1` reference-runtime line. It is an evidence ledger, not a claim of global formal correctness or empirical superiority.

## Release gate

A Wave-6 release candidate is acceptable only when the same exact commit passes all of the following on Python 3.11, 3.12 and 3.13:

| Gate | Required result |
|---|---:|
| Unit/integration discovery | 334/334 tests pass |
| Source compilation | pass |
| Principal-scope projection oracle | v0.14 `108` collisions -> v0.15 `0` |
| Wave 2 adversarial conformance | 10/10 |
| Wave 3 adversarial conformance | 12/12 |
| Wave 3 constitutional mutations | 4/4 killed |
| Wave 4 adversarial conformance | 14/14 |
| Wave 4 constitutional mutations | 7/7 killed |
| Wave 5 adversarial conformance | 29/29 |
| Wave 5 constitutional mutations | 13/13 killed |
| Wave 6 adversarial conformance | 43/43 |
| Wave 6 constitutional mutations | 12/12 killed |
| End-to-end demo | pass with valid journal |

## Wave 6 taxonomy

`nolane_plan.wave6_conformance` covers the exact v0.6 failure taxonomy once each:

- `CP01..CP12` — joint control-plane schedulability, finite verifier/human/writer resources, regime freshness, protected capacity, coexistence/correlation, recovery contention and fail-closed UNKNOWN handling.
- `HL01..HL12` — repeated handoff liveness, grounded deadlines, rank regression, bounded ordinary/recovery stutter, semantic churn, absolute horizon, recursive feasibility, debt lineage, temporal/information/budget bounds.
- `EF01..EF08` — activation-time generation/permission/resource/writer freshness, open side effects, opacity debt, shared stability resources and refresh-time reaction feasibility.
- `TM01..TM05` — modeled-support totality kept distinct from transition/observation-model adequacy and residual/open-world status.
- `OI01..OI06` — declared failure-set-relative route independence, common credential/network/evidence/control dependencies, co-activation feasibility, invalidation by newly discovered common causes and separate nominal/robust readiness reporting.

## Wave 6 constitutional mutations

`scripts/wave6_mutation_gate.py` deliberately weakens twelve constitutional seams and requires a focused test to kill every mutant:

1. `rs1_joint_guarantee_bypass`
2. `coexistence_bypass`
3. `resource_regime_freshness_bypass`
4. `protected_capacity_bypass`
5. `stutter_budget_bypass`
6. `deadline_self_extension_bypass`
7. `equivalent_debt_progress_bypass`
8. `edge_activation_refresh_bypass`
9. `totality_open_world_laundering`
10. `common_mode_independence_bypass`
11. `replay_internal_digest_bypass`
12. `stale_wave6_restart_resurrection`

The mutation gate also fails if a mutation target no longer matches exactly one production location. This prevents a refactor from silently turning a constitutional mutation into a no-op.

## Persistence conformance

Snapshot schema `nolane-plan-runtime-snapshot-v6` persists Wave-6 resource/job revision history, current logical pointers, schedulability certificates, coverage assessments, option-independence/robust-preparedness state, liveness certificates, stability contracts, edge-activation assessments and Wave-6 authorization bindings.

The bounded recovery contract requires:

- canonical reconstruction and internal digest verification;
- v5 snapshots migrate with empty Wave-6 state rather than invented certificates;
- historical revisions and current logical pointers remain distinct;
- stale current resource state does not resurrect an old certificate after restart;
- supported post-snapshot `schedulability.*` events replay exactly;
- unknown correctness-significant Wave-6 events fail closed;
- Wave-6 authorization lineage remains subordinate to existing identity, proof and sealed-policy authority.

## Claim boundary

`0.6.0a1` may be described as **GREEN for the bounded Wave-6 reference-runtime scope** only after exact release-head, PR-head and final `main` evidence pass. The repository still does not claim:

- full semantic replay for every strategic object/event;
- universal schema/world/environment migration closure;
- common immutable lineage and graph-compaction lineage across every object;
- distributed correctness writers or consensus;
- a generic scheduler/orchestrator/identity provider/messaging platform;
- property/metamorphic/chaos/differential exhaustion;
- production hardening, formal global proof or empirical superiority.

Those unresolved normative engineering surfaces remain Wave 7/8 work or explicit research/non-goal boundaries.
