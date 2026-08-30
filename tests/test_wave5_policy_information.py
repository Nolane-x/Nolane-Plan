from __future__ import annotations

import unittest

from nolane_plan.policy_information import (
    DecisionEpoch,
    InformationPartitionRevision,
    NonAnticipativityValidator,
    ObservationFrontierRevision,
    RevealEvent,
)


class Wave5PolicyInformationTests(unittest.TestCase):
    def _partition(self, principal: str = "agent:a") -> InformationPartitionRevision:
        return InformationPartitionRevision.create(
            logical_id="info-partition",
            revision_id=f"info-partition@{principal}",
            mission_revision=1,
            decision_epoch_ref="epoch@1",
            principal_scope_ref=principal,
            information_access_profile_revision=f"access:{principal}@1",
            principal_observation_history_digest=f"obs:{principal}@1",
            principal_delivery_frontier_refs=(f"delivery:{principal}@1",),
            canonical_state_version=1,
            observation_history_digest="history@1",
            observable_predicate_set=("signal",),
            hidden_or_unrevealed_predicate_set=("branch",),
            information_equivalence_classes={"same-signal": ("h1", "h2")},
            reveal_event_refs=("reveal-branch@1",),
            observation_model_refs=("obs-model@1",),
            perfect_recall_basis_ref="recall@1",
            abstraction_certificate_refs=("abstraction@1",),
            debt_refs=(),
            validity_regime="runtime@1",
        )

    def _frontier(self, principal: str = "agent:a") -> ObservationFrontierRevision:
        return ObservationFrontierRevision.create(
            frontier_id="frontier",
            revision_id=f"frontier@{principal}",
            principal_scope_ref=principal,
            information_access_profile_revision=f"access:{principal}@1",
            currently_available_observations=("signal",),
            pending_observations=("branch",),
            reveal_event_refs=("reveal-branch@1",),
            latest_safe_observation_times={"branch": 40},
            observation_costs={"branch": 1.0},
            observation_side_effects=(),
            observation_dependencies=("obs-model@1",),
            unobservable_predicates=(),
            conditionally_observable_predicates=("branch",),
            frontier_debt_refs=(),
            validity_regime="runtime@1",
        )

    def _epoch(self, principal: str = "agent:a") -> DecisionEpoch:
        partition = self._partition(principal)
        frontier = self._frontier(principal)
        return DecisionEpoch.create(
            epoch_id="epoch@1",
            plan_snapshot_version=7,
            mission_revision=1,
            decision_principal_ref=principal,
            strategic_location_revision=3,
            information_partition_revision=partition.revision_id,
            principal_information_access_profile_revision=f"access:{principal}@1",
            available_action_space_revision="actions@1",
            active_authority_profile="authority@1",
            active_obligation_basis="obligations@1",
            risk_policy_revision="risk@1",
            observation_frontier_revision=frontier.revision_id,
            temporal_window=(10, 50),
        )

    def _reveal(self, principal: str = "agent:a", available_at: int = 20) -> RevealEvent:
        return RevealEvent.create(
            reveal_event_id="reveal-branch@1",
            revision_id="reveal-branch@1",
            principal_scope_ref=principal,
            revealed_predicates=("branch",),
            observation_model_revision="obs-model@1",
            availability_time_or_condition=available_at,
            false_positive_semantics="bounded@0.01",
            false_negative_semantics="bounded@0.01",
            observer_effects=(),
            validity_regime="runtime@1",
            refines_information_classes=("same-signal",),
        )

    def test_principal_scope_is_part_of_information_partition_identity(self):
        a = self._partition("agent:a")
        b = self._partition("agent:b")
        self.assertNotEqual(a.canonical_digest, b.canonical_digest)
        self.assertNotEqual(a.information_access_profile_revision, b.information_access_profile_revision)

    def test_information_equivalent_histories_cannot_choose_different_actions_before_reveal(self):
        assessment = NonAnticipativityValidator.validate(
            self._partition(),
            self._epoch(),
            action_semantics_by_history={"h1": "deploy:red", "h2": "deploy:blue"},
            reveal_events=(self._reveal(available_at=30),),
            decision_time=20,
        )
        self.assertFalse(assessment.valid)
        self.assertEqual(assessment.violations[0].code, "NONANTICIPATIVITY_VIOLATION")

    def test_grounded_reveal_allows_policy_split_after_it_is_available(self):
        assessment = NonAnticipativityValidator.validate(
            self._partition(),
            self._epoch(),
            action_semantics_by_history={"h1": "deploy:red", "h2": "deploy:blue"},
            reveal_events=(self._reveal(available_at=20),),
            decision_time=20,
        )
        self.assertTrue(assessment.valid, assessment)

    def test_runtime_global_reveal_for_other_principal_cannot_split_policy(self):
        assessment = NonAnticipativityValidator.validate(
            self._partition("agent:b"),
            self._epoch("agent:b"),
            action_semantics_by_history={"h1": "deploy:red", "h2": "deploy:blue"},
            reveal_events=(self._reveal("agent:a", available_at=10),),
            decision_time=20,
        )
        self.assertFalse(assessment.valid)
        self.assertIn("PRINCIPAL_REVEAL_UNAVAILABLE", {v.code for v in assessment.violations})

    def test_late_reveal_is_explicit_nonanticipativity_debt(self):
        assessment = NonAnticipativityValidator.validate(
            self._partition(),
            self._epoch(),
            action_semantics_by_history={"h1": "deploy:red", "h2": "deploy:blue"},
            reveal_events=(self._reveal(available_at=45),),
            decision_time=20,
        )
        self.assertFalse(assessment.valid)
        self.assertIn("NONANTICIPATIVITY_DEBT:LATE_REVEAL", assessment.debt_refs)

    def test_epoch_requires_partition_frontier_and_access_to_share_principal_context(self):
        with self.assertRaises(ValueError):
            DecisionEpoch.create(
                epoch_id="bad",
                plan_snapshot_version=7,
                mission_revision=1,
                decision_principal_ref="agent:a",
                strategic_location_revision=3,
                information_partition_revision="partition-for-b",
                principal_information_access_profile_revision="access:agent:b@1",
                available_action_space_revision="actions@1",
                active_authority_profile="authority@1",
                active_obligation_basis="obligations@1",
                risk_policy_revision="risk@1",
                observation_frontier_revision="frontier-for-b",
                temporal_window=(10, 50),
                bound_principal_scope_ref="agent:b",
            )

    def test_decision_epoch_has_no_execution_authority_state(self):
        epoch = self._epoch()
        self.assertFalse(hasattr(epoch, "authorized"))
        self.assertFalse(hasattr(epoch, "authorization_id"))

    def test_frontier_rejects_latest_safe_time_before_current_observation_window(self):
        with self.assertRaises(ValueError):
            ObservationFrontierRevision.create(
                frontier_id="bad-frontier",
                revision_id="bad-frontier@1",
                principal_scope_ref="agent:a",
                information_access_profile_revision="access:agent:a@1",
                currently_available_observations=("signal",),
                pending_observations=("branch",),
                reveal_event_refs=("reveal@1",),
                latest_safe_observation_times={"branch": -1},
                observation_costs={},
                observation_side_effects=(),
                observation_dependencies=(),
                unobservable_predicates=(),
                conditionally_observable_predicates=("branch",),
                frontier_debt_refs=(),
                validity_regime="runtime@1",
            )


if __name__ == "__main__":
    unittest.main()
