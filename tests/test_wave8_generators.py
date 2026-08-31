from __future__ import annotations

import unittest

from nolane_plan.wave8_generators import (
    GENERATOR_FAMILIES,
    GENERATOR_VERSION,
    generate_case,
    minimize_recipe,
)


class Wave8GeneratorTests(unittest.TestCase):
    def test_every_generator_family_is_seed_deterministic_and_bounded(self) -> None:
        expected_families = {
            "principal_information",
            "evidence_support",
            "selector_candidates",
            "policy_information",
            "policy_bundle",
            "resource_jobs",
            "handoff",
            "resurrection",
            "relocation",
            "lineage_regime",
            "migration",
            "replay_compaction",
        }
        self.assertEqual(expected_families, set(GENERATOR_FAMILIES))
        for family in sorted(expected_families):
            first = generate_case(family, 17)
            second = generate_case(family, 17)
            self.assertEqual(first, second, family)
            self.assertEqual(GENERATOR_VERSION, first.generator_version)
            self.assertEqual(family, first.generator_family)
            self.assertEqual(17, first.seed)
            self.assertEqual(64, len(first.canonical_digest))
            dimensions = dict(first.dimensions)
            self.assertLessEqual(dimensions.get("principals", 0), 3)
            self.assertLessEqual(dimensions.get("items", 0), 8)
            self.assertLessEqual(dimensions.get("actions", 0), 6)
            self.assertLessEqual(dimensions.get("resources", 0), 5)
            self.assertLessEqual(dimensions.get("fault_points", 0), 8)
            self.assertGreaterEqual(len(first.operations), 1)

    def test_seed_changes_generated_case_without_uncontrolled_randomness(self) -> None:
        for family in GENERATOR_FAMILIES:
            digests = {generate_case(family, seed).canonical_digest for seed in range(4)}
            self.assertGreater(len(digests), 1, family)

    def test_minimizer_is_deterministic_and_reaches_fixed_point(self) -> None:
        recipe = generate_case("replay_compaction", 23)
        required = recipe.operations[-1]

        def still_fails(candidate) -> bool:
            return required in candidate.operations

        first = minimize_recipe(recipe, still_fails)
        second = minimize_recipe(recipe, still_fails)
        self.assertEqual(first, second)
        self.assertEqual((required,), first.operations)
        self.assertTrue(still_fails(first))

        # A second minimization pass must already be at the same fixed point.
        self.assertEqual(first, minimize_recipe(first, still_fails))

    def test_unknown_generator_family_fails_closed(self) -> None:
        with self.assertRaises(ValueError):
            generate_case("not-a-wave8-family", 1)


if __name__ == "__main__":
    unittest.main()
