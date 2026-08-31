from __future__ import annotations

import unittest

from nolane_plan.wave8_conformance import (
    EXECUTABLE_LAYERS,
    EXPECTED_LAYER_COUNTS,
    FROZEN_SEEDS,
    run_wave8_conformance,
)
from nolane_plan.wave8_registry import WAVE8_INVARIANTS, Wave8Layer, wave8_registry_digest


EXPECTED_COUNTS = {
    Wave8Layer.PROPERTY: 10,
    Wave8Layer.METAMORPHIC: 12,
    Wave8Layer.CHAOS: 10,
    Wave8Layer.DIFFERENTIAL: 10,
    Wave8Layer.MUTATION: 12,
    Wave8Layer.WORLD: 6,
    Wave8Layer.COVERAGE: 8,
}


class Wave8ConformanceTests(unittest.TestCase):
    def test_frozen_runner_shape_matches_registry_exactly(self) -> None:
        self.assertEqual(68, len(WAVE8_INVARIANTS))
        self.assertEqual(EXPECTED_COUNTS, EXPECTED_LAYER_COUNTS)
        self.assertEqual(tuple(range(16)), FROZEN_SEEDS)
        self.assertEqual(
            (
                Wave8Layer.PROPERTY,
                Wave8Layer.METAMORPHIC,
                Wave8Layer.CHAOS,
                Wave8Layer.DIFFERENTIAL,
                Wave8Layer.WORLD,
                Wave8Layer.COVERAGE,
            ),
            EXECUTABLE_LAYERS,
        )

    def test_frozen_runner_is_green_and_machine_reconcilable(self) -> None:
        first = run_wave8_conformance()
        second = run_wave8_conformance()
        self.assertTrue(first.green, first.failures)
        self.assertEqual((), first.failures)
        self.assertEqual((), first.counterexamples)
        self.assertEqual(68, first.registry_count)
        self.assertEqual(wave8_registry_digest(), first.registry_digest)
        self.assertEqual(EXPECTED_COUNTS, first.layer_counts)
        self.assertEqual(first, second)
        for layer in EXECUTABLE_LAYERS:
            self.assertEqual("GREEN", first.layer_statuses[layer], layer.value)
        self.assertEqual("SEPARATE_GATE", first.layer_statuses[Wave8Layer.MUTATION])


if __name__ == "__main__":
    unittest.main()
