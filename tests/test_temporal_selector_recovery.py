import unittest

from nolane_plan.recovery import RecoveryController, RecoveryMode
from nolane_plan.selector import ActionScore, pareto_front
from nolane_plan.temporal import HandoffContract, ReactionWindow
from nolane_plan.types import RiskClass


class TemporalSelectorRecoveryTests(unittest.TestCase):
    def test_reaction_window_detects_capacity_miss(self):
        w = ReactionWindow(trigger_time=10, deadline=15, prepare_seconds=2, verify_seconds=2, dispatch_seconds=2)
        self.assertFalse(w.schedulable())

    def test_handoff_requires_information_authority_and_time(self):
        h = HandoffContract("agent:a", "agent:b", handoff_deadline=20, communication_seconds=3, refinement_seconds=4, information_adequate=True, authority_adequate=True)
        self.assertTrue(h.live(now=10))
        self.assertFalse(h.live(now=14))

    def test_pareto_front_applies_hard_veto(self):
        scores = [
            ActionScore("a", progress=10, information=1, optionality=1, convergence=1, reversibility=1, tail_risk=1, debt=1, cost=1),
            ActionScore("b", progress=100, information=100, optionality=100, convergence=100, reversibility=1, tail_risk=0, debt=0, cost=0, hard_veto=True),
        ]
        self.assertEqual([s.action_id for s in pareto_front(scores)], ["a"])

    def test_ontology_break_quarantines_irreversible_actions(self):
        rc = RecoveryController()
        rc.enter_model_class_uncertain("unrepresentable observation", residual_weight=0.6)
        self.assertEqual(rc.state.mode, RecoveryMode.MODEL_CLASS_UNCERTAIN)
        self.assertFalse(rc.can_execute(RiskClass.IRREVERSIBLE))
        self.assertTrue(rc.can_execute(RiskClass.REVERSIBLE))

    def test_emergency_policy_is_explicit(self):
        rc = RecoveryController()
        rc.enter_model_class_uncertain("x", 0.9)
        self.assertTrue(rc.can_execute(RiskClass.IRREVERSIBLE, emergency_authorized=True))


if __name__ == "__main__": unittest.main()
