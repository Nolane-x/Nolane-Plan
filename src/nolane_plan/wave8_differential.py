from __future__ import annotations

from pathlib import Path
import tempfile
from typing import Callable, Iterable

from .actions import ActionIntent, AuthorityGrant
from .control_plane import ControlPlaneResourceRevision, ReactionJobContract, ReactionResourceDemand
from .handoff_liveness import (
    ContinuationProgressRank,
    HandoffLivenessEvaluator,
    HandoffProgressPolicy,
)
from .hashing import digest
from .lineage import SemanticRegimeKind
from .lineage_recovery import canonical_semantic_digest
from .migration import FieldMigrationDisposition, MigrationDisposition, MigrationManifest
from .principals import InformationItem
from .relocation import CandidateRegion, LocationStatus, StateRelocator
from .schedulability import ReactionSchedulabilityEvaluator
from .wave8_proof_fixture import build_proof_authorized_kernel
from .wave8_registry import WAVE8_INVARIANTS, Wave8Counterexample


DIFFERENTIAL_IDS = tuple(f"D{index:02d}" for index in range(1, 11))
_DIFFERENTIAL_ROWS = {
    row.invariant_id: row for row in WAVE8_INVARIANTS if row.invariant_id in DIFFERENTIAL_IDS
}


def _kernel(seed: int, root: Path):
    from . import PlanKernel

    return PlanKernel.create(
        root,
        f"wave8 differential mission {seed}",
        ("done",),
        ("preserve history",),
    )


def _authorized_kernel(seed: int, root: Path):
    kernel = _kernel(seed, root)
    action_id = f"action:{seed}"
    grant_id = f"grant:{seed}"
    principal = f"agent:{seed}"
    kernel.propose_action(ActionIntent(action_id, "deploy"))
    kernel.add_grant(AuthorityGrant(grant_id, principal, frozenset({"deploy"})))
    authorization = kernel.authorize(action_id, principal, (grant_id,), 1)
    return kernel, authorization, principal


def _manifest(kernel, seed: int) -> MigrationManifest:
    source = kernel.lineage.current_regime(SemanticRegimeKind.SCHEMA).revision_id
    return MigrationManifest.create(
        manifest_id=f"wave8-differential-migration:{seed}",
        source_schema_revision=source,
        target_schema_revision=f"schema:nolane-plan:v7-wave8-differential-{seed}",
        target_schema_semantic_digest=digest({"wave8-differential-target": seed}),
        changed_correctness_fields=(("PolicyNodeRevision", "guard_semantics"),),
        field_dispositions=(
            FieldMigrationDisposition(
                "PolicyNodeRevision",
                "guard_semantics",
                MigrationDisposition.INVALIDATED_REQUIRES_RECHECK,
            ),
        ),
        identity_mappings=(),
        checked_invariants=("no_authority_promotion",),
        revoked_certificate_refs=(),
        revoked_authorization_refs=(),
        new_debt_refs=(),
        replay_fixture_digests=(f"wave8-differential:{seed}",),
        rollback_procedure_ref="rollback:wave8-differential",
        backup_ref="backup:wave8-differential",
        unsupported_legacy_cases=("opaque-legacy",),
        external_effect_history_refs=(),
        provenance_refs=("wave8:differential",),
    )


def _projection(kernel) -> tuple[object, ...]:
    return (
        kernel.mission.current.version,
        kernel.mission.current.objective,
        kernel.canonical_version,
        tuple(sorted(kernel.canonical_state.items())),
        kernel.strategic_location.status.value,
        tuple(kernel.strategic_location.region_ids),
        tuple(sorted((tx.id, tx.state.value) for tx in kernel.transactions.all())),
        canonical_semantic_digest(kernel),
    )


def _d01(seed: int) -> tuple[bool, str]:
    with tempfile.TemporaryDirectory(prefix="nolane-wave8-d01-") as temp:
        root = Path(temp)
        kernel, _, _ = _authorized_kernel(seed, root)
        live = _projection(kernel)
        kernel.save_snapshot()
        from . import PlanKernel

        restored = PlanKernel.open(root)
        replayed = _projection(restored)
        return live == replayed, f"live={live!r} replayed={replayed!r}"


def _d02(seed: int) -> tuple[bool, str]:
    with tempfile.TemporaryDirectory(prefix="nolane-wave8-d02-") as temp:
        root = Path(temp)
        kernel = _kernel(seed, root)
        kernel.save_snapshot()
        kernel.revise_mission(objective=f"wave8-differential-suffix:{seed}")
        live = _projection(kernel)
        from . import PlanKernel

        restored = PlanKernel.open(root)
        replayed = _projection(restored)
        return live == replayed, f"live={live!r} replayed={replayed!r}"


def _d03(seed: int) -> tuple[bool, str]:
    with tempfile.TemporaryDirectory(prefix="nolane-wave8-d03-") as temp:
        root = Path(temp)
        kernel = _kernel(seed, root)
        kernel.save_snapshot()
        kernel.revise_mission(objective=f"wave8-deterministic-replay:{seed}")
        from . import PlanKernel

        first = _projection(PlanKernel.open(root))
        second = _projection(PlanKernel.open(root))
        return first == second, f"first={first!r} second={second!r}"


def _d04(seed: int) -> tuple[bool, str]:
    with tempfile.TemporaryDirectory(prefix="nolane-wave8-d04-") as temp:
        root = Path(temp)
        kernel, authorization, _ = _authorized_kernel(seed, root)
        before = canonical_semantic_digest(kernel)
        kernel._assert_authorization_lineage_current(authorization.id)
        kernel.save_snapshot()
        result = kernel.compact_lineage(f"wave8-differential-compaction:{seed}")
        after = canonical_semantic_digest(kernel)
        kernel._assert_authorization_lineage_current(authorization.id)
        from . import PlanKernel

        restored = PlanKernel.open(root)
        restored._assert_authorization_lineage_current(authorization.id)
        replayed = canonical_semantic_digest(restored)
        holds = (
            before == after == replayed
            and result.source_canonical_semantic_digest == result.target_canonical_semantic_digest
        )
        return holds, f"before={before} after={after} replayed={replayed}"


def _legacy_common_projection(kernel) -> tuple[object, ...]:
    return (
        kernel.mission.current.version,
        kernel.mission.current.objective,
        kernel.canonical_version,
        tuple(sorted(kernel.canonical_state.items())),
        tuple(sorted(kernel.actions)),
        tuple(sorted(kernel.grants)),
    )


def _d05(seed: int) -> tuple[bool, str]:
    with tempfile.TemporaryDirectory(prefix="nolane-wave8-d05-") as temp:
        root = Path(temp)
        kernel, authorization, _ = _authorized_kernel(seed, root)
        direct = _legacy_common_projection(kernel)
        kernel.save_snapshot_v6()
        from . import PlanKernel

        imported = PlanKernel.open(root)
        legacy = _legacy_common_projection(imported)
        holds = (
            direct == legacy
            and authorization.id in imported.authorizations
            and authorization.id in imported.migration_recheck_required_authorizations
        )
        return holds, f"direct={direct!r} legacy={legacy!r} recheck={authorization.id in imported.migration_recheck_required_authorizations}"


def _migration_projection(kernel) -> tuple[object, ...]:
    return (
        kernel.lineage.current_regime(SemanticRegimeKind.SCHEMA).revision_id,
        tuple(
            (
                row.manifest_id,
                row.source_schema_revision,
                row.target_schema_revision,
                row.invalidated_authorization_ids,
                row.new_debt_refs,
                row.bridge_evidence_ref,
            )
            for row in kernel.migration_history
        ),
        tuple(sorted(kernel.migration_recheck_required_authorizations)),
        canonical_semantic_digest(kernel),
    )


def _d06(seed: int) -> tuple[bool, str]:
    with tempfile.TemporaryDirectory(prefix="nolane-wave8-d06-") as temp:
        root = Path(temp)
        kernel, authorization, _ = _authorized_kernel(seed, root)
        kernel.save_snapshot()
        kernel.apply_semantic_migration(_manifest(kernel, seed), now=2)
        live = _migration_projection(kernel)
        from . import PlanKernel

        restored = PlanKernel.open(root)
        replayed = _migration_projection(restored)
        holds = live == replayed and authorization.id in restored.migration_recheck_required_authorizations
        return holds, f"live={live!r} replayed={replayed!r}"


def _d07(seed: int) -> tuple[bool, str]:
    with tempfile.TemporaryDirectory(prefix="nolane-wave8-d07-") as temp:
        root = Path(temp)
        kernel = _kernel(seed, root)
        principal = f"agent:{seed}"
        item_id = f"info:{seed}"
        kernel.register_principal(principal, {"public"})
        kernel.publish_information(
            InformationItem(
                id=item_id,
                payload={"seed": seed, "signal": "ready"},
                tags=frozenset({"public"}),
                assurance=0.95,
            )
        )
        kernel.observe_information(principal, item_id, observed_at=10)
        live_partition = kernel.principals.build_partition(
            principal,
            kernel.information_items.values(),
            20,
        )
        kernel.save_snapshot()
        from . import PlanKernel

        restored = PlanKernel.open(root)
        replayed_partition = restored.principals.build_partition(
            principal,
            restored.information_items.values(),
            20,
        )
        holds = (
            live_partition.digest == replayed_partition.digest
            and live_partition.item_ids == replayed_partition.item_ids
            and kernel.principals.profile(principal).revision == restored.principals.profile(principal).revision
        )
        return holds, f"live={live_partition.digest}:{live_partition.item_ids!r} replayed={replayed_partition.digest}:{replayed_partition.item_ids!r}"


def _d08(seed: int) -> tuple[bool, str]:
    with tempfile.TemporaryDirectory(prefix="nolane-wave8-d08-") as temp:
        root = Path(temp)
        kernel, authorization, _, artifact_revision = build_proof_authorized_kernel(seed, root)
        kernel._assert_authorization_lineage_current(authorization.id)
        live_proof_binding = dict(kernel.proof_authorization_bindings[authorization.id])
        live_closure = dict(kernel.authority_lineage_closure_bindings[authorization.id])
        live_assessment = kernel.evaluate_proof_authority(artifact_revision, active_context={"prod"})
        required_exact = {
            "proof_lineage_revision",
            "proof_manifest_lineage_revision",
            "proof_support_lineage_revision",
        }
        if not required_exact.issubset(live_closure):
            return False, f"live closure lacks exact proof lineage fields: {sorted(required_exact - set(live_closure))!r}"
        kernel.save_snapshot()
        from . import PlanKernel

        restored = PlanKernel.open(root)
        restored._assert_authorization_lineage_current(authorization.id)
        replayed_proof_binding = dict(restored.proof_authorization_bindings[authorization.id])
        replayed_closure = dict(restored.authority_lineage_closure_bindings[authorization.id])
        replayed_assessment = restored.evaluate_proof_authority(artifact_revision, active_context={"prod"})
        holds = (
            digest(live_proof_binding) == digest(replayed_proof_binding)
            and live_closure.get("closure_digest") == replayed_closure.get("closure_digest")
            and live_assessment.current_usable
            and replayed_assessment.current_usable
            and live_assessment.support.status == replayed_assessment.support.status
            and live_assessment.support.grounding_roots == replayed_assessment.support.grounding_roots
        )
        return holds, (
            f"proof_binding={digest(live_proof_binding)}/{digest(replayed_proof_binding)} "
            f"closure={live_closure.get('closure_digest')}/{replayed_closure.get('closure_digest')} "
            f"support={live_assessment.support.status.value}/{replayed_assessment.support.status.value}"
        )


def _resource(seed: int) -> ControlPlaneResourceRevision:
    return ControlPlaneResourceRevision.create(
        resource_id=f"worker:{seed}",
        revision_id=f"worker:{seed}@1",
        resource_kind="CONCURRENCY",
        capacity_units=4.0,
        concurrency_limit=2,
        service_rate_per_second=5.0,
        rate_window_seconds=1.0,
        availability_interval=(0.0, 100.0),
        priority_policy_ref="priority@1",
        reservation_policy_ref="reservation@1",
        regime_ref="runtime@1",
        assurance_profile="bounded-worst-case",
        opaque_dimensions=(),
        conservative_capacity_bound=None,
        validity_regime="ACTIVE",
    )


def _job(kernel, seed: int) -> ReactionJobContract:
    demand = ReactionResourceDemand.create(
        resource_ref=f"worker:{seed}",
        required_service=1.0,
        required_concurrency_units=1,
        release_offset_interval=(0.0, 0.0),
        demand_window=(0.0, 1.0),
        mandatory=True,
    )
    return ReactionJobContract.create(
        reaction_job_id=f"job:{seed}",
        revision_id=f"job:{seed}@1",
        policy_scope=f"action:action:{seed}",
        mission_revision=str(kernel.mission.current.version),
        information_partition_revision=f"partition:{seed}@1",
        reaction_envelope_ref=f"reaction:{seed}@1",
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


def _sched(kernel, seed: int, resource, job, suffix: str):
    return ReactionSchedulabilityEvaluator.evaluate(
        certificate_id=f"sched:{seed}:{suffix}",
        revision_id=f"sched:{seed}:{suffix}@1",
        policy_scope=f"action:action:{seed}",
        mission_revision=str(kernel.mission.current.version),
        information_partition_revision=f"partition:{seed}@1",
        jobs=(job,),
        resources=(resource,),
        mutually_exclusive_pairs=(),
        coexistence_known=True,
        resource_reservation_refs=(),
        scheduling_model_id="wave8-differential-exact",
        scheduling_model_version="1",
        analysis_mode="EXACT_BOUNDED",
        worst_case_or_interval_assumptions=("bounded-single-job",),
        proof_or_solver_ref="enumeration:wave8",
        assurance_profile="BOUNDED",
        model_adequacy_debt_refs=(),
        validity_regime="ACTIVE",
    )


def _rank(kernel, seed: int, debt: int, *, suffix: str) -> ContinuationProgressRank:
    return ContinuationProgressRank.create(
        rank_id=f"rank:{seed}:{suffix}",
        revision_id=f"rank:{seed}:{suffix}@1",
        continuation_scope=f"policy:{seed}",
        mission_revision=str(kernel.mission.current.version),
        unresolved_critical_debt_count=debt,
        remaining_unprepared_boundaries=1,
        absolute_executable_horizon=100.0,
        minimum_preparedness_at_next_boundary=3,
        remaining_synthesis_workload=float(debt + 2),
        reaction_refinement_slack=20.0,
        mission_distance_measure=float(debt),
        semantic_continuation_digest=f"semantic:{seed}:{suffix}",
        debt_equivalence_refs=tuple(f"debt:{seed}:{index}" for index in range(debt)),
        created_at=1.0 if suffix == "old" else 2.0,
    )


def _liveness(kernel, seed: int, *, suffix: str):
    policy = HandoffProgressPolicy.create(
        policy_id=f"handoff-policy:{seed}",
        revision_id=f"handoff-policy:{seed}@1",
        max_handoff_count=8,
        max_total_deferral_time=30.0,
        minimum_horizon_advance=5.0,
        minimum_debt_reduction_rate=1,
        mandatory_preparedness_floor_by_time=((10.0, 2),),
        bounded_stutter_allowance=2,
        recovery_stutter_allowance=1,
        absolute_latest_safe_refinement_time=50.0,
        temporal_authority_ref=f"temporal:{seed}@1",
    )
    return HandoffLivenessEvaluator.evaluate(
        certificate_id=f"live:{seed}:{suffix}",
        revision_id=f"live:{seed}:{suffix}@1",
        source_continuation_ref=f"continuation:{seed}:source",
        successor_continuation_ref=f"continuation:{seed}:successor",
        old_rank=_rank(kernel, seed, 2, suffix="old"),
        new_rank=_rank(kernel, seed, 1, suffix="new"),
        progress_policy=policy,
        handoff_count=1,
        ordinary_stutter_count=0,
        recovery_stutter_count=0,
        total_deferral_time=1.0,
        recursive_feasibility=True,
        information_available_by_deadline=True,
        recovery_mode=False,
        temporal_authority_revision_ref=f"temporal:{seed}@1",
        current_time=1.0,
        debt_lineage_equivalent=True,
    )


def _d09(seed: int) -> tuple[bool, str]:
    with tempfile.TemporaryDirectory(prefix="nolane-wave8-d09-") as temp:
        root = Path(temp)
        kernel = _kernel(seed, root)
        resource = _resource(seed)
        job = _job(kernel, seed)
        sched = _sched(kernel, seed, resource, job, "live")
        liveness = _liveness(kernel, seed, suffix="live")
        kernel.register_control_plane_resource(resource)
        kernel.register_reaction_job(job)
        kernel.register_schedulability_certificate(sched)
        kernel.register_handoff_liveness_certificate(liveness)
        kernel.save_snapshot()
        from . import PlanKernel

        restored = PlanKernel.open(root)
        restored_resource = restored.control_plane_resources[resource.resource_id]
        restored_job = restored.reaction_jobs[job.reaction_job_id]
        recalculated = _sched(restored, seed, restored_resource, restored_job, "recalculated")
        reliveness = _liveness(restored, seed, suffix="recalculated")
        persisted_sched = restored.schedulability_certificates[sched.revision_id]
        persisted_live = restored.handoff_liveness_certificates[liveness.revision_id]
        holds = (
            persisted_sched.canonical_digest == sched.canonical_digest
            and persisted_sched.level == recalculated.level
            and persisted_sched.overload_witnesses == recalculated.overload_witnesses
            and persisted_live.canonical_digest == liveness.canonical_digest
            and persisted_live.status == reliveness.status
            and persisted_live.supports_safe_handoff == reliveness.supports_safe_handoff
        )
        return holds, (
            f"sched={persisted_sched.level.value}/{recalculated.level.value} "
            f"liveness={persisted_live.status.value}/{reliveness.status.value}"
        )


class _PatchAdapter:
    def __init__(self, patch: dict[str, object]) -> None:
        self.patch = dict(patch)

    def execute(self, action, principal_ref):
        return {
            "ok": True,
            "postconditions_verified": True,
            "executing_principal_ref": principal_ref,
            "state_patch": dict(self.patch),
        }


def _d10(seed: int) -> tuple[bool, str]:
    with tempfile.TemporaryDirectory(prefix="nolane-wave8-d10-") as temp:
        root = Path(temp)
        kernel, authorization, principal = _authorized_kernel(seed, root)
        regions = (
            CandidateRegion(f"left:{seed}", {"mode": "ready"}, "deploy"),
            CandidateRegion(f"right:{seed}", {"mode": "ready"}, "rollback"),
        )
        state = {"mode": "ready"}
        forward = StateRelocator(regions).locate(state)
        reverse = StateRelocator(tuple(reversed(regions))).locate(state)
        for region in regions:
            kernel.register_region(region)
        kernel.dispatch(authorization.id, principal, _PatchAdapter(state), 2)
        live = (
            kernel.strategic_location.status.value,
            tuple(kernel.strategic_location.region_ids),
            tuple(kernel.strategic_location.decision_signatures),
        )
        kernel.save_snapshot()
        from . import PlanKernel

        restored = PlanKernel.open(root)
        replayed = (
            restored.strategic_location.status.value,
            tuple(restored.strategic_location.region_ids),
            tuple(restored.strategic_location.decision_signatures),
        )
        ordered_equal = (
            forward.status == reverse.status
            and forward.region_ids == reverse.region_ids
            and forward.decision_signatures == reverse.decision_signatures
        )
        holds = (
            forward.status is LocationStatus.AMBIGUOUS
            and len(forward.decision_signatures) == 2
            and ordered_equal
            and live == replayed
            and live == (
                forward.status.value,
                forward.region_ids,
                forward.decision_signatures,
            )
        )
        return holds, f"forward={forward!r} reverse={reverse!r} live={live!r} replayed={replayed!r}"


_DIFFERENTIAL_EVALUATORS: dict[str, Callable[[int], tuple[bool, str]]] = {
    "D01": _d01,
    "D02": _d02,
    "D03": _d03,
    "D04": _d04,
    "D05": _d05,
    "D06": _d06,
    "D07": _d07,
    "D08": _d08,
    "D09": _d09,
    "D10": _d10,
}


def _evaluate(invariant_id: str, seed: int) -> tuple[bool, str]:
    try:
        return _DIFFERENTIAL_EVALUATORS[invariant_id](seed)
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"


def _counterexample(invariant_id: str, seed: int, summary: str) -> Wave8Counterexample:
    row = _DIFFERENTIAL_ROWS[invariant_id]
    recipe = (f"differential:{invariant_id}", f"seed:{seed}")
    return Wave8Counterexample.create(
        invariant_id=invariant_id,
        case_id=f"{invariant_id}:{seed}",
        seed=seed,
        generator_version="wave8-differential-v1",
        recipe=recipe,
        minimized_recipe=recipe,
        expected_relation=row.expectation,
        observed_summary=summary,
    )


def run_wave8_differential_invariant(
    invariant_id: str,
    seeds: Iterable[int],
) -> tuple[Wave8Counterexample, ...]:
    invariant = str(invariant_id).strip().upper()
    if invariant not in _DIFFERENTIAL_EVALUATORS:
        raise ValueError(f"unknown Wave-8 differential invariant: {invariant_id}")
    failures: list[Wave8Counterexample] = []
    for seed in sorted({int(value) for value in seeds}):
        holds, summary = _evaluate(invariant, seed)
        if not holds:
            failures.append(_counterexample(invariant, seed, summary))
    return tuple(failures)


def run_wave8_differential(seeds: Iterable[int]) -> tuple[Wave8Counterexample, ...]:
    seed_tuple = tuple(sorted({int(value) for value in seeds}))
    failures = [
        counterexample
        for invariant_id in DIFFERENTIAL_IDS
        for counterexample in run_wave8_differential_invariant(invariant_id, seed_tuple)
    ]
    return tuple(sorted(failures, key=lambda row: (row.invariant_id, row.seed, row.case_id)))
