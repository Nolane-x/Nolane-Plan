from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable

from .hashing import digest


class Wave8Layer(str, Enum):
    PROPERTY = "PROPERTY"
    METAMORPHIC = "METAMORPHIC"
    CHAOS = "CHAOS"
    DIFFERENTIAL = "DIFFERENTIAL"
    MUTATION = "MUTATION"
    WORLD = "WORLD"
    COVERAGE = "COVERAGE"


class Wave8Expectation(str, Enum):
    EQUAL = "EQUAL"
    MONOTONIC_NON_PROMOTION = "MONOTONIC_NON_PROMOTION"
    FAIL_CLOSED = "FAIL_CLOSED"
    PRESERVE_HISTORY = "PRESERVE_HISTORY"
    PRESERVE_SEMANTICS = "PRESERVE_SEMANTICS"
    WEAKEN_OR_EQUAL = "WEAKEN_OR_EQUAL"


_PREFIX_LAYER = {
    "P": Wave8Layer.PROPERTY,
    "M": Wave8Layer.METAMORPHIC,
    "C": Wave8Layer.CHAOS,
    "D": Wave8Layer.DIFFERENTIAL,
    "X": Wave8Layer.MUTATION,
    "W": Wave8Layer.WORLD,
    "S": Wave8Layer.COVERAGE,
}

_EXPECTED_IDS = tuple(
    f"{prefix}{index:02d}"
    for prefix, count in (("P", 10), ("M", 12), ("C", 10), ("D", 10), ("X", 12), ("W", 6), ("S", 8))
    for index in range(1, count + 1)
)


def _required(name: str, value: object) -> str:
    text = str(value).strip()
    if not text:
        raise ValueError(f"{name} must be non-empty")
    return text


def _canon(values: Iterable[str]) -> tuple[str, ...]:
    result = tuple(sorted({_required("reference", value) for value in values}))
    if not result:
        raise ValueError("spec_surface_refs must not be empty")
    return result


@dataclass(frozen=True, slots=True)
class Wave8Invariant:
    invariant_id: str
    layer: Wave8Layer
    spec_surface_refs: tuple[str, ...]
    title: str
    expectation: Wave8Expectation
    generator_family: str
    required_oracle: str
    bounded_scope: str

    def __post_init__(self) -> None:
        invariant_id = _required("invariant_id", self.invariant_id)
        if invariant_id not in _EXPECTED_IDS:
            raise ValueError(f"unknown Wave-8 invariant ID: {invariant_id}")
        layer = self.layer if isinstance(self.layer, Wave8Layer) else Wave8Layer(str(self.layer))
        expectation = (
            self.expectation
            if isinstance(self.expectation, Wave8Expectation)
            else Wave8Expectation(str(self.expectation))
        )
        if _PREFIX_LAYER[invariant_id[0]] is not layer:
            raise ValueError(f"{invariant_id} belongs to {_PREFIX_LAYER[invariant_id[0]].value}, not {layer.value}")
        object.__setattr__(self, "invariant_id", invariant_id)
        object.__setattr__(self, "layer", layer)
        object.__setattr__(self, "expectation", expectation)
        object.__setattr__(self, "spec_surface_refs", _canon(self.spec_surface_refs))
        object.__setattr__(self, "title", _required("title", self.title))
        object.__setattr__(self, "generator_family", _required("generator_family", self.generator_family))
        object.__setattr__(self, "required_oracle", _required("required_oracle", self.required_oracle))
        object.__setattr__(self, "bounded_scope", _required("bounded_scope", self.bounded_scope))

    def canonical_payload(self) -> dict[str, object]:
        return {
            "invariant_id": self.invariant_id,
            "layer": self.layer.value,
            "spec_surface_refs": self.spec_surface_refs,
            "title": self.title,
            "expectation": self.expectation.value,
            "generator_family": self.generator_family,
            "required_oracle": self.required_oracle,
            "bounded_scope": self.bounded_scope,
        }


@dataclass(frozen=True, slots=True)
class Wave8Counterexample:
    invariant_id: str
    case_id: str
    seed: int
    generator_version: str
    recipe: tuple[str, ...]
    minimized_recipe: tuple[str, ...]
    expected_relation: Wave8Expectation
    observed_summary: str
    canonical_digest: str

    @classmethod
    def create(
        cls,
        *,
        invariant_id: str,
        case_id: str,
        seed: int,
        generator_version: str,
        recipe: Iterable[str],
        minimized_recipe: Iterable[str],
        expected_relation: Wave8Expectation,
        observed_summary: str,
    ) -> "Wave8Counterexample":
        invariant = _required("invariant_id", invariant_id)
        if invariant not in _EXPECTED_IDS:
            raise ValueError(f"unknown Wave-8 invariant ID: {invariant}")
        relation = (
            expected_relation
            if isinstance(expected_relation, Wave8Expectation)
            else Wave8Expectation(str(expected_relation))
        )
        recipe_rows = tuple(str(value) for value in recipe)
        minimized_rows = tuple(str(value) for value in minimized_recipe)
        body = {
            "invariant_id": invariant,
            "case_id": _required("case_id", case_id),
            "seed": int(seed),
            "generator_version": _required("generator_version", generator_version),
            "recipe": recipe_rows,
            "minimized_recipe": minimized_rows,
            "expected_relation": relation.value,
            "observed_summary": _required("observed_summary", observed_summary),
        }
        return cls(
            invariant_id=invariant,
            case_id=body["case_id"],
            seed=body["seed"],
            generator_version=body["generator_version"],
            recipe=recipe_rows,
            minimized_recipe=minimized_rows,
            expected_relation=relation,
            observed_summary=body["observed_summary"],
            canonical_digest=digest(body),
        )


def _inv(
    invariant_id: str,
    layer: Wave8Layer,
    surface: str,
    title: str,
    expectation: Wave8Expectation,
    family: str,
    oracle: str,
    scope: str,
) -> Wave8Invariant:
    return Wave8Invariant(
        invariant_id=invariant_id,
        layer=layer,
        spec_surface_refs=(surface,),
        title=title,
        expectation=expectation,
        generator_family=family,
        required_oracle=oracle,
        bounded_scope=scope,
    )


P = Wave8Layer.PROPERTY
M = Wave8Layer.METAMORPHIC
C = Wave8Layer.CHAOS
D = Wave8Layer.DIFFERENTIAL
X = Wave8Layer.MUTATION
W = Wave8Layer.WORLD
S = Wave8Layer.COVERAGE
E = Wave8Expectation


WAVE8_INVARIANTS = (
    _inv("P01", P, "Same supported snapshot+journal produces same bounded canonical semantic digest", "Canonical determinism", E.EQUAL, "lineage_regime", "canonical digest equality", "declared canonical serializers and supported runtime objects"),
    _inv("P02", P, "Principal-scoped access profiles and information partitions", "Principal information anti-escalation", E.WEAKEN_OR_EQUAL, "principal_information", "decision/authority non-promotion", "bounded principals, access profiles, observations and actions"),
    _inv("P03", P, "Blocking-invalidity vs positive-support distinction", "Blocking invalidity is monotone", E.MONOTONIC_NON_PROMOTION, "evidence_support", "proof usability cannot increase", "declared proof support graphs"),
    _inv("P04", P, "SupportAlternativeSet / conjunctive clauses / grounded support", "Removing support cannot strengthen authority", E.WEAKEN_OR_EQUAL, "evidence_support", "proof/seal strength weakens or stays equal", "declared bounded support alternatives"),
    _inv("P05", P, "Selection hard-veto monotonicity and dependency freshness", "Hard veto cannot be scored away", E.MONOTONIC_NON_PROMOTION, "selector_candidates", "vetoed candidate stays ineligible", "bounded selector candidates"),
    _inv("P06", P, "Resource/capacity feasibility beyond simple exclusive overlap", "Resource contraction cannot improve strong schedulability", E.WEAKEN_OR_EQUAL, "resource_jobs", "schedulability strength weakens or stays equal", "declared control-plane resource kinds"),
    _inv("P07", P, "Recursive feasibility and information-by-deadline requirement for `SAFE_HANDOFF`", "Temporal contraction cannot improve strong feasibility", E.WEAKEN_OR_EQUAL, "handoff", "handoff/executability strength weakens or stays equal", "bounded deadlines, observations and reaction windows"),
    _inv("P08", P, "Exact proof/policy/schedulability/action semantic lineage bound into authorization", "Authority-bound semantic drift invalidates reuse", E.FAIL_CLOSED, "lineage_regime", "old dispatch authority rejected", "declared strong authorization pipeline"),
    _inv("P09", P, "Snapshot v7 persists lineage/regimes/migration/compaction/replay registry and authority closure", "Required history is never erased", E.PRESERVE_HISTORY, "replay_compaction", "receipt/lineage/debt history inclusion", "supported restart, migration and compaction paths"),
    _inv("P10", P, "Strategic relocation `LOCATED/AMBIGUOUS/UNLOCATED`", "Unknown state never self-promotes", E.MONOTONIC_NON_PROMOTION, "relocation", "unknown/opaque/unlocated cannot become strong without evidence", "bounded unknown and relocation classifications"),

    _inv("M01", M, "Common immutable lineage schema for declared strategic runtime families", "Set-like reference permutation is semantics-preserving", E.EQUAL, "lineage_regime", "canonical digest equality", "declared set-like lineage fields"),
    _inv("M02", M, "Decision-relevant convergence guards", "Non-semantic presentation renaming preserves decisions", E.EQUAL, "selector_candidates", "bounded semantic projection equality", "presentation-only labels excluded from identity"),
    _inv("M03", M, "Authority-time dependency freshness", "Irrelevant evidence cannot strengthen authority", E.MONOTONIC_NON_PROMOTION, "evidence_support", "authority equal or conservatively stale, never stronger", "evidence outside declared dependency/query domain"),
    _inv("M04", M, "Evidence polarity, revocation, common-lineage independence", "Duplicate common-lineage support does not fake independence", E.EQUAL, "evidence_support", "independence assessment equality", "bounded support roots"),
    _inv("M05", M, "Principal-relative non-anticipativity checking", "Information-equivalent history aliases preserve pre-reveal choice", E.EQUAL, "policy_information", "selected action equality", "bounded information-equivalence classes"),
    _inv("M06", M, "Policy-level branch/resource coherence", "Mutually exclusive branch declaration order is irrelevant", E.EQUAL, "policy_bundle", "coherence assessment equality", "bounded explicit policy branches"),
    _inv("M07", M, "Joint control-plane schedulability certificate", "Resource/job ordering is irrelevant", E.EQUAL, "resource_jobs", "schedulability assessment equality", "stable resource/job identities"),
    _inv("M08", M, "Snapshot/journal integrity and prefix binding", "Immediate snapshot reopen preserves semantics", E.PRESERVE_SEMANTICS, "replay_compaction", "canonical semantic digest equality", "valid supported snapshot"),
    _inv("M09", M, "Replay coverage for every correctness-significant event emitted by the bounded runtime", "Equivalent supported journal replay preserves semantics", E.PRESERVE_SEMANTICS, "replay_compaction", "canonical semantic digest equality", "supported correctness-significant suffix"),
    _inv("M10", M, "Reversible representation-only graph compaction with read-only archive/reconstruction", "Representation-only compaction preserves semantics and authority", E.PRESERVE_SEMANTICS, "replay_compaction", "semantic roots and authority result equal", "Wave-7 representation-only compaction"),
    _inv("M11", M, "Conservative deterministic v6→v7 import without invented strong ancestry", "Repeated legacy import is deterministic", E.EQUAL, "migration", "semantic root and recheck set equality", "supported v6 import fixture family"),
    _inv("M12", M, "Typed semantic migration with exact six dispositions and explicit debt/identity mappings", "Migration manifest ordering is canonical", E.EQUAL, "migration", "manifest digest and migration projection equality", "set-like migration manifest fields"),

    _inv("C01", C, "Snapshot/journal integrity and prefix binding", "Torn or invalid snapshot fails closed", E.FAIL_CLOSED, "replay_compaction", "ReplayError before trusted state use", "bounded snapshot corruption points"),
    _inv("C02", C, "Same supported snapshot+journal produces same bounded canonical semantic digest", "Valid snapshot plus suffix reconstructs exactly", E.PRESERVE_SEMANTICS, "replay_compaction", "canonical semantic digest equality", "supported suffix sequences"),
    _inv("C03", C, "Unknown correctness-significant replay event fails closed", "Unknown correctness event fails closed", E.FAIL_CLOSED, "replay_compaction", "ReplayError", "journal suffix correctness events"),
    _inv("C04", C, "Proof-carrying `ActionAuthorization` bundle", "Interrupted pre-binding authorization cannot dispatch", E.FAIL_CLOSED, "policy_bundle", "no current dispatchable authorization", "bounded authorization persistence boundary"),
    _inv("C05", C, "Unknown non-idempotent outcome -> evidence-bound reconciliation", "Durable unknown dispatch remains reconciliation-required", E.FAIL_CLOSED, "replay_compaction", "transaction remains unresolved and retry-blocked", "non-idempotent durable dispatch"),
    _inv("C06", C, "Typed semantic migration with exact six dispositions and explicit debt/identity mappings", "Pre-root-switch migration failure preserves source authority root", E.PRESERVE_SEMANTICS, "migration", "source root remains current", "bounded migration precommit faults"),
    _inv("C07", C, "Migration cannot silently preserve authority or reinterpret ambiguous external effects", "Durable migration replays without authority resurrection", E.FAIL_CLOSED, "migration", "target root current and invalidated authority unusable", "supported durable migration event"),
    _inv("C08", C, "Reversible representation-only graph compaction with read-only archive/reconstruction", "Compaction is atomic at representation boundary", E.PRESERVE_SEMANTICS, "replay_compaction", "no mixed source/target representation state", "bounded compaction commit faults"),
    _inv("C09", C, "Mutable generation/permission/reservation/writer refresh at child activation", "Stale child activation remains blocked after restart", E.FAIL_CLOSED, "handoff", "child activation rejected", "bounded handoff stability contracts"),
    _inv("C10", C, "Dispatch fence contract / cancellation residual race semantics", "Cancellation race preserves residual ambiguity", E.FAIL_CLOSED, "action_transaction", "post-dispatch cancellation is not reported clean without evidence", "single durable transaction protocol"),

    _inv("D01", D, "Snapshot v7 persists lineage/regimes/migration/compaction/replay registry and authority closure", "Live state equals snapshot-reopen state", E.EQUAL, "replay_compaction", "canonical projection equality", "supported runtime state"),
    _inv("D02", D, "Replay coverage for every correctness-significant event emitted by the bounded runtime", "Live state equals prefix-plus-suffix replay", E.EQUAL, "replay_compaction", "canonical projection equality", "supported journal suffix"),
    _inv("D03", D, "Same supported snapshot+journal produces same bounded canonical semantic digest", "Repeated replay is deterministic", E.EQUAL, "replay_compaction", "canonical projection equality", "same snapshot and journal"),
    _inv("D04", D, "Reversible representation-only graph compaction with read-only archive/reconstruction", "Pre/post compaction execution paths agree", E.EQUAL, "replay_compaction", "canonical projection and authority equality", "representation-only compaction"),
    _inv("D05", D, "Conservative deterministic v6→v7 import without invented strong ancestry", "Equivalent direct and legacy-import state agree where expressible", E.EQUAL, "migration", "bounded common semantic projection equality", "legacy fields that actually encode equivalent semantics"),
    _inv("D06", D, "Typed semantic migration with exact six dispositions and explicit debt/identity mappings", "Live and replayed migration agree", E.EQUAL, "migration", "migration target projection equality", "supported declared migration edge"),
    _inv("D07", D, "Principal identity provenance across restart/replay", "Principal information reconstruction agrees after restart", E.EQUAL, "principal_information", "principal information projection equality", "bounded delivery/observation/access history"),
    _inv("D08", D, "Proof-carrying `ActionAuthorization` bundle", "Proof/policy authority recalculation agrees after restart", E.EQUAL, "policy_bundle", "authority assessment equality", "declared proof/policy authority path"),
    _inv("D09", D, "Wave-6 schedulability/liveness prerequisites under exact kernel writer", "Schedulability/liveness recalculation agrees after restart", E.EQUAL, "resource_jobs", "certificate assessment equality", "declared Wave-6 certificate path"),
    _inv("D10", D, "Strategic relocation `LOCATED/AMBIGUOUS/UNLOCATED`", "Relocation is stable across ordering and restart", E.EQUAL, "relocation", "location projection equality", "bounded canonical states and region sets"),

    _inv("X01", X, "Principal-scoped access profiles and information partitions", "Kill principal anti-escalation bypass", E.FAIL_CLOSED, "mutation", "P02 targeted failure", "principal information authority guard"),
    _inv("X02", X, "Blocking-invalidity vs positive-support distinction", "Kill blocker monotonicity bypass", E.FAIL_CLOSED, "mutation", "P03 targeted failure", "proof blocker guard"),
    _inv("X03", X, "Selection hard-veto monotonicity and dependency freshness", "Kill hard-veto resurrection", E.FAIL_CLOSED, "mutation", "P05 targeted failure", "selection veto guard"),
    _inv("X04", X, "Resource/capacity feasibility beyond simple exclusive overlap", "Kill resource monotonicity inversion", E.FAIL_CLOSED, "mutation", "P06 targeted failure", "bounded schedulability capacity guard"),
    _inv("X05", X, "Recursive feasibility and information-by-deadline requirement for `SAFE_HANDOFF`", "Kill deadline optimism", E.FAIL_CLOSED, "mutation", "P07 targeted failure", "information-by-deadline guard"),
    _inv("X06", X, "Same supported snapshot+journal produces same bounded canonical semantic digest", "Kill replay equivalence bypass", E.FAIL_CLOSED, "mutation", "D02 targeted failure", "replay semantic digest check"),
    _inv("X07", X, "Unknown correctness-significant replay event fails closed", "Kill unknown-event fail-open", E.FAIL_CLOSED, "mutation", "C03 targeted failure", "replay registry unknown-event guard"),
    _inv("X08", X, "Migration cannot silently preserve authority or reinterpret ambiguous external effects", "Kill migration authority resurrection", E.FAIL_CLOSED, "mutation", "C07 targeted failure", "migration authority recheck guard"),
    _inv("X09", X, "Reversible representation-only graph compaction with read-only archive/reconstruction", "Kill compaction semantic-equivalence break", E.FAIL_CLOSED, "mutation", "M10 targeted failure", "compaction equality guard"),
    _inv("X10", X, "Dispatch fence contract / cancellation residual race semantics", "Kill false clean post-dispatch cancellation", E.FAIL_CLOSED, "mutation", "C10 targeted failure", "durable dispatch/cancellation guard"),
    _inv("X11", X, "Strategic relocation `LOCATED/AMBIGUOUS/UNLOCATED`", "Kill arbitrary ambiguity collapse", E.FAIL_CLOSED, "mutation", "D10 targeted failure", "location ambiguity classifier"),
    _inv("X12", X, "N-way proof-context composition", "Kill pairwise-only global composition false positive", E.FAIL_CLOSED, "mutation", "bounded global composition targeted failure", "explicit finite context constraints"),

    _inv("W01", W, "Inter-principal planning-relevant delivery/observation evidence", "Principal Relay reference world", E.FAIL_CLOSED, "world_principal_relay", "named information and authority invariants", "two/three principals with delayed asymmetric observations"),
    _inv("W02", W, "`NULL_WORLD` / residual unknown-world representation", "Open-World Recovery reference world", E.FAIL_CLOSED, "world_open_recovery", "uncertainty/quarantine terminal classification", "bounded residual-world anomaly schedule"),
    _inv("W03", W, "Joint control-plane schedulability certificate", "Deadline Resource Contention reference world", E.FAIL_CLOSED, "world_resource_contention", "deadline/resource invariants", "bounded worker/writer/approval contention"),
    _inv("W04", W, "Repeated handoff liveness certificate", "Handoff Chain reference world", E.FAIL_CLOSED, "world_handoff_chain", "liveness/stutter/activation invariants", "bounded ordinary and recovery handoffs"),
    _inv("W05", W, "Migration cannot silently preserve authority or reinterpret ambiguous external effects", "Migration plus Ambiguous External Effect reference world", E.FAIL_CLOSED, "world_migration_effect", "reconciliation and migration invariants", "non-idempotent unknown effect across schema transition"),
    _inv("W06", W, "Compaction retains active authority, dormant/resurrection, proof/evidence/debt and unique-fallback lineage", "Dormant Hedge plus Compaction reference world", E.PRESERVE_HISTORY, "world_dormant_hedge", "fallback/resurrection lineage retention", "bounded dormant unique hedge and representation compaction"),

    _inv("S01", S, "Property/metamorphic/chaos/differential conformance", "Every in-scope ledger row has evidence", E.FAIL_CLOSED, "coverage", "no orphan in-scope row", "final v0.15 bounded ledger"),
    _inv("S02", S, "Property/metamorphic/chaos/differential conformance", "Every Wave-8 invariant maps to the ledger", E.FAIL_CLOSED, "coverage", "no orphan invariant", "frozen 68-row Wave-8 registry"),
    _inv("S03", S, "Generalized global minimality/exclusion proof beyond declared closure", "No unjustified GREEN promotion", E.FAIL_CLOSED, "coverage", "GREEN requires named evidence", "all final coverage states"),
    _inv("S04", S, "General migration contracts across every historical schema/version pair", "Remaining PARTIAL rows carry explicit rationale", E.FAIL_CLOSED, "coverage", "PARTIAL rows have reason/evidence", "final coverage ledger"),
    _inv("S05", S, "Real benchmark worlds / empirical superiority", "Research measurement stays non-correctness", E.FAIL_CLOSED, "coverage", "RESEARCH not accepted as correctness evidence", "benchmark-world measurement rows"),
    _inv("S06", S, "Distributed correctness writers / consensus", "Product boundaries stay out of bounded claim", E.FAIL_CLOSED, "coverage", "BOUNDARY rows excluded from correctness closure", "explicit non-goal rows"),
    _inv("S07", S, "Python 3.11/3.12/3.13 Wave-7 implementation matrix", "Release claim matches exact verified evidence", E.EQUAL, "coverage", "claim/evidence SHA and CI linkage", "release metadata and final ledger"),
    _inv("S08", S, "I-245..I-260 principal-scoped closure", "Final source-spec reconciliation is deterministic", E.EQUAL, "coverage", "repeated audit produces same registry/ledger projection", "bounded v0.15 source-spec coverage"),
)


def _validate_frozen_registry(rows: tuple[Wave8Invariant, ...]) -> None:
    ids = tuple(row.invariant_id for row in rows)
    if len(ids) != len(set(ids)):
        raise ValueError("Wave-8 invariant IDs must be unique")
    if tuple(sorted(ids)) != tuple(sorted(_EXPECTED_IDS)):
        missing = sorted(set(_EXPECTED_IDS) - set(ids))
        extra = sorted(set(ids) - set(_EXPECTED_IDS))
        raise ValueError(f"Wave-8 registry shape mismatch; missing={missing!r}, extra={extra!r}")


_validate_frozen_registry(WAVE8_INVARIANTS)


def wave8_registry_digest(rows: Iterable[Wave8Invariant] = WAVE8_INVARIANTS) -> str:
    canonical = tuple(
        row.canonical_payload()
        for row in sorted(tuple(rows), key=lambda item: item.invariant_id)
    )
    return digest(canonical)
