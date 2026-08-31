# Changelog

## 0.7.0a1 — 2026-08-31

- Added `CanonicalLineageRevision`, `SemanticRegimeRevision` and a kernel-owned immutable lineage registry with stable logical identity, globally owned exact revision IDs, causal writer sequence, parent/provenance/debt lineage and deterministic semantic-root hashing for declared strategic runtime families.
- Added explicit schema, world-model, environment, canonicalization and semantic-profile regime revisions. Authority-bearing paths now bind exact current regime revisions rather than relying on implicit validity strings alone.
- Completed DecisionEpoch and authority lineage sidecars across mission/canonical/action, proof, policy and schedulability surfaces. Exact lineage drift is checked before dispatch; representation-only compaction does not spuriously invalidate semantically equivalent authority.
- Added typed semantic migration with the exact six disposition vocabulary, explicit identity mappings and debt declarations, conservative authorization invalidation/recheck, rollback/external-effect provenance and verified migration bridges for ambiguous in-flight external actions.
- Added a frozen replay registry covering every correctness-significant `_record(...)` event emitted by the bounded runtime. Missing base reducers were closed, existing Wave 3–6 reducers are delegated, causal replay is sequence-driven and unknown correctness-significant events fail closed.
- Added snapshot schema v7 with canonical lineage/regime/migration/compaction/replay-registry/authority state and conservative deterministic v6 import. Legacy authority becomes recheck-required when exact historical ancestry cannot be established; historical receipts/revisions remain immutable and queryable.
- Added representation-only reversible compaction with read-only lineage archives and reconstruction manifests. Active authority lineage, dormant/resurrection refs, proof/evidence/debt refs and unique fallbacks are protected from destructive discard or revision-ID reuse.
- Added the exact 32-case Wave-7 adversarial taxonomy: LG01–08, MG01–10, RP01–06 and GC01–08.
- Added a 12-mutation Wave-7 constitutional gate covering revision rebinding, parent cycles, regime freshness, logical-only authority binding, migration silent-default/debt/ambiguous-action/authority-recheck bypasses, replay fail-closed/freshness bypasses and compaction lineage/authority-equivalence violations.
- Python 3.11/3.12/3.13 CI now gates 408 unit/integration tests, compile, the original `108 -> 0` principal oracle, all Wave 2–7 conformance, Wave 3–7 mutation gates and the end-to-end demo. Task-8 exact-head evidence is Wave7 `32/32` and `12/12` on all matrix entries.
- Wave 7 remains a bounded reference-runtime closure. Property/metamorphic/chaos/differential exhaustion, every historical schema-pair migration, arbitrary destructive production-storage compaction, distributed correctness, production hardening, formal global proof and empirical superiority remain outside this release claim.

## 0.6.0a1 — 2026-08-30

- Added canonical `ControlPlaneResourceRevision`, `ReactionResourceDemand`, `ReactionJobContract` and reservation semantics so verifier/model/rate-limit/human/kernel-writer capacity can participate in policy reaction guarantees instead of being treated as free parallel infrastructure.
- Added `ReactionSchedulabilityCertificate` with explicit RS0–RS4 levels, joint cohort analysis, coexistence/mutual-exclusion handling, overload witnesses, model-adequacy debt and exact job/resource revision freshness. Per-job feasibility no longer implies a strong joint guarantee.
- Extended the planning budget governor with protected deadline-critical capacity. Mandatory work plus protected reaction demand fails closed on oversubscription; speculative/background expansion cannot borrow reserved correctness capacity before release.
- Added `ContinuationProgressRank`, `HandoffProgressPolicy` and `HandoffLivenessCertificate` for repeated `SAFE_HANDOFF`. Handoff count, total deferral, ordinary/recovery stutter and grounded absolute deadlines are bounded; semantic renaming and equivalent-debt churn do not count as progress.
- Hardened handoff progress against HL03 laundering: executable-horizon advance is not credited when critical continuation debt or remaining synthesis workload regresses, and the certificate exposes stable `progress_rank_regression` diagnostics.
- Added `HandoffStabilityContract` and `EdgeActivationAssessment` for activation-time generation, permission, reservation/lock, external-writer and open-side-effect freshness. Opacity remains UNKNOWN and explicit refresh is required before stale child entry can become usable.
- Added `ExecutablePolicyCoverageAssessment` so policy totality over modeled support remains distinct from transition/observation-model adequacy and residual/open-world closure.
- Added `OptionIndependenceCertificate` and robust preparedness assessment. Redundancy uplift is failure-set-relative and collapses under shared credentials, network paths, evidence lineage, control-plane overlap, common causes or infeasible co-activation.
- Added revisioned dormant-branch resurrection semantics. Protected catastrophic/sole-route/unique-hedge/information-rich branches cannot be probability-pruned, and resurrection requires current revalidation of mission, assumption/evidence, transition, temporal, resource/capability/authority and risk lineage.
- Integrated Wave-6 prerequisites into `PlanKernel` under the exact existing correctness-writer lock. `authorize_schedulable_policy(...)` rechecks current resource/job/certificate/coverage/liveness/stability/independence lineage and delegates to `authorize_sealed_policy(...)`; Wave-6 objects never mint an independent action authority.
- Added snapshot schema v6 with canonical Wave-6 codecs, immutable revision history plus current logical pointers, exact suffix replay, fail-closed unknown events and bounded v5 migration with empty Wave-6 state rather than invented certificates. Internal digest tampering and stale-resource restart resurrection are rejected.
- Added the exact 43-case v0.6 failure-taxonomy oracle: CP01–12, HL01–12, EF01–08, TM01–05 and OI01–06.
- Added a 12-mutation Wave-6 constitutional gate covering joint-guarantee promotion, coexistence optimism, resource freshness, protected capacity, stutter/deadline/debt progress, edge refresh, totality laundering, common-mode independence and replay/restart integrity.
- Python 3.11/3.12/3.13 CI gates 334 unit/integration tests, compile, the original `108 -> 0` principal oracle, Wave 2–6 conformance, Wave 3–6 mutation gates and the end-to-end demo. Wave-6 evidence is `43/43` conformance and `12/12` mutations killed on every matrix entry.
- Wave 6 is a bounded reference-runtime closure. Common immutable lineage, full migration/replay exhaustion, graph-compaction lineage, property/metamorphic/chaos/differential exhaustion, production hardening, formal global correctness and empirical superiority were outside that release claim.

## 0.5.0a1 — 2026-08-30

- Added principal-scoped `InformationPartitionRevision`, `DecisionEpoch`, `RevealEvent` and `ObservationFrontierRevision` semantics with explicit non-anticipativity checking; runtime-global or other-principal reveal state cannot silently justify a decision split.
- Added immutable contingent-policy IR with `PolicyNodeRevision`, explicit successor guards and policy-level coherence checks for branch viability and shared-resource conflicts.
- Added frozen `SelectionTransaction` / advisory `SelectionRecord` semantics: hard vetoes precede ranking, deterministic ties use stable IDs, dependency-generation drift stales a record, and selection never creates execution authority.
- Added `DecisionSufficiencyCertificate`, `PlanSeal`, assurance ordering and bounded N-way proof-context composition. Unsupported/unknown constraint theories fail closed, global UNSAT is detected, accepted debt remains explicit, and seal invalidation is monotonic with a recomputed digest.
- Added bounded recursive recall, policy totality and edge-stitch certificates. Missing aliased histories remain unknown, downstream signature mismatches fail recall, generic catch-alls do not launder totality, and invalid parent→child refinement produces a stitch counterexample.
- Added `DecisionReactionEnvelope`, IA0–IA4 reaction classes, structure-aware preparedness aggregation, information-capability preservation checks and explicit continuation/terminal semantics. IA1 possible timing is not promoted to an IA2 bounded guarantee.
- Added exact-scope `PolicyExecutabilityAssessment` with typed `EXEC_*` states. Known policy holes, unresolved recall, stitch failure, inadequate reaction class, stale seals, mixed semantic snapshots, information-capability loss and unaccepted debt cannot silently become `EXEC_BOUNDED`.
- Integrated sealed-policy authorization into the existing single-writer `PlanKernel`. `authorize_sealed_policy(...)` rechecks current principal/access/partition/action-space/selection/sufficiency/seal/executability bindings and delegates to the existing proof-carrying identity/authority path; policy objects never issue dispatch authority independently.
- Added snapshot schema v5 with canonical policy codecs, internal digest verification and fail-closed `policy.*` suffix replay. Stale selections/seals and partial executability do not resurrect after restart; bounded v4→v5 migration starts with empty policy state rather than inventing one.
- Added deterministic 29-case Wave-5 adversarial conformance and a 13-mutation constitutional gate covering non-anticipativity, hard vetoes, selection freshness, recursive recall, totality, global composition, reaction timing, information preservation, continuation horizon, kernel authority, replay digest integrity and seal revival.
- Python 3.11/3.12/3.13 CI gates 248 unit/integration tests, compile, the original 108→0 principal-scope oracle, Wave 2–5 adversarial suites, Wave 3–5 mutation gates and the end-to-end demo.
- Wave 5 remains a bounded reference-runtime closure. Joint control-plane schedulability, repeated handoff liveness, activation-time edge stability and broader future/resource closure remained Wave-6 work.

## 0.4.0a1 — 2026-08-30

- Added `ProofInputEnvelopeRevision` with explicit dependency-capture assurance and a hidden-read firewall; self-reported/opaque capture cannot claim strong completeness.
- Added canonical `QueryDomainRevision` history with separate membership and result-sensitivity generations, plus filter/schema/alias/visibility/snapshot identity for absence and universal claims.
- Added `ProofDependencyManifestRevision` and `DependencyFreshnessVector` binding exact revisions, freshness generations, query-domain digests, semantic/trust/execution profiles and capture gaps.
- Added bounded-DNF `SupportAlternativeSetRevision` semantics with conjunctive clauses, alternative justifications, grounded-root cycle detection and independent-root floors.
- Separated positive support from blocking invalidity so `no blocker` never manufactures authority and active blockers override otherwise valid support.
- Added `SemanticClosureBarrier` sharing the exact kernel writer lock; canonical source mutation and all affected generation advances linearize in one critical section.
- Added proof-carrying kernel authorization through `authorize_proof_carrying`, which rechecks current capture, dependency, query, profile, support and invalidity semantics before issuing authority.
- Added snapshot schema v4 preserving semantic sources, proof inputs, query histories, dependency manifests, support graphs, invalidity causes and proof-authorization lineage with internal digest verification.
- Added fail-closed Wave 4 suffix replay for proof semantic sources, query-domain changes, manifests, support lineage, invalidity state and proof authorization bindings.
- Stale proof authority cannot resurrect across restart; post-snapshot semantic/query drift is replayed before authority is re-evaluated.
- Added deterministic 14-case Wave 4 adversarial conformance covering capture, query freshness, dependency freshness, support algebra, blocking invalidity, kernel authority and replay.
- Added a seven-mutation constitutional gate covering capture assurance, query revision freshness, independent grounding, blocking invalidity, semantic freshness, kernel manifest reuse and replay manifest integrity.
- Python 3.11/3.12/3.13 CI gates Wave 4 adversarial conformance and the Wave 4 mutation gate in addition to all prior Wave 1-3 release gates.

## 0.3.0a1 — 2026-08-30

- Added canonical host/platform `PrincipalAttestation` and durable `PrincipalBindingRevision` identity provenance.
- Principal identity fails closed on source-subject collision, weak assurance, expiry, revocation and historical pre-binding use.
- Added planning-relevant `CommunicationLedger` with `SENT -> DELIVERED -> OBSERVED` semantics; delivery alone never implies recipient knowledge and observation is recipient/time bound.
- Added `DispatchAttestation` binding authorization, transaction, action, adapter revision and exact canonical principal identity before side effects.
- Added transaction-bound `ReconciliationEvidence`; strong reconciliation no longer relies on caller-supplied trust booleans.
- Integrated strong identity/communication/dispatch/reconciliation paths into `PlanKernel` without creating a second correctness writer.
- Added snapshot schema v3 with exact trust-ledger, dispatch-attestation and reconciliation-evidence restoration while preserving v2 core restore compatibility.
- Added fail-closed Wave 3 suffix replay for identity and communication trust events with provenance-digest validation and non-retroactive knowledge reconstruction.
- Added deterministic 12-case Wave 3 adversarial conformance.
- Added a four-mutation constitutional gate covering identity non-retroactivity, OBSERVED-only knowledge, authorization/binding continuity and execution-evidence snapshot durability.
- Python 3.11/3.12/3.13 CI gates unit tests, compile, principal-scope oracle, Wave 2 conformance, Wave 3 conformance, Wave 3 mutation gate and end-to-end demo.

## 0.2.0a1 — 2026-08-29

- Added prefix-closed `DecisionCutRevision` authority views for causal decision consistency.
- Added authority-time `ArtifactRegistry` freshness so dependency mutation stales proofs immediately.
- Bound Decision Capsules and ActionAuthorizations to causal cuts and optional adapter capability revisions.
- Added adapter principal-attestation / dispatch-fence / postcondition-assurance profiles.
- Added durable action transactions with pre-effect `DISPATCH_RECORDED`, `RECONCILIATION_REQUIRED`, and trusted reconciliation.
- Non-idempotent actions cannot blind-retry after an ambiguous external outcome.
- Integrated universal-query completeness, preparedness and reaction-window schedulability into consequential authorization gates.
- Integrated strategic relocation after canonical commits; `UNLOCATED` enters model-class uncertainty rather than choosing a convenient branch.
- Completion reports are now proof artifacts bound to decision cuts and freshness dependencies.
- Added snapshot schema v2, journal-prefix binding, semantic-state restoration and fail-closed post-snapshot replay through `PlanKernel.open()`.
- Added deterministic 10-case Wave 2 adversarial conformance and made it a Python 3.11/3.12/3.13 CI gate.

## 0.1.0a1 — 2026-08-29

- Initial full reference-runtime wave for Nolane Plan v0.15.
- Strategic future lattice with `NULL_WORLD`, bounded factorized compiler and convergence certificates.
- Principal-scoped information partitions, Decision Capsules and hydration firewall.
- Principal-bound authority grants/authorizations, dispatch identity checks and execution receipts.
- Condition-centric obligations, evidence lineage, temporal/handoff liveness, shared reservations.
- Freshness-domain dependency manifests, strong universal-query completeness receipts.
- Safe pruning/resurrection, preparedness floors, state relocation and mandatory-first planning budget.
- Hash-chained persistence, snapshot integrity, end-to-end PlanKernel, CLI demo and conformance oracle.
- Deterministic bounded v0.14→v0.15 collision reproduction: 108 → 0.
