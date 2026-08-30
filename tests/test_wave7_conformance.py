from __future__ import annotations

import unittest

from nolane_plan.wave7_conformance import WAVE7_CASES, WAVE7_TAXONOMY, run_wave7_conformance


EXPECTED = {
    "LG01_LOGICAL_IDENTITY_ALIAS",
    "LG02_REVISION_REBIND",
    "LG03_LOGICAL_ONLY_AUTHORITY",
    "LG04_PARENT_CYCLE",
    "LG05_PARENT_PROVENANCE_DROP",
    "LG06_WALL_CLOCK_CAUSALITY",
    "LG07_REGIME_DRIFT",
    "LG08_DECISION_EPOCH_REUSE",
    "MG01_MISSING_DISPOSITION",
    "MG02_SILENT_DEFAULT",
    "MG03_IDENTITY_MAPPING_OMITTED",
    "MG04_DEBT_DISAPPEARS",
    "MG05_AUTHORITY_SURVIVES_CHANGE",
    "MG06_AMBIGUOUS_EXTERNAL_ACTION",
    "MG07_JOURNAL_ORDER_REWRITE",
    "MG08_MIGRATION_MINTS_AUTHORITY",
    "MG09_ROLLBACK_FORGETS_EXTERNAL_EFFECT",
    "MG10_UNSUPPORTED_LEGACY_GUESS",
    "RP01_BASE_SUFFIX_EXACT",
    "RP02_UNKNOWN_EVENT_FAILS_CLOSED",
    "RP03_CANONICAL_DIGEST_REPRODUCIBLE",
    "RP04_V6_IMPORT_CONSERVATIVE",
    "RP05_STALE_AUTHORITY_NO_RESURRECTION",
    "RP06_HISTORICAL_REVISION_QUERYABLE",
    "GC01_MISSION_REGIME_INVARIANT",
    "GC02_PARENT_REFS_RETAINED",
    "GC03_DORMANT_RESURRECTION_RETAINED",
    "GC04_PROOF_EVIDENCE_DEBT_RETAINED",
    "GC05_UNIQUE_FALLBACK_RETAINED",
    "GC06_REVISION_ID_IMMUTABLE",
    "GC07_RECONSTRUCTION_DIGEST",
    "GC08_AUTHORITY_EQUIVALENCE",
}


class Wave7ConformanceTests(unittest.TestCase):
    def test_registry_covers_exact_wave7_failure_taxonomy_once(self):
        self.assertEqual(len(WAVE7_CASES), 32)
        self.assertEqual(set(WAVE7_CASES), EXPECTED)
        self.assertEqual(len(WAVE7_CASES), len(set(WAVE7_CASES)))
        self.assertEqual(
            {prefix: sum(name.startswith(prefix) for name in WAVE7_CASES) for prefix in ("LG", "MG", "RP", "GC")},
            {"LG": 8, "MG": 10, "RP": 6, "GC": 8},
        )

    def test_taxonomy_is_frozen_and_case_names_are_unique(self):
        self.assertEqual(tuple(WAVE7_TAXONOMY), ("LG", "MG", "RP", "GC"))
        self.assertTrue(all(name[:2] in WAVE7_TAXONOMY for name in WAVE7_CASES))
        self.assertTrue(all(callable(case.check) for case in WAVE7_CASES.values()))

    def test_all_wave7_adversarial_cases_are_defended(self):
        results = run_wave7_conformance()
        self.assertEqual(set(results), EXPECTED)
        failed = {name: detail for name, (passed, detail) in results.items() if not passed}
        self.assertFalse(failed, failed)


if __name__ == "__main__":
    unittest.main()
