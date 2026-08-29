from __future__ import annotations

import unittest

from nolane_plan.artifacts import ArtifactRegistry
from nolane_plan.decision_cut import DecisionCutLedger
from nolane_plan.freshness import FreshnessDomainLedger


class DecisionCutWave2Tests(unittest.TestCase):
    def test_future_artifact_is_not_visible_in_historical_cut(self):
        freshness = FreshnessDomainLedger()
        cuts = DecisionCutLedger()
        registry = ArtifactRegistry(freshness)

        historical = cuts.capture(
            commit_frontier_sequence=3,
            mission_revision=1,
            canonical_state_revision=1,
            strategic_location_revision=1,
            source_generations=freshness.generations,
        )
        artifact = registry.register(
            artifact_id="proof:future",
            kind="proof",
            produced_sequence=4,
            dependency_domains=("state",),
            decision_cut_id=historical.id,
        )

        self.assertFalse(registry.usable_at_cut(artifact.id, historical))

    def test_dependency_generation_change_stales_authority_immediately(self):
        freshness = FreshnessDomainLedger()
        cuts = DecisionCutLedger()
        registry = ArtifactRegistry(freshness)
        freshness.ensure("state")
        cut = cuts.capture(1, 1, 1, 1, freshness.generations)
        artifact = registry.register("proof:state", "proof", 1, ("state",), cut.id)
        self.assertTrue(registry.usable_at_cut(artifact.id, cut))

        freshness.bump("state")
        self.assertFalse(registry.usable_at_cut(artifact.id, cut))

    def test_cut_digest_changes_when_frontier_changes(self):
        cuts = DecisionCutLedger()
        a = cuts.capture(1, 1, 1, 1, {})
        b = cuts.capture(2, 1, 1, 1, {})
        self.assertNotEqual(a.id, b.id)
        self.assertLess(a.commit_frontier_sequence, b.commit_frontier_sequence)


if __name__ == "__main__":
    unittest.main()
