# Wave 7 — Durable Lineage & Migration Closure Design

## Status

Implementation design for the bounded Nolane Plan v0.15 reference runtime. This wave closes the remaining durable-lineage, semantic-regime, migration, replay and compaction semantics identified in `docs/SPEC-COVERAGE.md`. It does not expand Nolane Plan into a generic database, distributed transaction system, identity provider or orchestration platform.

## Source-of-truth contracts

Wave 7 implements these normative v0.15 requirements:

- immutable canonical revisions have stable logical identity and exact immutable revision identity;
- causal ordering is journal/sequence based, never inferred from wall time;
- correctness-significant references bind exact revisions when stale meaning can change authority;
- mission, plan, world-model, schema and environment/tool validity regimes are explicit;
- graph merge/compaction preserves parent/provenance/debt/evidence/resurrection lineage rather than overwriting history;
- semantic migrations give every changed correctness surface an explicit disposition: `PRESERVED_EXACTLY`, `RECOMPUTED_FROM_CANONICAL_INPUTS`, `INVALIDATED_REQUIRES_RECHECK`, `ESCALATED_TO_DEBT`, `ARCHIVED_READ_ONLY` or `UNSUPPORTED_FAIL_CLOSED`;
- silent migration defaulting is forbidden;
- migration manifests bind source/target schema versions, object/field/identity mappings, checked invariants, revoked certificates, new debt, replay fixtures, rollback/backup procedure and unsupported legacy cases;
- migration cannot reinterpret an ambiguous in-flight external action without reconciliation or a verified bridge;
- rollback of storage semantics never pretends to roll back external effects;
- replay is deterministic for supported correctness-significant journal events and unknown events fail closed;
- storage compaction may remove only rebuildable/duplicate representation while canonical history is retained or archived under an explicit reconstructability contract;
- age alone cannot delete a unique fallback or dormant/resurrection lineage.

## Problem in the current runtime

The v0.6 runtime has strong local revision objects in later layers and a durable hash journal/snapshot chain, but the semantics are fragmented:

1. older canonical objects such as `MissionContract`, `FutureFamily`, obligations and strategic location use family-specific IDs/versions without one common immutable lineage contract;
2. later Wave-5/6 objects have strong `revision_id`/digest semantics, but those semantics are not registered in one kernel-owned lineage graph;
3. semantic regime identity is represented in several object-specific fields but there is no single registry that can answer which schema/world/environment regime an authoritative revision was created under;
4. replay is layered across `resume.py`, trust, proof, policy and schedulability recovery. Each layer is fail-closed, but the full set of correctness-significant event types is not declared in one reducer registry and several base-kernel mutation events remain snapshot-only;
5. migration support is bounded to hand-coded snapshot-version conversions and does not expose the required disposition/manifest/differential-replay contract;
6. there is no explicit graph-compaction manifest proving retention/reconstructability of canonical lineage.

Wave 7 closes these seams with sidecar canonical metadata rather than rewriting every existing dataclass constructor.

## Architecture

### 1. `CanonicalLineageRevision`

New module: `src/nolane_plan/lineage.py`.

A sidecar immutable revision binds a strategic object to the universal canonical identity contract:

```text
object_family
logical_id
revision_id
schema_version
created_sequence
created_at_wall_time?          # informational only
mission_revision_dependency?
plan_revision
world_model_revision
environment_regime_revision
validity_regime
parent_revision_ids[]
provenance_refs[]
assurance_profile
debt_refs[]
supersedes_revision_id?
semantic_digest
lineage_digest
```

`semantic_digest` is the canonical digest of the authoritative object semantics supplied by its owner module. `lineage_digest` binds that semantic digest plus the lineage envelope.

Rules:

- `(object_family, logical_id)` is the stable conceptual identity;
- a `revision_id` is immutable and cannot be rebound to different content;
- revision IDs are globally unique within the registry to avoid cross-family aliasing;
- a new revision for a logical object either supersedes the current revision or is explicitly historical/non-current;
- every parent revision must already exist unless the record is an explicit imported legacy root;
- parent relationships are acyclic;
- created sequence is monotonic causal metadata and cannot be replaced by wall-clock order;
- parent/provenance/debt refs are canonicalized deterministically;
- lineage never creates action authority.

### 2. `SemanticRegimeRevision`

The same module owns explicit revisions for correctness regimes:

```text
regime_kind = SCHEMA | WORLD_MODEL | ENVIRONMENT | CANONICALIZATION | SEMANTIC_PROFILE
logical_id
revision_id
created_sequence
parent_revision_id?
semantic_digest
provenance_refs[]
```

The runtime maintains one current revision for each required regime kind. Changing a regime creates a new immutable revision; it never mutates the previous record in place.

The initial Wave-7 runtime uses bounded defaults created by the host/kernel (`schema:nolane-plan:v7`, `world-model:default`, `environment:default`, etc.) and records that provenance. These defaults are explicit regime identities, not claims that the external environment is known or unchanged.

### 3. `LineageRegistry`

Kernel-owned, single-writer sidecar registry:

- immutable history by revision ID;
- current pointer by `(object_family, logical_id)`;
- current semantic-regime pointers;
- exact lookup and current lookup;
- cycle/identity/rebind validation;
- deterministic semantic root digest over current pointers + regime revisions;
- snapshot codec with internal digest verification.

The registry is installed after existing Wave-6 runtime extensions. Existing objects remain source-of-truth for their family semantics; lineage is canonical metadata binding those semantics, not a second mutable truth store.

### 4. Integration strategy

Do not add dozens of required constructor arguments to every old dataclass. Instead register lineage at canonical mutation boundaries under the existing `_writer_lock`.

Wave-7 registration covers correctness-significant families already present in the runtime, including:

- mission revision;
- canonical state revision;
- future family;
- strategic obligation;
- information item / evidence record where used by strategic authority;
- strategic location;
- Decision Cut / artifact binding / Decision Capsule;
- authority grant / action intent / authorization / receipt / transaction;
- principal identity/access/delivery evidence;
- proof input/manifest/query/support/semantic source artifacts;
- DecisionEpoch/information partition/frontier/policy node/selection/sufficiency/seal/executability;
- control-plane resource/job/schedulability/liveness/stability/coverage/independence artifacts.

A bounded adapter function maps each existing object to a deterministic semantic digest and lineage dependencies. Objects that already expose a canonical digest use it directly; legacy objects use the canonical serialization of their semantic fields.

### 5. Authority lineage binding

New action authorization does not gain a new authority source. Instead, authority-bearing paths record the exact current lineage revision IDs for the object families already required by that path.

At minimum, Wave-7 strong/sealed/schedulable authorization binds:

- mission lineage;
- canonical-state lineage;
- acting-principal lineage;
- action-intent lineage;
- selected policy/seal lineage when present;
- proof lineage when present;
- Wave-6 schedulability prerequisites when present;
- current semantic-regime bundle.

Before dispatch, exact bound revisions/regimes must remain current or the action is rejected/revalidated through the existing authority pipeline. The lineage layer itself never issues an authorization.

### 6. Semantic migration

New module: `src/nolane_plan/migration.py`.

Core types:

- `MigrationDisposition` exact six-value enum;
- `FieldMigrationDisposition`;
- `ObjectMigrationRule`;
- `IdentityMapping`;
- `MigrationManifest`;
- `MigrationAssessment` / `MigrationResult`;
- `MigrationError`.

A manifest is valid only if:

- source/target schema revisions are explicit and differ;
- every declared changed correctness field has exactly one disposition;
- no correctness field silently disappears;
- identity mappings are explicit where logical/revision identity changes;
- invalidated certificates/authorizations and introduced debt are explicit;
- unsupported legacy cases are fail-closed;
- manifest canonical digest is deterministic.

`PlanKernel.apply_semantic_migration(...)` executes under the one correctness-writer lock. It rejects migration while an external action is in an ambiguous/in-flight state unless a verified migration bridge is supplied. The bounded reference implementation will prefer fail-closed and recheck/reseal over attempting clever cross-schema authorization transport.

Migration root switch is a single journaled canonical mutation. Failure before root switch leaves the old root authoritative; failure after a durable root switch is recovered from the journal.

### 7. Replay reducer registry

New module: `src/nolane_plan/replay_registry.py`.

The current layered replay functions remain reusable, but Wave 7 introduces an explicit registry of supported correctness-significant event types. Every event is classified as:

- `STATE_REDUCER` — must deterministically reconstruct canonical state;
- `DERIVED_RECOMPUTE` — canonical inputs replay, derived view is rebuilt;
- `AUDIT_ONLY` — immutable history with no current-state mutation;
- `SNAPSHOT_BOUNDARY`;
- unsupported => fail closed.

Wave 7 adds exact reducers for base-kernel events currently missing from post-snapshot replay, including mission/principal/information/evidence/future/obligation/action/grant/adapter/region/resource/location/recovery/completion mutations as applicable. Existing trust/proof/policy/schedulability reducers are registered/delegated rather than duplicated.

The same journal + same snapshot prefix must produce the same canonical semantic digest.

### 8. Snapshot v7

New outer recovery layer persists:

- lineage registry and current pointers;
- semantic regime registry;
- authorization-lineage bindings;
- migration manifests/history/current schema root;
- compaction manifests/archive index;
- replay registry version/digest.

The v6→v7 migration does not invent strong historical ancestry. Legacy objects are imported as explicit legacy roots with provenance `snapshot-v6-import`; where exact historical parentage is unavailable, the lineage record carries explicit legacy/opaque debt or authority-bearing artifacts are marked recheck-required. Historical receipts are retained. Existing authorizations do not silently become portable merely because the object bytes loaded.

### 9. Reversible compaction lineage

New module: `src/nolane_plan/compaction.py`.

`CompactionManifest` describes a representation rewrite:

```text
compaction_id
source_root_digest
target_root_digest
archived_revision_ids[]
retained_revision_ids[]
rebuildable_index_refs[]
dormant_resurrection_refs[]
evidence_refs[]
debt_refs[]
unique_fallback_refs[]
parent_lineage_digest
reconstruction_digest
created_sequence
```

Rules:

- no canonical revision referenced by active authority, dormant resurrection, debt/evidence/proof lineage or unique fallback may be destructively discarded;
- canonical revisions may be archived read-only, not identity-reused;
- compaction cannot alter mission revision or semantic regime;
- reconstruction from retained + archive lineage must reproduce the pre-compaction canonical semantic digest for the certified scope;
- parent cycles/aliases fail closed;
- compaction does not create or strengthen authority;
- duplicate renderings and rebuildable indexes may be dropped freely because they are nonauthoritative.

### 10. DecisionEpoch lineage completion

Wave 5 created principal/access/partition/action-space/temporal binding. Wave 7 sidecar lineage additionally binds each DecisionEpoch to exact current mission, canonical-state, strategic-location, information-regime and semantic-regime revisions used to derive it. This closes the coverage-ledger row that remained PARTIAL without changing the Wave-5 object’s action-authority semantics.

## Failure-driven conformance

Wave 7 will implement a deterministic adversarial suite grouped as:

### Lineage (`LG`)

- logical identity reused for a different concept;
- revision ID rebound to different semantic content;
- certificate/authority binding only logical ID while current revision changed;
- parent lineage cycle;
- merge/compaction drops parent provenance;
- wall-clock ordering substituted for writer sequence;
- schema/world/environment regime drift ignored;
- DecisionEpoch reused across changed causal/regime lineage.

### Migration (`MG`)

- missing disposition for changed correctness field;
- silent default/empty substitution;
- identity mapping omitted;
- debt disappears;
- certificate/authorization survives semantic change without recheck;
- migration during ambiguous external action;
- journal semantic order changes;
- migration mapping itself creates authority;
- rollback forgets external receipt/effect history;
- unsupported legacy case guessed instead of fail-closed.

### Replay (`RP`)

- post-snapshot base mutations replay exactly;
- unknown correctness event fails closed;
- same journal produces same canonical semantic digest;
- v6 import deterministic and authority-conservative;
- stale lineage does not resurrect current authority;
- exact historical revision remains queryable after restart.

### Compaction (`GC`)

- compaction changes mission/regime;
- parent refs lost;
- dormant/resurrection refs lost;
- proof/evidence/debt refs lost;
- unique fallback deleted by age policy;
- revision ID aliased/reused;
- reconstruction digest differs;
- representation-only compaction changes authorization result.

The exact registry count will be frozen in `wave7_conformance.py` before release and mutation-tested.

## Mutation gate

At least twelve constitutional mutants must be target-specifically killed:

1. revision-rebind bypass;
2. parent-cycle bypass;
3. semantic-regime freshness bypass;
4. logical-only authority binding;
5. migration silent-default bypass;
6. migration debt-drop bypass;
7. ambiguous-action migration bypass;
8. migration-authority promotion bypass;
9. replay unknown-event bypass;
10. replay semantic-digest bypass;
11. compaction lineage-retention bypass;
12. compaction reconstruction/authority-equivalence bypass.

## Release target

Wave 7 release candidate: `0.7.0a1`.

Release requires the same exact commit to pass on Python 3.11/3.12/3.13:

- all existing 334 tests;
- all new Wave-7 tests;
- compile;
- principal collision oracle `108 -> 0`;
- Wave 2–7 adversarial conformance;
- Wave 3–7 mutation gates;
- end-to-end demo;
- deterministic v6→v7 migration fixture;
- exact release-head CI, PR synthetic-merge CI and final-main CI.

## Claim boundary

Wave 7 can close durable lineage/migration/replay/compaction only for the bounded reference runtime and its declared strategic object/event families. It does not prove production crash safety for every storage engine, distributed consensus, global formal correctness or empirical planning superiority. Wave 8 remains responsible for broader property/metamorphic/chaos/differential exhaustion, benchmark worlds and the final spec-to-code coverage audit.