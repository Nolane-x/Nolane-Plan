from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .hashing import digest


class Wave9Layer(str, Enum):
    DESTRUCTIVE_COMPACTION = "DESTRUCTIVE_COMPACTION"
    EXTERNAL_EXECUTION = "EXTERNAL_EXECUTION"
    MULTIWRITER = "MULTIWRITER"
    MUTATION = "MUTATION"
    COVERAGE = "COVERAGE"


class Wave9Expectation(str, Enum):
    FAIL_CLOSED = "FAIL_CLOSED"
    PRESERVE_SEMANTICS = "PRESERVE_SEMANTICS"
    MONOTONIC = "MONOTONIC"
    EXACT_BINDING = "EXACT_BINDING"
    SINGLE_CANONICAL = "SINGLE_CANONICAL"
    CONVERGE = "CONVERGE"
    EXPLICIT_RECONCILIATION = "EXPLICIT_RECONCILIATION"
    IDEMPOTENT = "IDEMPOTENT"
    UNSUPPORTED = "UNSUPPORTED"


WAVE9_CORE_INVARIANT_IDS = tuple(
    [f"DC{i:02d}" for i in range(1, 13)]
    + [f"EX{i:02d}" for i in range(1, 13)]
    + [f"MW{i:02d}" for i in range(1, 13)]
)
WAVE9_MUTATION_INVARIANT_IDS = tuple(f"X{i:02d}" for i in range(1, 13))
WAVE9_COVERAGE_INVARIANT_IDS = tuple(f"S{i:02d}" for i in range(1, 9))
_EXPECTED_IDS = WAVE9_CORE_INVARIANT_IDS + WAVE9_MUTATION_INVARIANT_IDS + WAVE9_COVERAGE_INVARIANT_IDS


@dataclass(frozen=True, slots=True)
class Wave9Invariant:
    invariant_id: str
    layer: Wave9Layer
    title: str
    spec_surface: str
    expectation: Wave9Expectation
    required_oracle: str
    bounded_scope: str
    canonical_digest: str

    def canonical_payload(self) -> dict[str, object]:
        return {
            "invariant_id": self.invariant_id,
            "layer": self.layer.value,
            "title": self.title,
            "spec_surface": self.spec_surface,
            "expectation": self.expectation.value,
            "required_oracle": self.required_oracle,
            "bounded_scope": self.bounded_scope,
        }


def _inv(invariant_id: str, layer: Wave9Layer, title: str, expectation: Wave9Expectation, required_oracle: str, bounded_scope: str) -> Wave9Invariant:
    if invariant_id not in _EXPECTED_IDS:
        raise ValueError(f"unknown Wave-9 invariant ID: {invariant_id}")
    title_value = str(title).strip()
    oracle_value = str(required_oracle).strip()
    scope_value = str(bounded_scope).strip()
    if not title_value or not oracle_value or not scope_value:
        raise ValueError(f"incomplete Wave-9 invariant: {invariant_id}")
    body = {"invariant_id": invariant_id, "layer": layer.value, "title": title_value, "spec_surface": invariant_id, "expectation": expectation.value, "required_oracle": oracle_value, "bounded_scope": scope_value}
    return Wave9Invariant(invariant_id, layer, title_value, invariant_id, expectation, oracle_value, scope_value, digest(body))


D, E, M, X, S, Q = Wave9Layer.DESTRUCTIVE_COMPACTION, Wave9Layer.EXTERNAL_EXECUTION, Wave9Layer.MULTIWRITER, Wave9Layer.MUTATION, Wave9Layer.COVERAGE, Wave9Expectation

_CORE_ROWS = (
    ("DC01", D, "Active authority lineage is never deleted", Q.FAIL_CLOSED, "retention closure contains active authority lineage", "bounded destructive compaction retention closure"),
    ("DC02", D, "Dormant and resurrection dependencies remain retained until proven obsolete", Q.FAIL_CLOSED, "dormant/resurrection retention audit", "bounded dormant branch lineage"),
    ("DC03", D, "Proof, evidence, accepted debt and unique fallback references are retained", Q.FAIL_CLOSED, "proof/evidence/debt/fallback retention audit", "bounded protected reference classes"),
    ("DC04", D, "Shadow reconstruction reproduces the source semantic root before switch", Q.PRESERVE_SEMANTICS, "source/target semantic-root equality", "declared reconstructable compaction archive"),
    ("DC05", D, "Production switch binds exact source revision and authority epoch", Q.EXACT_BINDING, "storage CAS receipt plus current epoch", "bounded production store with CAS/fencing"),
    ("DC06", D, "Source deletion before durable switch acknowledgement is forbidden", Q.FAIL_CLOSED, "retirement phase requires switch receipt", "bounded destructive compaction state machine"),
    ("DC07", D, "Crash before switch reopens source authority", Q.PRESERVE_SEMANTICS, "recovery pointer remains source", "deterministic pre-switch fault schedule"),
    ("DC08", D, "Crash after switch reopens target authority without mixed representation", Q.PRESERVE_SEMANTICS, "recovery pointer target and representation set coherent", "deterministic post-switch fault schedule"),
    ("DC09", D, "Repeated retirement is idempotent and cannot broaden deletion", Q.IDEMPOTENT, "retirement manifest digest and deletion set equality", "bounded exact retirement manifest"),
    ("DC10", D, "Tampered deletion manifest fails closed", Q.FAIL_CLOSED, "internal manifest digest validation", "bounded persisted compaction state"),
    ("DC11", D, "Stale writer cannot retire after a newer epoch becomes current", Q.FAIL_CLOSED, "stale epoch retirement rejection", "bounded storage epoch transition"),
    ("DC12", D, "Post-compaction live, replay and reopen projections remain equivalent", Q.PRESERVE_SEMANTICS, "canonical projection equality", "supported Wave-9 snapshot/replay path"),
    ("EX01", E, "Adapter capability claims are revision-bound and digest-bound", Q.EXACT_BINDING, "execution-contract revision and digest equality", "declared adapter revisions"),
    ("EX02", E, "Strong dispatch cannot use a weaker adapter revision than authorization bound", Q.FAIL_CLOSED, "dispatch contract freshness rejection", "bounded strong dispatch path"),
    ("EX03", E, "Remote cancellation acknowledgement binds transaction, action, adapter, principal and epoch", Q.EXACT_BINDING, "exact cancellation acknowledgement validation", "acknowledged cancellation contracts"),
    ("EX04", E, "Best-effort remote cancellation never means clean cancellation", Q.EXPLICIT_RECONCILIATION, "best-effort acknowledgement cannot close transaction", "post-dispatch best-effort cancellation"),
    ("EX05", E, "Fenced-effect cancellation is clean only with stale-effect exclusion evidence", Q.EXACT_BINDING, "fencing evidence plus acknowledged prevention", "fenced-effect adapter contracts"),
    ("EX06", E, "Unknown non-idempotent external outcome remains retry-blocking", Q.FAIL_CLOSED, "reconciliation-required transaction state", "durably dispatched non-idempotent effects"),
    ("EX07", E, "Compensation is a new effect rather than history rewrite", Q.PRESERVE_SEMANTICS, "distinct compensation transaction and authorization", "bounded compensation records"),
    ("EX08", E, "Compensation failure does not erase the original applied outcome", Q.PRESERVE_SEMANTICS, "original outcome remains applied across compensation transition", "bounded compensation outcomes"),
    ("EX09", E, "Capability downgrade invalidates previous strong execution assumptions", Q.MONOTONIC, "contract revision downgrade blocks stale binding", "declared adapter capability history"),
    ("EX10", E, "Restart preserves pending cancellation and compensation ambiguity", Q.PRESERVE_SEMANTICS, "snapshot/reopen ambiguity projection equality", "supported Wave-9 snapshot state"),
    ("EX11", E, "Wrong-epoch reconciliation evidence cannot close a transaction", Q.FAIL_CLOSED, "authority-epoch mismatch rejection", "epoch-bound cancellation/reconciliation"),
    ("EX12", E, "Unsupported cancellation capability is explicit and fail-closed", Q.UNSUPPORTED, "unsupported contract cannot produce clean cancellation", "declared unsupported cancellation class"),
    ("MW01", M, "Authority epochs are strictly monotonic", Q.MONOTONIC, "epoch successor and predecessor validation", "bounded backend epoch sequence"),
    ("MW02", M, "A stale epoch cannot append a correctness-authoritative event", Q.FAIL_CLOSED, "current-epoch fence rejection", "bounded production store"),
    ("MW03", M, "Two CAS commits against one predecessor cannot both become canonical", Q.SINGLE_CANONICAL, "exact expected-revision CAS", "bounded linearizable store contract"),
    ("MW04", M, "Duplicate idempotent intent converges without duplicate authority", Q.CONVERGE, "idempotency semantic convergence", "bounded idempotency-key domain"),
    ("MW05", M, "Conflicting non-idempotent intents become explicit reconciliation state", Q.EXPLICIT_RECONCILIATION, "conflict record durability", "bounded conflict scope"),
    ("MW06", M, "Lease expiration alone never proves an external effect absent", Q.FAIL_CLOSED, "expiry assessment never asserts absence", "bounded writer lease"),
    ("MW07", M, "Writer identity is bound into epoch acquisition and commit receipts", Q.EXACT_BINDING, "writer digest equality across lease and receipt", "bounded writer identity"),
    ("MW08", M, "Epoch reconstruction after restart is deterministic", Q.PRESERVE_SEMANTICS, "snapshot/reopen epoch projection equality", "supported Wave-9 snapshot"),
    ("MW09", M, "Snapshot plus suffix replay agrees with live multi-writer projection", Q.PRESERVE_SEMANTICS, "live/replayed projection equality", "supported journal suffix"),
    ("MW10", M, "Split-brain simulation leaves at most one canonical successor revision", Q.SINGLE_CANONICAL, "one CAS successor under competing writers", "bounded deterministic split-brain schedule"),
    ("MW11", M, "Backends without CAS and fencing are unsupported for strong multi-writer", Q.UNSUPPORTED, "capability proof rejection", "declared production-store capability profile"),
    ("MW12", M, "Old-epoch authority is unusable after transition without explicit revalidation", Q.FAIL_CLOSED, "authorization epoch binding freshness", "bounded strong authority path"),
)
_MUTATION_TITLES = ("Bypass authority-epoch monotonicity", "Allow stale-writer authoritative commit", "Replace CAS with last-writer-wins", "Delete active authority lineage during compaction", "Delete source before switch durability", "Accept mixed source/target recovery", "Treat best-effort cancellation as clean", "Accept cancellation acknowledgement from wrong epoch", "Erase original applied outcome after compensation", "Treat unsupported backend as strong multi-writer", "Resurrect old-epoch authorization", "Accept unknown Wave-9 replay event")
_COVERAGE_TITLES = ("Every DC/EX/MW invariant has implementation evidence", "Every GREEN Wave-9 row has unit or integration evidence", "Deterministic chaos evidence covers all three production frontiers", "Differential evidence covers the four required projection relations", "Every declared constitutional mutant has a target-specific valid kill", "Historical Wave-8 and earlier gates remain mandatory", "RESEARCH and BOUNDARY claims remain explicit and unpromoted", "Release evidence binds exact registry, coverage, mutation and commit digests")

WAVE9_INVARIANTS = tuple(_inv(*row) for row in _CORE_ROWS) + tuple(_inv(f"X{i:02d}", X, title, Q.FAIL_CLOSED, "target-specific mutation kill", "declared Wave-9 constitutional mutation") for i, title in enumerate(_MUTATION_TITLES, 1)) + tuple(_inv(f"S{i:02d}", S, title, Q.EXACT_BINDING, "coverage evidence audit", "bounded Wave-9 claim ledger") for i, title in enumerate(_COVERAGE_TITLES, 1))
_BY_ID = {row.invariant_id: row for row in WAVE9_INVARIANTS}
WAVE9_REGISTRY_DIGEST = digest(tuple(row.canonical_payload() for row in WAVE9_INVARIANTS))


def get_wave9_invariant(invariant_id: str) -> Wave9Invariant:
    try:
        return _BY_ID[str(invariant_id)]
    except KeyError as exc:
        raise KeyError(f"unknown Wave-9 invariant ID: {invariant_id}") from exc


def validate_wave9_registry() -> str:
    if tuple(row.invariant_id for row in WAVE9_INVARIANTS) != _EXPECTED_IDS:
        raise ValueError("Wave-9 invariant registry IDs/order drifted")
    if len(_BY_ID) != len(_EXPECTED_IDS):
        raise ValueError("Wave-9 invariant registry contains duplicate IDs")
    for row in WAVE9_INVARIANTS:
        if row.canonical_digest != digest(row.canonical_payload()):
            raise ValueError(f"Wave-9 invariant digest mismatch: {row.invariant_id}")
        expected = D if row.invariant_id.startswith("DC") else E if row.invariant_id.startswith("EX") else M if row.invariant_id.startswith("MW") else X if row.invariant_id.startswith("X") else S
        if row.layer is not expected:
            raise ValueError(f"Wave-9 invariant layer mismatch: {row.invariant_id}")
    current = digest(tuple(row.canonical_payload() for row in WAVE9_INVARIANTS))
    if current != WAVE9_REGISTRY_DIGEST:
        raise ValueError("Wave-9 registry digest drifted")
    return current


validate_wave9_registry()
