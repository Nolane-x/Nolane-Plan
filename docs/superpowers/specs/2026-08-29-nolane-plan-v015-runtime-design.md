# Nolane Plan v0.15 Full Reference Runtime Design

## Objective

Build a broad, executable reference implementation of the v0.15 Nolane Plan architecture rather than a toy kernel. The runtime must preserve the specification's core semantics: strategic future-space compilation, canonical-state authority, principal-scoped information, principal-bound authorization and dispatch, condition-centric obligations, open-world recovery, temporal/handoff constraints, durable replay, and deterministic conformance oracles.

## Architectural boundary

The runtime has one serialized correctness writer: `PlanKernel`. Read-only projections, speculative future compilation, model proposals, and independent verifiers may run outside the writer, but correctness-critical mutation passes through the kernel. The first implementation is intentionally not a distributed consensus system, identity provider, generic message bus, or task marketplace.

## Subsystems

1. `mission`: versioned objective, hard constraints, anti-goals, completion conditions.
2. `principals`: canonical principal identity, access profiles, delivered/observed information, principal-scoped partitions and decision epochs.
3. `evidence`: provenance-bearing evidence records, lineage grouping, freshness generations, contradiction/unknown polarity.
4. `obligations`: condition-centric strategic obligations that survive worker/principal replacement.
5. `future`: future families, residual/null world, strategic states, transitions, convergence certificates, lazy factorized compilation.
6. `capsule`: bounded Decision Capsule projections bound to recipient principal, access profile, information partition, mission/canonical versions, freshness and dependency digests.
7. `actions`: typed action intents, authority grants, principal-bound authorization, dispatch fences, receipts and lifecycle states.
8. `temporal`: deadlines, reaction windows, schedulability and handoff liveness checks.
9. `recovery`: explicit model-class-uncertain mode and unknown-world quarantine protocol.
10. `persistence`: hash-chained journal, snapshots and deterministic replay validation.
11. `selector`: hard-veto + Pareto-style cross-future action assessment without forcing hard constraints into a scalar.
12. `conformance`: deterministic model-free oracles, including the v0.14→v0.15 principal projection collision matrix.
13. `cli`: usable local interface for creating sessions, principals, evidence, obligations, future families, capsules, authorizations, snapshots and verification.

## Data authority

`trusted observation/evidence > canonical kernel state > verified plan inference > model narrative`.

Model-produced content enters as a proposal. It is not promoted to canonical fact without the same typed checks as any other producer.

## Principal semantics

A planning principal is not a role, model name, worker process, session, or grant. Information availability for principal `p` at decision `d` requires visibility, access permission, delivery/observation before the decision, decision validity, and required assurance. Kernel-global visibility never fills a missing principal term.

Decision Capsules are recipient-bound and non-transferable by default. Hydration cannot enlarge the principal's information scope. Action authorization resolves an exact `acting_principal_ref`; dispatch rechecks the presented principal when identity can affect legality.

## Open-world semantics

The future graph always includes residual/null-world state. Model-class anomalies move the session into explicit uncertainty/quarantine and prevent high-irreversibility actions unless an emergency policy explicitly permits them.

## Persistence semantics

Every correctness mutation appends a deterministic journal event with previous-hash linkage. Snapshots carry journal head and semantic versions. Replay validates the chain and reconstructs the same canonical digest or fails closed.

## Verification strategy

Tests are written first. The test suite includes:
- principal information leakage and capsule-swap attacks;
- bearer authorization and authorization→dispatch principal swap;
- mission/freshness invalidation;
- condition-centric obligation survival;
- residual-world preservation and anomaly quarantine;
- convergence certificate rejection;
- temporal/handoff failure;
- journal tamper/replay detection;
- end-to-end kernel lifecycle;
- exact bounded principal projection oracle: 128 information decisions + 16 authorization decisions, v0.14 collisions 108, v0.15 collisions 0.

## Definition of done for this implementation wave

The repository is installable, the CLI executes a demonstrator lifecycle, the full unit/conformance suite passes, `python -m nolane_plan.conformance` reproduces the collision oracle, snapshots/replay pass, and CI is configured. This is a reference implementation claim, not empirical superiority over external planners.
