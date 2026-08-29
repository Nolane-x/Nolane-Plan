# Changelog

## 0.2.0a1 — 2026-08-29

- Added prefix-closed `DecisionCutRevision` authority views for causal decision consistency.
- Added authority-time `ArtifactRegistry` freshness so dependency mutation stales proofs immediately.
- Bound Decision Capsules and ActionAuthorizations to causal cuts and optional adapter capability revisions.
- Added adapter principal-attestation / dispatch-fence / postcondition-assurance profiles.
- Added durable action transactions with pre-effect `DISPATCH_RECORDED`, `RECONCILIATION_REQUIRED`, and trusted reconciliation.
- Non-idempotent actions cannot blind-retry after an ambiguous external outcome.
- Integrated universal-query completeness, preparedness and reaction-window schedulability into consequential authorization gates.
- Integrated strategic relocation after canonical commits; `UNLOCATED` enters model-class uncertainty rather than choosing a convenient branch.
- Completion reports are now proof artifacts bound to decision cuts and freshness dependencies.
- Added snapshot schema v2, journal-prefix binding, semantic-state restoration and fail-closed post-snapshot replay through `PlanKernel.open()`.
- Added deterministic 10-case Wave 2 adversarial conformance and made it a Python 3.11/3.12/3.13 CI gate.

## 0.1.0a1 — 2026-08-29

- Initial full reference-runtime wave for Nolane Plan v0.15.
- Strategic future lattice with `NULL_WORLD`, bounded factorized compiler and convergence certificates.
- Principal-scoped information partitions, Decision Capsules and hydration firewall.
- Principal-bound authority grants/authorizations, dispatch identity checks and execution receipts.
- Condition-centric obligations, evidence lineage, temporal/handoff liveness, shared reservations.
- Freshness-domain dependency manifests, strong universal-query completeness receipts.
- Safe pruning/resurrection, preparedness floors, state relocation and mandatory-first planning budget.
- Hash-chained persistence, snapshot integrity, end-to-end PlanKernel, CLI demo and conformance oracle.
- Deterministic bounded v0.14→v0.15 collision reproduction: 108 → 0.
