from __future__ import annotations

import unittest

from nolane_plan.wave8_registry import (
    WAVE8_INVARIANTS,
    Wave8Expectation,
    Wave8Layer,
    wave8_registry_digest,
)


EXPECTED_PREFIX_COUNTS = {
    "P": 10,
    "M": 12,
    "C": 10,
    "D": 10,
    "X": 12,
    "W": 6,
    "S": 8,
}

EXPECTED_LAYER_BY_PREFIX = {
    "P": Wave8Layer.PROPERTY,
    "M": Wave8Layer.METAMORPHIC,
    "C": Wave8Layer.CHAOS,
    "D": Wave8Layer.DIFFERENTIAL,
    "X": Wave8Layer.MUTATION,
    "W": Wave8Layer.WORLD,
    "S": Wave8Layer.COVERAGE,
}


class Wave8RegistryTests(unittest.TestCase):
    def test_registry_is_unique_and_frozen_at_sixty_eight_invariants(self) -> None:
        ids = [row.invariant_id for row in WAVE8_INVARIANTS]
        self.assertEqual(68, len(ids))
        self.assertEqual(68, len(set(ids)))
        for prefix, count in EXPECTED_PREFIX_COUNTS.items():
            self.assertEqual(count, sum(value.startswith(prefix) for value in ids), prefix)

    def test_each_prefix_matches_layer_and_every_row_has_bounded_evidence_contract(self) -> None:
        for row in WAVE8_INVARIANTS:
            prefix = row.invariant_id[0]
            self.assertEqual(EXPECTED_LAYER_BY_PREFIX[prefix], row.layer)
            self.assertTrue(row.spec_surface_refs)
            self.assertTrue(all(ref.strip() for ref in row.spec_surface_refs))
            self.assertTrue(row.required_oracle.strip())
            self.assertTrue(row.generator_family.strip())
            self.assertTrue(row.bounded_scope.strip())
            self.assertIsInstance(row.expectation, Wave8Expectation)

    def test_registry_digest_is_order_stable_but_semantic_sensitive(self) -> None:
        forward = wave8_registry_digest(WAVE8_INVARIANTS)
        reverse = wave8_registry_digest(tuple(reversed(WAVE8_INVARIANTS)))
        self.assertEqual(forward, reverse)
        self.assertEqual(64, len(forward))

        first = WAVE8_INVARIANTS[0]
        changed = first.__class__(
            invariant_id=first.invariant_id,
            layer=first.layer,
            spec_surface_refs=first.spec_surface_refs,
            title=first.title + " changed",
            expectation=first.expectation,
            generator_family=first.generator_family,
            required_oracle=first.required_oracle,
            bounded_scope=first.bounded_scope,
        )
        altered = (changed,) + tuple(WAVE8_INVARIANTS[1:])
        self.assertNotEqual(forward, wave8_registry_digest(altered))


if __name__ == "__main__":
    unittest.main()
