from __future__ import annotations

import threading
import unittest

from nolane_plan.freshness import FreshnessDomainLedger
from nolane_plan.proof_dependencies import DependencyFreshnessVector
from nolane_plan.proof_inputs import DependencyCaptureAssurance
from nolane_plan.semantic_barrier import (
    MutationImpactProfileRevision,
    SemanticClosureBarrier,
    SemanticClosureError,
)


class Wave4SemanticBarrierTests(unittest.TestCase):
    def setUp(self):
        self.freshness = FreshnessDomainLedger()
        for domain in ("source:policy", "proof:policy", "global-semantic"):
            self.freshness.ensure(domain)
        self.barrier = SemanticClosureBarrier(self.freshness)
        self.barrier.register_source("policy", revision_id="policy@1", value={"mode": "old"})

    def _vector(self):
        return DependencyFreshnessVector.capture(
            self.freshness,
            artifact_revision="proof@1",
            exact_dependency_revisions={"policy": "policy@1"},
            dependency_domains=("source:policy", "proof:policy"),
            query_domain_revisions=(),
            trust_profile_capability_revision_refs=(),
            evaluated_at_cut="cut@1",
            capture_assurance=DependencyCaptureAssurance.FULL_ENVELOPE_ENFORCED,
        )

    def test_source_revision_and_affected_generations_advance_in_one_receipt(self):
        profile = MutationImpactProfileRevision(
            "impact@1", "policy", ("source:policy", "proof:policy"), True, ()
        )
        receipt = self.barrier.mutate(
            "policy",
            new_revision_id="policy@2",
            new_value={"mode": "new"},
            impact_profile=profile,
        )
        self.assertEqual(receipt.previous_revision_id, "policy@1")
        self.assertEqual(receipt.new_revision_id, "policy@2")
        self.assertEqual(dict(receipt.after_generations)["source:policy"], 2)
        self.assertEqual(dict(receipt.after_generations)["proof:policy"], 2)
        self.assertEqual(self.barrier.read_source("policy").revision_id, "policy@2")

    def test_old_freshness_vector_stales_immediately_after_mutation(self):
        vector = self._vector()
        profile = MutationImpactProfileRevision("impact@1", "policy", ("source:policy", "proof:policy"), True, ())
        self.barrier.mutate("policy", new_revision_id="policy@2", new_value={}, impact_profile=profile)
        self.assertFalse(self.barrier.artifact_current(vector, cached_valid=True))

    def test_cached_validity_never_overrides_generation_mismatch(self):
        vector = self._vector()
        self.freshness.bump("proof:policy")
        self.assertFalse(self.barrier.artifact_current(vector, cached_valid=True))
        self.assertFalse(self.barrier.artifact_current(vector, cached_valid=False))

    def test_unknown_impact_without_conservative_fallback_fails_closed(self):
        profile = MutationImpactProfileRevision("impact@weak", "policy", (), False, ())
        with self.assertRaises(SemanticClosureError):
            self.barrier.mutate("policy", new_revision_id="policy@2", new_value={}, impact_profile=profile)
        self.assertEqual(self.barrier.read_source("policy").revision_id, "policy@1")

    def test_unknown_impact_with_conservative_fallback_bumps_fallback_domain(self):
        profile = MutationImpactProfileRevision(
            "impact@fallback", "policy", ("source:policy",), False, ("global-semantic",)
        )
        receipt = self.barrier.mutate("policy", new_revision_id="policy@2", new_value={}, impact_profile=profile)
        after = dict(receipt.after_generations)
        self.assertEqual(after["source:policy"], 2)
        self.assertEqual(after["global-semantic"], 2)

    def test_reader_cannot_observe_new_source_with_old_generation(self):
        profile = MutationImpactProfileRevision("impact@1", "policy", ("source:policy",), True, ())
        observed: list[tuple[str, int]] = []
        start = threading.Event()

        def reader():
            start.wait()
            for _ in range(100):
                observed.append(self.barrier.read_consistent("policy", ("source:policy",)))

        thread = threading.Thread(target=reader)
        thread.start()
        start.set()
        self.barrier.mutate("policy", new_revision_id="policy@2", new_value={}, impact_profile=profile)
        thread.join()

        self.assertTrue(observed)
        self.assertTrue(all(pair in {("policy@1", 1), ("policy@2", 2)} for pair in observed), observed)
        self.assertNotIn(("policy@2", 1), observed)

    def test_impact_profile_is_source_bound(self):
        profile = MutationImpactProfileRevision("impact@other", "other-source", ("source:policy",), True, ())
        with self.assertRaises(SemanticClosureError):
            self.barrier.mutate("policy", new_revision_id="policy@2", new_value={}, impact_profile=profile)

    def test_revision_must_advance(self):
        profile = MutationImpactProfileRevision("impact@1", "policy", ("source:policy",), True, ())
        with self.assertRaises(SemanticClosureError):
            self.barrier.mutate("policy", new_revision_id="policy@1", new_value={}, impact_profile=profile)


if __name__ == "__main__":
    unittest.main()
