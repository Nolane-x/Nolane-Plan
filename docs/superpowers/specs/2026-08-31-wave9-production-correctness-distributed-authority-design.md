# Nolane Plan Wave 9 — Production Correctness & Distributed Authority

Date: 2026-08-31
Status: DESIGN APPROVED IN CHAT; implementation not yet started
Base release: `0.8.0a1`
Base SHA: `8f0288ee2119a05a83923ae16e0ec56b7cbad1c8`
Target release: `0.9.0a1`

## 1. Purpose

Wave 8 closed bounded conformance exhaustion for the single-correctness-writer reference runtime. Wave 9 deliberately expands the correctness boundary in three production-facing directions that are currently explicit boundaries rather than silently assumed guarantees:

1. destructive production-storage compaction;
2. external adapter execution/cancellation capability contracts;
3. bounded multi-writer/distributed authority correctness.

Wave 9 does **not** claim to solve arbitrary open-world completeness, arbitrary unknown historical schemas, universal distributed consensus, formal proof of the whole real world, or empirical superiority. Those remain separate later waves so their evidence cannot be confused with Wave 9 evidence.

## 2. Why this decomposition

Three implementation strategies were considered.

### A. Big-bang frontier closure

Implement all remaining frontiers in one release.

Rejected because it mixes unrelated proof obligations, makes failures hard to localize, and encourages weak aggregate GREEN claims.

### B. Layered production-correctness closure — selected

First harden storage, execution boundary, and multi-writer authority. Then build open-world/schema archaeology, formal assurance, and empirical evaluation as separate waves.

Selected because all three Wave 9 areas share one common invariant: **a correctness-relevant effect must never become authoritative merely because a local process observed or wrote something**. Storage deletion, external side effects, and concurrent writers therefore belong to one production-authority wave.

### C. Adapter-first incremental patching

Only extend cancellation/execution adapters now and defer storage/concurrency.

Rejected because external execution correctness is incomplete if the persistence layer or concurrent writer model can still violate the authority record surrounding the execution.

## 3. Architectural principle

Wave 9 introduces a common durable concept: **Authority Epoch**.

An authority epoch is a monotonically advancing, persistence-backed fencing identity for correctness-relevant mutation. Every production mutation must prove that it is executing under the current epoch before its result may become canonical.

The epoch is not wall-clock time and is not a distributed-consensus claim. It is an explicit compare-and-swap/fencing contract inside a bounded storage backend. Backends that cannot provide the contract are classified `UNSUPPORTED` for strong multi-writer use.

This keeps the existing single-writer kernel semantics as the reference behavior while allowing stronger storage backends to prove that multiple processes cannot silently create two authoritative histories.

## 4. New components

### 4.1 `production_store.py`

Defines the bounded storage capability contract.

Core concepts:

- `StorageCapabilityProfile`
  - atomic replace support;
  - durable fsync/commit support;
  - compare-and-swap revision support;
  - fencing-token support;
  - transactional batch support;
  - destructive-delete support;
  - crash-recovery assurance classification.
- `AuthorityEpoch`
  - epoch number;
  - writer identity;
  - predecessor epoch;
  - acquisition receipt digest;
  - backend revision/token;
  - canonical digest.
- `ConditionalWriteReceipt`
  - expected revision;
  - committed revision;
  - epoch identity;
  - payload digest;
  - durable acknowledgement.
- `ProductionStore` protocol.

The reference filesystem backend remains usable as single-writer. Strong multi-writer mode requires an implementation that proves CAS/fencing semantics; lack of those capabilities must fail closed rather than be inferred from advisory locks.

### 4.2 `destructive_compaction.py`

Adds a real destructive compaction protocol on top of the Wave 7 representation-only compaction machinery.

Protocol phases:

1. `PREPARED`
   - freeze source semantic root;
   - capture active-authority, dormant-resurrection, proof/evidence/debt and unique-fallback retention closure;
   - capture source journal frontier and authority epoch;
   - write immutable compaction intent.
2. `SHADOW_WRITTEN`
   - write compacted target representation to a shadow namespace;
   - reconstruct from target;
   - require semantic-root and canonical-state equivalence;
   - verify retained references are resolvable.
3. `SWITCH_COMMITTED`
   - compare-and-swap the production pointer under the same authority epoch;
   - write a durable switch receipt before any source deletion.
4. `SOURCE_RETIRED`
   - only after a valid switch receipt and recovery barrier may unreachable source representation be deleted;
   - deletion set is exact and digest-bound.
5. `VERIFIED`
   - reopen from production pointer;
   - replay suffix;
   - verify canonical semantic digest and authority usability equivalence.

A crash between any two phases must recover to either the source representation or the fully switched target representation. Mixed authoritative representation is forbidden.

### 4.3 `execution_contract.py`

Extends `AdapterProfile` without pretending that all adapters can physically cancel external work.

New capability dimensions:

- dispatch acknowledgement class;
- idempotency guarantee class;
- deduplication-key support;
- remote fencing-token support;
- cancellation class;
- cancellation acknowledgement assurance;
- compensation support;
- reconciliation observability;
- outcome finality class.

Cancellation classes:

- `PRE_DISPATCH_ONLY`
- `REMOTE_BEST_EFFORT`
- `REMOTE_ACKNOWLEDGED`
- `FENCED_EFFECT`
- `UNSUPPORTED`

Strong semantics:

- pre-dispatch cancellation may be terminal only before durable dispatch;
- after durable dispatch, `REMOTE_BEST_EFFORT` can never produce a clean cancelled state by itself;
- `REMOTE_ACKNOWLEDGED` requires exact transaction/action/adapter/epoch-bound acknowledgement;
- `FENCED_EFFECT` additionally requires evidence that stale/withdrawn epochs cannot commit the external effect;
- ambiguous post-dispatch state remains `CANCELLATION_PENDING` or reconciliation-required;
- compensation is represented as a new effect with its own authority and evidence, never as retroactive erasure of the original effect.

### 4.4 `multiwriter.py`

Defines bounded multi-writer coordination semantics.

Objects:

- `WriterIdentity`
- `WriterLease`
- `WriteIntent`
- `WriteConflict`
- `EpochFenceReceipt`
- `CommitDecision`

Rules:

- only the current epoch holder can create correctness-authoritative journal entries;
- stale epoch writers may compute/read but cannot commit;
- CAS mismatch is conflict, never automatic overwrite;
- duplicate intent with the same idempotency key must converge to one authoritative result;
- conflicting non-idempotent intents require explicit reconciliation;
- writer lease expiry alone does not prove old external effects did not occur;
- a process restart must reconstruct current epoch and outstanding ambiguous effects before issuing new strong authority;
- split-brain simulations must leave at most one canonical commit for an epoch transition.

Wave 9 does not implement universal network consensus. It specifies correctness for a bounded backend that already provides linearizable compare-and-swap/fencing. A backend without that primitive is not promoted to strong multi-writer status.

## 5. Kernel integration

`PlanKernel` remains the semantic owner. Wave 9 must not create a second kernel or second replay engine.

Integration rules:

- existing `_writer_lock` remains the in-process serialization primitive;
- production storage fencing is checked **in addition to**, not instead of, `_writer_lock`;
- journal events for Wave 9 are registered in the existing replay registry;
- snapshot state extends the existing snapshot envelope conservatively;
- Wave 7 lineage remains the source of semantic identity;
- Wave 8 conformance remains mandatory regression evidence.

Expected kernel-facing methods include bounded forms of:

- acquire/renew/release authority epoch;
- conditional correctness commit;
- prepare/commit/retire destructive compaction;
- register adapter execution contract;
- record remote cancellation acknowledgement;
- record compensation intent/outcome;
- reconcile ambiguous external effect.

Exact public names may be adjusted during implementation only if tests and docs are updated atomically; semantics may not be weakened.

## 6. Durable event taxonomy

Proposed correctness-significant events:

- `writer.epoch_acquired`
- `writer.epoch_renewed`
- `writer.epoch_released`
- `writer.conditional_commit`
- `writer.conflict_recorded`
- `compaction.destructive_prepared`
- `compaction.shadow_verified`
- `compaction.production_switched`
- `compaction.source_retired`
- `execution.contract_registered`
- `action.remote_cancellation_acknowledged`
- `action.compensation_authorized`
- `action.compensation_outcome_observed`

Every correctness-significant event must either have a deterministic reducer/delegate in the existing replay registry or be rejected by the existing unknown-event fail-closed rule.

## 7. Destructive compaction invariants

DC01. Active authority lineage is never deleted.

DC02. Dormant/resurrection dependencies are retained until explicitly obsolete under a current proof.

DC03. Proof, evidence, accepted debt and unique fallback references are retained.

DC04. Shadow target reconstruction must reproduce the source semantic root before switch.

DC05. Production pointer switch is conditional on exact source revision + authority epoch.

DC06. Source deletion before durable switch acknowledgement is forbidden.

DC07. Crash before switch reopens source authority.

DC08. Crash after switch reopens target authority and never a mixed representation.

DC09. Repeated retirement is idempotent and cannot broaden the deletion set.

DC10. Tampered deletion manifest fails closed even when outer storage metadata is valid.

DC11. Stale writer cannot retire storage after a newer epoch is current.

DC12. Post-compaction live/replay/reopen canonical projections remain equivalent.

## 8. External execution invariants

EX01. Adapter capability claims are revision-bound and digest-bound.

EX02. Strong dispatch cannot use a weaker adapter revision than authorization bound.

EX03. A remote cancellation acknowledgement must bind exact transaction, action, adapter revision, principal and authority epoch.

EX04. Best-effort remote cancellation never means clean cancellation.

EX05. Fenced-effect cancellation may be clean only when stale epoch effect commit is cryptographically/durably excluded by the backend contract.

EX06. Unknown external outcome remains retry-blocking for non-idempotent effects.

EX07. Compensation is a new action/effect, not history rewrite.

EX08. Compensation failure does not erase original applied outcome.

EX09. Adapter capability downgrade invalidates previous strong execution assumptions.

EX10. Restart preserves pending cancellation/compensation ambiguity.

EX11. Reconciliation evidence from a different epoch cannot close the transaction.

EX12. Unsupported cancellation capability is explicit and fail-closed.

## 9. Multi-writer invariants

MW01. Authority epochs are strictly monotonic.

MW02. A stale epoch cannot append a correctness-authoritative event.

MW03. Two concurrent CAS commits against the same predecessor cannot both become canonical.

MW04. Duplicate idempotent intent converges without duplicate external authority.

MW05. Conflicting non-idempotent intents become explicit conflict/reconciliation state.

MW06. Lease expiration alone never proves an external effect was absent.

MW07. Writer identity is bound into epoch acquisition and commit receipts.

MW08. Epoch reconstruction after restart is deterministic.

MW09. Snapshot + suffix replay agrees with live multi-writer projection.

MW10. Split-brain simulation leaves at most one canonical successor revision.

MW11. Storage backend lacking CAS/fencing is `UNSUPPORTED` for strong multi-writer mode.

MW12. Authority minted under an old epoch is unusable after epoch transition unless explicitly revalidated and rebound.

## 10. Crash and concurrency test matrix

The test suite must use deterministic fault points rather than sleeps or timing luck.

Destructive compaction fault points:

- before intent durability;
- after intent durability;
- during shadow write;
- after shadow verification;
- immediately before pointer CAS;
- immediately after pointer CAS;
- during source retirement;
- after retirement before final verification.

Multi-writer schedules:

- W1 acquires, W2 loses CAS;
- W1 expires, W2 advances epoch, W1 attempts stale commit;
- duplicate idempotent intent from W1/W2;
- conflicting non-idempotent intents;
- restart between epoch acquisition and commit;
- restart with ambiguous external dispatch;
- snapshot under epoch N, suffix under epoch N+1;
- stale compactor versus current writer.

Execution schedules:

- cancel before dispatch;
- cancel after dispatch before remote acknowledgement;
- best-effort cancellation with unknown result;
- acknowledged cancellation with exact binding;
- wrong adapter revision acknowledgement;
- wrong epoch acknowledgement;
- fenced effect under stale epoch;
- compensation succeeds/fails/unknown;
- restart in every durable transaction state.

## 11. Mutation gate

Wave 9 must add target-specific constitutional mutants. A mutant counts as killed only when its declared Wave 9 invariant assertion fails; import errors, syntax errors, timeout or unrelated test failures are invalid kills.

Minimum mutation targets:

- bypass epoch monotonicity;
- allow stale writer commit;
- make CAS last-writer-wins;
- delete active lineage during compaction;
- delete source before switch durability;
- accept mixed source/target recovery;
- treat best-effort cancel as clean;
- accept cancellation acknowledgement from wrong epoch;
- erase original outcome after compensation;
- treat unsupported backend as strong multi-writer;
- resurrect old-epoch authorization;
- accept unknown Wave 9 replay event.

## 12. Coverage and claim discipline

Wave 9 coverage must reconcile every new invariant against implementation, unit/integration tests, crash schedule, replay/restart evidence and mutation evidence.

Allowed statuses remain:

- `GREEN`
- `PARTIAL — <explicit rationale>`
- `RESEARCH`
- `BOUNDARY`

No row may become GREEN from documentation alone.

Wave 9 may claim:

> bounded production correctness for destructive compaction, external execution capability semantics, and multi-writer authority on storage backends that satisfy the declared atomicity/CAS/fencing contract.

Wave 9 may **not** claim:

- universal distributed consensus;
- Byzantine fault tolerance;
- cancellation guarantees stronger than the external adapter exposes;
- correctness on storage engines without the required capability proof;
- arbitrary open-world completeness;
- arbitrary unknown-schema semantic recovery;
- empirical superiority.

## 13. Compatibility

- Existing single-writer filesystem usage remains supported.
- Existing `AdapterProfile` callers remain source-compatible where possible; new execution guarantees default to conservative/unsupported rather than being invented.
- Existing representation-only compaction remains available and semantically distinct from destructive compaction.
- v7 snapshot compatibility remains required; Wave 9 snapshot extensions must have explicit migration defaults that do not invent authority.
- Wave 8 registry/conformance/mutation/coverage gates remain mandatory regression gates.

## 14. Release gates

Wave 9 cannot release until all of the following hold on an exact release head:

1. all historical tests GREEN on Python 3.11/3.12/3.13;
2. Wave 8 full conformance still GREEN;
3. DC01–DC12 GREEN;
4. EX01–EX12 GREEN;
5. MW01–MW12 GREEN;
6. deterministic crash schedules rerun identically;
7. Wave 9 target-specific mutation gate kills every declared mutant with zero invalid kills;
8. coverage audit has no orphan invariant and no evidence-free GREEN row;
9. release-head CI GREEN 3/3;
10. PR synthetic merge CI GREEN 3/3;
11. base/head race-check clean;
12. non-forced fast-forward to `main` when possible;
13. fresh final-main CI GREEN 3/3.

Target release version: `0.9.0a1`.

## 15. Explicitly deferred frontiers

These are intentionally *not* hidden inside Wave 9:

### Wave 10 — Open World & Schema Archaeology

- progressive candidate-universe protocol;
- completeness/residual certificates;
- arbitrary historical schema fingerprinting;
- semantic disposition synthesis;
- quarantine and recheck-required migration.

### Wave 11 — Formal Assurance

- formal state-machine model;
- machine-checked safety/liveness invariants for authority, replay, migration, cancellation and concurrency;
- refinement mapping from implementation-visible events to the formal model.

### Wave 12 — Empirical Evaluation

- reproducible benchmark harness;
- baselines and ablations;
- adversarial workloads;
- statistical reporting;
- superiority claims only when empirical evidence supports them.

This decomposition is a correctness boundary, not a postponement of known Wave 9 defects.