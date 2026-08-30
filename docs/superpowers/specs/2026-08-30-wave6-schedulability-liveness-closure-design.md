# Wave 6 Schedulability, Liveness & Future-Temporal-Resource Closure Design

## Status

Architecture design for the bounded v0.6 reference-runtime closure derived from `NOLANE-PLAN-RUNTIME-ARCHITECTURE-V0.15-PRINCIPAL-SCOPED-MULTI-AGENT-CLOSURE-SPEC.md`, especially Sections 164–172 and the still-PARTIAL/MISSING Wave-6 rows in `docs/SPEC-COVERAGE.md`.

Wave 6 extends the already-GREEN Wave-5 executable-policy path. It does **not** create a second correctness writer, a generic real-time scheduler, a generic orchestration platform, a distributed consensus layer, or a second authorization gateway.

## Goals

Wave 6 closes the bounded reference semantics required to distinguish:

1. local reaction timing from joint control-plane schedulability;
2. locally safe handoff from recursively feasible and progress-bounded handoff chains;
3. snapshot-time edge compatibility from activation-time freshness/stability;
4. nominal route multiplicity from robust independent alternatives;
5. totality over a modeled support from transition/observation model adequacy and residual/open-world debt;
6. simple exclusive resource overlap from bounded capacity/rate/reservation feasibility where planning guarantees depend on it;
7. dormant/pruned future storage from safe, current, resource/temporal revalidated resurrection;
8. speculative planning budget from capacity protected for certified deadline-critical reaction work.

The release target is `0.6.0a1`.

## Source invariants

The implementation SHALL preserve the following v0.6 invariants:

- I-65: local reaction feasibility does not imply joint reaction schedulability.
- I-66: strong policy reaction guarantees account for shared control-plane resources over simultaneously reachable jobs.
- I-67: background planning cannot consume capacity reserved by a certified deadline-critical reaction.
- I-68: `SAFE_HANDOFF` preserves recursive feasibility and obeys a bounded liveness/progress contract.
- I-69: the planner cannot extend continuation deadlines through ungrounded self-revision.
- I-70: policy-edge compatibility does not waive activation-time freshness of mutable world predicates.
- I-71: policy totality and transition/observation model adequacy remain distinct axes in every strong claim.
- I-72: redundant-route preparedness earns robustness credit only for declared independent/common-mode-resistant alternatives.

Existing invariants remain normative, including the single serialized correctness writer, host-grounded identity, proof freshness, policy sealing, exact principal binding, and existing Action Binder / Execution Binder authority.

## Architectural approach

Wave 6 uses **modular certificate closure**. Each new object is immutable, canonical-digest-bound, scope/version-bound, and has no direct dispatch authority. Strong policy authority consumes the new certificates as additional prerequisites under `PlanKernel._writer_lock`, then delegates to the existing sealed-policy → proof → identity authorization stack.

The runtime intentionally implements only a bounded deterministic planning-level schedulability abstraction. It does not expose task queues, worker executors, OS scheduling controls, or a generalized scheduler API.

## 1. Control-plane resource model

### `ControlPlaneResourceRevision`

Canonical resource contract for correctness-significant planning/execution control capacity.

Required fields:

```text
resource_id
revision_id
resource_kind
capacity_units
concurrency_limit
service_rate_per_second
rate_window_seconds
availability_interval
priority_policy_ref
reservation_policy_ref
regime_ref
assurance_profile
opaque_dimensions
validity_regime
canonical_digest
```

Supported bounded `resource_kind` values:

- `SERIAL`
- `CONCURRENCY`
- `RATE_LIMIT`
- `CAPACITY_WINDOW`
- `AUTHORITY_HUMAN`
- `KERNEL_WRITER`

A resource with correctness-relevant opaque capacity cannot support an RS2+ strong claim unless a conservative bound is supplied. Average throughput is not a worst-case service guarantee.

### `ReactionResourceDemand`

A job-to-resource demand edge:

```text
resource_ref
required_service
required_concurrency_units
release_offset_interval
demand_window
mandatory
```

The edge is immutable and participates in the job digest.

### `ReactionJobContract`

Canonical job object:

```text
reaction_job_id
revision_id
policy_scope
mission_revision
information_partition_revision
reaction_envelope_ref
release_window
deadline
resource_demands
coexistence_tags
correlation_refs
priority_class
reservation_refs
risk_class
model_adequacy_debt_refs
validity_regime
canonical_digest
```

A job does not acquire authority by being sealed or schedulable.

## 2. Joint schedulability

### Levels

Exact vocabulary:

```text
RS0_UNANALYZED
RS1_EACH_JOB_INDIVIDUALLY_FEASIBLE
RS2_DECLARED_COHORT_FEASIBLE
RS3_ROBUST_COHORT_SCHEDULABLE
RS4_CLOSED_SUBDOMAIN_PROVEN
```

RS1 never supports a strong policy-level reaction guarantee when concurrent jobs are possible.

### Analysis modes

```text
EXACT_BOUNDED
CONSERVATIVE_OVERAPPROX
INTERVAL_ROBUST
SCENARIO_STRESS
UNSUPPORTED
```

`SCENARIO_STRESS` cannot be rendered as exact proof. `UNSUPPORTED` yields explicit UNKNOWN/debt rather than success.

### `ReactionSchedulabilityCertificate`

Required fields:

```text
certificate_id
revision_id
policy_scope
mission_revision
information_partition_revision
reaction_job_digests
control_resource_digests
coexistence_constraint_refs
resource_reservation_refs
scheduling_model_id
scheduling_model_version
analysis_mode
worst_case_or_interval_assumptions
proof_or_solver_ref
overload_witnesses
assurance_profile
model_adequacy_debt_refs
validity_regime
level
canonical_digest
```

### Bounded deterministic evaluator

The reference runtime uses a finite-window conservative demand test, not a general scheduler.

For each declared resource and every candidate interval endpoint induced by co-reachable jobs:

1. determine jobs that can be simultaneously active according to declared coexistence/correlation constraints;
2. compute conservative service demand in the interval;
3. compute service available from the bound resource revision;
4. reject if demand exceeds service or concurrency/rate constraints;
5. emit a typed `OverloadWitness(resource_ref, window_start, window_end, available_service, job_refs, required_service)`.

Mutually exclusive jobs do not create simultaneous demand. Unknown correlation/coexistence relevant to a strong claim yields UNKNOWN/debt, not optimistic exclusivity.

RS2 requires a declared cohort to pass the bounded model. RS3 additionally requires robust interval assumptions and strong resource assurance. RS4 requires an explicit closed-subdomain proof reference and otherwise cannot be inferred.

### Invalidation

Certificate freshness binds:

- resource revisions/capacity/rate regime;
- reaction job digests;
- coexistence/correlation model revisions;
- mission/information partition;
- reservation/priority semantics;
- scheduling model id/version;
- future control-resource frontier generation.

Any drift stales the certificate before authority.

## 3. Protected reaction reservations and resource governance

### `ControlPlaneReservation`

Canonical bounded reservation:

```text
reservation_id
revision_id
resource_ref
policy_scope
job_refs
start_time
end_time
reserved_service
reserved_concurrency_units
priority_class
preemptible
risk_justification_ref
cross_future_value_ref
validity_regime
canonical_digest
```

Reservations are not free robustness. The evaluator must detect both under-reservation and over-reservation that starves a more valuable required route.

### Resource Governor integration

`PlanningBudgetGovernor` gains a protected-capacity input for already-certified deadline-critical work. Optional/background planning may use only unprotected residual budget. Mandatory planning work remains non-droppable; if mandatory + protected demand exceeds the available budget, the result is explicit infeasibility rather than silent pruning.

The existing `ReservationLedger` remains the simple compatibility API for exclusive resources. Wave 6 adds a separate bounded control-plane ledger rather than changing the legacy semantics into a generic resource scheduler.

## 4. Continuation progress and handoff liveness

### `ContinuationProgressRank`

Canonical progress snapshot:

```text
rank_id
revision_id
continuation_scope
mission_revision
unresolved_critical_debt_count
remaining_unprepared_boundaries
absolute_executable_horizon
minimum_preparedness_at_next_boundary
remaining_synthesis_workload
reaction_refinement_slack
mission_distance_measure
semantic_continuation_digest
created_at
canonical_digest
```

No universal scalar distance is assumed. The bounded reference relation is lexicographic over policy-declared dimensions, while preserving explicit horizon and debt semantics.

### `HandoffProgressPolicy`

Canonical bounded policy:

```text
policy_id
revision_id
max_handoff_count
max_total_deferral_time
minimum_horizon_advance
minimum_debt_reduction_rate
mandatory_preparedness_floor_by_time
bounded_stutter_allowance
recovery_stutter_allowance
absolute_latest_safe_refinement_time
temporal_authority_ref
canonical_digest
```

The absolute deadline cannot advance just because a new continuation/plan object is emitted. A deadline revision requires a grounded external mission/world/temporal revision or explicitly authorized policy revision reference.

### Progress statuses

```text
STRICT_PROGRESS
BOUNDED_STUTTER
RECOVERY_STUTTER
NO_PROGRESS
UNKNOWN
```

### `HandoffLivenessCertificate`

Binds source/successor continuation, old/new progress vectors, recursive feasibility evidence, stutter counters, absolute time/horizon refs, debt lineage and policy revision.

`STRICT_PROGRESS` requires progress under the configured relation.
`BOUNDED_STUTTER` requires no progress but consumes finite ordinary stutter allowance.
`RECOVERY_STUTTER` is separately typed and consumes recovery allowance.
`NO_PROGRESS` prohibits another ordinary `SAFE_HANDOFF` at the same assurance level.
`UNKNOWN` never supports a strong handoff claim.

Equivalent debt renamed under a new ID remains equivalent through lineage/equivalence refs and does not count as progress. Semantically identical continuation digests do not count as novelty.

## 5. Edge activation stability

### `HandoffStabilityContract`

Canonical edge contract:

```text
contract_id
revision_id
policy_edge_ref
protected_predicate_refs
protected_generation_bindings
lock_or_reservation_refs
stability_start
stability_end
external_writer_assumption_refs
refresh_required_predicate_refs
authorization_time_precondition_refs
invalidating_event_refs
open_side_effect_refs
fallback_on_instability
opacity_debt_refs
validity_regime
canonical_digest
```

At child activation, every mutable entry predicate is either:

- still protected by a current stability contract; or
- explicitly refreshed against current canonical state under the kernel writer lock.

A valid Wave-5 `PolicyEdgeCertificate` does not suppress this refresh. The existing Execution Binder remains the authority for dispatch-time preconditions; this contract only determines which edge assumptions survive or must be refreshed.

If stability/refresh cannot be established in time, the route may remain represented, but its preparedness/executability/reaction guarantee is downgraded.

## 6. Totality versus model adequacy

Wave 6 does not redefine Wave-5 totality. It adds explicit two-axis reporting.

### `ExecutablePolicyCoverageAssessment`

Canonical advisory/closure assessment:

```text
assessment_id
revision_id
policy_scope
policy_totality_certificate_ref
policy_totality_mode
transition_observation_model_adequacy
residual_open_world_status
residual_debt_refs
closed_domain_proof_ref
created_sequence
validity_regime
canonical_digest
```

A policy may be `TOTAL` over modeled support while model adequacy is `DEGRADED` and residual debt is active. This must never be rendered or consumed as “handles every possible outcome.”

A closed-open-world strong claim requires an explicit closed-domain proof reference. Otherwise totality and adequacy remain separate blockers/qualifiers.

## 7. Option independence and robust preparedness

### `OptionIndependenceCertificate`

Required fields follow the spec:

```text
certificate_id
revision_id
route_refs
failure_uncertainty_set_ref
shared_dependency_graph_ref
resource_overlap_refs
observation_lineage_overlap_refs
control_plane_overlap_refs
common_mode_failure_refs
coactivation_feasibility_ref
assurance_profile
status
canonical_digest
```

Status vocabulary:

```text
ROBUST_INDEPENDENT
NOMINAL_ONLY
UNKNOWN
UNSUPPORTED
```

Independence is always relative to the declared failure/uncertainty set. Distinct route IDs, principals, or textual plans do not imply independence.

Preparedness composition reports two values:

```text
nominal_alternative_preparedness
robust_independent_preparedness
```

OR/K-of-N robust uplift is allowed only when the certificate establishes sufficient common-mode resistance and co-activation feasibility for the protected target. Shared credential/provider/database/model endpoint/human approver/recovery script/observation lineage can collapse robust preparedness even when both routes are individually P4/P5.

## 8. Dormancy, resurrection, future/resource integration

Wave 6 strengthens existing `PruningEngine` behavior without making future compilation unbounded.

### `DormantBranchRevision`

A persistent dormant representation binds:

- branch digest;
- mission revision;
- assumption/evidence revisions;
- transition/model revisions;
- temporal feasibility revision;
- resource/capability/authority revisions;
- risk classification;
- resurrection dependency refs;
- dormant reason and generation.

### `BranchResurrectionAssessment`

Resurrection is permitted only after current revalidation of mission compatibility, assumptions/evidence, stale transitions, temporal feasibility, resource/capability/authority feasibility and risk classification. A dormant route never becomes live solely because its old trigger becomes probable again.

Probability-only pruning remains forbidden for catastrophic exposure/sole hard route/unique hedge/information-rich branch. The existing simple `PruningEngine` API remains backward compatible; strong Wave-6 paths use the revisioned assessment.

## 9. Kernel integration

A new `schedulability_runtime.py` extension installs bounded registries and authority rechecks under the exact existing `PlanKernel._writer_lock`.

Strong sealed-policy authorization with a declared strong timing/robustness scope requires, as applicable:

1. current Wave-5 policy/seal/executability bundle;
2. current RS2+ schedulability certificate when concurrent reactions are possible;
3. current handoff liveness certificate for `SAFE_HANDOFF` continuation authority;
4. current edge stability/refresh evidence for child activation;
5. explicit totality + model-adequacy/residual assessment;
6. current option-independence certificate when robust redundancy uplift is claimed;
7. current resource/reservation generations.

These objects do not mint authorization. The method delegates to `authorize_sealed_policy`, preserving proof and identity binding.

## 10. Persistence and replay

Snapshot schema advances from v5 to `nolane-plan-runtime-snapshot-v6`.

A new `schedulability_recovery.py` wraps `policy_recovery.py` exactly as v5 wrapped v4. It persists canonical Wave-6 objects, verifies every internal digest during restore, supports bounded migration from v5 with empty Wave-6 state, and fail-closes unknown correctness-significant `sched.*`, `handoff.*`, `stability.*`, `independence.*`, `coverage.*`, and strong dormancy/resurrection suffix events.

Public mutators are not used during replay. Replay restores exact canonical state without journaling the event a second time.

No persistent Wave-6 object may ship without codec + internal digest + replay/migration semantics.

## 11. Conformance and mutation gates

Wave 6 MUST reproduce at least these five discriminating counterexamples:

1. two reaction jobs each pass local timing but joint shared capacity is infeasible;
2. eight nominally safe handoffs preserve local slack but never reduce continuation debt or compile an executable suffix;
3. a policy is total over modeled support while a real unmodeled TIMEOUT remains residual;
4. a valid policy edge becomes stale through external interference before child activation;
5. two high-preparedness alternatives collapse under one shared credential failure.

The deterministic Wave-6 oracle targets CP01–CP12, HL01–HL12, edge-freshness failures, totality/adequacy separation, and option-independence failures that are representable by the bounded runtime.

Minimum constitutional mutations:

- RS1 promoted to strong joint guarantee;
- mutual-exclusion/coexistence bypass;
- resource regime drift ignored;
- protected capacity consumed by background planning;
- stutter budget not consumed;
- deadline self-extension accepted;
- equivalent debt rename counted as progress;
- edge activation refresh bypassed;
- totality laundered into open-world completeness;
- shared common-mode route counted independent;
- replay internal digest bypass;
- stale Wave-6 authority certificate resurrected after restart.

All must be target-specifically killed.

## 12. Release gate

Wave 6 is GREEN for bounded reference-runtime scope only when:

- all Wave-6 unit/integration tests pass;
- prior Wave 2–5 suites remain GREEN;
- Wave-6 deterministic conformance is fully GREEN;
- all Wave-6 constitutional mutations are killed;
- snapshot v6 replay/migration tests are GREEN;
- package version and release-facing docs are aligned to `0.6.0a1`;
- fresh branch CI passes Python 3.11/3.12/3.13;
- PR CI passes Python 3.11/3.12/3.13;
- exact integrated `main` SHA passes fresh Python 3.11/3.12/3.13 CI;
- `docs/SPEC-COVERAGE.md` promotes only actually closed Wave-6 rows.

## 13. Explicit non-goals

Wave 6 does not claim:

- formal real-time scheduling correctness outside the bounded analysis model;
- a general scheduler product;
- distributed/multi-writer correctness;
- full graph/storage migration exhaustion (Wave 7);
- graph compaction lineage (Wave 7);
- empirical superiority (Wave 8 measurement);
- full property/metamorphic/chaos/differential exhaustion (Wave 8);
- full Nolane World W5 convergence.

`GREEN` remains a tested bounded reference-runtime claim, not a global formal proof.