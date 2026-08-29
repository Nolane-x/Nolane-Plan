from __future__ import annotations

import unittest

from nolane_plan.query_domain import QueryDomainError, QueryDomainLedger, QueryDomainStatus


class Wave4QueryDomainTests(unittest.TestCase):
    def _ledger(self):
        ledger = QueryDomainLedger()
        revision = ledger.create(
            query_domain_id="grants",
            scope_revision="scope@1",
            index_schema_revision="grant-index@2",
            completeness_contract="enumerate-all-visible-grants@1",
            filter_predicate_revision="conflict-filter@3",
            alias_equivalence_regime="principal-alias@1",
            visibility_permission_regime="authority-view@4",
            mutation_impact_profile_revision="grant-impact@2",
            query_snapshot_id="snapshot-1",
            snapshot_complete=True,
            opaque=False,
            visibility_assurance=0.95,
            created_sequence=10,
        )
        return ledger, revision

    def test_complete_current_zero_result_can_support_absence(self):
        ledger, revision = self._ledger()
        self.assertEqual(revision.status(0.8), QueryDomainStatus.COMPLETE)
        self.assertTrue(ledger.can_prove_absence(revision, returned_match_count=0, minimum_assurance=0.8))

    def test_zero_results_do_not_prove_absence_when_domain_is_incomplete(self):
        ledger = QueryDomainLedger()
        revision = ledger.create(
            query_domain_id="grants",
            scope_revision="scope@1",
            index_schema_revision="grant-index@2",
            completeness_contract="sample-only",
            filter_predicate_revision="conflict-filter@3",
            alias_equivalence_regime="principal-alias@1",
            visibility_permission_regime="authority-view@4",
            mutation_impact_profile_revision="grant-impact@2",
            query_snapshot_id="snapshot-1",
            snapshot_complete=False,
            opaque=False,
            visibility_assurance=0.95,
            created_sequence=10,
        )
        self.assertEqual(revision.status(0.8), QueryDomainStatus.INCOMPLETE)
        self.assertFalse(ledger.can_prove_absence(revision, returned_match_count=0, minimum_assurance=0.8))

    def test_opaque_domain_never_proves_strong_absence(self):
        ledger, _ = self._ledger()
        opaque = ledger.revise("grants", opaque=True, query_snapshot_id="snapshot-2", snapshot_complete=True)
        self.assertEqual(opaque.status(0.8), QueryDomainStatus.OPAQUE)
        self.assertFalse(ledger.can_prove_absence(opaque, returned_match_count=0, minimum_assurance=0.8))

    def test_new_member_stales_old_absence_proof(self):
        ledger, old = self._ledger()
        current = ledger.advance_membership("grants", query_snapshot_id="snapshot-2")
        self.assertGreater(current.membership_generation, old.membership_generation)
        self.assertFalse(ledger.current(old))

    def test_existing_member_predicate_mutation_stales_without_membership_change(self):
        ledger, old = self._ledger()
        current = ledger.record_member_mutation(
            "grants",
            predicate_result_may_change=True,
            query_snapshot_id="snapshot-2",
        )
        self.assertEqual(current.membership_generation, old.membership_generation)
        self.assertGreater(current.result_sensitivity_generation, old.result_sensitivity_generation)
        self.assertFalse(ledger.current(old))

    def test_irrelevant_member_mutation_does_not_advance_result_sensitivity(self):
        ledger, old = self._ledger()
        current = ledger.record_member_mutation(
            "grants",
            predicate_result_may_change=False,
            query_snapshot_id="snapshot-1",
        )
        self.assertEqual(current.result_sensitivity_generation, old.result_sensitivity_generation)
        self.assertTrue(ledger.current(old))

    def test_filter_schema_visibility_and_alias_regime_are_query_identity(self):
        changes = (
            {"filter_predicate_revision": "conflict-filter@4"},
            {"index_schema_revision": "grant-index@3"},
            {"visibility_permission_regime": "authority-view@5"},
            {"alias_equivalence_regime": "principal-alias@2"},
        )
        for change in changes:
            with self.subTest(change=change):
                ledger, old = self._ledger()
                ledger.revise("grants", query_snapshot_id="snapshot-2", **change)
                self.assertFalse(ledger.current(old))

    def test_strong_domain_requires_mutation_impact_profile_and_stable_snapshot(self):
        ledger = QueryDomainLedger()
        with self.assertRaises(QueryDomainError):
            ledger.create(
                query_domain_id="grants",
                scope_revision="scope@1",
                index_schema_revision="index@1",
                completeness_contract="complete",
                filter_predicate_revision="filter@1",
                alias_equivalence_regime="alias@1",
                visibility_permission_regime="view@1",
                mutation_impact_profile_revision="",
                query_snapshot_id="snapshot",
                snapshot_complete=True,
                opaque=False,
                visibility_assurance=0.95,
                created_sequence=1,
            )

    def test_low_visibility_assurance_is_inconclusive(self):
        ledger, _ = self._ledger()
        weak = ledger.revise("grants", visibility_assurance=0.4, query_snapshot_id="snapshot-2")
        self.assertEqual(weak.status(0.8), QueryDomainStatus.INCONCLUSIVE)
        self.assertFalse(ledger.can_prove_absence(weak, returned_match_count=0, minimum_assurance=0.8))


if __name__ == "__main__":
    unittest.main()
