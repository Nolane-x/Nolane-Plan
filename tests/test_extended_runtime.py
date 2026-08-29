import unittest

from nolane_plan.budget import PlanningBudgetGovernor, PlanningWorkUnit
from nolane_plan.freshness import DependencyStamp, FreshnessDomainLedger
from nolane_plan.policy import DecisionBranch, check_non_anticipativity
from nolane_plan.relocation import CandidateRegion, LocationStatus, StateRelocator
from nolane_plan.resources import ReservationConflict, ReservationLedger, SharedCommitment
from nolane_plan.verification import CompletionVerifier
from nolane_plan.mission import MissionLedger
from nolane_plan.obligations import ObligationLedger, ObligationStatus, StrategicObligation


class ExtendedRuntimeTests(unittest.TestCase):
    def test_freshness_stamp_invalidates_on_domain_bump(self):
        ledger = FreshnessDomainLedger()
        ledger.ensure("evidence")
        stamp = DependencyStamp.capture(ledger, ("evidence",))
        self.assertTrue(stamp.current(ledger))
        ledger.bump("evidence")
        self.assertFalse(stamp.current(ledger))

    def test_non_anticipativity_is_principal_relative(self):
        branches = [
            DecisionBranch("h1", "agent:a", "same-info", "action:x"),
            DecisionBranch("h2", "agent:a", "same-info", "action:y"),
            DecisionBranch("h3", "agent:b", "same-info", "action:z"),
        ]
        violations = check_non_anticipativity(branches)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].principal_ref, "agent:a")

    def test_budget_governor_never_silently_drops_mandatory_work(self):
        governor = PlanningBudgetGovernor(total_budget=10)
        units = [
            PlanningWorkUnit("mandatory", "verification", cost=6, value=1, mandatory=True),
            PlanningWorkUnit("optional-high", "future", cost=5, value=100),
            PlanningWorkUnit("optional-small", "future", cost=4, value=2),
        ]
        allocation = governor.allocate(units)
        self.assertIn("mandatory", allocation.selected_ids)
        self.assertIn("optional-small", allocation.selected_ids)
        self.assertNotIn("optional-high", allocation.selected_ids)

    def test_relocator_preserves_decision_distinct_ambiguity(self):
        relocator = StateRelocator([
            CandidateRegion("r1", {"build": "ok"}, "deploy-primary"),
            CandidateRegion("r2", {"build": "ok"}, "deploy-fallback"),
        ])
        result = relocator.locate({"build": "ok"})
        self.assertEqual(result.status, LocationStatus.AMBIGUOUS)
        self.assertEqual(set(result.region_ids), {"r1", "r2"})

    def test_relocator_can_return_unlocated(self):
        relocator = StateRelocator([CandidateRegion("r1", {"build": "ok"}, "x")])
        self.assertEqual(relocator.locate({"build": "bad"}).status, LocationStatus.UNLOCATED)

    def test_shared_commitment_blocks_exclusive_overlap(self):
        ledger = ReservationLedger()
        ledger.reserve(SharedCommitment("repo-main", "agent:a", 0, 10, exclusive=True))
        with self.assertRaises(ReservationConflict):
            ledger.reserve(SharedCommitment("repo-main", "agent:b", 5, 15, exclusive=True))

    def test_completion_requires_success_and_hard_obligations(self):
        mission = MissionLedger.create("ship", success_conditions=("deployed",)).current
        obligations = ObligationLedger()
        obligations.add(StrategicObligation("verify", "verification complete"))
        verifier = CompletionVerifier()
        report = verifier.verify(mission, {"deployed": True}, obligations, anti_goal_violations=())
        self.assertFalse(report.complete)
        obligations.set_status("verify", ObligationStatus.SATISFIED)
        report = verifier.verify(mission, {"deployed": True}, obligations, anti_goal_violations=())
        self.assertTrue(report.complete)


if __name__ == "__main__": unittest.main()
