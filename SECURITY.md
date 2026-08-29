# Security and correctness boundary

Nolane Plan treats external/model content as untrusted with respect to authority. A model cannot establish its own principal identity, grant itself authority, turn global kernel visibility into personal knowledge, or commit a world fact by narration.

The reference implementation is not an identity provider or sandbox. Hosts integrating real tools must provide principal identity/provenance at the assurance level required by their risk policy and must ensure tool calls cannot bypass the kernel's binder/dispatch fence.

Wave 2 additionally treats adapters and crash recovery as correctness boundaries. Executor-sensitive actions should bind an adapter capability revision with principal-attestation and dispatch-fence assurance. A recorded dispatch with an ambiguous external outcome must be reconciled before a non-idempotent retry. `PlanKernel.open()` verifies snapshot integrity, the journal hash chain and snapshot-to-journal prefix binding; unsupported post-snapshot mutation events fail closed rather than being guessed during replay.

Please report semantic authorization, information-scope, causal-cut, adapter-attestation, replay, reconciliation, freshness, or postcondition bypasses with a minimal reproducer whenever possible.
