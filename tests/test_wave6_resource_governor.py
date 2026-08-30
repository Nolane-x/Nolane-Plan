from __future__ import annotations

import unittest

from nolane_plan.budget import PlanningBudgetGovernor, PlanningWorkUnit, ProtectedBudgetDemand
from nolane_plan.types import InvariantViolation


class Wave6ResourceGovernorTests(unittest.TestCase):
    def test_background_work_cannot_consume_protected_deadline_capacity(self):
        governor = PlanningBudgetGovernor(10.0)
        allocation = governor.allocate(
            [
                PlanningWorkUnit("mandatory", "core", 3.0, 100.0, mandatory=True),
                PlanningWorkUnit("background", "speculative", 4.0, 1000.0),
            ],
            protected_demands=(
                ProtectedBudgetDemand(
                    id="reaction-a",
                    amount=4.0,
                    active_from=0.0,
                    active_until=10.0,
                    release_after=10.0,
                    source_reservation_ref="reserve-a",
                    required_route=True,
                ),
            ),
            now=1.0,
        )
        self.assertEqual(allocation.selected_ids, ("mandatory",))
        self.assertEqual(allocation.protected, 4.0)
        self.assertEqual(allocation.remaining, 3.0)

    def test_mandatory_plus_protected_over_budget_fails_instead_of_pruning(self):
        governor = PlanningBudgetGovernor(10.0)
        with self.assertRaises(InvariantViolation):
            governor.allocate(
                [PlanningWorkUnit("mandatory", "core", 7.0, 1.0, mandatory=True)],
                protected_demands=(
                    ProtectedBudgetDemand(
                        id="reaction-a",
                        amount=4.0,
                        active_from=0.0,
                        active_until=10.0,
                        release_after=10.0,
                        source_reservation_ref="reserve-a",
                        required_route=True,
                    ),
                ),
                now=1.0,
            )

    def test_protected_capacity_is_not_reused_before_release_policy_allows(self):
        governor = PlanningBudgetGovernor(10.0)
        protected = ProtectedBudgetDemand(
            id="reaction-a",
            amount=6.0,
            active_from=0.0,
            active_until=20.0,
            release_after=5.0,
            source_reservation_ref="reserve-a",
            required_route=True,
        )
        before = governor.allocate(
            [PlanningWorkUnit("background", "speculative", 7.0, 100.0)],
            protected_demands=(protected,),
            now=4.0,
        )
        self.assertEqual(before.selected_ids, ())
        self.assertEqual(before.protected, 6.0)

        after = governor.allocate(
            [PlanningWorkUnit("background", "speculative", 7.0, 100.0)],
            protected_demands=(protected,),
            now=6.0,
        )
        self.assertEqual(after.selected_ids, ("background",))
        self.assertEqual(after.protected, 0.0)

    def test_multiple_required_protections_cannot_starve_each_other_silently(self):
        governor = PlanningBudgetGovernor(5.0)
        with self.assertRaises(InvariantViolation):
            governor.allocate(
                [],
                protected_demands=(
                    ProtectedBudgetDemand("a", 3.0, 0.0, 10.0, 10.0, "reserve-a", True),
                    ProtectedBudgetDemand("b", 3.0, 0.0, 10.0, 10.0, "reserve-b", True),
                ),
                now=1.0,
            )

    def test_legacy_allocate_call_remains_unchanged(self):
        governor = PlanningBudgetGovernor(5.0)
        allocation = governor.allocate(
            [
                PlanningWorkUnit("mandatory", "core", 2.0, 1.0, mandatory=True),
                PlanningWorkUnit("optional", "search", 3.0, 3.0),
            ]
        )
        self.assertEqual(allocation.selected_ids, ("mandatory", "optional"))
        self.assertEqual(allocation.spent, 5.0)
        self.assertEqual(allocation.remaining, 0.0)
        self.assertEqual(allocation.protected, 0.0)

    def test_invalid_protected_demand_fails_closed(self):
        with self.assertRaises(ValueError):
            ProtectedBudgetDemand("x", -1.0, 0.0, 1.0, 1.0, "reserve", True)
        with self.assertRaises(ValueError):
            ProtectedBudgetDemand("x", 1.0, 2.0, 1.0, 1.0, "reserve", True)
        with self.assertRaises(ValueError):
            ProtectedBudgetDemand("x", 1.0, 0.0, 2.0, 3.0, "reserve", True)


if __name__ == "__main__":
    unittest.main()
