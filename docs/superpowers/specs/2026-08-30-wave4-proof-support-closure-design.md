# Wave 4 — Proof Dependency & Support Closure Design

## Source of truth

This wave implements the bounded reference semantics from v0.15 sections 317–326: proof input envelopes, dependency-capture assurance, negative/query-domain dependencies, hermetic correctness procedures, proof dependency manifests, bounded alternative support, positive-support versus invalidity separation, authority-time freshness, semantic mutation linearization, and crash/replay derived-state rules.

## Design constraints

1. Strong dependency completeness is never established by the proof producer's self-report alone.
2. Conservative dependency over-approximation is sound; under-approximation is not.
3. Universal/absence proofs bind query-domain membership and mutation-sensitive query semantics, not only returned members.
4. `ANY_OF([])` is unsupported and `ALL_OF([])` never creates a grounding root.
5. Support is bounded disjunctive-normal form: one valid conjunctive clause is sufficient; every leaf of a clause is required.
6. Positive support and blocking invalidity are independent axes. Clearing blockers cannot manufacture support.
7. Authority checks exact dependency revisions/generations at use time; cached validity cannot override freshness mismatch.
8. Canonical source mutation and every soundly affected generation advance share one correctness linearization point.
9. Replay may restore canonical proof lineage, but cached derived support/freshness must be rechecked before authority.
10. The core remains bounded; arbitrary truth-maintenance and distributed snapshots remain outside this wave.

## Runtime surfaces

### `proof_inputs.py`

- `DependencyCaptureAssurance`
- `ExternalReadPolicy`
- `ProofInputEnvelopeRevision`
- canonical input digest
- capture-assurance floor and hidden-read validation
- trusted dynamic capture mechanism binding

### `query_domain.py`

- `QueryDomainRevision`
- membership generation plus scope/schema/filter/alias/visibility revisions
- mutation-impact profile and stable query snapshot/completeness binding
- explicit incomplete/opaque status

### `proof_dependencies.py`

- `ProofDependencyManifestRevision`
- `DependencyFreshnessVector`
- exact revision and domain-generation capture
- capture gaps/opacity debt
- strong-reuse eligibility

### `support.py`

- `SupportClause`
- `SupportAlternativeSetRevision`
- `SupportAssessment`
- `SupportStatus`
- `InvalidityCause`
- bounded grounded ANY-OF / ALL-OF evaluation
- context/assumption compatibility
- circular/common-root safeguards needed for authority semantics

### `semantic_barrier.py`

- canonical source revision ledger
- mutation-impact declaration
- one lock/linearization point for source mutation plus affected freshness-domain advances
- conservative global/ancestor bump when exact impact is unknown
- fail closed if impact is unknown and no conservative fallback is declared

### Kernel integration

Wave 4 adds one proof-authority path to the existing single writer:

1. create/capture proof input envelope;
2. register query domain where needed;
3. register proof dependency manifest + support alternatives;
4. evaluate current support/freshness;
5. permit proof artifact to contribute to consequential authorization only if:
   - visible/current cut;
   - strong enough dependency capture;
   - current exact/query/profile dependencies;
   - `SUPPORTED` positive support;
   - no blocking invalidity cause;
6. canonical source mutation advances all affected generations under the same writer lock;
7. old proof becomes unusable immediately without waiting for descendant status rewrites.

## Replay boundary

Wave 4 persists canonical proof lineage needed for current-state reconstruction and rechecks derived support/freshness after restart. It does not claim full-event replay exhaustion; Wave 7 remains responsible for all strategic event types and migrations.

## Verification gates

- hidden-read/self-report adversary
- query new-member / predicate-mutation adversary
- OR/AND support retraction
- empty-support vacuity
- no-support vs no-blocker distinction
- circular support rejection
- source-mutation/authorization ordering race
- crash/reopen freshness resurrection attempt
- deliberate constitutional mutations
- Python 3.11/3.12/3.13 full regression
