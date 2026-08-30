from __future__ import annotations

import unittest

from nolane_plan.selection import (
    CandidateAdmissibility,
    SelectionEvaluator,
    SelectionStatus,
    SelectionTransaction,
)


class Wave5SelectionTests(unittest.TestCase):
    def _transaction(self, candidates=("a", "b"), principal="agent:a") -> SelectionTransaction:
        return SelectionTransaction.create(
            transaction_id="selection-tx@1",
            plan_snapshot_version=7,
            mission_revision=1,
            decision_principal_ref=principal,
            principal_information_access_profile_revision=f"access:{principal}@1",
            information_partition_revision="partition@1",
            decision_epoch_ref="epoch@1",
            action_space_revision="actions@1",
            candidate_action_refs=candidates,
            route_guarantee_requirement="G2",
            measure_mode="scenario",
            risk_policy_revision="risk@1",
            survival_profile_ref="survival@1",
            commitment_pressure_ref="commitment@1",
            debt_policy_ref="debt-policy@1",
            tie_policy="stable-id",
            dependency_generations={"mission": 3, "evidence": 8},
        )

    def test_status_vocabulary_cannot_contain_authorized(self):
        self.assertEqual(
            {status.value for status in SelectionStatus},
            {"advisory", "stale", "superseded"},
        )

    def test_selection_transaction_digest_binds_frozen_candidate_set(self):
        first = self._transaction(("a", "b"))
        second = self._transaction(("a", "c"))
        self.assertNotEqual(first.candidate_set_digest, second.candidate_set_digest)
        self.assertNotEqual(first.canonical_digest, second.canonical_digest)

    def test_selection_transaction_is_principal_information_bound(self):
        a = self._transaction(principal="agent:a")
        b = self._transaction(principal="agent:b")
        self.assertNotEqual(a.canonical_digest, b.canonical_digest)

    def test_hard_rejected_candidate_cannot_be_resurrected_by_score(self):
        record = SelectionEvaluator.select(
            self._transaction(),
            admissibility={
                "a": CandidateAdmissibility("a", False, ("HARD_RISK_VETO",)),
                "b": CandidateAdmissibility("b", True, ()),
            },
            scores={"a": 1000.0, "b": 1.0},
            pareto_front=("a", "b"),
        )
        self.assertEqual(record.chosen_action_ref, "b")
        self.assertEqual(record.status, SelectionStatus.ADVISORY)

    def test_deterministic_tie_uses_stable_id_policy(self):
        record = SelectionEvaluator.select(
            self._transaction(("b", "a")),
            admissibility={
                "a": CandidateAdmissibility("a", True, ()),
                "b": CandidateAdmissibility("b", True, ()),
            },
            scores={"a": 5.0, "b": 5.0},
            pareto_front=("a", "b"),
        )
        self.assertEqual(record.chosen_action_ref, "a")
        self.assertEqual(record.tie_break_reason, "stable-id")

    def test_candidate_outside_frozen_transaction_is_rejected(self):
        with self.assertRaises(ValueError):
            SelectionEvaluator.select(
                self._transaction(("a",)),
                admissibility={"c": CandidateAdmissibility("c", True, ())},
                scores={"c": 9.0},
                pareto_front=("c",),
            )

    def test_dependency_generation_drift_marks_record_stale(self):
        record = SelectionEvaluator.select(
            self._transaction(),
            admissibility={
                "a": CandidateAdmissibility("a", True, ()),
                "b": CandidateAdmissibility("b", True, ()),
            },
            scores={"a": 2.0, "b": 1.0},
            pareto_front=("a",),
        )
        self.assertEqual(record.status_against({"mission": 3, "evidence": 8}), SelectionStatus.ADVISORY)
        self.assertEqual(record.status_against({"mission": 4, "evidence": 8}), SelectionStatus.STALE)

    def test_superseded_record_never_returns_to_advisory(self):
        record = SelectionEvaluator.select(
            self._transaction(),
            admissibility={
                "a": CandidateAdmissibility("a", True, ()),
                "b": CandidateAdmissibility("b", True, ()),
            },
            scores={"a": 2.0, "b": 1.0},
            pareto_front=("a",),
        ).supersede("selection-record@next")
        self.assertEqual(record.status_against({"mission": 3, "evidence": 8}), SelectionStatus.SUPERSEDED)

    def test_selection_record_has_no_external_authorization(self):
        record = SelectionEvaluator.select(
            self._transaction(),
            admissibility={
                "a": CandidateAdmissibility("a", True, ()),
                "b": CandidateAdmissibility("b", True, ()),
            },
            scores={"a": 2.0, "b": 1.0},
            pareto_front=("a",),
        )
        self.assertFalse(hasattr(record, "authorization_id"))
        self.assertFalse(hasattr(record, "dispatch"))


if __name__ == "__main__":
    unittest.main()
