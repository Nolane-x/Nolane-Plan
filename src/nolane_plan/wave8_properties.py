from __future__ import annotations

from pathlib import Path
import tempfile
from typing import Callable, Iterable

from .actions import ActionIntent, AuthorityGrant
from .control_plane import ControlPlaneResourceRevision, ReactionJobContract, ReactionResourceDemand
from .handoff_liveness import ContinuationProgressRank, HandoffLivenessEvaluator, HandoffProgressPolicy
from .hashing import digest
from .lineage import CanonicalLineageRevision, LineageRegistry, SemanticRegimeKind
from .principals import InformationItem, PrincipalRegistry
from .relocation import CandidateRegion, LocationStatus, StateRelocator
from .schedulability import ReactionSchedulabilityEvaluator, ReactionSchedulabilityLevel
from .selector import ActionScore, pareto_front
from .support import (
    ArtifactAuthorityAssessment,
    InvalidityCause,
    SupportAlternativeSetRevision,
    SupportClause,
    SupportEvaluator,
    SupportNode,
)
from .types import AuthorizationError
from .wave8_generators import Wave8CaseRecipe, generate_case, minimize_recipe
from .wave8_registry import WAVE8_INVARIANTS, Wave8Counterexample


PROPERTY_IDS = tuple(f"P{index:02d}" for index in range(1, 11))
_PROPERTY_ROWS = {row.invariant_id: row for row in WAVE8_INVARIANTS if row.invariant_id in PROPERTY_IDS}


class _CountingAdapter:
    def __init__(self) -> None:
        self.calls = 0

    def execute(self, action, principal_ref):
        self.calls += 1
        return {
            "ok": True,
            "postconditions_verified": True,
            "executing_principal_ref": principal_ref,
            "state_patch": {"done": True},
        }


def _lineage_revision(seed: int, logical_id: str, created_sequence: int) -> CanonicalLineageRevision:
    return CanonicalLineageRevision.create(
        object_family="Wave8Generated",
        logical_id=logical_id,
        revision_id=f"wave8:{logical_id}:{seed}",
        schema_version="schema:wave8-property:v1",
        created_sequence=created_sequence,
        created_at_wall_time=None,
        mission_revision_dependency=None,
        plan_revision=1,
        world_model_revision="world-model:property:v1",
        environment_regime_revision="environment:property:v1",
        validity_regime="ACTIVE",
        parent_revision_ids=(),
        provenance_refs=(f"seed:{seed}", "wave8:property"),
        assurance_profile="KERNEL_ACCEPTED",
        debt_refs=(),
        supersedes_revision_id=None,
        semantic_digest=digest({"logical_id": logical_id, "seed": seed}),
    )


def _p01(recipe: Wave8CaseRecipe) -> tuple[bool, str]:
    rows = (
        _lineage_revision(recipe.seed, "alpha", 1),
        _lineage_revision(recipe.seed, "beta", 2),
        _lineage_revision(recipe.seed, "gamma", 3),
    )
    left = LineageRegistry()
    right = LineageRegistry()
    for row in rows:
        left.register(row)
    for row in reversed(rows):
        right.register(row)
    left_digest = left.semantic_root_digest()
    right_digest = right.semantic_root_digest()
    return left_digest == right_digest, f"left={left_digest} right={right_digest}"


def _p02(recipe: Wave8CaseRecipe) -> tuple[bool, str]:
    registry = PrincipalRegistry()
    principal = f"agent:property:{recipe.seed}"
    registry.register(principal, {"public", "secret"})
    count = max(2, dict(recipe.dimensions).get("items", 2))
    items = tuple(
        InformationItem(
            id=f"item:{recipe.seed}:{index}",
            payload={"seed": recipe.seed, "index": index},
            tags=frozenset({"public" if index % 2 == 0 else "secret"}),
            assurance=1.0,
        )
        for index in range(count)
    )
    for item in items:
        registry.observe(principal, item.id, 1)
    broad = registry.build_partition(principal, items, 2)
    registry.update_access(principal, {"public"})
    narrowed = registry.build_partition(principal, items, 2)
    holds = set(narrowed.item_ids).issubset(broad.item_ids)
    return holds, f"broad={broad.item_ids!r} narrowed={narrowed.item_ids!r}"


def _support_fixture(seed: int, *, second_current: bool = True):
    clause = SupportClause(
        clause_id=f"clause:{seed}",
        required_support_refs=(f"e1:{seed}", f"e2:{seed}"),
        scope="mission",
        assumption_basis=frozenset({"assumption@1"}),
        proof_kind="verification",
        grounding_root_requirements=frozenset(),
        validity_regime="runtime@1",
        context_tags=frozenset({"prod"}),
        minimum_independent_roots=1,
    )
    support_set = SupportAlternativeSetRevision.create(
        support_set_id=f"support:{seed}",
        revision_id=f"support:{seed}@1",
        subject_artifact_revision=f"proof:{seed}@1",
        clauses=(clause,),
        scope="mission",
        assumption_context_rules=("prod",),
        proof_kind="verification",
        grounding_policy="accepted-roots-only",
        support_evaluation_profile="bounded-dnf@1",
        created_sequence=30,
    )
    nodes = {
        f"e1:{seed}": SupportNode(
            ref=f"e1:{seed}",
            current=True,
            direct_grounding_roots=frozenset({f"root:a:{seed}"}),
            support_refs=(),
            scope="mission",
            assumption_basis=frozenset({"assumption@1"}),
            proof_kind="verification",
            validity_regime="runtime@1",
            context_tags=frozenset({"prod"}),
        ),
        f"e2:{seed}": SupportNode(
            ref=f"e2:{seed}",
            current=second_current,
            direct_grounding_roots=frozenset({f"root:b:{seed}"}),
            support_refs=(),
            scope="mission",
            assumption_basis=frozenset({"assumption@1"}),
            proof_kind="verification",
            validity_regime="runtime@1",
            context_tags=frozenset({"prod"}),
        ),
    }
    return support_set, nodes


def _p03(recipe: Wave8CaseRecipe) -> tuple[bool, str]:
    support_set, nodes = _support_fixture(recipe.seed)
    support = SupportEvaluator.evaluate(
        support_set, nodes, active_context={"prod"}, evaluated_at_cut=f"cut:{recipe.seed}", generation=1
    )
    baseline = ArtifactAuthorityAssessment(support, ()).current_usable
    blocked = ArtifactAuthorityAssessment(
        support,
        (InvalidityCause(f"blocker:{recipe.seed}", "WAVE8_ACTIVE_BLOCKER", active=True, blocking=True),),
    ).current_usable
    return baseline and not blocked, f"baseline={baseline} blocked={blocked}"


def _p04(recipe: Wave8CaseRecipe) -> tuple[bool, str]:
    support_set, full_nodes = _support_fixture(recipe.seed)
    full = SupportEvaluator.evaluate(
        support_set, full_nodes, active_context={"prod"}, evaluated_at_cut=f"cut:{recipe.seed}:full", generation=1
    )
    _, reduced_nodes = _support_fixture(recipe.seed, second_current=False)
    reduced = SupportEvaluator.evaluate(
        support_set, reduced_nodes, active_context={"prod"}, evaluated_at_cut=f"cut:{recipe.seed}:reduced", generation=2
    )
    before = int(ArtifactAuthorityAssessment(full, ()).current_usable)
    after = int(ArtifactAuthorityAssessment(reduced, ()).current_usable)
    return after <= before, f"before={before} after={after}"


def _score(seed: int, action_id: str, *, veto: bool, boost: float = 0.0) -> ActionScore:
    base = float((seed % 7) + 1)
    return ActionScore(
        action_id=action_id,
        progress=base + boost,
        information=base + boost,
        optionality=base + boost,
        convergence=base + boost,
        reversibility=base + boost,
        tail_risk=max(0.0, base - boost),
        debt=max(0.0, base - boost),
        cost=max(0.0, base - boost),
        hard_veto=veto,
    )


def _p05(recipe: Wave8CaseRecipe) -> tuple[bool, str]:
    veto_id = f"veto:{recipe.seed}"
    safe = _score(recipe.seed, f"safe:{recipe.seed}", veto=False)
    front_before = pareto_front([safe, _score(recipe.seed, veto_id, veto=True)])
    front_after = pareto_front([safe, _score(recipe.seed, veto_id, veto=True, boost=1000.0)])
    before_ids = {row.action_id for row in front_before}
    after_ids = {row.action_id for row in front_after}
    holds = veto_id not in before_ids and veto_id not in after_ids
    return holds, f"before={sorted(before_ids)!r} after={sorted(after_ids)!r}"


def _resource(seed: int, *, contracted: bool) -> ControlPlaneResourceRevision:
    return ControlPlaneResourceRevision.create(
        resource_id=f"worker:{seed}",
        revision_id=f"worker:{seed}@{'2' if contracted else '1'}",
        resource_kind="CONCURRENCY",
        capacity_units=1 if contracted else 3,
        concurrency_limit=1 if contracted else 3,
        service_rate_per_second=0.1 if contracted else 2.0,
        rate_window_seconds=1.0,
        availability_interval=(0.0, 10.0),
        priority_policy_ref="priority@1",
        reservation_policy_ref="reservation@1",
        regime_ref=f"resource-regime:{'2' if contracted else '1'}",
        assurance_profile="BOUNDED",
        opaque_dimensions=(),
        conservative_capacity_bound=None,
        validity_regime="ACTIVE",
    )


def _job(seed: int) -> ReactionJobContract:
    demand = ReactionResourceDemand.create(
        resource_ref=f"worker:{seed}",
        required_service=float(2 + (seed % 4)),
        required_concurrency_units=1,
        release_offset_interval=(0.0, 0.0),
        demand_window=(0.0, 10.0),
        mandatory=True,
    )
    return ReactionJobContract.create(
        reaction_job_id=f"job:{seed}",
        revision_id=f"job:{seed}@1",
        policy_scope="policy:wave8",
        mission_revision="mission@1",
        information_partition_revision="partition@1",
        reaction_envelope_ref="reaction@1",
        release_window=(0.0, 0.0),
        deadline=10.0,
        resource_demands=(demand,),
        coexistence_tags=("default",),
        correlation_refs=(),
        priority_class="critical",
        reservation_refs=(),
        risk_class="consequential",
        model_adequacy_debt_refs=(),
        validity_regime="ACTIVE",
    )


def _sched(seed: int, resource: ControlPlaneResourceRevision):
    return ReactionSchedulabilityEvaluator.evaluate(
        certificate_id=f"sched:{seed}:{resource.revision_id}",
        revision_id=f"sched-rev:{seed}:{resource.revision_id}",
        policy_scope="policy:wave8",
        mission_revision="mission@1",
        information_partition_revision="partition@1",
        jobs=(_job(seed),),
        resources=(resource,),
        mutually_exclusive_pairs=(),
        coexistence_known=True,
        resource_reservation_refs=(),
        scheduling_model_id="wave8-bounded",
        scheduling_model_version="1",
        analysis_mode="EXACT_BOUNDED",
        worst_case_or_interval_assumptions=(),
        proof_or_solver_ref="enumeration:wave8",
        assurance_profile="BOUNDED",
        model_adequacy_debt_refs=(),
        validity_regime="ACTIVE",
    )


def _p06(recipe: Wave8CaseRecipe) -> tuple[bool, str]:
    order = {
        ReactionSchedulabilityLevel.RS0_UNANALYZED: 0,
        ReactionSchedulabilityLevel.RS1_EACH_JOB_INDIVIDUALLY_FEASIBLE: 1,
        ReactionSchedulabilityLevel.RS2_DECLARED_COHORT_FEASIBLE: 2,
        ReactionSchedulabilityLevel.RS3_ROBUST_COHORT_SCHEDULABLE: 3,
        ReactionSchedulabilityLevel.RS4_CLOSED_SUBDOMAIN_PROVEN: 4,
    }
    broad = _sched(recipe.seed, _resource(recipe.seed, contracted=False))
    contracted = _sched(recipe.seed, _resource(recipe.seed, contracted=True))
    holds = order[contracted.level] <= order[broad.level]
    return holds, f"broad={broad.level.value} contracted={contracted.level.value}"


def _rank(seed: int, *, debt: int) -> ContinuationProgressRank:
    return ContinuationProgressRank.create(
        rank_id=f"rank:{seed}:{debt}",
        revision_id=f"rank:{seed}:{debt}@1",
        continuation_scope=f"policy:{seed}",
        mission_revision="mission@1",
        unresolved_critical_debt_count=debt,
        remaining_unprepared_boundaries=1,
        absolute_executable_horizon=100.0,
        minimum_preparedness_at_next_boundary=3,
        remaining_synthesis_workload=4.0,
        reaction_refinement_slack=20.0,
        mission_distance_measure=float(debt),
        semantic_continuation_digest=f"semantic:{seed}:{debt}",
        debt_equivalence_refs=tuple(f"debt:{index}" for index in range(debt)),
        created_at=float(3 - debt),
    )


def _p07(recipe: Wave8CaseRecipe) -> tuple[bool, str]:
    policy = HandoffProgressPolicy.create(
        policy_id=f"policy:{recipe.seed}",
        revision_id=f"policy:{recipe.seed}@1",
        max_handoff_count=5,
        max_total_deferral_time=30.0,
        minimum_horizon_advance=5.0,
        minimum_debt_reduction_rate=1,
        mandatory_preparedness_floor_by_time=((10.0, 2),),
        bounded_stutter_allowance=1,
        recovery_stutter_allowance=1,
        absolute_latest_safe_refinement_time=50.0,
        temporal_authority_ref="temporal@1",
    )
    kwargs = dict(
        certificate_id=f"live:{recipe.seed}",
        revision_id=f"live:{recipe.seed}@1",
        source_continuation_ref="source",
        successor_continuation_ref="successor",
        old_rank=_rank(recipe.seed, debt=2),
        new_rank=_rank(recipe.seed, debt=1),
        progress_policy=policy,
        handoff_count=1,
        ordinary_stutter_count=0,
        recovery_stutter_count=0,
        total_deferral_time=1.0,
        recursive_feasibility=True,
        recovery_mode=False,
        temporal_authority_revision_ref="temporal@1",
        current_time=1.0,
        debt_lineage_equivalent=True,
    )
    baseline = HandoffLivenessEvaluator.evaluate(information_available_by_deadline=True, **kwargs)
    delayed = HandoffLivenessEvaluator.evaluate(information_available_by_deadline=False, **kwargs)
    holds = (not delayed.supports_safe_handoff) or baseline.supports_safe_handoff
    return holds, f"baseline={baseline.status.value} delayed={delayed.status.value}"


def _kernel(seed: int, root: Path):
    # Import here so package installer layering has already completed before the
    # generated property invokes the runtime class.
    from . import PlanKernel

    return PlanKernel.create(root, f"wave8 property mission {seed}", ("done",), ("preserve history",))


def _p08(recipe: Wave8CaseRecipe) -> tuple[bool, str]:
    with tempfile.TemporaryDirectory(prefix="nolane-wave8-p08-") as temp:
        kernel = _kernel(recipe.seed, Path(temp))
        action_id = f"action:{recipe.seed}"
        grant_id = f"grant:{recipe.seed}"
        principal = f"agent:{recipe.seed}"
        kernel.propose_action(ActionIntent(action_id, "deploy"))
        kernel.add_grant(AuthorityGrant(grant_id, principal, frozenset({"deploy"})))
        authorization = kernel.authorize(action_id, principal, (grant_id,), 1)
        kernel.revise_semantic_regime(
            SemanticRegimeKind.ENVIRONMENT,
            semantic_digest=f"environment:drift:{recipe.seed}",
            provenance_refs=("wave8:property",),
        )
        adapter = _CountingAdapter()
        blocked = False
        try:
            kernel.dispatch(authorization.id, principal, adapter, 2)
        except AuthorizationError:
            blocked = True
        return blocked and adapter.calls == 0, f"blocked={blocked} adapter_calls={adapter.calls}"


def _p09(recipe: Wave8CaseRecipe) -> tuple[bool, str]:
    with tempfile.TemporaryDirectory(prefix="nolane-wave8-p09-") as temp:
        kernel = _kernel(recipe.seed, Path(temp))
        action_id = f"action:{recipe.seed}"
        grant_id = f"grant:{recipe.seed}"
        principal = f"agent:{recipe.seed}"
        kernel.propose_action(ActionIntent(action_id, "deploy"))
        kernel.add_grant(AuthorityGrant(grant_id, principal, frozenset({"deploy"})))
        authorization = kernel.authorize(action_id, principal, (grant_id,), 1)
        before = {row.revision_id for row in kernel.lineage.all_revisions()}
        result = kernel.compact_lineage(f"property-compaction:{recipe.seed}")
        after = {row.revision_id for row in kernel.lineage.all_revisions()}
        reconstructed = kernel.reconstruct_compacted_lineage(result.manifest_id)
        reconstructed_ids = {row.revision_id for row in reconstructed.all_revisions()}
        binding = kernel.authorization_lineage_bindings[authorization.id]
        protected = {
            binding.mission_revision_id,
            binding.canonical_state_revision_id,
            binding.action_revision_id,
            *binding.grant_revision_ids,
        }
        manifest = kernel.compaction_manifests[result.manifest_id]
        holds = before.issubset(after) and before.issubset(reconstructed_ids) and protected.issubset(
            set(manifest.active_authority_revision_ids)
        )
        return holds, (
            f"before={len(before)} after={len(after)} reconstructed={len(reconstructed_ids)} "
            f"protected={len(protected)}"
        )


def _p10(recipe: Wave8CaseRecipe) -> tuple[bool, str]:
    suffix = str(recipe.seed)
    state = {"mode": "ready"}
    no_match = StateRelocator(
        [CandidateRegion(f"off:{suffix}", {"mode": "offline"}, "hold")]
    ).locate(state)
    ambiguous = StateRelocator(
        [
            CandidateRegion(f"left:{suffix}", {"mode": "ready"}, "deploy"),
            CandidateRegion(f"right:{suffix}", {"mode": "ready"}, "rollback"),
        ]
    ).locate(state)
    holds = no_match.status is LocationStatus.UNLOCATED and ambiguous.status is LocationStatus.AMBIGUOUS
    return holds, f"no_match={no_match.status.value} ambiguous={ambiguous.status.value}"


_PROPERTY_EVALUATORS: dict[str, Callable[[Wave8CaseRecipe], tuple[bool, str]]] = {
    "P01": _p01,
    "P02": _p02,
    "P03": _p03,
    "P04": _p04,
    "P05": _p05,
    "P06": _p06,
    "P07": _p07,
    "P08": _p08,
    "P09": _p09,
    "P10": _p10,
}


def _evaluate(invariant_id: str, recipe: Wave8CaseRecipe) -> tuple[bool, str]:
    try:
        return _PROPERTY_EVALUATORS[invariant_id](recipe)
    except Exception as exc:  # exceptions are counterexamples, never silent skips
        return False, f"{type(exc).__name__}: {exc}"


def _counterexample(invariant_id: str, recipe: Wave8CaseRecipe, summary: str) -> Wave8Counterexample:
    row = _PROPERTY_ROWS[invariant_id]

    def still_fails(candidate: Wave8CaseRecipe) -> bool:
        holds, _ = _evaluate(invariant_id, candidate)
        return not holds

    minimized = minimize_recipe(recipe, still_fails)
    return Wave8Counterexample.create(
        invariant_id=invariant_id,
        case_id=f"{invariant_id}:{recipe.seed}",
        seed=recipe.seed,
        generator_version=recipe.generator_version,
        recipe=recipe.operations,
        minimized_recipe=minimized.operations,
        expected_relation=row.expectation,
        observed_summary=summary,
    )


def run_wave8_property(
    invariant_id: str,
    seeds: Iterable[int],
) -> tuple[Wave8Counterexample, ...]:
    invariant = str(invariant_id).strip().upper()
    if invariant not in _PROPERTY_EVALUATORS:
        raise ValueError(f"unknown Wave-8 property invariant: {invariant_id}")
    row = _PROPERTY_ROWS[invariant]
    failures: list[Wave8Counterexample] = []
    for seed in sorted({int(value) for value in seeds}):
        recipe = generate_case(row.generator_family, seed)
        holds, summary = _evaluate(invariant, recipe)
        if not holds:
            failures.append(_counterexample(invariant, recipe, summary))
    return tuple(failures)


def run_wave8_properties(seeds: Iterable[int]) -> tuple[Wave8Counterexample, ...]:
    seed_tuple = tuple(sorted({int(value) for value in seeds}))
    failures = [
        counterexample
        for invariant_id in PROPERTY_IDS
        for counterexample in run_wave8_property(invariant_id, seed_tuple)
    ]
    return tuple(sorted(failures, key=lambda row: (row.invariant_id, row.seed, row.case_id)))
