# Security and correctness boundary

Nolane Plan treats external/model content as untrusted with respect to authority. A model cannot establish its own principal identity, grant itself authority, turn global kernel visibility into personal knowledge, rewrite immutable semantic lineage, carry stale authority across a migration or storage epoch, or commit a world fact by narration.

The `0.9.0a1` reference implementation is not an identity provider, sandbox, generic scheduler, arbitrary storage engine, distributed consensus protocol or remote-service truth oracle. Hosts must provide principal identity/provenance and real external capability/resource observations at the assurance required by policy, and must prevent tool calls from bypassing the kernel authority/dispatch fence.

Correctness boundaries include the historical principal-scope, proof, policy, schedulability, lineage, migration, replay, cancellation and compaction invariants plus these Wave-9 production contracts:

- **Production storage:** declared backend capabilities are part of the correctness claim. Strong multi-writer authority requires the necessary durable acknowledgement, exact-revision CAS and fencing semantics; weaker backends must remain single-writer or explicitly unsupported. The in-memory production store is a semantic reference and is not itself a durable deployment backend.
- **Authority epochs:** epochs are monotone and bind backend revision, writer identity and predecessor. Old-epoch authorization cannot be resurrected after a newer epoch is acquired. The process-local `_writer_lock` remains a serialization aid, not a distributed lock or consensus protocol.
- **Destructive compaction:** source retirement is permitted only after target shadow verification and a durably observable production-pointer switch while protected lineage remains retained/reconstructable. Wave 9 does not claim arbitrary database/storage-engine compaction or garbage-collection safety.
- **External execution:** authorization binds the exact adapter revision and execution contract. Cancellation assurance cannot exceed the adapter contract; best-effort/unsupported cancellation remains ambiguous. Compensation is a distinct effect and cannot erase the original outcome.
- **Restart/replay:** correctness-significant Wave-9 sidecars are restored on supported paths and unknown correctness-significant events fail closed. Replay does not reproduce the external storage engine, service or physical device.

`PlanKernel.open()` remains a correctness operation. Snapshot import does not invent ancestry or authority, migration mappings do not mint authorization, and historical revisions remain distinct from current logical pointers.

The release claim remains explicitly bounded: no universal distributed consensus, arbitrary multi-host coordination/crash safety, arbitrary physical remote cancellation, generalized opaque constraint completeness, or Wave-10+ capability is asserted. Benchmark/reference-world measurements remain research observations rather than security evidence.

Please report semantic authorization, information-scope, proof-capture, policy, schedulability, lineage/revision, migration, compaction, cancellation, storage-epoch/CAS/fencing, replay, reconciliation or coverage-claim bypasses with a minimal reproducer whenever possible.
