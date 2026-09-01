from __future__ import annotations

import unittest

from nolane_plan.wave9_coverage import (
    WAVE9_COVERAGE_HEADER,
    audit_coverage_text,
    audit_repository_coverage,
)
from nolane_plan.wave9_registry import WAVE9_CORE_INVARIANT_IDS


class Wave9CoverageTests(unittest.TestCase):
    def test_repository_ledger_has_exact_core_rows_and_named_evidence(self) -> None:
        audit = audit_repository_coverage()
        self.assertTrue(audit.passed, audit.failures)
        self.assertEqual(tuple(audit.invariant_states), WAVE9_CORE_INVARIANT_IDS)
        self.assertEqual(audit.green_count, len(WAVE9_CORE_INVARIANT_IDS))
        self.assertEqual(audit.partial_count, 0)
        self.assertEqual(audit.orphan_count, 0)
        self.assertEqual(audit.evidence_free_green_count, 0)

    def test_green_without_evidence_is_rejected(self) -> None:
        text = "\n".join(
            [
                WAVE9_COVERAGE_HEADER,
                "| --- | --- | --- | --- | --- | --- |",
                "| DC01 | GREEN |  |  |  |  |",
            ]
        )
        audit = audit_coverage_text(text, expected_ids=("DC01",))
        self.assertFalse(audit.passed)
        self.assertEqual(audit.evidence_free_green_count, 1)

    def test_partial_requires_explicit_rationale_and_never_counts_as_green(self) -> None:
        text = "\n".join(
            [
                WAVE9_COVERAGE_HEADER,
                "| --- | --- | --- | --- | --- | --- |",
                "| DC01 | PARTIAL | production_store.py | test_wave9_production_store.py | wave9_chaos.py | pending |",
            ]
        )
        audit = audit_coverage_text(text, expected_ids=("DC01",))
        self.assertFalse(audit.passed)
        self.assertTrue(any("PARTIAL row lacks explicit rationale" in failure for failure in audit.failures))


if __name__ == "__main__":
    unittest.main()
