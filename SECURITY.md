# Security and correctness boundary

Nolane Plan treats external/model content as untrusted with respect to authority. A model cannot establish its own principal identity, grant itself authority, turn global kernel visibility into personal knowledge, or commit a world fact by narration.

The reference implementation is not an identity provider or sandbox. Hosts integrating real tools must provide principal identity/provenance at the assurance level required by their risk policy and must ensure tool calls cannot bypass the kernel's binder/dispatch fence.

Please report semantic authorization, information-scope, replay, freshness, or postcondition bypasses with a minimal reproducer whenever possible.
