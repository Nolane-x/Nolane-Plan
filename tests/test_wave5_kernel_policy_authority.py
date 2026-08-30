from __future__ import annotations

import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from nolane_plan import PlanKernel
from nolane_plan.actions import ActionIntent, AuthorityGrant
from nolane_plan.identity import PrincipalAttestation
from nolane_plan.policy_executability import ExecutabilityStatus, PolicyExecutabilityEvaluator
from nolane_plan.policy_information import (
    DecisionEpoch,
    InformationPartitionRevision,
    ObservationFrontierRevision,
)
from nolane_plan.policy_ir import PolicyNodeRevision
from nolane_plan.policy_readiness import (
    ContinuationContract,
    ReactionControllabilityClass,
    TerminalSemantics,
)
from nolane_plan.policy_runtime import install_policy_runtime
from nolane_plan.proof_inputs import DependencyCaptureAssurance, ExternalReadPolicy, ProofInputEnvelopeRevision
from nolane_plan.seals import (
    ArtifactAssurance,
    CompositionStatus,
    DecisionSufficiencyCertificate,
    ProofContextComponent,
    SealCompiler,
    SealStatus,
)
from nolane_plan.selection import CandidateAdmissibility, SelectionEvaluator, SelectionTransaction
from nolane_plan.support import SupportAlternativeSetRevision, SupportClause, SupportNode
from nolane_plan.types import AuthorizationError, RiskClass


class Wave5KernelPolicyAuthorityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.kernel = PlanKernel.create(self.root, "sealed policy authority")
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
        self.bundle = self._install_policy_bundle()

    def tearDown(self):
        self.tmp.cleanup()

    def _install_proof(self):
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

    def _continuation(self):
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

    def _install_policy_bundle(self):
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
            "access_ref": access_ref,
            "action_space": action_space,
            "frontier": frontier,
            "partition": partition,
            "epoch": epoch,
            "node": node,
            "selection": selection,
            "sufficiency": sufficiency,
            "seal": seal,
            "executability": executability,
        }

    def _authorize(self, **changes):
        args = dict(
            action_id="act",
            acting_principal_ref="agent:a",
            grant_ids=("grant",),
            now=50,
            proof_artifact_revision="proof@1",
            active_context={"prod"},
            policy_node_revision=self.bundle["node"].revision_id,
            selection_record_id=self.bundle["selection"].record_id,
            sufficiency_revision=self.bundle["sufficiency"].revision_id,
            seal_revision=self.bundle["seal"].revision_id,
            executability_revision=self.bundle["executability"].revision_id,
        )
        args.update(changes)
        return self.kernel.authorize_sealed_policy(**args)

    def test_policy_runtime_uses_exact_kernel_writer_lock(self):
        self.assertIs(self.kernel.policy_writer_lock, self.kernel._writer_lock)

    def test_valid_sealed_policy_authorization_preserves_identity_proof_and_policy_bindings(self):
        authorization = self._authorize()
        self.assertIn(authorization.id, self.kernel.authorization_identity_bindings)
        self.assertIn(authorization.id, self.kernel.proof_authorization_bindings)
        self.assertIn(authorization.id, self.kernel.policy_authorization_bindings)
        binding = self.kernel.policy_authorization_bindings[authorization.id]
        self.assertEqual(binding["policy_node_revision"], self.bundle["node"].revision_id)
        self.assertEqual(binding["selection_record_id"], self.bundle["selection"].record_id)
        self.assertEqual(binding["seal_revision"], self.bundle["seal"].revision_id)

    def test_access_rebind_stales_epoch_and_selection_before_authorization(self):
        before = len(self.kernel.authorizations)
        self.kernel.bind_principal(
            PrincipalAttestation.create(
                attestation_id="identity-a-2",
                canonical_principal_ref="agent:a",
                source="host-runtime",
                source_subject="subject-a",
                revision=2,
                issued_at=55,
                valid_until=1000,
                assurance=0.95,
                session_ref="session-a-2",
            ),
            allowed_tags={"new-scope"},
            now=55,
        )
        with self.assertRaises(AuthorizationError):
            self._authorize(now=60)
        self.assertEqual(len(self.kernel.authorizations), before)

    def test_policy_node_for_other_principal_is_rejected(self):
        bad = replace(
            self.bundle["node"],
            revision_id="policy-node@other",
            decision_principal_ref="agent:b",
        )
        self.kernel.register_policy_node(bad)
        before = len(self.kernel.authorizations)
        with self.assertRaises(AuthorizationError):
            self._authorize(policy_node_revision=bad.revision_id)
        self.assertEqual(len(self.kernel.authorizations), before)

    def test_stale_selection_generation_blocks_authorization(self):
        before = len(self.kernel.authorizations)
        self.kernel.freshness.bump("plan")
        with self.assertRaises(AuthorizationError):
            self._authorize()
        self.assertEqual(len(self.kernel.authorizations), before)

    def test_stale_seal_blocks_authorization(self):
        stale = replace(
            self.bundle["seal"],
            revision_id="seal@stale",
            status=SealStatus.STALE,
        )
        self.kernel.register_plan_seal(stale)
        before = len(self.kernel.authorizations)
        with self.assertRaises(AuthorizationError):
            self._authorize(seal_revision=stale.revision_id)
        self.assertEqual(len(self.kernel.authorizations), before)

    def test_non_bounded_executability_blocks_authorization(self):
        partial = replace(
            self.bundle["executability"],
            assessment_id="exec@partial",
            revision_id="exec@partial",
            status=ExecutabilityStatus.EXEC_PARTIAL,
        )
        self.kernel.register_policy_executability(partial)
        before = len(self.kernel.authorizations)
        with self.assertRaises(AuthorizationError):
            self._authorize(executability_revision=partial.revision_id)
        self.assertEqual(len(self.kernel.authorizations), before)

    def test_missing_or_mismatched_sufficiency_cannot_be_bypassed(self):
        before = len(self.kernel.authorizations)
        with self.assertRaises(AuthorizationError):
            self._authorize(sufficiency_revision="missing@1")
        self.assertEqual(len(self.kernel.authorizations), before)


if __name__ == "__main__":
    unittest.main()
