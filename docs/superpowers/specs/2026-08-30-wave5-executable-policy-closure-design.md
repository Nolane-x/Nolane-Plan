# Wave 5 — Sealed Executable Policy Closure Design

## Scope

Wave 5 closes the v0.4/v0.5 contingent-policy and bounded-executability semantics required by the v0.15 Nolane Plan specification. It deliberately stops before the v0.6 joint control-plane schedulability and handoff-liveness additions, which remain Wave 6.

The release target is a bounded model-free reference runtime. It does not claim global formal correctness, empirical superiority, distributed correctness writers, or production hardening.

## Architectural choice

Use one canonical policy subsystem layered onto the existing `PlanKernel` through the same single serialized correctness writer used by Waves 2–4. Policy objects never become independent world-truth authorities: they reference current canonical state, principal information/access state, proof lineage, action-space and certificate revisions.

Wave 5 is split into two coupled layers:

1. **5A — Sealed Policy Semantics**: information partitions, decision epochs, reveal/frontier contracts, policy nodes, non-anticipativity, advisory selection records, decision sufficiency and PlanSeal.
2. **5B — Executable Policy Certificates**: recursive recall, successor totality, edge stitchability, reveal-to-dispatch reaction envelopes, multi-axis preparedness, N-way proof-context composition, continuation contracts and a scope-bound executability assessment.

The release cannot claim Wave-5 closure unless both layers are integrated with snapshot/replay and the authorization path.

## 5A — Information and policy control structure

### `InformationPartitionRevision`

A principal-scoped derived planning semantic. It binds mission, decision epoch, principal scope, access revision, observation/delivery history, canonical state, observable/hidden predicates, information-equivalence classes, reveal events, observation-model refs, recall basis, debt and validity regime.

Two histories may share a policy decision only while they are information-equivalent for the bound decision principal. Runtime-global knowledge is never sufficient to refine a principal-specific partition.

### `DecisionEpoch`

A semantic decision boundary, not a clock tick and not an authorization. It binds one coherent mission/plan/location/principal/information/action-space/authority/obligation/risk/frontier/temporal snapshot. Stale context rejects the epoch. Only an epoch reachable through a sealed contingent policy may support strong preparedness/executability claims.

### `RevealEvent` and `ObservationFrontierRevision`

Reveal contracts describe when previously indistinguishable histories may legally split. The frontier is principal-relative when availability differs by principal and records current/pending observations, latest safe observation times, costs, side effects, dependencies and unobservable/conditional predicates.

A policy split before a grounded reveal is anticipatory. A discriminator that arrives after the reaction window cannot justify the branch-specific action.

### Non-anticipativity validator

For each epoch + information class, all histories must choose identical action semantics until a grounded discriminator available to the decision principal can distinguish them. A violation is explicit `NONANTICIPATIVITY_VIOLATION`; incomplete information modeling yields debt, never silent feasibility.

### `PolicyNodeRevision`

A sealed policy artifact referencing exact canonical revisions. It binds mission, decision principal, location, information partition, epoch, action space, candidate/selected action contracts, execution-principal requirement, runtime guards, observation frontier, successor mapping, shared commitments/resources, obligations, risk, authority, route guarantee, preparedness, proof context, assurance and debt.

A policy node is never a new world fact and has no external action authority by itself.

### `SelectionRecord`

Selection is advisory only. The record binds the frozen decision transaction, candidate digest, principal/information context, hard-admissibility manifest, route/measure/risk/Pareto/survival/debt/tie semantics and staleness dependencies. Status is only `ADVISORY | STALE | SUPERSEDED`; `AUTHORIZED` is structurally impossible.

Hard rejection stages are monotonic: no later utility or commitment-pressure stage may resurrect a candidate rejected by an earlier hard stage.

## Plan sealing and decision sufficiency

### `DecisionSufficiencyCertificate`

Provides bounded, scope-specific evidence that the current capsule/action dependency surface includes the decision-relevant state, obligations, debt, transition/observation versions, principal scope/access, risk policy and known adequacy limits. It is not a global minimality proof.

### `PlanSeal`

The seal is the boundary between planner idea and correctness artifact eligible to participate in consequential authorization. It binds exact plan root, mission/state, scope, object revision digests, assurance manifest, open/accepted debt, compiler-pass manifest, invariant digest, validity regimes, sequence and expiry/recheck conditions.

No self-promotion is allowed. A model-generated artifact starts DRAFT; stronger assurance requires independent structural/grounding/checking/verification evidence appropriate to the configured floor.

Sealing is compositional: only objects in the action-relevant semantic closure must meet the required floor. Unrelated far-future drafts do not block a near-horizon action.

## 5B — Bounded executable-policy certificates

### `DecisionRecallCertificate`

Certifies decision-relevant recursive history sufficiency over a declared policy/horizon/model scope. Current-action equality alone is insufficient: action-conditioned downstream transition, observation capability, obligations, resources/authority, risk, action-space and continuation signatures must remain equivalent. Missing proof becomes recall debt.

### `PolicyTotalityCertificate`

For each reachable policy action node, modeled post-action state/observation/timing/residual support must be covered by a successor, reconciliation handler or legitimate residual handler. A supported uncovered outcome produces a typed `MissingSuccessorCounterexample`. Solver UNKNOWN/unsupported never means total.

### `PolicyEdgeCertificate`

Certifies parent post-support + edge guard refines child entry contract, including mission, location, information/recall, obligations, resources, authority, risk, temporal window, side-effect state, action-space, adequacy and preparedness. Individually valid nodes do not imply a valid edge.

### `DecisionReactionEnvelope`

Models the full reveal-to-effect pipeline: reveal, ingestion, canonical commit, relocation, capsule compile, model/solver, verification, authorization, dispatch and effect latency. Event time is not decision availability time. Strong guarantees require a configured controllability class; omitted stages are explicit NOT_APPLICABLE rather than zero.

### `PreparednessProfile`

Preparedness is a revocable multi-axis property: recognition, trigger, observation, recall, routing, action contract, authority, resource, temporal reaction, recovery, coherence, proof context, continuation and model-adequacy/debt. Derived P-levels are shorthand only. AND/sequence, OR, K-of-N and contingency aggregation follow structure and independence/coexistence rules.

### Global ProofContext composition

Seal compilation performs N-way composition over assumptions, scope, guarantee, assurance, debt, risk, authority, resources, external regimes and validity horizon. Pairwise compatibility is not sufficient. Results are `COMPOSABLE`, `COMPOSABLE_WITH_ACCEPTED_DEBT`, `NONCOMPOSABLE_CONFLICT`, `COMPOSITION_UNKNOWN` or `UNSUPPORTED_CONSTRAINT_THEORY`, with diagnostic conflict lineage where possible.

### `InformationCapabilityRevision`

Represents decision-critical future observation capability as a planning resource, principal-scoped when required. Actions that destroy the only future discriminator reduce policy feasibility unless an information-independent continuation or protected alternative exists.

### `ContinuationContract`

Every certified horizon endpoint has explicit terminal semantics: `MISSION_COMPLETE`, `SAFE_HANDOFF`, `DEFERRED_CONTINUATION`, `RECOVERY_BOUNDARY`, or `UNKNOWN_TERMINAL`. Route/executability/preparedness guarantees stop at the certified horizon. Deferred continuation carries explicit debt; SAFE_HANDOFF requires sufficient refinement lead time/capability/fallback but its repeated-liveness proof remains Wave 6.

### `PolicyExecutabilityAssessment`

Runtime-owned, exact-scope assessment with status `EXEC_UNANALYZED | EXEC_PARTIAL | EXEC_BOUNDED | EXEC_BOUNDED_WITH_ACCEPTED_DEBT | EXEC_NOT_EXECUTABLE | EXEC_UNKNOWN`.

`EXEC_BOUNDED` requires one coherent semantic snapshot with valid mission/action-space, non-anticipativity, recall, totality, edge refinement, resource/shared commitments, information capability, reaction timing, preparedness, global proof-context composition, route guarantee, debt policy, continuation semantics and fresh seals/certificates.

No model confidence, branch count, token count or plan length may directly promote executability.

## Kernel integration

Wave 5 adds a `policy_runtime` extension using the exact `PlanKernel._writer_lock`.

Consequential proof-carrying authorization becomes a layered gate:

1. principal/authority/freshness checks from Waves 2–4;
2. current DecisionEpoch + principal information/access compatibility;
3. current advisory SelectionRecord for the candidate;
4. current DecisionSufficiencyCertificate for capsule/action scope;
5. valid PlanSeal containing the candidate closure;
6. `PolicyExecutabilityAssessment` at the required policy floor for actions whose strong claim depends on contingent policy;
7. existing `authorize_strong` / proof-carrying action binder creates the actual external authority.

No policy/selection/seal object directly dispatches or bypasses the existing Action Binder.

## Persistence and replay

Snapshot schema advances to v5. The v5 layer wraps v4 proof recovery instead of duplicating it. Durable policy objects, certificates, invalidation state and authorization bindings are internally digest-verified. Post-snapshot policy events replay through direct canonical reducers without appending journal entries again.

Replay must preserve:

- principal-relative information classes;
- stale/non-anticipative status;
- selection advisory/stale state;
- seal validity/debt;
- recall/totality/edge/reaction/preparedness/composition/continuation certificates;
- the same executability assessment on the same journal/receipts.

Any unsupported or inconsistent policy event fails closed with `ReplayError`.

## Test strategy

Every task uses RED → GREEN. Required model-free/adversarial fixtures include:

- information-equivalent histories cannot choose different actions before reveal;
- global kernel observation unavailable to principal cannot split policy;
- lossy history aliasing fails recursive recall;
- supported TIMEOUT/RESIDUAL with no successor fails totality;
- generic `else continue` cannot launder residual totality;
- parent and child sealed independently but incompatible entry contract fail edge stitchability;
- reveal before deadline but full reaction pipeline after last safe dispatch fails strong timing;
- OR versus AND preparedness aggregation differs and common dependencies block redundancy uplift where relevant;
- pairwise-compatible but globally inconsistent proof contexts fail seal composition;
- action destroying unique future information channel damages executable policy;
- abstract goal basin without continuation cannot extend executable horizon;
- `SelectionRecord` cannot become authorization;
- unsealed/stale seal cannot support consequential authorization;
- principal/access/reveal change stales policy artifacts;
- snapshot/replay cannot resurrect stale policy authority.

The final Wave-5 release adds a deterministic adversarial oracle and constitutional mutation gate before `0.5.0a1` can merge.

## Explicit Wave-6 boundary

Wave 5 intentionally does not claim the v0.6 additions: joint shared-capacity reaction schedulability (`ControlPlaneResourceRevision`, `ReactionJobContract`, `ReactionSchedulabilityCertificate`), repeated SAFE_HANDOFF liveness/progress, activation-time edge stability and robust option-independence/common-mode closure. Those become Wave 6 so each closure level has a testable release boundary.
