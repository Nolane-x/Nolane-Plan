# Nolane Plan Conformance

This document records the executable bounded conformance surface for the Wave-7 `0.7.0a1` release candidate. It is an evidence ledger, not a claim of global formal correctness or empirical superiority.

## Release gate

A Wave-7 release candidate is acceptable only when the same exact commit passes all of the following on Python 3.11, 3.12 and 3.13:

| Gate | Required result |
|---|---:|
| Unit/integration discovery | 408/408 tests pass |
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
| Wave 7 adversarial conformance | 32/32 |
| Wave 7 constitutional mutations | 12/12 killed |
| End-to-end demo | pass with valid journal |

Task-8 exact head `5f58455d3161ed08cefcde7407e086279c8582ff` already satisfies this executable surface on all three Python versions in CI run `33343969251`. Release-head, PR synthetic-merge and final-main evidence must still be produced after the release/documentation commits.

## Wave 7 taxonomy

`nolane_plan.wave7_conformance` freezes exactly 32 adversarial cases across four bounded failure families:

- `LG01..LG08` — logical identity aliasing, immutable revision rebinding, exact authority revision identity, parent/provenance DAG integrity, writer-sequence causality, semantic-regime drift and DecisionEpoch lineage reuse.
- `MG01..MG10` — missing migration disposition, silent defaulting, omitted identity mapping, disappearing debt, authority survival across semantic change, ambiguous external action migration, journal-order preservation, authority minting, rollback/external-effect retention and unsupported legacy guessing.
- `RP01..RP06` — exact base suffix replay, unknown-event fail-closed behavior, canonical digest reproducibility, conservative v6 import, stale-authority non-resurrection and historical revision queryability.
- `GC01..GC08` — mission/regime invariance, parent retention, dormant/resurrection retention, proof/evidence/debt retention, unique-fallback preservation, archived revision immutability, reconstruction digest equality and authority equivalence under representation-only compaction.

Run directly with:

```bash
python -m nolane_plan.wave7_conformance
```

Required summary: `WAVE7_CONFORMANCE=32/32`.

## Wave 7 constitutional mutations

`scripts/wave7_mutation_gate.py` deliberately weakens twelve production constitutional seams and requires a focused test to kill every mutant:

1. `revision_rebind_bypass`
2. `parent_cycle_bypass`
3. `semantic_regime_freshness_bypass`
4. `logical_only_authority_binding`
5. `migration_silent_default_bypass`
6. `migration_debt_drop_bypass`
7. `ambiguous_action_migration_bypass`
8. `migration_authority_recheck_bypass`
9. `replay_unknown_event_bypass`
10. `replay_semantic_freshness_drop`
11. `compaction_active_lineage_drop`
12. `compaction_authority_equivalence_break`

Run directly with:

```bash
python scripts/wave7_mutation_gate.py
```

Required summary: `WAVE7_MUTATIONS_CAUGHT=12/12`.

The mutation gate fails if a target no longer matches the expected production seam. Conceptually multi-layer invariants such as parent-cycle prevention may require multiple physical edits inside one mutant so redundant guards do not create a false mutation-survival result.

## Durable lineage and semantic-regime conformance

The bounded Wave-7 lineage contract requires:

- stable `(object_family, logical_id)` conceptual identity and immutable globally owned revision IDs;
- deterministic semantic and lineage digests over correctness-significant content;
- parent revisions to pre-exist except explicit conservative legacy roots, with acyclic append-only ancestry;
- causal order from serialized writer/journal sequence rather than wall-clock time;
- exact current schema/world/environment/canonicalization/semantic-profile regime revisions;
- exact lineage sidecars for declared mission/canonical/future/obligation/evidence/action/grant/adapter/region and derived proof/policy/schedulability authority surfaces;
- exact DecisionEpoch and ActionAuthorization lineage binding, with semantic drift rejected before dispatch.

The lineage layer remains authority-neutral: it records and validates identity/ancestry but does not mint independent action authority.

## Migration and persistence conformance

Snapshot schema `nolane-plan-runtime-snapshot-v7` persists lineage history/current pointers, semantic regimes, migration manifests/history/bridges/recheck state, compaction manifests/archives/results, replay-registry identity and authority-lineage closure.

The bounded recovery/migration contract requires:

- internal canonical-digest verification for restored lineage, regimes and manifests;
- deterministic conservative v6→v7 import without invented strong historical parentage;
- imported legacy authority marked recheck-required when exact lineage cannot be established;
- historical receipts/revisions remain immutable and queryable;
- the exact six migration dispositions: `PRESERVED_EXACTLY`, `RECOMPUTED_FROM_CANONICAL_INPUTS`, `INVALIDATED_REQUIRES_RECHECK`, `ESCALATED_TO_DEBT`, `ARCHIVED_READ_ONLY`, `UNSUPPORTED_FAIL_CLOSED`;
- no silent changed-field default, identity remap, debt loss or authority promotion;
- ambiguous/in-flight external action migration fails closed without verified bridge evidence;
- storage rollback metadata never pretends to erase external effect history.

## Replay conformance

The frozen replay registry classifies every correctness-significant event emitted by the bounded runtime as a state reducer, derived recomputation, audit-only event or snapshot boundary. Existing Wave 3–6 reducers are delegated rather than duplicated.

The replay contract requires:

- same supported snapshot prefix + journal suffix => same bounded canonical semantic digest;
- sequence-driven replay independent of wall-clock ordering;
- exact replay of declared base, trust, proof, policy, schedulability, migration and compaction events;
- stale caches/currentness views never outrank replayed canonical inputs;
- unknown correctness-significant events fail closed.

## Reversible compaction conformance

The reference runtime supports representation-only compaction through a read-only archive and reconstructability manifest. It intentionally prefers retention/archive over speculative destructive deletion.

The compaction contract requires:

- mission and semantic-regime roots remain unchanged;
- active authority lineage, dormant/resurrection refs, proof/evidence/debt refs and unique fallbacks cannot be destructively discarded;
- archived revision IDs cannot be rebound or reused;
- parent DAG/provenance remains reconstructable;
- reconstruction reproduces the certified source semantic root and canonical semantic digest;
- compaction cannot create or strengthen authorization, and representation-only rewriting preserves an otherwise-current authorization result.

## Current verification evidence

Task-8 exact head `5f58455d3161ed08cefcde7407e086279c8582ff`, CI run `33343969251`:

- Python 3.11: GREEN all gates;
- Python 3.12: GREEN all gates; inspected full log confirms 408 tests, Wave7 32/32, Wave7 mutations 12/12 and demo success;
- Python 3.13: GREEN all gates;
- principal-scope oracle remains `108 -> 0`;
- all earlier Wave 2–6 conformance and mutation gates remain GREEN.

This is pre-release implementation evidence. The release commit must reproduce the same gate surface at its own exact SHA, followed by PR synthetic-merge and final-main CI.

## Claim boundary

The `0.7.0a1` line may be described as **GREEN for the bounded Wave-7 durable-lineage/migration/replay/compaction reference-runtime scope** only after exact release-head, PR synthetic-merge and final `main` evidence pass.

The repository still does not claim:

- every historical schema-to-schema migration pair;
- arbitrary destructive storage compaction across production storage engines;
- generalized global minimality/exclusion outside the implemented bounded theories;
- distributed correctness writers or consensus;
- a generic scheduler/orchestrator/identity provider/messaging platform;
- property/metamorphic/chaos/differential exhaustion;
- production hardening, formal global proof or empirical superiority.

Those unresolved normative engineering surfaces remain Wave 8 work, research measurement, or explicit non-goal boundaries.
