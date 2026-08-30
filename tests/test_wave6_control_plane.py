from __future__ import annotations

import unittest

from nolane_plan.control_plane import (
    ControlPlaneReservation,
    ControlPlaneResourceError,
    ControlPlaneResourceRevision,
    ReactionJobContract,
    ReactionResourceDemand,
)


class Wave6ControlPlaneTests(unittest.TestCase):
    def _resource(self, **overrides):
        kwargs = dict(
            resource_id="verifier",
            revision_id="verifier-r1",
            resource_kind="CONCURRENCY",
            capacity_units=2.0,
            concurrency_limit=2,
            service_rate_per_second=2.0,
            rate_window_seconds=1.0,
            availability_interval=(0.0, 100.0),
            priority_policy_ref="priority-v1",
            reservation_policy_ref="reservation-v1",
            regime_ref="verifier-regime-1",
            assurance_profile="bounded-worst-case",
            opaque_dimensions=(),
            conservative_capacity_bound=None,
            validity_regime="mission-1",
        )
        kwargs.update(overrides)
        return ControlPlaneResourceRevision.create(**kwargs)

    def _demand(self, **overrides):
        kwargs = dict(
            resource_ref="verifier",
            required_service=1.0,
            required_concurrency_units=1,
            release_offset_interval=(0.0, 0.0),
            demand_window=(0.0, 1.0),
            mandatory=True,
        )
        kwargs.update(overrides)
        return ReactionResourceDemand.create(**kwargs)

    def _job(self, **overrides):
        kwargs = dict(
            reaction_job_id="job-a",
            revision_id="job-a-r1",
            policy_scope="policy-1",
            mission_revision="mission-1",
            information_partition_revision="partition-1",
            reaction_envelope_ref="reaction-a-r1",
            release_window=(0.0, 0.0),
            deadline=1.0,
            resource_demands=(self._demand(),),
            coexistence_tags=("cohort:primary",),
            correlation_refs=("corr-r1",),
            priority_class="deadline-critical",
            reservation_refs=(),
            risk_class="high",
            model_adequacy_debt_refs=(),
            validity_regime="mission-1",
        )
        kwargs.update(overrides)
        return ReactionJobContract.create(**kwargs)

    def test_canonical_control_resource_is_revision_and_regime_bound(self):
        resource = self._resource()
        self.assertEqual(resource.concurrency_limit, 2)
        changed = self._resource(revision_id="verifier-r2", regime_ref="verifier-regime-2")
        self.assertNotEqual(resource.canonical_digest, changed.canonical_digest)

    def test_resource_kind_and_capacity_validation_fail_closed(self):
        with self.assertRaises(ControlPlaneResourceError):
            self._resource(resource_kind="MAGICAL_UNLIMITED")
        with self.assertRaises(ControlPlaneResourceError):
            self._resource(capacity_units=-1)
        with self.assertRaises(ControlPlaneResourceError):
            self._resource(rate_window_seconds=0)
        with self.assertRaises(ControlPlaneResourceError):
            self._resource(availability_interval=(10, 5))

    def test_opaque_resource_requires_conservative_bound_for_strong_use(self):
        opaque = self._resource(opaque_dimensions=("provider-burst",))
        self.assertFalse(opaque.supports_strong_bound)
        bounded = self._resource(
            opaque_dimensions=("provider-burst",), conservative_capacity_bound=1.0
        )
        self.assertTrue(bounded.supports_strong_bound)
        self.assertEqual(bounded.effective_capacity_units, 1.0)

    def test_reaction_resource_demand_rejects_negative_or_inverted_values(self):
        with self.assertRaises(ControlPlaneResourceError):
            self._demand(required_service=-0.1)
        with self.assertRaises(ControlPlaneResourceError):
            self._demand(required_concurrency_units=-1)
        with self.assertRaises(ControlPlaneResourceError):
            self._demand(release_offset_interval=(2, 1))
        with self.assertRaises(ControlPlaneResourceError):
            self._demand(demand_window=(2, 1))

    def test_strong_reaction_job_requires_resource_demand_and_valid_deadline(self):
        with self.assertRaises(ControlPlaneResourceError):
            self._job(resource_demands=())
        with self.assertRaises(ControlPlaneResourceError):
            self._job(release_window=(2.0, 3.0), deadline=1.0)

    def test_job_digest_is_order_stable_for_set_like_refs(self):
        left = self._job(
            coexistence_tags=("b", "a"),
            correlation_refs=("corr-2", "corr-1"),
            reservation_refs=("r2", "r1"),
        )
        right = self._job(
            coexistence_tags=("a", "b"),
            correlation_refs=("corr-1", "corr-2"),
            reservation_refs=("r1", "r2"),
        )
        self.assertEqual(left.canonical_digest, right.canonical_digest)

    def test_reservation_binds_resource_policy_window_and_service(self):
        reservation = ControlPlaneReservation.create(
            reservation_id="reserve-a",
            revision_id="reserve-a-r1",
            resource_ref="verifier",
            policy_scope="policy-1",
            job_refs=("job-a",),
            start_time=0.0,
            end_time=2.0,
            reserved_service=1.5,
            reserved_concurrency_units=1,
            priority_class="deadline-critical",
            preemptible=False,
            risk_justification_ref="risk-high",
            cross_future_value_ref="cfv-1",
            validity_regime="mission-1",
        )
        self.assertEqual(reservation.job_refs, ("job-a",))
        self.assertGreater(reservation.reserved_service, 0)

    def test_reservation_invalid_window_or_service_is_rejected(self):
        base = dict(
            reservation_id="reserve-a",
            revision_id="reserve-a-r1",
            resource_ref="verifier",
            policy_scope="policy-1",
            job_refs=("job-a",),
            start_time=0.0,
            end_time=2.0,
            reserved_service=1.5,
            reserved_concurrency_units=1,
            priority_class="deadline-critical",
            preemptible=False,
            risk_justification_ref="risk-high",
            cross_future_value_ref="cfv-1",
            validity_regime="mission-1",
        )
        with self.assertRaises(ControlPlaneResourceError):
            ControlPlaneReservation.create(**{**base, "end_time": -1})
        with self.assertRaises(ControlPlaneResourceError):
            ControlPlaneReservation.create(**{**base, "reserved_service": -1})
        with self.assertRaises(ControlPlaneResourceError):
            ControlPlaneReservation.create(**{**base, "reserved_concurrency_units": -1})


if __name__ == "__main__":
    unittest.main()
