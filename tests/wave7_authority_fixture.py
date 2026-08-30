from __future__ import annotations

from pathlib import Path

from nolane_plan import PlanKernel
from nolane_plan.actions import ActionIntent, AuthorityGrant
from nolane_plan.control_plane import ControlPlaneResourceRevision, ReactionJobContract, ReactionResourceDemand
from nolane_plan.identity import PrincipalAttestation
from nolane_plan.migration import FieldMigrationDisposition, MigrationDisposition, MigrationManifest
from nolane_plan.policy_certificates import OutcomeSupport, PolicyTotalityCertificate, SuccessorHandler
from nolane_plan.policy_coverage import ExecutablePolicyCoverageAssessment
from nolane_plan.policy_executability import PolicyExecutabilityEvaluator
from nolane_plan.policy_information import DecisionEpoch, InformationPartitionRevision, ObservationFrontierRevision
from nolane_plan.policy_ir import PolicyNodeRevision
from nolane_plan.policy_readiness import ContinuationContract, ReactionControllabilityClass, TerminalSemantics
from nolane_plan.proof_inputs import DependencyCaptureAssurance, ExternalReadPolicy, ProofInputEnvelopeRevision
from nolane_plan.schedulability import ReactionSchedulabilityEvaluator
from nolane_plan.seals import ArtifactAssurance, CompositionStatus, DecisionSufficiencyCertificate, ProofContextComponent, SealCompiler
from nolane_plan.selection import CandidateAdmissibility, SelectionEvaluator, SelectionTransaction
from nolane_plan.support import SupportAlternativeSetRevision, SupportClause, SupportNode
from nolane_plan.types import RiskClass


class CountingAdapter:
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


class AuthorityFixture:
    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.kernel = PlanKernel.create(self.root, "wave7 exact authority lineage", ("done",), ("preserve rollback",))
        self.kernel.bind_principal(
            PrincipalAttestation.create(
                attestation_id="identity-a",
                canonical_principal_ref="agent:a",
                source="host-runtime",
                source_subject="subject-a",
                revision=1,
                issued_at=1,
                valid_until=1000,
                assurance=0.95,
                session_ref="session-a",
            ),
            allowed_tags=set(),
            now=10,
        )
        self.kernel.propose_action(ActionIntent("act", "deploy", RiskClass.CONSEQUENTIAL))
        self.kernel.add_grant(AuthorityGrant("grant", "agent:a", frozenset({"deploy"})))
        self._install_proof()
        self.policy = self._install_policy_bundle()
        self.wave6 = self._install_wave6_bundle()

    def _install_proof(self) -> None:
        self.kernel.register_semantic_source(
            "proof-source",
            revision_id="proof-source@1",
            value={"safe": True},
            dependency_domains=("source:proof-source",),
        )
        self.kernel.register_proof_profile_refs("semantic@1", "python@3.13")
        env = ProofInputEnvelopeRevision.create(
            input_envelope_id="proof-env",
            revision_id="proof-env@1",
            procedure_kind="verification",
            procedure_capability_revision="checker@1",
            explicit_input_revision_refs=("proof-source@1",),
            semantic_profile_refs=("semantic@1",),
            execution_environment_profile_refs=("python@3.13",),
            external_read_policy=ExternalReadPolicy.DENY_UNDECLARED,
            created_from_decision_cut=self.kernel.current_cut().id,
            capture_assurance=DependencyCaptureAssurance.FULL_ENVELOPE_ENFORCED,
        )
        self.kernel.register_proof_input(env)
        self.kernel.capture_proof_manifest(
            manifest_id="proof-manifest",
            revision_id="proof-manifest@1",
            artifact_revision="proof@1",
            proof_obligation_revision="proof-obligation@1",
            producer_capability_revision="checker@1",
            input_envelope_revision=env.revision_id,
            positive_revision_dependencies={"proof-source": "proof-source@1"},
            dependency_domains=("source:proof-source",),
            semantic_profile_dependencies=("semantic@1",),
            execution_semantic_profile_dependencies=("python@3.13",),
        )
        self.kernel.register_support_node(
            SupportNode(
                ref="evidence@1",
                current=True,
                direct_grounding_roots=frozenset({"root:host"}),
                support_refs=(),
                scope="mission",
                assumption_basis=frozenset({"assumption@1"}),
                proof_kind="verification",
                validity_regime="runtime@1",
                context_tags=frozenset({"prod"}),
            )
        )
        self.kernel.register_support_set(
            SupportAlternativeSetRevision.create(
                support_set_id="proof-support",
                revision_id="proof-support@1",
                subject_artifact_revision="proof@1",
                clauses=(
                    SupportClause(
                        "proof-clause@1",
                        ("evidence@1",),
                        "mission",
                        frozenset({"assumption@1"}),
                        "verification",
                        frozenset(),
                        "runtime@1",
                        frozenset({"prod"}),
                        1,
                    ),
                ),
                scope="mission",
                assumption_context_rules=("prod",),
                proof_kind="verification",
                grounding_policy="accepted-roots-only",
                support_evaluation_profile="bounded-dnf@1",
                created_sequence=self.kernel.writer_sequence,
            )
        )

    def _continuation(self) -> ContinuationContract:
        return ContinuationContract.create(
            continuation_contract_id="continuation@1",
            revision_id="continuation@1",
            boundary_region_ref="boundary@1",
            mission_revision=self.kernel.mission.current.version,
            certified_prefix_horizon=100,
            terminal_semantics=TerminalSemantics.MISSION_COMPLETE,
            required_next_preparedness_profile="prep@next",
            remaining_subgoal_obligation_refs=(),
            refinement_dependencies=("world-model@1",),
            required_action_space_capability_discovery=("deploy",),
            estimated_refinement_latency=5,
            latest_safe_refinement_time=120,
            fallback_if_refinement_misses_boundary="recovery@1",
            continuation_debt_refs=(),
            assurance_profile="CHECKED",
        )

    def _install_policy_bundle(self) -> dict[str, object]:
        principal = "agent:a"
        access_ref = self.kernel.current_policy_access_revision(principal)
        action_space = self.kernel.current_policy_action_space_revision()
        epoch_id = "epoch@1"
        frontier = ObservationFrontierRevision.create(
            frontier_id="frontier",
            revision_id="frontier@1",
            principal_scope_ref=principal,
            information_access_profile_revision=access_ref,
            currently_available_observations=("signal",),
            pending_observations=(),
            reveal_event_refs=(),
            latest_safe_observation_times={},
            observation_costs={},
            observation_side_effects=(),
            observation_dependencies=("obs-model@1",),
            unobservable_predicates=(),
            conditionally_observable_predicates=(),
            frontier_debt_refs=(),
            validity_regime="runtime@1",
        )
        partition = InformationPartitionRevision.create(
            logical_id="partition",
            revision_id="partition@1",
            mission_revision=self.kernel.mission.current.version,
            decision_epoch_ref=epoch_id,
            principal_scope_ref=principal,
            information_access_profile_revision=access_ref,
            principal_observation_history_digest="obs-history@1",
            principal_delivery_frontier_refs=(),
            canonical_state_version=self.kernel.canonical_version,
            observation_history_digest="history@1",
            observable_predicate_set=("signal",),
            hidden_or_unrevealed_predicate_set=(),
            information_equivalence_classes={"visible": ("h1",)},
            reveal_event_refs=(),
            observation_model_refs=("obs-model@1",),
            perfect_recall_basis_ref="recall@1",
            abstraction_certificate_refs=("abstraction@1",),
            debt_refs=(),
            validity_regime="runtime@1",
        )
        epoch = DecisionEpoch.create(
            epoch_id=epoch_id,
            plan_snapshot_version=self.kernel.plan_snapshot_version,
            mission_revision=self.kernel.mission.current.version,
            decision_principal_ref=principal,
            strategic_location_revision=self.kernel._location_revision,
            information_partition_revision=partition.revision_id,
            principal_information_access_profile_revision=access_ref,
            available_action_space_revision=action_space,
            active_authority_profile="authority@1",
            active_obligation_basis="obligations@1",
            risk_policy_revision="risk@1",
            observation_frontier_revision=frontier.revision_id,
            temporal_window=(20, 100),
        )
        node = PolicyNodeRevision.create(
            policy_node_id="policy-node",
            revision_id="policy-node@1",
            mission_revision=self.kernel.mission.current.version,
            decision_principal_ref=principal,
            plan_snapshot_version=self.kernel.plan_snapshot_version,
            strategic_location_revision=self.kernel._location_revision,
            information_partition_revision=partition.revision_id,
            decision_epoch_ref=epoch.epoch_id,
            action_space_revision=action_space,
            candidate_action_contracts=("act",),
            execution_principal_requirement_or_set=(principal,),
            selected_action_contract_or_policy_set=("act",),
            runtime_guard_refs=("guard@1",),
            observation_frontier_revision=frontier.revision_id,
            successor_policy_mapping=(),
            shared_commitment_refs=(),
            resource_reservation_refs=(),
            obligation_basis_ref="obligations@1",
            risk_policy_revision="risk@1",
            authority_profile_requirement="authority@1",
            route_guarantee_requirement="G2",
            preparedness_level="P3",
            proof_context_ref="proof-context@1",
            assurance_profile="CHECKED",
            debt_refs=(),
            sealed=True,
        )
        tx = SelectionTransaction.create(
            transaction_id="selection-tx@1",
            plan_snapshot_version=self.kernel.plan_snapshot_version,
            mission_revision=self.kernel.mission.current.version,
            decision_principal_ref=principal,
            principal_information_access_profile_revision=access_ref,
            information_partition_revision=partition.revision_id,
            decision_epoch_ref=epoch.epoch_id,
            action_space_revision=action_space,
            candidate_action_refs=("act",),
            route_guarantee_requirement="G2",
            measure_mode="scenario",
            risk_policy_revision="risk@1",
            survival_profile_ref="survival@1",
            commitment_pressure_ref="commitment@1",
            debt_policy_ref="debt-policy@1",
            tie_policy="stable-id",
            dependency_generations={"plan": self.kernel.freshness.generation("plan")},
        )
        selection = SelectionEvaluator.select(
            tx,
            admissibility={"act": CandidateAdmissibility("act", True, ())},
            scores={"act": 1.0},
            pareto_front=("act",),
        )
        sufficiency = DecisionSufficiencyCertificate.create(
            certificate_id="sufficiency@1",
            revision_id="sufficiency@1",
            scope_ref="action:act",
            action_ref="act",
            decision_epoch_ref=epoch.epoch_id,
            decision_principal_ref=principal,
            information_partition_revision=partition.revision_id,
            exact_object_revisions={"policy": node.revision_id, "proof": "proof@1"},
            included_object_refs=("act", node.revision_id, "proof@1"),
            excluded_known_object_refs=(),
            compiler_profile_ref="closure@1",
            adequacy_limits=("bounded-reference-world",),
            debt_refs=(),
            complete=True,
            created_sequence=self.kernel.writer_sequence,
            validity_regime="runtime@1",
        )
        context = ProofContextComponent.create(
            component_ref="policy-proof-context@1",
            assurance=ArtifactAssurance.CHECKED,
            assumptions=(),
            scope="action:act",
            guarantee="G2",
            debt_refs=(),
            risk_refs=("risk@1",),
            authority_refs=("authority@1",),
            resource_refs=(),
            external_regime_refs=("runtime@1",),
            validity_horizon=(20, 100),
            constraint_theory="finite-world-set",
            allowed_worlds=("w1",),
        )
        seal = SealCompiler.issue(
            seal_id="seal@1",
            revision_id="seal@1",
            plan_root_revision="plan-root@1",
            mission_revision=self.kernel.mission.current.version,
            canonical_state_version=self.kernel.canonical_version,
            action_closure_refs=("act", node.revision_id, "proof@1"),
            sufficiency=sufficiency,
            proof_contexts=(context,),
            required_assurance=ArtifactAssurance.CHECKED,
            accepted_debt_refs=(),
            compiler_pass_manifest=("P0", "P1", "P2", "P15", "P16", "P17", "P18", "P19", "P20", "P21", "P22", "P23"),
            invariant_digest="invariants@1",
            created_sequence=self.kernel.writer_sequence,
            validity_regime="runtime@1",
        )
        executability = PolicyExecutabilityEvaluator.evaluate(
            assessment_id="exec@1",
            revision_id="exec@1",
            scope_ref="action:act",
            mission_revision=self.kernel.mission.current.version,
            plan_snapshot_version=self.kernel.plan_snapshot_version,
            policy_revision=node.revision_id,
            information_partition_revision=partition.revision_id,
            action_space_revision=action_space,
            bound_snapshot_revisions={
                "mission": str(self.kernel.mission.current.version),
                "plan": str(self.kernel.plan_snapshot_version),
                "policy": node.revision_id,
                "partition": partition.revision_id,
                "actions": action_space,
            },
            nonanticipativity_valid=True,
            recall_level=__import__("nolane_plan.policy_certificates", fromlist=["RecallLevel"]).RecallLevel.RECALL_SUFFICIENT,
            totality_mode=__import__("nolane_plan.policy_certificates", fromlist=["TotalityMode"]).TotalityMode.TOTAL,
            edge_certificates_valid=True,
            shared_resource_commitments_feasible=True,
            information_capability_preserved=True,
            reaction_class=ReactionControllabilityClass.IA2_BOUNDED_GUARANTEED_TIMELY,
            required_reaction_class=ReactionControllabilityClass.IA2_BOUNDED_GUARANTEED_TIMELY,
            preparedness_level=4,
            required_preparedness_level=3,
            composition_status=CompositionStatus.COMPOSABLE,
            route_guarantee_met=True,
            continuation=self._continuation(),
            requested_horizon=100,
            seal_status=seal.status,
            debt_refs=(),
            accepted_debt_refs=(),
        )
        self.kernel.register_policy_frontier(frontier)
        self.kernel.register_information_partition(partition)
        self.kernel.register_decision_epoch(epoch)
        self.kernel.register_policy_node(node)
        self.kernel.register_selection_record(selection)
        self.kernel.register_decision_sufficiency(sufficiency)
        self.kernel.register_plan_seal(seal)
        self.kernel.register_policy_executability(executability)
        return {
            "frontier": frontier,
            "partition": partition,
            "epoch": epoch,
            "node": node,
            "selection": selection,
            "sufficiency": sufficiency,
            "seal": seal,
            "executability": executability,
        }

    def _install_wave6_bundle(self) -> dict[str, object]:
        resource = ControlPlaneResourceRevision.create(
            resource_id="verifier",
            revision_id="verifier@1",
            resource_kind="CONCURRENCY",
            capacity_units=2.0,
            concurrency_limit=2,
            service_rate_per_second=10.0,
            rate_window_seconds=1.0,
            availability_interval=(0.0, 100.0),
            priority_policy_ref="priority@1",
            reservation_policy_ref="reservation@1",
            regime_ref="runtime@1",
            assurance_profile="bounded-worst-case",
            opaque_dimensions=(),
            conservative_capacity_bound=None,
            validity_regime="runtime@1",
        )
        demand = ReactionResourceDemand.create(
            resource_ref="verifier",
            required_service=1.0,
            required_concurrency_units=1,
            release_offset_interval=(0.0, 0.0),
            demand_window=(0.0, 1.0),
            mandatory=True,
        )
        job = ReactionJobContract.create(
            reaction_job_id="reaction-a",
            revision_id="reaction-a@1",
            policy_scope="action:act",
            mission_revision=str(self.kernel.mission.current.version),
            information_partition_revision=self.policy["partition"].revision_id,
            reaction_envelope_ref="envelope:reaction-a",
            release_window=(0.0, 0.0),
            deadline=1.0,
            resource_demands=(demand,),
            coexistence_tags=("same-window",),
            correlation_refs=(),
            priority_class="critical",
            reservation_refs=(),
            risk_class="consequential",
            model_adequacy_debt_refs=(),
            validity_regime="runtime@1",
        )
        sched = ReactionSchedulabilityEvaluator.evaluate(
            certificate_id="sched",
            revision_id="sched@1",
            policy_scope="action:act",
            mission_revision=str(self.kernel.mission.current.version),
            information_partition_revision=self.policy["partition"].revision_id,
            jobs=(job,),
            resources=(resource,),
            mutually_exclusive_pairs=(),
            coexistence_known=True,
            resource_reservation_refs=(),
            scheduling_model_id="bounded-window",
            scheduling_model_version="1",
            analysis_mode="EXACT_BOUNDED",
            worst_case_or_interval_assumptions=("bounded-service",),
            proof_or_solver_ref="evaluator@1",
            assurance_profile="bounded-worst-case",
            model_adequacy_debt_refs=(),
            validity_regime="runtime@1",
        )
        totality = PolicyTotalityCertificate.evaluate(
            certificate_id="totality",
            revision_id="totality@1",
            policy_revision=self.policy["node"].revision_id,
            action_node_revision=self.policy["node"].revision_id,
            outcomes=(OutcomeSupport("ok", "modeled", True, False),),
            handlers=(SuccessorHandler("ok", "done", "successor", False),),
            solver_status="PROVED",
            created_sequence=self.kernel.writer_sequence,
            validity_regime="runtime@1",
        )
        coverage = ExecutablePolicyCoverageAssessment.create(
            assessment_id="coverage",
            revision_id="coverage@1",
            policy_scope="action:act",
            policy_totality_certificate=totality,
            transition_observation_model_adequacy="STRONG",
            residual_open_world_status="CLOSED",
            residual_debt_refs=(),
            closed_domain_proof_ref="closed-domain@1",
            created_sequence=self.kernel.writer_sequence,
            validity_regime="runtime@1",
        )
        self.kernel.register_control_plane_resource(resource)
        self.kernel.register_reaction_job(job)
        self.kernel.register_schedulability_certificate(sched)
        self.kernel.register_policy_coverage_assessment(coverage)
        return {"resource": resource, "job": job, "sched": sched, "coverage": coverage}

    def authorize(self):
        return self.kernel.authorize_schedulable_policy(
            action_id="act",
            acting_principal_ref="agent:a",
            grant_ids=("grant",),
            now=50,
            proof_artifact_revision="proof@1",
            active_context={"prod"},
            policy_node_revision=self.policy["node"].revision_id,
            selection_record_id=self.policy["selection"].record_id,
            sufficiency_revision=self.policy["sufficiency"].revision_id,
            seal_revision=self.policy["seal"].revision_id,
            executability_revision=self.policy["executability"].revision_id,
            schedulability_revision=self.wave6["sched"].revision_id,
            coverage_revision=self.wave6["coverage"].revision_id,
        )

    def migration_manifest(self) -> MigrationManifest:
        return MigrationManifest.create(
            manifest_id="migration:v7-to-v7b-authority",
            source_schema_revision="schema:nolane-plan:v7",
            target_schema_revision="schema:nolane-plan:v7b",
            target_schema_semantic_digest="schema-v7b-semantic",
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
            revoked_certificate_refs=("seal:old",),
            revoked_authorization_refs=(),
            new_debt_refs=("debt:migration-review",),
            replay_fixture_digests=("fixture:authority",),
            rollback_procedure_ref="rollback:restore-v7-root",
            backup_ref="backup:v7",
            unsupported_legacy_cases=(),
            external_effect_history_refs=(),
            provenance_refs=("migration:wave7-authority-test",),
        )
