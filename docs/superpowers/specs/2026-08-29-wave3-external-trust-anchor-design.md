# Wave 3 External Trust Anchor Design

## Status

Approved architectural continuation of Nolane Plan v0.15. This design implements the remaining principal-grounding seams without turning Nolane Plan into an identity provider, messaging platform, distributed multi-writer system, or generic orchestration framework.

## Source-of-truth contracts

Wave 3 implements the v0.15 requirements that principal identity comes from a canonical host/platform binding rather than model narration; that identity must remain stable enough for referenced artifacts, preserve provenance through restart/replay, and fail closed when unavailable at a decision/dispatch boundary. It also implements principal-relative communication delivery/reveal semantics and executing-principal attribution for authority-sensitive receipts/reconciliation.

Normative invariants primarily closed by this wave: I-245..I-257, especially I-254, I-255, I-256 and I-257. Existing condition-centric obligation, SharedCommitment, evidence-lineage and single-writer semantics remain canonical.

## Design principles

1. **Identity evidence, not caller narration.** A strong principal is established by a host-supplied `PrincipalAttestation`; a raw string may remain usable only as an explicitly weak/legacy binding whose assurance cannot authorize identity-sensitive operations.
2. **Nolane Plan is not the identity provider.** The host decides how a subject is authenticated. Nolane Plan records the canonical subject, source, revision, validity and assurance and enforces its planning consequences.
3. **Decision principal and acting principal remain separate.** Identity grounding strengthens both bindings without collapsing them.
4. **Communication is planning evidence, not generic messaging.** The runtime models only send/delivery/observation state needed to decide whether information is legally and operationally available to a recipient principal.
5. **Reconciliation takes evidence objects, not booleans.** Callers cannot manufacture trust by passing `trusted=True`.
6. **Everything correctness-relevant is replayable.** Identity revisions, delivery receipts and reconciliation evidence are journal/snapshot state and participate in freshness.

## New semantic objects

### `PrincipalAttestation`

Fields: `attestation_id`, `canonical_principal_ref`, `source`, `source_subject`, `revision`, `issued_at`, `valid_until`, `assurance`, `session_ref`, `provenance_digest`, `revoked`.

Strong identity-sensitive authority requires a non-revoked, non-expired attestation meeting the configured assurance floor. Two materially different source subjects cannot silently collapse into one canonical principal unless an explicit host equivalence mapping is supplied.

### `PrincipalBindingRevision`

Fields: `binding_id`, `canonical_principal_ref`, `attestation_id`, `binding_revision`, `created_sequence`, `assurance`, `source`, `source_subject`.

This is the durable identity revision that planning artifacts depend upon. Rebinding/revocation bumps `principal-identity:<principal_ref>` freshness.

### `CommunicationReceipt`

State machine: `SENT -> DELIVERED -> OBSERVED` with optional terminal `EXPIRED`/`REVOKED`.

Fields include sender principal, recipient principal, semantic payload refs/digest, sent/delivered/observed times, access condition, validity window and provenance. Only `OBSERVED` at or before a decision boundary can make transferred information decision-usable. Queue existence and `SENT` do not count as recipient knowledge.

### `DispatchAttestation`

Fields bind `authorization_id`, `transaction_id`, `action_id`, `adapter_id`, `adapter_revision`, `canonical_principal_ref`, `principal_attestation_id`, `observed_at`, `assurance`, `provenance_digest`.

Executor-sensitive dispatch requires the attested principal to equal `ActionAuthorization.acting_principal_ref`; attestation must be current and compatible with the adapter revision.

### `ReconciliationEvidence`

Fields bind exact transaction/action/authorization/principal/adapter revisions, observed outcome (`APPLIED` or `NOT_APPLIED`), source, observed time, assurance and provenance digest. `ActionTransactionLedger.reconcile` accepts evidence only through a verifier; a bare boolean trust flag is removed from the strong path.

## Kernel integration

`PlanKernel` gains identity, communication and reconciliation ledgers. Strong principal registration binds an attestation before creating the access profile. Capsule dependency closure includes principal-identity and relevant delivery generations. Authorization of executor-sensitive actions requires a current acting-principal binding. Dispatch records a durable dispatch fence request before external execution, then requires a `DispatchAttestation` before the adapter can be treated as the intended principal. Reconciliation records evidence before state transition.

Legacy reference paths remain backward-compatible for reversible/non-identity-sensitive examples, but they are explicitly capped at weak assurance and cannot satisfy the strong executor-sensitive floor.

## Crash/replay

Snapshot version advances. Durable state includes principal attestations/bindings, communication receipts, dispatch attestations and reconciliation evidence. Replay is fail-closed for unknown Wave-3 correctness events. An attestation that was valid historically may justify a historical cut but cannot be relabeled current after expiry/revocation.

## Conformance

Wave-3 adversarial conformance must cover at least: narrated-admin spoofing, source-subject collision, expired/revoked identity, authorize→dispatch principal swap, adapter/session migration, wrong-transaction reconciliation evidence, cross-principal reconciliation, SENT-vs-OBSERVED knowledge, late delivery non-retroactivity, recipient swap, replay preservation and stale capsule invalidation on identity/delivery changes.

## Mutation gate

Release requires semantic kills for: (M1) bypass canonical identity binding, (M2) bypass dispatch principal attestation, (M3) treat `SENT` as observed, (M4) accept boolean trusted reconciliation. Each mutant must fail focused contracts and/or Wave-3 conformance.

## Scope boundary

This design does not add OAuth, passwords, PKI account management, generic message queues, distributed consensus or multiple correctness writers. Host identity mechanisms remain an engineering choice, exactly as the v0.15 research boundary requires.
