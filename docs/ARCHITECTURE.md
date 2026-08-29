# Architecture

## 1. Correctness root

`PlanKernel` is the only component that commits correctness-significant canonical mutation. It uses an in-process reentrant writer lock and appends every mutation to a hash-chained JSONL journal. Future implementations may place the writer behind a service boundary, but must not silently turn speculative workers into independent correctness roots.

## 2. Strategic future plane

`FutureLattice` contains future families plus an immutable conceptual residual family `NULL_WORLD`. `FutureSpaceCompiler` performs bounded factorized expansion rather than unbounded Cartesian materialization. `ConvergenceCertificate` encodes decision-relevant merge guards, including mission, obligation, anti-goal, irreversible-fact, resource, temporal, side-effect, downstream-action, actor-regime, verification-debt and provenance compatibility.

## 3. Principal plane

`PrincipalRegistry` binds access profiles, observation/delivery times and information partitions to canonical principal references. A partition digest includes the principal and access revision, so two agents seeing the same item IDs are still not silently treated as the same decision authority.

## 4. Capsule plane

`DecisionCapsule` is a decision-local projection, not a summary of the whole plan. It binds recipient principal, information partition, access revision, mission version, canonical state version, evidence watermark and action set. Reuse under a different principal is rejected. Hydration re-checks actual principal availability.

## 5. Action plane

`AuthorityGrant` is principal-scoped. `ActionAuthorization` resolves the exact acting principal. `AuthorityEngine.dispatch_eligible` checks presented principal, mission/canonical freshness, grant revocation and scope. Adapter receipts must report the executing principal. Canonical state changes only after postconditions are verified.

## 6. Freshness and proof plane

`FreshnessDomainLedger` gives correctness domains durable generations. `DependencyManifest` captures exact generations used by derived artifacts. Mutation bumps invalidate current reuse without relying on asynchronous deletion. Universal/absence proofs additionally require a `QuerySnapshotCompletenessReceipt` that proves enumeration completeness and visibility assurance at a compatible generation.

## 7. Unknown-world plane

`RecoveryController` separates normal operation from `MODEL_CLASS_UNCERTAIN`/quarantine. Reversible probes remain possible, while consequential/irreversible actions are blocked unless an explicit emergency authorization exists.

## 8. Temporal and resource plane

`ReactionWindow` and `HandoffContract` distinguish logical reachability from reaction-time feasibility. `ReservationLedger` prevents overlapping exclusive commitments. `PlanningBudgetGovernor` never silently drops mandatory verification/recovery work merely because optional work has higher heuristic value.

## 9. Persistence

`HashJournal` detects mutation, deletion/reordering and broken previous-hash links. `SnapshotStore` protects snapshot bytes with a semantic digest. The current reference snapshot is intentionally compact; future migration support must retain explicit versioning rather than guess old semantics.
