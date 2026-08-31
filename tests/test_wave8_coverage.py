from __future__ import annotations

from pathlib import Path
import unittest

from nolane_plan.wave8_coverage import (
    FINAL_WAVE7_CI_RUN,
    FINAL_WAVE7_RELEASE_SHA,
    audit_coverage_text,
    audit_repository_coverage,
    coverage_ledger_path,
    parse_coverage_table,
)
from nolane_plan.wave8_registry import WAVE8_INVARIANTS, Wave8Layer


class Wave8CoverageTests(unittest.TestCase):
    def test_repository_coverage_is_deterministic_and_fail_closed(self) -> None:
        path = coverage_ledger_path()
        self.assertTrue(path.is_file(), path)
        text = path.read_text(encoding="utf-8")
        rows = parse_coverage_table(text)
        self.assertTrue(rows)
        first = audit_repository_coverage()
        second = audit_repository_coverage()
        self.assertTrue(first.passed, first.failures)
        self.assertEqual((), first.failures)
        self.assertEqual(first, second)
        self.assertEqual(FINAL_WAVE7_RELEASE_SHA, "78e44da066bd362a2ee935c06ad5902bb0872238")
        self.assertEqual(FINAL_WAVE7_CI_RUN, "33350465557")
        self.assertIn(FINAL_WAVE7_RELEASE_SHA, text)
        self.assertIn(FINAL_WAVE7_CI_RUN, text)

    def test_every_noncoverage_wave8_invariant_maps_to_non_boundary_correctness_row(self) -> None:
        audit = audit_repository_coverage()
        mapped = audit.invariant_surface_states
        for invariant in WAVE8_INVARIANTS:
            if invariant.layer is Wave8Layer.COVERAGE:
                continue
            for surface in invariant.spec_surface_refs:
                with self.subTest(invariant=invariant.invariant_id, surface=surface):
                    self.assertIn(surface, mapped)
                    state = mapped[surface]
                    self.assertNotIn("BOUNDARY", state)
                    self.assertNotIn("RESEARCH", state)

    def test_partial_research_boundary_and_release_claim_rules_are_enforced(self) -> None:
        text = coverage_ledger_path().read_text(encoding="utf-8")
        bare_partial = text.replace(
            "| General migration contracts across every historical schema/version pair | PARTIAL — repository-owned v2-v6 to v7 edges are exhausted; arbitrary external/historical schema pairs remain unsupported | W8 |",
            "| General migration contracts across every historical schema/version pair | PARTIAL | W8 |",
            1,
        )
        self.assertFalse(audit_coverage_text(bare_partial).passed)

        boundary_promoted = text.replace(
            "| Distributed correctness writers / consensus | BOUNDARY | not v0.15 |",
            "| Distributed correctness writers / consensus | GREEN | W8 |",
            1,
        )
        self.assertFalse(audit_coverage_text(boundary_promoted).passed)

        research_promoted = text.replace(
            "| Real benchmark worlds / empirical superiority | RESEARCH | W8 measurement only |",
            "| Real benchmark worlds / empirical superiority | GREEN | W8 |",
            1,
        )
        self.assertFalse(audit_coverage_text(research_promoted).passed)

        stale_release = text.replace(FINAL_WAVE7_CI_RUN, "00000000000")
        self.assertFalse(audit_coverage_text(stale_release).passed)


if __name__ == "__main__":
    unittest.main()
