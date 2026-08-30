from __future__ import annotations

import unittest

from nolane_plan.policy_readiness import (
    DecisionReactionEnvelope,
    InformationCapabilityRevision,
    PreparednessProfile,
    PreparednessStructure,
    ReactionControllabilityClass,
    TerminalSemantics,
    ContinuationContract,
)


class Wave5PolicyReadinessTests(unittest.TestCase):
    def _reaction(self, *, slow_model=(1, 8), slow_authorize=(1, 4)) -> DecisionReactionEnvelope:
        return DecisionReactionEnvelope.create(
            reaction_envelope_id="reaction@1",
            revision_id="reaction@1",
            policy_node_or_reveal_ref="reveal@1",
            reveal_time_interval=(10, 12),
            ingestion_latency_interval=(1, 2),
            canonical_commit_latency_interval=(1, 2),
            relocation_latency_interval=(0, 1),
            capsule_compile_latency_interval=(1, 2),
            model_or_solver_latency_interval=slow_model,
            verification_latency_interval=(1, 2),
            authorization_latency_interval=slow_authorize,
            dispatch_latency_interval=(1, 2),
            external_effect_start_latency_interval=(0, 2),
            latest_safe_authorization_time=25,
            latest_safe_dispatch_time=28,
            latest_safe_effect_time=30,
            cancellation_or_preemption_window=(20, 29),
            clock_regime_refs=("clock@1", "latency-regime@1"),
            model_adequacy_debt_refs=(),
        )

    def test_possible_timing_is_ia1_not_strong_guarantee(self):
        envelope = self._reaction(slow_model=(1, 8), slow_authorize=(1, 4))
        self.assertEqual(envelope.controllability_class, ReactionControllabilityClass.IA1_POSSIBLE_TIMELY)
        self.assertFalse(envelope.supports_strong_route_guarantee)

    def test_worst_case_pipeline_inside_window_is_ia2(self):
        envelope = self._reaction(slow_model=(1, 2), slow_authorize=(1, 1))
        self.assertEqual(envelope.controllability_class, ReactionControllabilityClass.IA2_BOUNDED_GUARANTEED_TIMELY)
        self.assertTrue(envelope.supports_strong_route_guarantee)
        self.assertGreaterEqual(envelope.worst_case_slack, 0)

    def test_omitted_stage_must_be_explicit_not_applicable(self):
        with self.assertRaises(ValueError):
            DecisionReactionEnvelope.create(
                reaction_envelope_id="bad",
                revision_id="bad@1",
                policy_node_or_reveal_ref="reveal@1",
                reveal_time_interval=(10, 10),
                ingestion_latency_interval=None,
                canonical_commit_latency_interval=(0, 0),
                relocation_latency_interval=(0, 0),
                capsule_compile_latency_interval=(0, 0),
                model_or_solver_latency_interval=(0, 0),
                verification_latency_interval=(0, 0),
                authorization_latency_interval=(0, 0),
                dispatch_latency_interval=(0, 0),
                external_effect_start_latency_interval="NOT_APPLICABLE",
                latest_safe_authorization_time=20,
                latest_safe_dispatch_time=20,
                latest_safe_effect_time=20,
                cancellation_or_preemption_window=(10, 20),
                clock_regime_refs=("clock@1",),
                model_adequacy_debt_refs=(),
            )

    def _profile(self, ref: str, level: int, **axis_changes) -> PreparednessProfile:
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
        axes.update(axis_changes)
        return PreparednessProfile.create(
            preparedness_profile_id=ref,
            revision_id=f"{ref}@1",
            future_region_or_policy_scope="policy@1",
            axes=axes,
            model_adequacy_cap=5,
            debt_refs=(),
            validity_regime="runtime@1",
        )

    def test_single_sequential_route_p_level_is_weakest_required_axis(self):
        profile = self._profile("p", 5, trigger=2, recovery=4)
        self.assertEqual(profile.derived_p_level, 2)
        self.assertEqual(profile.bottleneck_axes, ("trigger",))

    def test_or_aggregation_uses_best_route_only_with_independence_and_activation_proof(self):
        strong = self._profile("strong", 5)
        weak = self._profile("weak", 2)
        good = PreparednessProfile.aggregate(
            PreparednessStructure.OR,
            (strong, weak),
            independence_verified=True,
            coexistence_verified=True,
            required_count=1,
        )
        conservative = PreparednessProfile.aggregate(
            PreparednessStructure.OR,
            (strong, weak),
            independence_verified=False,
            coexistence_verified=True,
            required_count=1,
        )
        self.assertEqual(good, 5)
        self.assertEqual(conservative, 2)

    def test_k_of_n_requires_coexistence_before_kth_order_uplift(self):
        routes = (self._profile("a", 5), self._profile("b", 4), self._profile("c", 1))
        verified = PreparednessProfile.aggregate(
            PreparednessStructure.K_OF_N,
            routes,
            independence_verified=True,
            coexistence_verified=True,
            required_count=2,
        )
        unverified = PreparednessProfile.aggregate(
            PreparednessStructure.K_OF_N,
            routes,
            independence_verified=True,
            coexistence_verified=False,
            required_count=2,
        )
        self.assertEqual(verified, 4)
        self.assertEqual(unverified, 1)

    def test_refinement_can_downgrade_preparedness(self):
        high = self._profile("p", 5)
        low = high.revise_axis("observation", 2, revision_id="p@2", debt_ref="debt:observation-drift")
        self.assertEqual(high.derived_p_level, 5)
        self.assertEqual(low.derived_p_level, 2)
        self.assertIn("debt:observation-drift", low.debt_refs)

    def test_action_destroying_unique_future_information_channel_is_damaging_without_alternative(self):
        capability = InformationCapabilityRevision.create(
            information_capability_id="diagnostic-channel",
            revision_id="diagnostic-channel@1",
            principal_scope_ref="agent:a",
            information_access_profile_revision="access:a@1",
            channel_or_probe_refs=("logs",),
            distinguishable_predicate_classes=("migration-success-vs-partial",),
            availability_guard="before-log-delete",
            validity_regime="runtime@1",
            latency_reaction_envelope_refs=("reaction@1",),
            resource_cost=1.0,
            permission_authority_requirements=("read-logs",),
            observer_effects=(),
            capacity_rate_limits=("1/s",),
            durability="until-deleted",
            failure_common_mode_dependencies=("log-store",),
            transition_effect_dependencies=("action:delete-logs",),
            debt_refs=(),
        )
        self.assertFalse(
            capability.action_preserves_required_information(
                "action:delete-logs", robust_information_independent_continuation=False
            )
        )
        self.assertTrue(
            capability.action_preserves_required_information(
                "action:delete-logs", robust_information_independent_continuation=True
            )
        )

    def _continuation(self, semantics: TerminalSemantics, **changes) -> ContinuationContract:
        fields = dict(
            continuation_contract_id="continuation@1",
            revision_id=f"continuation@{semantics.value}",
            boundary_region_ref="basin@1",
            mission_revision=1,
            certified_prefix_horizon=100,
            terminal_semantics=semantics,
            required_next_preparedness_profile="prep-next@1",
            remaining_subgoal_obligation_refs=("obligation@later",),
            refinement_dependencies=("world-model@1",),
            required_action_space_capability_discovery=("deploy-recovery",),
            estimated_refinement_latency=10,
            latest_safe_refinement_time=130,
            fallback_if_refinement_misses_boundary="recovery-policy@1",
            continuation_debt_refs=(),
            assurance_profile="CHECKED",
        )
        fields.update(changes)
        return ContinuationContract.create(**fields)

    def test_deferred_continuation_cannot_extend_executable_coverage_beyond_horizon(self):
        contract = self._continuation(
            TerminalSemantics.DEFERRED_CONTINUATION,
            continuation_debt_refs=("debt:uncompiled-suffix",),
        )
        self.assertTrue(contract.supports_executable_horizon(100))
        self.assertFalse(contract.supports_executable_horizon(101))

    def test_safe_handoff_requires_lead_time_capability_and_fallback(self):
        good = self._continuation(TerminalSemantics.SAFE_HANDOFF)
        self.assertTrue(good.safe_handoff_ready(now=110, capability_available=True))
        self.assertFalse(good.safe_handoff_ready(now=125, capability_available=True))
        self.assertFalse(good.safe_handoff_ready(now=110, capability_available=False))
        with self.assertRaises(ValueError):
            self._continuation(TerminalSemantics.SAFE_HANDOFF, fallback_if_refinement_misses_boundary="")

    def test_unknown_terminal_never_extends_executable_horizon(self):
        contract = self._continuation(TerminalSemantics.UNKNOWN_TERMINAL)
        self.assertFalse(contract.supports_executable_horizon(101))


if __name__ == "__main__":
    unittest.main()
