# Nolane Plan Conformance

This document records the executable bounded conformance surface for the `0.9.0a1` Wave-9 release candidate. It is an evidence ledger, not a claim of global formal correctness or empirical superiority.

## Release gate

The release is closed only when the exact release commit passes Python 3.11 / 3.12 / 3.13, its pull-request synthetic merge reproduces that matrix, and a fresh final-`main` push run succeeds at the same release SHA.

Pre-release implementation head `97ce80f13fd22e2347caf99e625865cfd2bb88f5` passed the complete historical + Wave-9 matrix in CI run `33468034330`. On Python 3.11, unit discovery ran 534 tests successfully; Python 3.12 and 3.13 also completed the matrix successfully.

## Frozen Wave-9 evidence

| Surface | Frozen result |
|---|---:|
| Registry | 56 invariants; `15e4876c1fabe75bbfe78c5f3a921299315863277bc791ac5324bf6115204ea8` |
| Deterministic production-fault schedules | 12/12; `acd59b52184cea99cd5101fde9cb83c74f947b207af813c6ac81388eaf60e01a` |
| Differential equivalence | 4/4; `14ab39e4b32a5e235c245dee5507b0e1b3f7196845d8d44a05076d667166a3df` |
| Constitutional mutations | 12/12 killed; 0 invalid |
| Coverage ledger | 36/36 GREEN; 0 PARTIAL; 0 orphan; 0 evidence-free GREEN |
| Coverage digest | `2f33d179b69238051ab2db1ba9a0662b52f6292450233bf2b18613ddf3ae6564` |
| Unified Wave-9 release-conformance digest | `ded92c7e947ce2c3eeb82fb9b6fd36c3563e6b6fb71f5a3172450b48a8c98188` |

The unified Wave-9 release-conformance digest is the canonical digest of the frozen registry digest, chaos digest, differential digest and the ordered tuple `(mutant_id, name, target_invariant_id, outcome)` for X01–X12. It is release evidence aggregation only; it does not create a second runtime authority.

## Bounded correctness surface

### Destructive compaction

The production-store path requires explicit prepare, shadow verification, durable production-pointer switch and conservative retirement. Active authority, dormant/resurrection, proof/evidence/debt and unique fallback references remain protected. Source retirement cannot precede a durably observable target switch. This is not a claim about arbitrary storage-engine garbage collection.

### External execution

Authorization binds an exact adapter revision and execution contract. Dispatch acknowledgement, idempotency, remote fencing, cancellation and compensation are represented according to that contract. Best-effort or unsupported cancellation cannot be promoted to a clean cancelled outcome; compensation is a separate effect and does not erase the original external outcome.

### Strong multi-writer authority

Strong multi-writer claims require a storage capability profile with the required durable acknowledgement, exact-revision compare-and-swap and fencing semantics. Authority epochs are monotone, bind backend/writer identity and immediately prior epoch, and stale epoch authorization fails closed. Storage profiles that cannot uphold those semantics are not promoted to strong multi-writer support.

### Restart and replay

Wave-9 correctness-significant storage, execution, compaction and authority sidecars survive supported snapshot/restart and replay paths. Unknown correctness-significant replay events remain fail-closed. Replay does not pretend to replay the external storage engine, remote service or device itself.

## Historical regression obligations

Wave 2 through Wave 8 conformance, mutation and coverage gates remain mandatory. Wave 9 extends the verified surface; it does not replace or weaken prior constitutional gates.

## Claim boundary

`0.9.0a1` may be described as GREEN only for the exact bounded contracts exercised above. It does not establish universal distributed consensus, arbitrary multi-host crash safety, arbitrary database compaction/GC safety, universal physical remote cancellation, generalized external schema migration, formal global proof or empirical planning superiority. No Wave-10+ capability is included in this release.
