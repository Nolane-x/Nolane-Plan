from __future__ import annotations

import unittest

from nolane_plan.handoff_stability import (
    EdgeActivationStatus,
    HandoffStabilityContract,
    HandoffStabilityEvaluator,
)


class Wave6HandoffStabilityTests(unittest.TestCase):
    def contract(self, **overrides):
        kwargs = dict(
            contract_id="stability-1",
            revision_id="stability-r1",
            policy_edge_ref="edge-a-b",
            protected_predicate_refs=("inventory-ok", "permission-ok"),
            protected_generation_bindings=(("inventory", 7), ("permission", 3)),
            lock_or_reservation_refs=("inventory-lock-r1",),
            stability_start=10.0,
            stability_end=30.0,
            external_writer_assumption_refs=("writer-set-r1",),
            refresh_required_predicate_refs=("inventory-ok", "permission-ok"),
            authorization_time_precondition_refs=("inventory-ok", "permission-ok"),
            invalidating_event_refs=("inventory.external_write", "permission.revoked"),
            open_side_effect_refs=(),
            fallback_on_instability="replan-edge",
            opacity_debt_refs=(),
            validity_regime="mission-1",
        )
        kwargs.update(overrides)
        return HandoffStabilityContract.create(**kwargs)

    def assess(self, contract=None, **overrides):
        kwargs = dict(
            contract=contract or self.contract(),
            current_generations={"inventory": 7, "permission": 3},
            refreshed_predicates=(),
            active_lock_or_reservation_refs=("inventory-lock-r1",),
            observed_invalidating_events=(),
            resolved_side_effect_refs=(),
            current_external_writer_assumption_refs=("writer-set-r1",),
            now=20.0,
        )
        kwargs.update(overrides)
        return HandoffStabilityEvaluator.assess(**kwargs)

    def test_protected_current_edge_is_stable(self):
        result = self.assess()
        self.assertEqual(result.status, EdgeActivationStatus.STABLE)
        self.assertTrue(result.supports_activation)

    def test_generation_drift_requires_activation_refresh(self):
        result = self.assess(current_generations={"inventory": 8, "permission": 3})
        self.assertEqual(result.status, EdgeActivationStatus.REFRESH_REQUIRED)
        self.assertFalse(result.supports_activation)
        self.assertIn("inventory-ok", result.required_refresh_predicates)

    def test_explicit_refresh_can_reestablish_activation_after_generation_drift(self):
        result = self.assess(
            current_generations={"inventory": 8, "permission": 3},
            refreshed_predicates=("inventory-ok",),
        )
        self.assertEqual(result.status, EdgeActivationStatus.REFRESHED)
        self.assertTrue(result.supports_activation)

    def test_permission_generation_drift_cannot_be_waived_by_old_edge_certificate(self):
        result = self.assess(current_generations={"inventory": 7, "permission": 4})
        self.assertEqual(result.status, EdgeActivationStatus.REFRESH_REQUIRED)
        self.assertIn("permission-ok", result.required_refresh_predicates)

    def test_expired_stability_window_requires_refresh(self):
        result = self.assess(now=31.0)
        self.assertEqual(result.status, EdgeActivationStatus.REFRESH_REQUIRED)
        self.assertFalse(result.supports_activation)

    def test_missing_lock_or_reservation_requires_refresh(self):
        result = self.assess(active_lock_or_reservation_refs=())
        self.assertEqual(result.status, EdgeActivationStatus.REFRESH_REQUIRED)
        self.assertIn("lock_or_reservation_not_current", result.blocker_refs)

    def test_observed_invalidating_event_makes_edge_invalid(self):
        result = self.assess(observed_invalidating_events=("permission.revoked",))
        self.assertEqual(result.status, EdgeActivationStatus.INVALID)
        self.assertFalse(result.supports_activation)
        self.assertEqual(result.fallback_ref, "replan-edge")

    def test_open_asynchronous_side_effect_requires_resolution(self):
        contract = self.contract(open_side_effect_refs=("dispatch-x",))
        result = self.assess(contract=contract)
        self.assertEqual(result.status, EdgeActivationStatus.REFRESH_REQUIRED)
        resolved = self.assess(contract=contract, resolved_side_effect_refs=("dispatch-x",))
        self.assertEqual(resolved.status, EdgeActivationStatus.STABLE)

    def test_external_writer_assumption_drift_requires_refresh(self):
        result = self.assess(current_external_writer_assumption_refs=("writer-set-r2",))
        self.assertEqual(result.status, EdgeActivationStatus.REFRESH_REQUIRED)

    def test_opacity_debt_is_unknown_not_stable(self):
        contract = self.contract(opacity_debt_refs=("opaque-external-writer",))
        result = self.assess(contract=contract)
        self.assertEqual(result.status, EdgeActivationStatus.UNKNOWN)
        self.assertFalse(result.supports_activation)

    def test_contract_validation_fails_closed(self):
        with self.assertRaises(ValueError):
            self.contract(stability_start=30.0, stability_end=20.0)
        with self.assertRaises(ValueError):
            self.contract(protected_predicate_refs=())
        with self.assertRaises(ValueError):
            self.contract(protected_generation_bindings=(("inventory", -1),))
        with self.assertRaises(ValueError):
            self.contract(fallback_on_instability="")


if __name__ == "__main__":
    unittest.main()
