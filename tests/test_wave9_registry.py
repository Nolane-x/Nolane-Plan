from __future__ import annotations

import unittest

# TDD RED: this contract is committed before the Wave-9 registry implementation.
from nolane_plan.wave9_registry import (
    WAVE9_CORE_INVARIANT_IDS,
    WAVE9_COVERAGE_INVARIANT_IDS,
    WAVE9_INVARIANTS,
    WAVE9_MUTATION_INVARIANT_IDS,
    WAVE9_REGISTRY_DIGEST,
    get_wave9_invariant,
    validate_wave9_registry,
)


class Wave9RegistryTests(unittest.TestCase):
    def test_registry_freezes_core_mutation_and_coverage_ids(self) -> None:
        expected_core = tuple(
            [f"DC{i:02d}" for i in range(1, 13)]
            + [f"EX{i:02d}" for i in range(1, 13)]
            + [f"MW{i:02d}" for i in range(1, 13)]
        )
        self.assertEqual(WAVE9_CORE_INVARIANT_IDS, expected_core)
        self.assertEqual(WAVE9_MUTATION_INVARIANT_IDS, tuple(f"X{i:02d}" for i in range(1, 13)))
        self.assertEqual(WAVE9_COVERAGE_INVARIANT_IDS, tuple(f"S{i:02d}" for i in range(1, 9)))
        self.assertEqual(len(WAVE9_INVARIANTS), 56)
        self.assertEqual(len({row.invariant_id for row in WAVE9_INVARIANTS}), 56)

    def test_registry_is_self_validating_and_deterministic(self) -> None:
        first = validate_wave9_registry()
        second = validate_wave9_registry()
        self.assertEqual(first, WAVE9_REGISTRY_DIGEST)
        self.assertEqual(second, WAVE9_REGISTRY_DIGEST)
        self.assertEqual(first, second)
        for row in WAVE9_INVARIANTS:
            self.assertTrue(row.title)
            self.assertTrue(row.spec_surface)
            self.assertTrue(row.required_oracle)
            self.assertTrue(row.bounded_scope)
            self.assertEqual(get_wave9_invariant(row.invariant_id), row)

    def test_unknown_registry_id_fails_closed(self) -> None:
        with self.assertRaises(KeyError):
            get_wave9_invariant("MW99")


if __name__ == "__main__":
    unittest.main()
