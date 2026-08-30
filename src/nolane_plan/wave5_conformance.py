from __future__ import annotations

from typing import Callable

from .policy_certificates import (
    DecisionHistorySignature,
    DecisionRecallCertificate,
    OutcomeSupport,
    PolicyEdgeCertificate,
    PolicyTotalityCertificate,
    RecallLevel,
    SuccessorHandler,
    TotalityMode,
)
from .policy_executability import ExecutabilityStatus, PolicyExecutabilityEvaluator
from .policy_information import (
    DecisionEpoch,
    InformationPartitionRevision,
    NonAnticipativityValidator,
    RevealEvent,
)
from .policy_ir import PolicyCoherenceEvaluator, PolicyNodeRevision
from .policy_readiness import (
    NOT_APPLICABLE,
    ContinuationContract,
    DecisionReactionEnvelope,
    InformationCapabilityRevision,
    PreparednessProfile,
    PreparednessStructure,
    ReactionControllabilityClass,
    TerminalSemantics,
)
from .resources import SharedCommitment
from .seals import (
    ArtifactAssurance,
    CompositionStatus,
    DecisionSufficiencyCertificate,
    ProofContextComponent,
    SealCompiler,
    SealStatus,
)
from .selection import CandidateAdmissibility, SelectionEvaluator, SelectionStatus, SelectionTransaction


def _raises(exc_type, fn: Callable[[], object]) -> bool:
    try:
        fn()
    except exc_type:
        return True
    return False


def _partition_epoch(*, principal: str = "agent:a") -> tuple[InformationPartitionRevision, DecisionEpoch]:
    access = f"access:{principal}@1"
    partition = InformationPartitionRevision.create(
        logical_id="partition",
        revision_id="partition@1",
        mission_revision=1,
        decision_epoch_ref="epoch@1",
        principal_scope_ref=principal,
        information_access_profile_revision=access,
        principal_observation_history_digest="principal-history@1",
        principal_delivery_frontier_refs=(),
        canonical_state_version=1,
        observation_history_digest="history@1",
        observable_predicate_set=(),
        hidden_or_unrevealed_predicate_set=("branch",),
        information_equivalence_classes={"hidden-branch": ("h1", "h2")},
        reveal_event_refs=("reveal@1",),
        observation_model_refs=("obs@1",),
        perfect_recall_basis_ref="recall@1",
        abstraction_certificate_refs=("abstract@1",),
        debt_refs=(),
        validity_regime="runtime@1",
    )
    epoch = DecisionEpoch.create(
        epoch_id="epoch@1",
        plan_snapshot_version=1,
        mission_revision=1,
        decision_principal_ref=principal,
        strategic_location_revision=1,
        information_partition_revision=partition.revision_id,
        principal_information_access_profile_revision=access,
        available_action_space_revision="actions@1",
        active_authority_profile="authority@1",
        active_obligation_basis="obligation@1",
        risk_policy_revision="risk@1",
        observation_frontier_revision="frontier@1",
        temporal_window=(0, 100),
    )
    return partition, epoch


def _reveal(*, principal: str = "agent:a", available_at: int | float | str = 5) -> RevealEvent:
    return RevealEvent.create(
        reveal_event_id="reveal",
        revision_id=f"reveal:{principal}:{available_at}",
        principal_scope_ref=principal,
        revealed_predicates=("branch",),
        observation_model_revision="obs@1",
        availability_time_or_condition=available_at,
        false_positive_semantics="none",
        false_negative_semantics="none",
        observer_effects=(),
        validity_regime="runtime@1",
        refines_information_classes=("hidden-branch",),
    )


def _nonanticipativity(*, reveals=(), decision_time: int | float = 10, actions=None):
    partition, epoch = _partition_epoch()
    action_map = {"h1": "act:a", "h2": "act:b"} if actions is None else actions
    return NonAnticipativityValidator.validate(
        partition,
        epoch,
        action_semantics_by_history=action_map,
        reveal_events=reveals,
        decision_time=decision_time,
    )


def _policy_node() -> PolicyNodeRevision:
    return PolicyNodeRevision.create(
        policy_node_id="node",
        revision_id="node@1",
        mission_revision=1,
        decision_principal_ref="agent:a",
        plan_snapshot_version=1,
        strategic_location_revision=1,
        information_partition_revision="partition@1",
        decision_epoch_ref="epoch@1",
        action_space_revision="actions@1",
        candidate_action_contracts=("act:a",),
        execution_principal_requirement_or_set=("agent:a",),
        selected_action_contract_or_policy_set=("act:a",),
        runtime_guard_refs=("guard@1",),
        observation_frontier_revision="frontier@1",
        successor_policy_mapping=(),
        shared_commitment_refs=(),
        resource_reservation_refs=(),
        obligation_basis_ref="obligation@1",
        risk_policy_revision="risk@1",
        authority_profile_requirement="authority@1",
        route_guarantee_requirement="G2",
        preparedness_level="P3",
        proof_context_ref="proof@1",
        assurance_profile="CHECKED",
        debt_refs=(),
        sealed=True,
    )


def _selection_transaction() -> SelectionTransaction:
    return SelectionTransaction.create(
        transaction_id="selection-tx@1",
        plan_snapshot_version=1,
        mission_revision=1,
        decision_principal_ref="agent:a",
        principal_information_access_profile_revision="access:agent:a@1",
        information_partition_revision="partition@1",
        decision_epoch_ref="epoch@1",
        action_space_revision="actions@1",
        candidate_action_refs=("act:a", "act:b"),
        route_guarantee_requirement="G2",
        measure_mode="scenario",
        risk_policy_revision="risk@1",
        survival_profile_ref="survival@1",
        commitment_pressure_ref="commitment@1",
        debt_policy_ref="debt@1",
        tie_policy="stable-id",
        dependency_generations={"plan": 1},
    )


def _history(ref: str, *, transition: str = "transition@1") -> DecisionHistorySignature:
    return DecisionHistorySignature.create(
        history_ref=ref,
        current_information_class="hidden-branch",
        current_action_semantics="act:a",
        transition_signature=transition,
        observation_capability_signature="observation@1",
        obligation_signature="obligation@1",
        resource_authority_signature="resource-authority@1",
        risk_signature="risk@1",
        action_space_signature="actions@1",
        continuation_signature="continuation@1",
    )


def _reaction(**overrides) -> DecisionReactionEnvelope:
    args = dict(
        reaction_envelope_id="reaction",
        revision_id="reaction@1",
        policy_node_or_reveal_ref="node@1",
        reveal_time_interval=(0, 1),
        ingestion_latency_interval=(1, 2),
        canonical_commit_latency_interval=(1, 2),
        relocation_latency_interval=(1, 2),
        capsule_compile_latency_interval=(1, 2),
        model_or_solver_latency_interval=(1, 2),
        verification_latency_interval=(1, 2),
        authorization_latency_interval=(1, 2),
        dispatch_latency_interval=(1, 2),
        external_effect_start_latency_interval=(1, 2),
        latest_safe_authorization_time=20,
        latest_safe_dispatch_time=22,
        latest_safe_effect_time=24,
        cancellation_or_preemption_window=NOT_APPLICABLE,
        clock_regime_refs=("clock@1",),
        model_adequacy_debt_refs=(),
    )
    args.update(overrides)
    return DecisionReactionEnvelope.create(**args)


def _profile(ref: str, level: int) -> PreparednessProfile:
    axes = {
        "recognition": level,
        "trigger": level,
        "observation": level,
        "recall": level,
        "routing": level,
        "action_contract": level,
        "authority": level,
        "resource": level,
        "temporal_reaction": level,
        "recovery": level,
        "policy_coherence": level,
        "proof_context": level,
        "continuation": level,
    }
    return PreparednessProfile.create(
        preparedness_profile_id=ref,
        revision_id=f"{ref}@1",
        future_region_or_policy_scope="policy@1",
        axes=axes,
        model_adequacy_cap=5,
        debt_refs=(),
        validity_regime="runtime@1",
    )


def _continuation(terminal: TerminalSemantics, *, debt_refs=(), safe_time=120, latency=5) -> ContinuationContract:
    discovery = ("deploy",) if terminal == TerminalSemantics.SAFE_HANDOFF else ("deploy",)
    fallback = "recovery@1" if terminal == TerminalSemantics.SAFE_HANDOFF else "recovery@1"
    return ContinuationContract.create(
        continuation_contract_id=f"continuation:{terminal.value}",
        revision_id=f"continuation:{terminal.value}@1",
        boundary_region_ref="boundary@1",
        mission_revision=1,
        certified_prefix_horizon=100,
        terminal_semantics=terminal,
        required_next_preparedness_profile="prep@next",
        remaining_subgoal_obligation_refs=(),
        refinement_dependencies=("model@1",),
        required_action_space_capability_discovery=discovery,
        estimated_refinement_latency=latency,
        latest_safe_refinement_time=safe_time,
        fallback_if_refinement_misses_boundary=fallback,
        continuation_debt_refs=debt_refs,
        assurance_profile="CHECKED",
    )


def _exec(**overrides):
    continuation = overrides.pop("continuation", _continuation(TerminalSemantics.MISSION_COMPLETE))
    args = dict(
        assessment_id="exec",
        revision_id="exec@1",
        scope_ref="action:act:a",
        mission_revision=1,
        plan_snapshot_version=1,
        policy_revision="node@1",
        information_partition_revision="partition@1",
        action_space_revision="actions@1",
        bound_snapshot_revisions={
            "mission": "1",
            "plan": "1",
            "policy": "node@1",
            "partition": "partition@1",
            "actions": "actions@1",
        },
        nonanticipativity_valid=True,
        recall_level=RecallLevel.RECALL_SUFFICIENT,
        totality_mode=TotalityMode.TOTAL,
        edge_certificates_valid=True,
        shared_resource_commitments_feasible=True,
        information_capability_preserved=True,
        reaction_class=ReactionControllabilityClass.IA2_BOUNDED_GUARANTEED_TIMELY,
        required_reaction_class=ReactionControllabilityClass.IA2_BOUNDED_GUARANTEED_TIMELY,
        preparedness_level=4,
        required_preparedness_level=3,
        composition_status=CompositionStatus.COMPOSABLE,
        route_guarantee_met=True,
        continuation=continuation,
        requested_horizon=100,
        seal_status=SealStatus.SEALED,
        debt_refs=(),
        accepted_debt_refs=(),
    )
    args.update(overrides)
    return PolicyExecutabilityEvaluator.evaluate(**args)


def _seal() -> object:
    sufficiency = DecisionSufficiencyCertificate.create(
        certificate_id="sufficiency",
        revision_id="sufficiency@1",
        scope_ref="action:act:a",
        action_ref="act:a",
        decision_epoch_ref="epoch@1",
        decision_principal_ref="agent:a",
        information_partition_revision="partition@1",
        exact_object_revisions={"policy": "node@1", "proof": "proof@1"},
        included_object_refs=("act:a", "node@1", "proof@1"),
        excluded_known_object_refs=(),
        compiler_profile_ref="closure@1",
        adequacy_limits=("bounded",),
        debt_refs=(),
        complete=True,
        created_sequence=1,
        validity_regime="runtime@1",
    )
    context = ProofContextComponent.create(
        component_ref="context@1",
        assurance=ArtifactAssurance.CHECKED,
        assumptions=(),
        scope="action:act:a",
        guarantee="G2",
        debt_refs=(),
        risk_refs=("risk@1",),
        authority_refs=("authority@1",),
        resource_refs=(),
        external_regime_refs=("runtime@1",),
        validity_horizon=(0, 100),
        constraint_theory="finite-world-set",
        allowed_worlds=("w1",),
    )
    return SealCompiler.issue(
        seal_id="seal",
        revision_id="seal@1",
        plan_root_revision="plan@1",
        mission_revision=1,
        canonical_state_version=1,
        action_closure_refs=("act:a", "node@1", "proof@1"),
        sufficiency=sufficiency,
        proof_contexts=(context,),
        required_assurance=ArtifactAssurance.CHECKED,
        accepted_debt_refs=(),
        compiler_pass_manifest=("P0", "P15", "P16", "P17", "P18", "P19", "P20", "P21", "P22", "P23"),
        invariant_digest="invariants@1",
        created_sequence=1,
        validity_regime="runtime@1",
    )


def _anticipative_hidden_split_blocked() -> bool:
    assessment = _nonanticipativity()
    return not assessment.valid and any(v.code == "NONANTICIPATIVITY_VIOLATION" for v in assessment.violations)


def _other_principal_reveal_cannot_split() -> bool:
    assessment = _nonanticipativity(reveals=(_reveal(principal="agent:b", available_at=1),))
    return not assessment.valid and any(v.code == "PRINCIPAL_REVEAL_UNAVAILABLE" for v in assessment.violations)


def _late_reveal_creates_debt() -> bool:
    assessment = _nonanticipativity(reveals=(_reveal(available_at=20),), decision_time=10)
    return not assessment.valid and "NONANTICIPATIVITY_DEBT:LATE_REVEAL" in assessment.debt_refs


def _grounded_reveal_allows_split() -> bool:
    return _nonanticipativity(reveals=(_reveal(available_at=5),), decision_time=10).valid


def _branch_route_gap_blocks_policy() -> bool:
    na = _nonanticipativity(actions={"h1": "act:a", "h2": "act:a"})
    result = PolicyCoherenceEvaluator.evaluate(
        policy_nodes=(_policy_node(),),
        nonanticipativity=na,
        branch_route_viability={"red": True, "blue": False},
        pre_reveal_commitments={},
        required_policy_scope=("red", "blue"),
    )
    return not result.valid and "POLICY_SCOPE_ROUTE_GAP" in result.blockers


def _pre_reveal_shared_resource_conflict() -> bool:
    na = _nonanticipativity(actions={"h1": "act:a", "h2": "act:a"})
    shared = SharedCommitment("gpu", "agent:a", 0, 10, True)
    result = PolicyCoherenceEvaluator.evaluate(
        policy_nodes=(_policy_node(),),
        nonanticipativity=na,
        branch_route_viability={"red": True, "blue": True},
        pre_reveal_commitments={"red": (shared,), "blue": (shared,)},
        required_policy_scope=("red", "blue"),
    )
    return not result.valid and "SHARED_COMMITMENT_CONFLICT" in result.blockers


def _post_reveal_mutually_exclusive_commitments_allowed() -> bool:
    na = _nonanticipativity(actions={"h1": "act:a", "h2": "act:a"})
    red = SharedCommitment("gpu", "agent:a", 0, 10, True)
    blue = SharedCommitment("gpu", "agent:a", 0, 10, True)
    result = PolicyCoherenceEvaluator.evaluate(
        policy_nodes=(_policy_node(),),
        nonanticipativity=na,
        branch_route_viability={"red": True, "blue": True},
        pre_reveal_commitments={},
        post_reveal_commitments={"red": (red,), "blue": (blue,)},
        mutually_exclusive_branches=(frozenset({"red", "blue"}),),
        required_policy_scope=("red", "blue"),
    )
    return result.valid


def _hard_veto_not_resurrected_by_score() -> bool:
    tx = _selection_transaction()
    record = SelectionEvaluator.select(
        tx,
        admissibility={
            "act:a": CandidateAdmissibility("act:a", True, ()),
            "act:b": CandidateAdmissibility("act:b", False, ("HARD_VETO",)),
        },
        scores={"act:a": 1.0, "act:b": 1000.0},
        pareto_front=("act:a", "act:b"),
    )
    return record.chosen_action_ref == "act:a"


def _selection_generation_drift_stales() -> bool:
    tx = _selection_transaction()
    record = SelectionEvaluator.select(
        tx,
        admissibility={
            "act:a": CandidateAdmissibility("act:a", True, ()),
            "act:b": CandidateAdmissibility("act:b", True, ()),
        },
        scores={"act:a": 2.0, "act:b": 1.0},
        pareto_front=("act:a", "act:b"),
    )
    return record.status_against({"plan": 2}) == SelectionStatus.STALE


def _superseded_selection_never_advisory() -> bool:
    tx = _selection_transaction()
    record = SelectionEvaluator.select(
        tx,
        admissibility={
            "act:a": CandidateAdmissibility("act:a", True, ()),
            "act:b": CandidateAdmissibility("act:b", True, ()),
        },
        scores={"act:a": 2.0, "act:b": 1.0},
        pareto_front=("act:a", "act:b"),
    ).supersede("selection:new")
    return record.status_against({"plan": 1}) == SelectionStatus.SUPERSEDED


def _recursive_recall_alias_detected() -> bool:
    cert = DecisionRecallCertificate.evaluate(
        certificate_id="recall",
        revision_id="recall@1",
        policy_revision="node@1",
        horizon_ref="horizon@1",
        histories=(_history("h1", transition="t1"), _history("h2", transition="t2")),
        alias_classes={"hidden-branch": ("h1", "h2")},
        created_sequence=1,
        validity_regime="runtime@1",
    )
    return cert.level == RecallLevel.RECALL_INSUFFICIENT and bool(cert.counterexamples)


def _missing_recall_history_is_unknown() -> bool:
    cert = DecisionRecallCertificate.evaluate(
        certificate_id="recall",
        revision_id="recall@1",
        policy_revision="node@1",
        horizon_ref="horizon@1",
        histories=(_history("h1"),),
        alias_classes={"hidden-branch": ("h1", "h2")},
        created_sequence=1,
        validity_regime="runtime@1",
    )
    return cert.level == RecallLevel.RECALL_UNKNOWN


def _missing_successor_breaks_totality() -> bool:
    cert = PolicyTotalityCertificate.evaluate(
        certificate_id="totality",
        revision_id="totality@1",
        policy_revision="node@1",
        action_node_revision="node@1",
        outcomes=(OutcomeSupport("timeout", "modeled", True, False),),
        handlers=(),
        solver_status="PROVED",
        created_sequence=1,
        validity_regime="runtime@1",
    )
    return cert.mode == TotalityMode.INCOMPLETE and any(c.code == "MISSING_SUCCESSOR" for c in cert.counterexamples)


def _generic_catchall_cannot_launder_totality() -> bool:
    cert = PolicyTotalityCertificate.evaluate(
        certificate_id="totality",
        revision_id="totality@1",
        policy_revision="node@1",
        action_node_revision="node@1",
        outcomes=(OutcomeSupport("timeout", "modeled", True, False),),
        handlers=(SuccessorHandler("*", "continue", "successor", False),),
        solver_status="PROVED",
        created_sequence=1,
        validity_regime="runtime@1",
    )
    return cert.mode == TotalityMode.INCOMPLETE and any(c.code == "GENERIC_CATCHALL_NOT_TOTALITY_PROOF" for c in cert.counterexamples)


def _policy_edge_stitch_failure() -> bool:
    cert = PolicyEdgeCertificate.evaluate(
        certificate_id="edge",
        revision_id="edge@1",
        parent_policy_node_revision="parent@1",
        child_policy_node_revision="child@1",
        edge_guard_ref="guard@1",
        parent_post_contract={"schema": "v1", "mode": "safe"},
        child_entry_contract={"schema": "v2", "mode": "safe"},
        created_sequence=1,
        validity_regime="runtime@1",
    )
    return not cert.valid and cert.counterexample is not None and "schema" in cert.counterexample.mismatched_fields


def _pairwise_context_global_unsat() -> bool:
    contexts = tuple(
        ProofContextComponent.create(
            component_ref=ref,
            assurance=ArtifactAssurance.CHECKED,
            assumptions=(),
            scope="action:act:a",
            guarantee="G2",
            debt_refs=(),
            risk_refs=(),
            authority_refs=(),
            resource_refs=(),
            external_regime_refs=(),
            validity_horizon=(0, 100),
            constraint_theory="finite-world-set",
            allowed_worlds=worlds,
        )
        for ref, worlds in (("A", ("w1", "w2")), ("B", ("w2", "w3")), ("C", ("w1", "w3")))
    )
    result = SealCompiler.compose_contexts(contexts, accepted_debt_refs=())
    return result.status == CompositionStatus.NONCOMPOSABLE_CONFLICT and bool(result.conflict_component_refs)


def _ia1_not_strong_guarantee() -> bool:
    envelope = _reaction(latest_safe_authorization_time=10, latest_safe_dispatch_time=12, latest_safe_effect_time=14)
    return envelope.controllability_class == ReactionControllabilityClass.IA1_POSSIBLE_TIMELY and not envelope.supports_strong_route_guarantee


def _ia2_worst_case_is_strong() -> bool:
    envelope = _reaction()
    return envelope.controllability_class == ReactionControllabilityClass.IA2_BOUNDED_GUARANTEED_TIMELY and envelope.supports_strong_route_guarantee


def _omitted_latency_stage_rejected() -> bool:
    return _raises(ValueError, lambda: _reaction(verification_latency_interval=None))


def _or_uplift_requires_independence() -> bool:
    high, low = _profile("high", 5), _profile("low", 2)
    conservative = PreparednessProfile.aggregate(
        PreparednessStructure.OR,
        (high, low),
        independence_verified=False,
        coexistence_verified=True,
        required_count=1,
    )
    proven = PreparednessProfile.aggregate(
        PreparednessStructure.OR,
        (high, low),
        independence_verified=True,
        coexistence_verified=True,
        required_count=1,
    )
    return conservative == 2 and proven == 5


def _k_of_n_requires_coexistence() -> bool:
    profiles = (_profile("p5", 5), _profile("p4", 4), _profile("p1", 1))
    conservative = PreparednessProfile.aggregate(
        PreparednessStructure.K_OF_N,
        profiles,
        independence_verified=True,
        coexistence_verified=False,
        required_count=2,
    )
    proven = PreparednessProfile.aggregate(
        PreparednessStructure.K_OF_N,
        profiles,
        independence_verified=True,
        coexistence_verified=True,
        required_count=2,
    )
    return conservative == 1 and proven == 4


def _self_induced_blindness_detected() -> bool:
    capability = InformationCapabilityRevision.create(
        information_capability_id="logs",
        revision_id="logs@1",
        principal_scope_ref="agent:a",
        information_access_profile_revision="access:agent:a@1",
        channel_or_probe_refs=("logs",),
        distinguishable_predicate_classes=("rollback-needed",),
        availability_guard="available",
        validity_regime="runtime@1",
        latency_reaction_envelope_refs=("reaction@1",),
        resource_cost=1,
        permission_authority_requirements=("read-logs",),
        observer_effects=(),
        capacity_rate_limits=(),
        durability="session",
        failure_common_mode_dependencies=(),
        transition_effect_dependencies=("delete-logs",),
        debt_refs=(),
    )
    return (
        not capability.action_preserves_required_information(
            "delete-logs", robust_information_independent_continuation=False
        )
        and capability.action_preserves_required_information(
            "delete-logs", robust_information_independent_continuation=True
        )
    )


def _deferred_continuation_cannot_extend_horizon() -> bool:
    contract = _continuation(TerminalSemantics.DEFERRED_CONTINUATION, debt_refs=("continuation-debt",))
    return contract.supports_executable_horizon(100) and not contract.supports_executable_horizon(101)


def _safe_handoff_requires_lead_time() -> bool:
    contract = _continuation(TerminalSemantics.SAFE_HANDOFF, safe_time=20, latency=10)
    return contract.safe_handoff_ready(now=5, capability_available=True) and not contract.safe_handoff_ready(now=15, capability_available=True)


def _known_policy_hole_blocks_exec_bounded() -> bool:
    result = _exec(totality_mode=TotalityMode.INCOMPLETE)
    return result.status == ExecutabilityStatus.EXEC_NOT_EXECUTABLE and "POLICY_TOTALITY_HOLE" in result.blockers


def _recall_unknown_cannot_be_exec_bounded() -> bool:
    result = _exec(recall_level=RecallLevel.RECALL_UNKNOWN)
    return result.status == ExecutabilityStatus.EXEC_UNKNOWN and "RECALL_UNRESOLVED" in result.unknowns


def _ia1_cannot_meet_ia2_exec_floor() -> bool:
    result = _exec(reaction_class=ReactionControllabilityClass.IA1_POSSIBLE_TIMELY)
    return result.status != ExecutabilityStatus.EXEC_BOUNDED and "REACTION_CLASS_BELOW_REQUIRED" in result.blockers


def _unaccepted_debt_not_silently_bounded() -> bool:
    result = _exec(debt_refs=("debt:open",), accepted_debt_refs=())
    return result.status == ExecutabilityStatus.EXEC_PARTIAL and result.unaccepted_debt_refs == ("debt:open",)


def _seal_invalidation_cannot_revive() -> bool:
    sealed = _seal()
    stale = sealed.invalidate(SealStatus.STALE, revision_id="seal@2")
    return stale.status == SealStatus.STALE and _raises(
        ValueError, lambda: stale.invalidate(SealStatus.SEALED, revision_id="seal@3")
    )


_CASES: tuple[tuple[str, Callable[[], bool]], ...] = (
    ("anticipative_hidden_state_split_blocked", _anticipative_hidden_split_blocked),
    ("other_principal_reveal_cannot_split", _other_principal_reveal_cannot_split),
    ("late_reveal_creates_nonanticipativity_debt", _late_reveal_creates_debt),
    ("grounded_reveal_allows_policy_split", _grounded_reveal_allows_split),
    ("branch_route_gap_blocks_policy_coherence", _branch_route_gap_blocks_policy),
    ("pre_reveal_shared_resource_conflict", _pre_reveal_shared_resource_conflict),
    ("post_reveal_mutually_exclusive_commitments_allowed", _post_reveal_mutually_exclusive_commitments_allowed),
    ("hard_veto_not_resurrected_by_score", _hard_veto_not_resurrected_by_score),
    ("selection_generation_drift_stales", _selection_generation_drift_stales),
    ("superseded_selection_never_advisory", _superseded_selection_never_advisory),
    ("recursive_recall_alias_detected", _recursive_recall_alias_detected),
    ("missing_recall_history_is_unknown", _missing_recall_history_is_unknown),
    ("missing_successor_breaks_totality", _missing_successor_breaks_totality),
    ("generic_catchall_cannot_launder_totality", _generic_catchall_cannot_launder_totality),
    ("policy_edge_stitch_failure", _policy_edge_stitch_failure),
    ("pairwise_context_global_unsat", _pairwise_context_global_unsat),
    ("ia1_not_strong_guarantee", _ia1_not_strong_guarantee),
    ("ia2_worst_case_is_strong", _ia2_worst_case_is_strong),
    ("omitted_latency_stage_rejected", _omitted_latency_stage_rejected),
    ("or_preparedness_uplift_requires_independence", _or_uplift_requires_independence),
    ("k_of_n_preparedness_requires_coexistence", _k_of_n_requires_coexistence),
    ("self_induced_blindness_detected", _self_induced_blindness_detected),
    ("deferred_continuation_cannot_extend_horizon", _deferred_continuation_cannot_extend_horizon),
    ("safe_handoff_requires_refinement_lead_time", _safe_handoff_requires_lead_time),
    ("known_policy_hole_blocks_exec_bounded", _known_policy_hole_blocks_exec_bounded),
    ("recall_unknown_cannot_be_exec_bounded", _recall_unknown_cannot_be_exec_bounded),
    ("ia1_cannot_meet_ia2_exec_floor", _ia1_cannot_meet_ia2_exec_floor),
    ("unaccepted_debt_not_silently_bounded", _unaccepted_debt_not_silently_bounded),
    ("seal_invalidation_cannot_revive", _seal_invalidation_cannot_revive),
)


def run_wave5_conformance() -> dict:
    rows: list[dict[str, object]] = []
    for name, fn in _CASES:
        try:
            passed = bool(fn())
            detail = "defense held" if passed else "unsafe shortcut was not rejected"
        except Exception as exc:
            passed = False
            detail = f"unexpected {type(exc).__name__}: {exc}"
        rows.append({"name": name, "passed": passed, "detail": detail})
    passed = sum(1 for row in rows if row["passed"])
    return {
        "cases": rows,
        "total": len(rows),
        "passed": passed,
        "failed": len(rows) - passed,
    }


def main() -> int:
    result = run_wave5_conformance()
    for row in result["cases"]:
        print(f"{'PASS' if row['passed'] else 'FAIL'} {row['name']}: {row['detail']}")
    print(f"WAVE5_CONFORMANCE={result['passed']}/{result['total']}")
    return 0 if result["passed"] == result["total"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
