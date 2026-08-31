from __future__ import annotations

import json
import unittest
from pathlib import Path

from nolane_plan.wave8_worlds import REFERENCE_WORLD_FIXTURES, WORLD_IDS, run_reference_worlds


class Wave8ReferenceWorldTests(unittest.TestCase):
    def test_world_taxonomy_and_checked_in_fixtures_are_exact(self) -> None:
        self.assertEqual(tuple(f"W{index:02d}" for index in range(1, 7)), WORLD_IDS)
        self.assertEqual(WORLD_IDS, tuple(row.world_id for row in REFERENCE_WORLD_FIXTURES))
        fixture_root = Path(__file__).parent / "fixtures" / "wave8_worlds"
        files = tuple(sorted(fixture_root.glob("W*.json")))
        self.assertEqual(6, len(files))
        documents = tuple(json.loads(path.read_text(encoding="utf-8")) for path in files)
        self.assertEqual(WORLD_IDS, tuple(document["world_id"] for document in documents))
        for fixture, document in zip(REFERENCE_WORLD_FIXTURES, documents):
            self.assertEqual(fixture.canonical_payload(), document)
            self.assertTrue(fixture.event_schedule)
            self.assertTrue(fixture.invariant_ids)
            self.assertTrue(fixture.expected_terminal_classification)
            self.assertTrue(fixture.measurement_names)

    def test_all_six_worlds_are_correctness_green_and_repeatable(self) -> None:
        first = run_reference_worlds()
        second = run_reference_worlds()
        self.assertEqual(6, len(first))
        self.assertEqual(first, second)
        self.assertEqual(WORLD_IDS, tuple(result.world_id for result in first))
        for result in first:
            with self.subTest(world_id=result.world_id):
                self.assertTrue(result.passed, result)
                self.assertEqual((), result.failed_invariant_ids)
                self.assertEqual(result.expected_terminal_classification, result.terminal_classification)
                self.assertTrue(result.canonical_digest)
                self.assertTrue(result.measurements)

    def test_measurements_are_reported_but_not_used_as_superiority_claims(self) -> None:
        for fixture in REFERENCE_WORLD_FIXTURES:
            self.assertFalse(fixture.measurements_gate_correctness)
        for result in run_reference_worlds():
            self.assertFalse(result.empirical_superiority_claimed)


if __name__ == "__main__":
    unittest.main()
