from __future__ import annotations

import unittest
from pathlib import Path

import nolane_plan
from nolane_plan.replay_registry import (
    DEFAULT_REPLAY_REGISTRY,
    ReplayEventClass,
    ReplayEventSpec,
    ReplayRegistry,
    discover_recorded_event_types,
)
from nolane_plan.types import ReplayError


class Wave7ReplayRegistryTests(unittest.TestCase):
    def test_every_emitted_record_event_is_frozen_in_registry(self):
        package_root = Path(nolane_plan.__file__).resolve().parent
        emitted = discover_recorded_event_types(package_root)
        self.assertTrue(emitted)
        self.assertEqual(emitted, DEFAULT_REPLAY_REGISTRY.event_types)

    def test_registry_has_exact_four_classification_kinds(self):
        self.assertEqual(
            {item.value for item in ReplayEventClass},
            {"STATE_REDUCER", "DERIVED_RECOMPUTE", "AUDIT_ONLY", "SNAPSHOT_BOUNDARY"},
        )

    def test_unknown_correctness_event_fails_closed(self):
        with self.assertRaises(ReplayError):
            DEFAULT_REPLAY_REGISTRY.require("wave7.unknown_correctness_event", correctness_significant=True)

    def test_duplicate_event_name_is_rejected(self):
        spec = ReplayEventSpec("x", ReplayEventClass.AUDIT_ONLY, correctness_significant=False)
        with self.assertRaises(ValueError):
            ReplayRegistry((spec, spec))

    def test_state_reducers_declare_a_reducer_or_delegate(self):
        for spec in DEFAULT_REPLAY_REGISTRY.specs:
            if spec.classification == ReplayEventClass.STATE_REDUCER:
                self.assertTrue(spec.reducer_name or spec.delegate_layer, spec.event_type)


if __name__ == "__main__":
    unittest.main()
