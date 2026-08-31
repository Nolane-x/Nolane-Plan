from __future__ import annotations

from pathlib import Path
import tempfile
from typing import Callable, Iterable

from .actions import ActionIntent, AuthorityGrant
from .control_plane import ControlPlaneResourceRevision, ReactionJobContract, ReactionResourceDemand
from .hashing import digest
from .lineage import CanonicalLineageRevision
from .lineage_recovery import canonical_semantic_digest
from .migration import FieldMigrationDisposition, MigrationDisposition, MigrationManifest
from .policy_information import DecisionEpoch, InformationPartitionRevision, NonAnticipativityValidator
from .policy_ir import PolicyNodeRevision, PolicySuccessorRoute
from .schedulability import ReactionSchedulabilityEvaluator
from .support import SupportAlternativeSetRevision, SupportClause, SupportEvaluator, SupportNode
from .wave8_generators import Wave8CaseRecipe, generate_case, minimize_recipe
from .wave8_registry import WAVE8_INVARIANTS, Wave8Counterexample


METAMORPHIC_IDS = tuple(f"M{index:02d}" for index in range(1, 13))
_METAMORPHIC_ROWS = {
    row.invariant_id: row for row in WAVE8_INVARIANTS if row.invariant_id in METAMORPHIC_IDS
}


def _revision(seed: int, *, wall_time: float | None, provenance: Iterable[str]) -> CanonicalLineageRevision:
    return CanonicalLineageRevision.create(
        object_family="Wave8Metamorphic",
        logical_id=f"logical:{seed}",
        revision_id=f"revision:{seed}",
        schema_version="schema:wave8-metamorphic:v1",
        created_sequence=seed + 1,
        created_at_wall_time=wall_time,
        mission_revision_dependency=None,
        plan_revision=1,
        world_model_revision="world-model:wave8:v1",
        environment_regime_revision="environment:wave8:v1",
        validity_regime="ACTIVE",
        parent_revision_ids=(),
        provenance_refs=tuple(provenance),
        assurance_profile="KERNEL_ACCEPTED",
        debt_refs=(f"debt:{seed}:b", f"debt:{seed}:a"),
        supersedes_revision_id=None,
        semantic_digest=digest({"seed": seed, "semantic": "stable"}),
    )


def _m01(recipe: Wave8CaseRecipe) -> tuple[bool, str]:
    left = _revision(
        recipe.seed,
        wall_time=None,
        provenance=(f"source:{recipe.seed}:a", f"source:{recipe.seed}:b"),
    )
    right = _revision(
        recipe.seed,
        wall_time=None,
        provenance=(f"source:{recipe.seed}:b", f"source:{recipe.seed}:a"),
    )
    holds = left.lineage_digest == right.lineage_digest and left.provenance_refs == right.provenance_refs
    return holds, f"left={left.lineage_digest} right={right.lineage_digest}"


def _m02(recipe: Wave8CaseRecipe) -> tuple[bool, str]:
    left = _revision(recipe.seed, wall_time=1.0, provenance=(f"source:{recipe.seed}",))
    right = _revision(recipe.seed, wall_time=999999.0, provenance=(f"source:{recipe.seed}",))
    holds = left.lineage_digest == right.lineage_digest and left.semantic_digest == right.semantic_digest
    return holds, f"left={left.lineage_digest} right={right.lineage_digest}"


def _single_support(seed: int, *, include_irrelevant: bool):
    clause = SupportClause(
        clause_id=f"clause:{seed}",
        required_support_refs=(f"required:{seed}",),
        scope="mission",
        assumption_basis=frozenset({"assumption@1"}),
        proof_kind="verification",
        grounding_root_requirements=frozenset(),
        validity_regime="runtime@1",
        context_tags=frozenset({"prod"}),
        minimum_independent_roots=1,
    )
    support_set = SupportAlternativeSetRevision.create(
        support_set_id=f"set:{seed}",
        revision_id=f"set:{seed}@1",
        subject_artifact_revision=f"proof:{seed}@1",
        clauses=(clause,),
        scope="mission",
        assumption_context_rules=("prod",),
        proof_kind="verification",
        grounding_policy="accepted-roots-only",
        support_evaluation_profile="bounded-dnf@1",
        created_sequence=10,
    )
    nodes = {
        f"required:{seed}": SupportNode(
            ref=f"required:{seed}",
            current=True,
            direct_grounding_roots=frozenset({f"root:{seed}"}),
            support_refs=(),
            scope="mission",
            assumption_basis=frozenset({"assumption@1"}),
            proof_kind="verification",
            validity_regime="runtime@1",
            context_tags=frozenset({"prod"}),
        )
    }
    if include_irrelevant:
        nodes[f"irrelevant:{seed}"] = SupportNode(
            ref=f"irrelevant:{seed}",
            current=True,
            direct_grounding_roots=frozenset({f"irrelevant-root:{seed}"}),
            support_refs=(),
            scope="other-scope",
            assumption_basis=frozenset({"other@1"}),
            proof_kind="advisory",
            validity_regime="runtime@1",
            context_tags=frozenset({"other"}),
        )
    return SupportEvaluator.evaluate(
        support_set,
        nodes,
        active_context={"prod"},
        evaluated_at_cut=f"cut:{seed}",
        generation=1,
    )


def _m03(recipe: Wave8CaseRecipe) -> tuple[bool, str]:
    base = _single_support(recipe.seed, include_irrelevant=False)
    transformed = _single_support(recipe.seed, include_irrelevant=True)
    projection = lambda row: (
        row.status,
        row.surviving_clause_refs,
        row.grounding_roots,
        row.assessment_digest,
    )
    holds = projection(base) == projection(transformed)
    return holds, f"base={projection(base)!r} transformed={projection(transformed)!r}"


def _common_root_support(seed: int, refs: tuple[str, ...]):
    clause = SupportClause(
        clause_id=f"independence:{seed}",
        required_support_refs=refs,
        scope="mission",
        assumption_basis=frozenset({"assumption@1"}),
        proof_kind="verification",
        grounding_root_requirements=frozenset(),
        validity_regime="runtime@1",
        context_tags=frozenset({"prod"}),
        minimum_independent_roots=2,
    )
    support_set = SupportAlternativeSetRevision.create(
        support_set_id=f"independence-set:{seed}",
        revision_id=f"independence-set:{seed}@1",
        subject_artifact_revision=f"proof:{seed}@1",
        clauses=(clause,),
        scope="mission",
        assumption_context_rules=("prod",),
        proof_kind="verification",
        grounding_policy="accepted-roots-only",
        support_evaluation_profile="bounded-dnf@1",
        created_sequence=20,
    )
    nodes = {
        ref: SupportNode(
            ref=ref,
            current=True,
            direct_grounding_roots=frozenset({f"shared-root:{seed}"}),
            support_refs=(),
            scope="mission",
            assumption_basis=frozenset({"assumption@1"}),
            proof_kind="verification",
            validity_regime="runtime@1",
            context_tags=frozenset({"prod"}),
        )
        for ref in refs
    }
    return SupportEvaluator.evaluate(
        support_set,
        nodes,
        active_context={"prod"},
        evaluated_at_cut=f"cut:{seed}",
        generation=1,
    )


def _m04(recipe: Wave8CaseRecipe) -> tuple[bool, str]:
    base_refs = (f"a:{recipe.seed}", f"b:{recipe.seed}")
    duplicate_refs = base_refs + (f"copy:{recipe.seed}",)
    base = _common_root_support(recipe.seed, base_refs)
    duplicated = _common_root_support(recipe.seed, duplicate_refs)
    holds = base.status == duplicated.status and base.grounding_roots == duplicated.grounding_roots
    return holds, f"base={base.status.value}:{base.grounding_roots!r} duplicated={duplicated.status.value}:{duplicated.grounding_roots!r}"


def _partition(seed: int, histories: tuple[str, ...]) -> InformationPartitionRevision:
    return InformationPartitionRevision.create(
        logical_id=f"partition:{seed}",
        revision_id=f"partition:{seed}@1",
        mission_revision=1,
        decision_epoch_ref=f"epoch:{seed}",
        principal_scope_ref=f"agent:{seed}",
        information_access_profile_revision="access@1",
        principal_observation_history_digest=digest({"seed": seed, "principal": "history"}),
        principal_delivery_frontier_refs=(),
        canonical_state_version=1,
        observation_history_digest=digest({"seed": seed, "global": "history"}),
        observable_predicate_set=("visible",),
        hidden_or_unrevealed_predicate_set=("hidden",),
        information_equivalence_classes={"class:equivalent": histories},
        reveal_event_refs=(),
        observation_model_refs=("observation-model@1",),
        perfect_recall_basis_ref="recall@1",
        abstraction_certificate_refs=(),
        debt_refs=(),
        validity_regime="ACTIVE",
    )


def _epoch(seed: int) -> DecisionEpoch:
    return DecisionEpoch.create(
        epoch_id=f"epoch:{seed}",
        plan_snapshot_version=1,
        mission_revision=1,
        decision_principal_ref=f"agent:{seed}",
        strategic_location_revision=1,
        information_partition_revision=f"partition:{seed}@1",
        principal_information_access_profile_revision="access@1",
        available_action_space_revision="actions@1",
        active_authority_profile="authority@1",
        active_obligation_basis="obligations@1",
        risk_policy_revision="risk@1",
        observation_frontier_revision="frontier@1",
        temporal_window=(0, 10),
    )


def _m05(recipe: Wave8CaseRecipe) -> tuple[bool, str]:
    histories = (f"h:{recipe.seed}:a", f"h:{recipe.seed}:b")
    aliases = (f"alias:{recipe.seed}:a", f"alias:{recipe.seed}:b")
    base = NonAnticipativityValidator.validate(
        _partition(recipe.seed, histories),
        _epoch(recipe.seed),
        action_semantics_by_history={value: "deploy" for value in histories},
        reveal_events=(),
        decision_time=1,
    )
    transformed = NonAnticipativityValidator.validate(
        _partition(recipe.seed, aliases),
        _epoch(recipe.seed),
        action_semantics_by_history={value: "deploy" for value in aliases},
        reveal_events=(),
        decision_time=1,
    )
    projection = lambda row: (row.valid, tuple(item.code for item in row.violations), bool(row.debt_refs))
    holds = projection(base) == projection(transformed)
    return holds, f"base={projection(base)!r} transformed={projection(transformed)!r}"


def _policy_node(seed: int, routes: Iterable[PolicySuccessorRoute]) -> PolicyNodeRevision:
    return PolicyNodeRevision.create(
        policy_node_id=f"node:{seed}",
        revision_id=f"node:{seed}@1",
        mission_revision=1,
        decision_principal_ref=f"agent:{seed}",
        plan_snapshot_version=1,
        strategic_location_revision=1,
        information_partition_revision=f"partition:{seed}@1",
        decision_epoch_ref=f"epoch:{seed}",
        action_space_revision="actions@1",
        candidate_action_contracts=("deploy", "rollback"),
        execution_principal_requirement_or_set=(f"agent:{seed}",),
        selected_action_contract_or_policy_set=("deploy",),
        runtime_guard_refs=("guard:ready",),
        observation_frontier_revision="frontier@1",
        successor_policy_mapping=tuple(routes),
        shared_commitment_refs=(),
        resource_reservation_refs=(),
        obligation_basis_ref="obligations@1",
        risk_policy_revision="risk@1",
        authority_profile_requirement="authority@1",
        route_guarantee_requirement="IA2",
        preparedness_level="P2",
        proof_context_ref="proof-context@1",
        assurance_profile="BOUNDED",
        debt_refs=(),
        sealed=False,
    )


def _m06(recipe: Wave8CaseRecipe) -> tuple[bool, str]:
    routes = (
        PolicySuccessorRoute("guard:a", "reveal:a", f"child:{recipe.seed}:a"),
        PolicySuccessorRoute("guard:b", "reveal:b", f"child:{recipe.seed}:b"),
    )
    left = _policy_node(recipe.seed, routes)
    right = _policy_node(recipe.seed, reversed(routes))
    holds = left.canonical_digest == right.canonical_digest and left.successor_policy_mapping == right.successor_policy_mapping
    return holds, f"left={left.canonical_digest} right={right.canonical_digest}"


def _resource(seed: int, suffix: str) -> ControlPlaneResourceRevision:
    return ControlPlaneResourceRevision.create(
        resource_id=f"worker:{seed}:{suffix}",
        revision_id=f"worker:{seed}:{suffix}@1",
        resource_kind="CONCURRENCY",
        capacity_units=3,
        concurrency_limit=3,
        service_rate_per_second=3.0,
        rate_window_seconds=1.0,
        availability_interval=(0.0, 20.0),
        priority_policy_ref="priority@1",
        reservation_policy_ref="reservation@1",
        regime_ref="resource-regime@1",
        assurance_profile="BOUNDED",
        opaque_dimensions=(),
        conservative_capacity_bound=None,
        validity_regime="ACTIVE",
    )


def _job(seed: int, suffix: str, resource_ref: str) -> ReactionJobContract:
    demand = ReactionResourceDemand.create(
        resource_ref=resource_ref,
        required_service=1.0,
        required_concurrency_units=1,
        release_offset_interval=(0.0, 0.0),
        demand_window=(0.0, 10.0),
        mandatory=True,
    )
    return ReactionJobContract.create(
        reaction_job_id=f"job:{seed}:{suffix}",
        revision_id=f"job:{seed}:{suffix}@1",
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


def _sched(seed: int, *, reverse: bool):
    resources = (_resource(seed, "a"), _resource(seed, "b"))
    jobs = (
        _job(seed, "a", resources[0].resource_id),
        _job(seed, "b", resources[1].resource_id),
    )
    if reverse:
        resources = tuple(reversed(resources))
        jobs = tuple(reversed(jobs))
    return ReactionSchedulabilityEvaluator.evaluate(
        certificate_id=f"sched:{seed}",
        revision_id=f"sched:{seed}@1",
        policy_scope="policy:wave8",
        mission_revision="mission@1",
        information_partition_revision="partition@1",
        jobs=jobs,
        resources=resources,
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


def _m07(recipe: Wave8CaseRecipe) -> tuple[bool, str]:
    left = _sched(recipe.seed, reverse=False)
    right = _sched(recipe.seed, reverse=True)
    holds = left.canonical_digest == right.canonical_digest and left.level == right.level
    return holds, f"left={left.level.value}:{left.canonical_digest} right={right.level.value}:{right.canonical_digest}"


def _kernel(seed: int, root: Path):
    from . import PlanKernel

    return PlanKernel.create(root, f"wave8 metamorphic mission {seed}", ("done",), ("preserve history",))


def _m08(recipe: Wave8CaseRecipe) -> tuple[bool, str]:
    with tempfile.TemporaryDirectory(prefix="nolane-wave8-m08-") as temp:
        root = Path(temp)
        kernel = _kernel(recipe.seed, root)
        before = canonical_semantic_digest(kernel)
        kernel.save_snapshot()
        from . import PlanKernel

        restored = PlanKernel.open(root)
        after = canonical_semantic_digest(restored)
        return before == after, f"before={before} after={after}"


def _m09(recipe: Wave8CaseRecipe) -> tuple[bool, str]:
    with tempfile.TemporaryDirectory(prefix="nolane-wave8-m09-") as temp:
        root = Path(temp)
        kernel = _kernel(recipe.seed, root)
        kernel.save_snapshot()
        kernel.revise_mission(objective=f"after-snapshot:{recipe.seed}")
        expected = canonical_semantic_digest(kernel)
        from . import PlanKernel

        restored = PlanKernel.open(root)
        actual = canonical_semantic_digest(restored)
        holds = expected == actual and restored.mission.current.objective == f"after-snapshot:{recipe.seed}"
        return holds, f"expected={expected} actual={actual}"


def _m10(recipe: Wave8CaseRecipe) -> tuple[bool, str]:
    with tempfile.TemporaryDirectory(prefix="nolane-wave8-m10-") as temp:
        kernel = _kernel(recipe.seed, Path(temp))
        action_id = f"action:{recipe.seed}"
        grant_id = f"grant:{recipe.seed}"
        principal = f"agent:{recipe.seed}"
        kernel.propose_action(ActionIntent(action_id, "deploy"))
        kernel.add_grant(AuthorityGrant(grant_id, principal, frozenset({"deploy"})))
        authorization = kernel.authorize(action_id, principal, (grant_id,), 1)
        before = canonical_semantic_digest(kernel)
        kernel._assert_authorization_lineage_current(authorization)
        result = kernel.compact_lineage(f"metamorphic-compaction:{recipe.seed}")
        kernel._assert_authorization_lineage_current(authorization)
        after = canonical_semantic_digest(kernel)
        holds = before == after and result.source_canonical_semantic_digest == result.target_canonical_semantic_digest
        return holds, f"before={before} after={after}"


def _m11(recipe: Wave8CaseRecipe) -> tuple[bool, str]:
    with tempfile.TemporaryDirectory(prefix="nolane-wave8-m11-") as temp:
        root = Path(temp)
        kernel = _kernel(recipe.seed, root)
        kernel.propose_action(ActionIntent(f"action:{recipe.seed}", "deploy"))
        kernel.add_grant(
            AuthorityGrant(f"grant:{recipe.seed}", f"agent:{recipe.seed}", frozenset({"deploy"}))
        )
        kernel.save_snapshot_v6()
        from . import PlanKernel

        first = PlanKernel.open(root)
        second = PlanKernel.open(root)
        projection = lambda row: (
            row.lineage.semantic_root_digest(),
            tuple(sorted(row.migration_recheck_required_authorizations)),
        )
        holds = projection(first) == projection(second)
        return holds, f"first={projection(first)!r} second={projection(second)!r}"


def _manifest(seed: int, *, reverse: bool) -> MigrationManifest:
    fields = [
        ("ActionIntent", "parameters"),
        ("EvidenceRecord", "assurance"),
    ]
    dispositions = [
        FieldMigrationDisposition(
            "ActionIntent",
            "parameters",
            MigrationDisposition.PRESERVED_EXACTLY,
            source_ref=f"action:{seed}:source",
            target_ref=f"action:{seed}:target",
        ),
        FieldMigrationDisposition(
            "EvidenceRecord",
            "assurance",
            MigrationDisposition.INVALIDATED_REQUIRES_RECHECK,
            source_ref=f"evidence:{seed}:source",
            target_ref=f"evidence:{seed}:target",
        ),
    ]
    if reverse:
        fields.reverse()
        dispositions.reverse()
    return MigrationManifest.create(
        manifest_id=f"manifest:{seed}",
        source_schema_revision="schema:source:v1",
        target_schema_revision="schema:target:v2",
        target_schema_semantic_digest=digest({"target": seed}),
        changed_correctness_fields=fields,
        field_dispositions=dispositions,
        identity_mappings=(),
        checked_invariants=("I-B", "I-A") if reverse else ("I-A", "I-B"),
        revoked_certificate_refs=("cert:b", "cert:a") if reverse else ("cert:a", "cert:b"),
        revoked_authorization_refs=("auth:b", "auth:a") if reverse else ("auth:a", "auth:b"),
        new_debt_refs=(),
        replay_fixture_digests=("fixture:b", "fixture:a") if reverse else ("fixture:a", "fixture:b"),
        rollback_procedure_ref="rollback@1",
        backup_ref="backup@1",
        unsupported_legacy_cases=("legacy:b", "legacy:a") if reverse else ("legacy:a", "legacy:b"),
        external_effect_history_refs=("effect:b", "effect:a") if reverse else ("effect:a", "effect:b"),
        provenance_refs=("provenance:b", "provenance:a") if reverse else ("provenance:a", "provenance:b"),
    )


def _m12(recipe: Wave8CaseRecipe) -> tuple[bool, str]:
    left = _manifest(recipe.seed, reverse=False)
    right = _manifest(recipe.seed, reverse=True)
    holds = left.canonical_digest == right.canonical_digest and left.canonical_payload() == right.canonical_payload()
    return holds, f"left={left.canonical_digest} right={right.canonical_digest}"


_RELATIONS: dict[str, Callable[[Wave8CaseRecipe], tuple[bool, str]]] = {
    "M01": _m01,
    "M02": _m02,
    "M03": _m03,
    "M04": _m04,
    "M05": _m05,
    "M06": _m06,
    "M07": _m07,
    "M08": _m08,
    "M09": _m09,
    "M10": _m10,
    "M11": _m11,
    "M12": _m12,
}


def _evaluate(invariant_id: str, recipe: Wave8CaseRecipe) -> tuple[bool, str]:
    try:
        return _RELATIONS[invariant_id](recipe)
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"


def _counterexample(invariant_id: str, recipe: Wave8CaseRecipe, summary: str) -> Wave8Counterexample:
    row = _METAMORPHIC_ROWS[invariant_id]

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


def run_wave8_metamorphic_relation(
    invariant_id: str,
    seeds: Iterable[int],
) -> tuple[Wave8Counterexample, ...]:
    invariant = str(invariant_id).strip().upper()
    if invariant not in _RELATIONS:
        raise ValueError(f"unknown Wave-8 metamorphic invariant: {invariant_id}")
    row = _METAMORPHIC_ROWS[invariant]
    failures: list[Wave8Counterexample] = []
    for seed in sorted({int(value) for value in seeds}):
        recipe = generate_case(row.generator_family, seed)
        holds, summary = _evaluate(invariant, recipe)
        if not holds:
            failures.append(_counterexample(invariant, recipe, summary))
    return tuple(failures)


def run_wave8_metamorphic(seeds: Iterable[int]) -> tuple[Wave8Counterexample, ...]:
    seed_tuple = tuple(sorted({int(value) for value in seeds}))
    failures = [
        counterexample
        for invariant_id in METAMORPHIC_IDS
        for counterexample in run_wave8_metamorphic_relation(invariant_id, seed_tuple)
    ]
    return tuple(sorted(failures, key=lambda row: (row.invariant_id, row.seed, row.case_id)))
