# Wave 7 — Durable Lineage & Migration Closure Implementation Plan

> Execute with strict RED → GREEN → refactor discipline. No Wave-7 correctness primitive reaches `main` without exact-head, PR synthetic-merge and final-main CI evidence.

## Goal

Close the remaining v0.15 durable-lineage, semantic-regime, migration, replay and reversible-compaction contracts for the bounded Nolane Plan reference runtime while preserving the existing one serialized correctness writer and all Wave 2–6 authority semantics.

## Baseline

- base/main SHA: `5b284fbbc519e887238a4a791d52823bf3dda5d4`
- release baseline: `0.6.0a1`
- baseline tests: 334
- Wave 6 final-main run: `33311063142`, Python 3.11/3.12/3.13 GREEN
- working branch: `wave7-durable-lineage-migration-closure`

## Task 1 — Canonical lineage primitives

**Create**
- `src/nolane_plan/lineage.py`
- `tests/test_wave7_lineage.py`

**RED tests first**

1. stable logical identity can have immutable ordered revisions;
2. revision ID cannot be rebound to different semantic digest;
3. revision ID cannot alias another object family/logical ID;
4. parent revision must exist unless explicitly imported legacy root;
5. parent cycle fails closed;
6. current pointer changes only to a valid new revision;
7. created sequence cannot move backwards within a logical lineage;
8. parent/provenance/debt refs canonicalize deterministically;
9. lineage digest changes on any correctness-significant field;
10. wall-time change alone does not define causal order;
11. exact historical revisions remain queryable after supersession;
12. semantic root digest is deterministic under insertion-order changes.

**GREEN implementation**

Implement:
- `LineageError`
- `CanonicalLineageRevision`
- `SemanticRegimeKind`
- `SemanticRegimeRevision`
- `LineageRegistry`

Use canonical hashing from `nolane_plan.hashing.digest`.

**Focused verification**

`python -m unittest tests.test_wave7_lineage -v`

## Task 2 — Semantic regime registry and kernel integration

**Create/modify**
- `src/nolane_plan/lineage_runtime.py`
- `src/nolane_plan/__init__.py`
- `tests/test_wave7_kernel_lineage.py`

**RED tests**

1. kernel starts with explicit schema/world/environment/canonicalization/profile regime revisions;
2. mission/current canonical state each have lineage roots;
3. adding/revising future/obligation/evidence/action/grant/adapter/region creates immutable lineage sidecars under the exact writer lock;
4. later revision supersedes rather than overwrites history;
5. regime change creates a new regime revision and advances a typed freshness domain;
6. old authority binding fails after relevant environment/schema/world regime drift;
7. lineage objects cannot call dispatch or mint authorization;
8. direct DecisionEpoch sidecar binds current mission/canonical/location/information/regime revisions;
9. same logical object plus changed semantic content cannot reuse an old revision ID;
10. all lineage mutations journal sufficient exact replay payload.

**GREEN implementation**

Install a Wave-7 runtime extension after Wave-6 runtime/recovery. Keep lineage sidecar canonical metadata inside `PlanKernel` and mutate it only under `_writer_lock`.

Create helper registration paths for existing object families instead of changing every public dataclass constructor.

## Task 3 — Typed semantic migration contract

**Create**
- `src/nolane_plan/migration.py`
- `src/nolane_plan/migration_runtime.py`
- `tests/test_wave7_migration.py`

**RED tests**

1. disposition vocabulary is exact six-value enum;
2. changed correctness field without disposition fails;
3. silent `None`/empty default cannot satisfy an unmapped correctness field;
4. identity-changing mapping requires explicit identity mapping;
5. debt cannot disappear silently;
6. unsupported legacy case is fail-closed;
7. manifest digest is insertion-order deterministic;
8. source/target schema revisions must differ and exist;
9. authoritative certificate/authorization defaults to invalidated/recheck across semantic change;
10. migration during `DISPATCH_RECORDED`/`RECONCILIATION_REQUIRED` fails without verified bridge;
11. migration cannot create action authority;
12. rollback metadata retains external receipt/side-effect lineage;
13. migration root switch is journaled atomically under the kernel writer;
14. pre-root-switch failure leaves old schema root authoritative.

**GREEN implementation**

Implement `MigrationDisposition`, field/object rules, identity mappings, migration manifest/assessment and `PlanKernel.apply_semantic_migration`.

Bounded policy: prefer invalidation/recheck over speculative cross-schema authority transport.

## Task 4 — Replay registry and base-event replay closure

**Create/modify**
- `src/nolane_plan/replay_registry.py`
- `src/nolane_plan/lineage_recovery.py`
- possibly small delegation hooks in existing recovery modules
- `tests/test_wave7_replay_registry.py`
- `tests/test_wave7_base_replay.py`

**First inventory journal events**

Programmatically/static-audit every `_record("...")` event in current source and freeze an event registry. Classify each as state reducer, derived recompute, audit-only or snapshot boundary.

**RED tests**

1. every correctness-significant emitted event appears in registry;
2. unknown correctness event fails closed;
3. post-snapshot `mission.created/revised` state replays where supported;
4. principal/access/information/evidence/future/obligation/action/grant/adapter/region/resource/location/recovery mutations replay exactly;
5. same snapshot+journal yields same canonical semantic digest across restart;
6. event ordering is sequence-based and deterministic;
7. current derived indexes may rebuild but cannot change semantic digest;
8. existing trust/proof/policy/schedulability events delegate to existing exact reducers;
9. stale cached status cannot override replayed exact lineage/current pointers.

**GREEN implementation**

Do not duplicate existing reducer semantics. Register/delegate each layer and add missing base-kernel reducers.

## Task 5 — Snapshot v7 and conservative v6 import

**Modify/create**
- `src/nolane_plan/lineage_recovery.py`
- `tests/test_wave7_snapshot.py`

**RED tests**

1. snapshot schema v7 persists lineage/regimes/migration/compaction/replay-registry state;
2. all internal lineage/manifests verify their canonical digests on restore;
3. v6 snapshot imports deterministically;
4. v6 import does not invent historical parents;
5. legacy authority-bearing objects are recheck-required where exact lineage cannot be established;
6. historical receipts remain immutable/queryable;
7. corrupt lineage record fails closed even if outer snapshot digest is recomputed;
8. stale regime after restart cannot resurrect old authorization;
9. current logical pointers and immutable history remain distinct;
10. repeated v6→v7 import of identical bytes yields identical semantic root.

## Task 6 — Reversible compaction lineage

**Create**
- `src/nolane_plan/compaction.py`
- `src/nolane_plan/compaction_runtime.py`
- `tests/test_wave7_compaction.py`

**RED tests**

1. compaction cannot change mission/schema/world/environment regime;
2. active authority lineage cannot be destructively discarded;
3. dormant/resurrection refs are retained;
4. proof/evidence/debt refs are retained;
5. unique fallback cannot be dropped merely due to age;
6. archived revision IDs remain immutable and cannot be reused;
7. parent DAG remains acyclic;
8. representation-only compaction preserves canonical semantic digest;
9. reconstruction from active+archive reproduces source digest;
10. compaction manifest itself is deterministic and exact-sequence bound;
11. compaction cannot create/strengthen action authority;
12. crash/replay around compaction manifest/root switch cannot expose mixed roots.

**GREEN implementation**

Implement archive/read-only lineage and manifests. Do not physically erase canonical revision data in the reference runtime unless reconstructability is independently demonstrated; memory optimization is secondary to semantic closure.

## Task 7 — DecisionEpoch and exact authority lineage closure

**Modify**
- `src/nolane_plan/lineage_runtime.py`
- relevant Wave-5/6 runtime binding dictionaries
- `tests/test_wave7_authority_lineage.py`

**RED tests**

1. DecisionEpoch exact sidecar binds mission/canonical/location/information/regime revisions;
2. selection/seal/proof/schedulability authority binds exact current lineage revisions;
3. changing one bound semantic revision blocks dispatch/requires reauthorization;
4. representation-only compaction that preserves certified semantics does not spuriously change authorization result;
5. migration mapping alone never restores expired/revoked authority;
6. authority history survives restart but current usability is recalculated.

## Task 8 — Wave-7 adversarial conformance and mutation gate

**Create**
- `src/nolane_plan/wave7_conformance.py`
- `tests/test_wave7_conformance.py`
- `scripts/wave7_mutation_gate.py`

Freeze an exact bounded taxonomy across LG/MG/RP/GC failures. Every registry name is unique and exercised exactly once.

Minimum mutation targets:

1. revision rebind;
2. parent cycle;
3. regime freshness;
4. logical-only authority reference;
5. migration silent default;
6. migration debt drop;
7. ambiguous-action migration;
8. migration creates authority;
9. replay unknown event;
10. replay semantic digest;
11. compaction lineage retention;
12. compaction reconstruction/authority equivalence.

Run focused mutation tests and require every mutant killed target-specifically.

## Task 9 — CI and spec-coverage update

**Modify**
- `.github/workflows/ci.yml`
- `docs/SPEC-COVERAGE.md`
- `CONFORMANCE.md`

Add Wave-7 conformance + mutation commands after Wave 6. Change Wave-6 roadmap wording from “pending exact release/main integration” to released/verified. Mark only Wave-7 rows actually proven GREEN.

Do not promote Wave-8 property/chaos/differential/benchmark claims yet.

## Task 10 — Release `0.7.0a1`

Only after all Wave-7 semantics are GREEN:

**Modify atomically in release commit**
- `src/nolane_plan/__init__.py`
- `pyproject.toml`
- `README.md`
- `SECURITY.md`
- `CHANGELOG.md`
- `CONFORMANCE.md`
- `docs/SPEC-COVERAGE.md`

Then:

1. fresh exact release-head CI on 3.11/3.12/3.13;
2. inspect at least one full matrix job log and confirm test/conformance/mutation counts;
3. audit compare to main and exact merge base;
4. open PR;
5. fresh PR synthetic-merge CI 3/3;
6. re-read PR mergeability and race-check main SHA;
7. fast-forward `main` to exact verified feature SHA with `force=false`;
8. fresh exact-main push CI 3/3;
9. only then call Wave 7 GREEN for bounded reference-runtime scope.

## Task 11 — Handoff to Wave 8

After Wave 7 final-main evidence, re-run `docs/SPEC-COVERAGE.md` audit. Wave 8 begins only on remaining PARTIAL/MISSING normative surfaces: property/metamorphic/chaos/differential exhaustion, broader constitutional mutants, bounded reference worlds/benchmarks and final source-spec coverage reconciliation.

## Completion discipline

No statement of “spec exhausted” is allowed during Wave 7. Valid claim after this plan is fully verified is only: **Wave 7 GREEN for the bounded durable-lineage/migration/replay/compaction reference-runtime scope**. Full reference-runtime normative coverage remains conditional on Wave 8 final audit.