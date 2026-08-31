# Nolane Plan Conformance

This document records the executable bounded conformance surface for the `0.8.0a1` Wave-8 release candidate. It is an evidence ledger, not a claim of global formal correctness or empirical superiority.

## Release gate

The release candidate is acceptable only when the same exact release commit passes the required matrix and is then reproduced on the pull-request synthetic merge and final `main`.

| Gate | Required result |
|---|---:|
| Unit/integration discovery | 464/464 tests pass |
| Source compilation | pass |
| Principal-scope projection oracle | v0.14 `108` collisions → v0.15 `0` |
| Wave 2 adversarial conformance | 10/10 |
| Wave 3 adversarial conformance / mutations | 12/12 + 4/4 |
| Wave 4 adversarial conformance / mutations | 14/14 + 7/7 |
| Wave 5 adversarial conformance / mutations | 29/29 + 13/13 |
| Wave 6 adversarial conformance / mutations | 43/43 + 12/12 |
| Wave 7 adversarial conformance / mutations | 32/32 + 12/12 |
| Wave 8 unified conformance | GREEN; 0 counterexamples |
| Wave 8 constitutional mutations | 12/12 killed; 0 invalid kills |
| Wave 8 coverage audit | GREEN |
| End-to-end demo | valid journal |

Wave-8 conformance and coverage run on Python 3.11, 3.12 and 3.13. The target-specific X01–X12 mutation subprocess gate runs on Python 3.11; the unit suite that validates mutation-gate semantics remains part of all matrix entries.

Pre-release implementation head `c75cb337f84a1b0ad0477b2f892723fd8ff672a6` passed this matrix in CI run `33361860635`. That run is implementation evidence, not a substitute for exact release-head, PR synthetic-merge or final-main verification.

## Frozen Wave-8 registry

The registry contains exactly 68 invariants:

- P01–P10 — properties;
- M01–M12 — metamorphic relations;
- C01–C10 — deterministic chaos/fault schedules;
- D01–D10 — live/restart/replay differential relations;
- X01–X12 — target-specific constitutional mutants;
- W01–W06 — bounded reference worlds;
- S01–S08 — final coverage and claim reconciliation.

Frozen registry digest:

`d9f4e9fd9cd111c3a458b2018686060b74235102702352230f7546360a942dfc`

Pre-release unified conformance digest:

`7c41aeb2a075a997451e024ccdc53554aada45ad86967242c53706f98fd42f33`

Pre-release coverage digest:

`60019f5f3ff3d723849bb912bbf0f47b187347a6cd676198d537af6f56b5a3dd`

## Property and metamorphic closure

P01–P10 exercise canonical determinism, principal anti-escalation, blocker/support monotonicity, hard vetoes, resource and temporal contraction, semantic authority drift, history preservation and unknown non-promotion.

M01–M12 exercise set-like ordering, non-semantic metadata, irrelevant evidence, common-lineage independence, information-equivalent histories, branch/resource ordering, snapshot/replay, representation-only compaction, deterministic legacy import and migration-manifest canonicalization.

All seeded runners use deterministic bounded recipes and treat runtime exceptions as explicit counterexamples rather than silently skipping a case.

## Chaos and differential closure

C01–C10 exercise invalid/torn snapshots, valid suffix recovery, unknown correctness events, interrupted authority binding, ambiguous durable dispatch, migration pre-switch failure, migration replay without authority resurrection, atomic compaction, stale handoff activation and cancellation/dispatch residual races.

D01–D10 compare live runtime against snapshot reopen, prefix+suffix replay, repeated replay, pre/post compaction, direct vs supported legacy import, live vs replayed migration, principal information restart, proof/policy authority restart, schedulability/liveness restart and relocation ordering/restart.

## Cancellation fence

The bounded durable action protocol distinguishes cancellation before and after durable dispatch:

- `AUTHORIZED -> CANCELLED_PRE_DISPATCH` is terminal and prevents adapter execution;
- `DISPATCH_RECORDED -> CANCELLATION_PENDING` preserves residual ambiguity;
- a pending non-idempotent transaction cannot blind-retry;
- only transaction/principal/adapter-bound reconciliation evidence can classify the external outcome as applied or not applied;
- cancellation state survives snapshot/restart and post-snapshot suffix replay;
- tampered cancellation transitions fail closed.

No claim is made that arbitrary external adapters provide physical cancellation guarantees.

## Relocation, migration and bounded global closure

Relocation exhausts bounded region sets while preserving `LOCATED`, `AMBIGUOUS` and `UNLOCATED`; multiple compatible regions may be located only when their decision signatures agree. Decision-relevant relocation invalidates old decision/authority lineage.

The repository-owned migration matrix covers supported historical snapshot schemas v2 through v6 into v7 conservatively. It does not claim arbitrary external or unknown historical schema compatibility.

Bounded finite complete candidate universes can support explicit global exclusion. Opaque/open candidate universes remain UNKNOWN. N-way proof-context composition checks global intersection rather than inferring composability from pairwise compatibility alone. Unsupported theories fail closed.

## Reference worlds

W01–W06 are checked-in correctness fixtures:

1. Principal Relay;
2. Open-World Recovery;
3. Deadline Resource Contention;
4. Handoff Chain;
5. Migration + Ambiguous External Effect;
6. Dormant Hedge + Compaction.

Their correctness invariants gate the release. Measurements emitted by these worlds are research observations only and do not establish empirical superiority.

## Constitutional mutation gate

X01–X12 deliberately weaken principal anti-escalation, blocker semantics, hard vetoes, resource monotonicity, temporal information deadlines, replay equivalence, unknown-event fail-closed behavior, migration authority invalidation, compaction equivalence, cancellation residual ambiguity, relocation ambiguity and global N-way composition.

A mutant counts as killed only when its declared target assertion fails. Setup, import, syntax, timeout or unrelated failures are invalid kills. Required summary:

`WAVE8_MUTATIONS_CAUGHT=12/12`

`WAVE8_MUTATIONS_INVALID=0`

## Coverage reconciliation

S01–S08 audit the source/spec ledger so that:

- in-scope rows have named evidence;
- all Wave-8 invariants map to the ledger;
- GREEN cannot be promoted without bounded evidence;
- PARTIAL rows retain an explicit rationale;
- RESEARCH measurements are not accepted as correctness proof;
- BOUNDARY product surfaces remain outside the release claim;
- exact prior Wave-7 release evidence remains linked;
- reconciliation is deterministic.

The pre-release ledger contained 123 rows: 117 in scope, 1 RESEARCH and 5 BOUNDARY rows.

## Claim boundary

`0.8.0a1` may be described as GREEN only for the bounded reference-runtime surfaces exercised by the exact release gates. It does not establish universal optimality, arbitrary production crash safety, generalized constraint-theory completeness, arbitrary external schema migration, adapter-specific physical cancellation, destructive storage-engine compaction, distributed consensus/multi-writer safety, production hardening, formal global proof or empirical superiority.
