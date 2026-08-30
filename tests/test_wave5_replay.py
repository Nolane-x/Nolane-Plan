from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from nolane_plan import PlanKernel
from nolane_plan.actions import ActionIntent
from nolane_plan.hashing import digest
from nolane_plan.policy_certificates import RecallLevel, TotalityMode
from nolane_plan.policy_executability import ExecutabilityStatus, PolicyExecutabilityEvaluator
from nolane_plan.policy_information import DecisionEpoch, InformationPartitionRevision, ObservationFrontierRevision
from nolane_plan.policy_ir import PolicyNodeRevision
from nolane_plan.policy_readiness import ContinuationContract, ReactionControllabilityClass, TerminalSemantics
from nolane_plan.seals import (
    ArtifactAssurance,
    CompositionStatus,
    DecisionSufficiencyCertificate,
    ProofContextComponent,
    SealCompiler,
    SealStatus,
)
from nolane_plan.selection import CandidateAdmissibility, SelectionEvaluator, SelectionStatus, SelectionTransaction
from nolane_plan.types import ReplayError, RiskClass


class Wave5PolicyReplayTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.kernel = PlanKernel.create(self.root, "policy recovery")
        self.kernel.register_principal("agent:a", set())
        self.kernel.propose_action(ActionIntent("act", "deploy", RiskClass.CONSEQUENTIAL))

    def tearDown(self):
        self.tmp.cleanup()

    def _continuation(self, prefix: str) -> ContinuationContract:
        return ContinuationContract.create(
            continuation_contract_id=f"{prefix}-continuation",
            revision_id=f"{prefix}-continuation@1",
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

    def _build_policy_objects(self, prefix: str = "p"):
        principal = "agent:a"
        access = self.kernel.current_policy_access_revision(principal)
        action_space = self.kernel.current_policy_action_space_revision()
        epoch_id = f"{prefix}-epoch@1"
        frontier = ObservationFrontierRevision.create(
            frontier_id=f"{prefix}-frontier",
            revision_id=f"{prefix}-frontier@1",
            principal_scope_ref=principal,
            information_access_profile_revision=access,
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
            logical_id=f"{prefix}-partition",
            revision_id=f"{prefix}-partition@1",
            mission_revision=self.kernel.mission.current.version,
            decision_epoch_ref=epoch_id,
            principal_scope_ref=principal,
            information_access_profile_revision=access,
            principal_observation_history_digest="principal-history@1",
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
            principal_information_access_profile_revision=access,
            available_action_space_revision=action_space,
            active_authority_profile="authority@1",
            active_obligation_basis="obligations@1",
            risk_policy_revision="risk@1",
            observation_frontier_revision=frontier.revision_id,
            temporal_window=(0, 100),
        )
        node = PolicyNodeRevision.create(
            policy_node_id=f"{prefix}-node",
            revision_id=f"{prefix}-node@1",
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
            transaction_id=f"{prefix}-selection-tx@1",
            plan_snapshot_version=self.kernel.plan_snapshot_version,
            mission_revision=self.kernel.mission.current.version,
            decision_principal_ref=principal,
            principal_information_access_profile_revision=access,
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
            certificate_id=f"{prefix}-sufficiency",
            revision_id=f"{prefix}-sufficiency@1",
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
            component_ref=f"{prefix}-context@1",
            assurance=ArtifactAssurance.CHECKED,
            assumptions=(),
            scope="action:act",
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
        seal = SealCompiler.issue(
            seal_id=f"{prefix}-seal",
            revision_id=f"{prefix}-seal@1",
            plan_root_revision="plan-root@1",
            mission_revision=self.kernel.mission.current.version,
            canonical_state_version=self.kernel.canonical_version,
            action_closure_refs=("act", node.revision_id, "proof@1"),
            sufficiency=sufficiency,
            proof_contexts=(context,),
            required_assurance=ArtifactAssurance.CHECKED,
            accepted_debt_refs=(),
            compiler_pass_manifest=("P0", "P15", "P16", "P17", "P18", "P19", "P20", "P21", "P22", "P23"),
            invariant_digest="invariants@1",
            created_sequence=self.kernel.writer_sequence,
            validity_regime="runtime@1",
        )
        continuation = self._continuation(prefix)
        executability = PolicyExecutabilityEvaluator.evaluate(
            assessment_id=f"{prefix}-exec",
            revision_id=f"{prefix}-exec@1",
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
            seal_status=seal.status,
            debt_refs=(),
            accepted_debt_refs=(),
        )
        return frontier, partition, epoch, node, selection, sufficiency, seal, executability

    def _partial_executability(self, base, prefix: str = "partial"):
        manifest = base.closure_manifest
        return PolicyExecutabilityEvaluator.evaluate(
            assessment_id=f"{prefix}-exec",
            revision_id=f"{prefix}-exec@1",
            scope_ref=base.scope_ref,
            mission_revision=manifest.mission_revision,
            plan_snapshot_version=manifest.plan_snapshot_version,
            policy_revision=manifest.policy_revision,
            information_partition_revision=manifest.information_partition_revision,
            action_space_revision=manifest.action_space_revision,
            bound_snapshot_revisions=dict(manifest.bound_snapshot_revisions),
            nonanticipativity_valid=manifest.nonanticipativity_valid,
            recall_level=manifest.recall_level,
            totality_mode=manifest.totality_mode,
            edge_certificates_valid=manifest.edge_certificates_valid,
            shared_resource_commitments_feasible=manifest.shared_resource_commitments_feasible,
            information_capability_preserved=manifest.information_capability_preserved,
            reaction_class=manifest.reaction_class,
            required_reaction_class=manifest.required_reaction_class,
            preparedness_level=manifest.preparedness_level,
            required_preparedness_level=manifest.required_preparedness_level,
            composition_status=manifest.composition_status,
            route_guarantee_met=manifest.route_guarantee_met,
            continuation=self._continuation(prefix),
            requested_horizon=manifest.requested_horizon,
            seal_status=manifest.seal_status,
            debt_refs=("debt:open",),
            accepted_debt_refs=(),
        )

    def _register_policy_objects(self, objects):
        frontier, partition, epoch, node, selection, sufficiency, seal, executability = objects
        self.kernel.register_policy_frontier(frontier)
        self.kernel.register_information_partition(partition)
        self.kernel.register_decision_epoch(epoch)
        self.kernel.register_policy_node(node)
        self.kernel.register_selection_record(selection)
        self.kernel.register_decision_sufficiency(sufficiency)
        self.kernel.register_plan_seal(seal)
        self.kernel.register_policy_executability(executability)
        return objects

    def test_v5_snapshot_round_trip_preserves_policy_registry_and_exact_digests(self):
        objects = self._register_policy_objects(self._build_policy_objects())
        state = self.kernel.save_snapshot()
        self.assertEqual(state["snapshot_schema"], "nolane-plan-runtime-snapshot-v5")

        reopened = PlanKernel.open(self.root)
        frontier, partition, epoch, node, selection, sufficiency, seal, executability = objects
        self.assertEqual(reopened.policy_frontiers[frontier.revision_id].canonical_digest, frontier.canonical_digest)
        self.assertEqual(reopened.policy_partitions[partition.revision_id].canonical_digest, partition.canonical_digest)
        self.assertEqual(reopened.policy_epochs[epoch.epoch_id].canonical_digest, epoch.canonical_digest)
        self.assertEqual(reopened.policy_nodes[node.revision_id].canonical_digest, node.canonical_digest)
        self.assertEqual(reopened.policy_selections[selection.record_id].canonical_digest, selection.canonical_digest)
        self.assertEqual(reopened.policy_sufficiency[sufficiency.revision_id].canonical_digest, sufficiency.canonical_digest)
        self.assertEqual(reopened.policy_seals[seal.revision_id].canonical_digest, seal.canonical_digest)
        self.assertEqual(reopened.policy_executability[executability.revision_id].canonical_digest, executability.canonical_digest)

    def test_stale_selection_before_snapshot_does_not_resurrect(self):
        objects = self._register_policy_objects(self._build_policy_objects())
        selection = objects[4]
        self.kernel.freshness.bump("plan")
        self.assertEqual(self.kernel._current_selection_status(selection), SelectionStatus.STALE)
        self.kernel.save_snapshot()

        reopened = PlanKernel.open(self.root)
        restored = reopened.policy_selections[selection.record_id]
        self.assertEqual(reopened._current_selection_status(restored), SelectionStatus.STALE)

    def test_stale_seal_and_partial_executability_do_not_promote_after_restart(self):
        objects = self._register_policy_objects(self._build_policy_objects())
        seal = objects[6].invalidate(SealStatus.STALE, revision_id="p-seal@stale")
        partial = self._partial_executability(objects[7])
        self.assertEqual(partial.status, ExecutabilityStatus.EXEC_PARTIAL)
        self.kernel.register_plan_seal(seal)
        self.kernel.register_policy_executability(partial)
        self.kernel.save_snapshot()

        reopened = PlanKernel.open(self.root)
        self.assertEqual(reopened.policy_seals[seal.revision_id].status, SealStatus.STALE)
        self.assertEqual(reopened.policy_executability[partial.revision_id].status, ExecutabilityStatus.EXEC_PARTIAL)

    def test_tampered_internal_policy_digest_fails_closed_even_with_valid_outer_snapshot_digest(self):
        self._register_policy_objects(self._build_policy_objects())
        self.kernel.save_snapshot()
        path = self.root / "snapshot.json"
        doc = json.loads(path.read_text(encoding="utf-8"))
        doc["state"]["policy"]["nodes"][0]["decision_principal_ref"] = "agent:tampered"
        doc["digest"] = digest(doc["state"])
        path.write_text(json.dumps(doc, sort_keys=True), encoding="utf-8")

        with self.assertRaises(ReplayError):
            PlanKernel.open(self.root)

    def test_post_snapshot_policy_registration_suffix_replays_exactly(self):
        self.kernel.save_snapshot()
        objects = self._register_policy_objects(self._build_policy_objects("suffix"))
        reopened = PlanKernel.open(self.root)
        node = objects[3]
        executability = objects[7]
        self.assertEqual(reopened.policy_nodes[node.revision_id].canonical_digest, node.canonical_digest)
        self.assertEqual(reopened.policy_executability[executability.revision_id].canonical_digest, executability.canonical_digest)

    def test_unknown_correctness_significant_policy_suffix_event_fails_closed(self):
        self.kernel.save_snapshot()
        self.kernel._record("policy.unknown_correctness_mutation", {"revision": "x@2"})
        with self.assertRaises(ReplayError):
            PlanKernel.open(self.root)

    def test_v4_snapshot_migrates_with_empty_policy_state_instead_of_inventing_policy(self):
        self.kernel.save_snapshot()
        path = self.root / "snapshot.json"
        doc = json.loads(path.read_text(encoding="utf-8"))
        doc["state"]["snapshot_schema"] = "nolane-plan-runtime-snapshot-v4"
        doc["state"].pop("policy", None)
        doc["digest"] = digest(doc["state"])
        path.write_text(json.dumps(doc, sort_keys=True), encoding="utf-8")

        reopened = PlanKernel.open(self.root)
        self.assertEqual(reopened.policy_nodes, {})
        self.assertEqual(reopened.policy_seals, {})
        self.assertEqual(reopened.policy_executability, {})


if __name__ == "__main__":
    unittest.main()
