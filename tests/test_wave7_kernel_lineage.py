from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from nolane_plan import PlanKernel
from nolane_plan.actions import ActionIntent, AuthorityGrant
from nolane_plan.evidence import EvidencePolarity, EvidenceRecord
from nolane_plan.execution import AdapterProfile
from nolane_plan.future import FutureFamily
from nolane_plan.lineage import SemanticRegimeKind
from nolane_plan.obligations import StrategicObligation
from nolane_plan.relocation import CandidateRegion
from nolane_plan.types import AuthorizationError


class CountingAdapter:
    def __init__(self) -> None:
        self.calls = 0

    def execute(self, action, principal_ref):
        self.calls += 1
        return {
            "ok": True,
            "postconditions_verified": True,
            "executing_principal_ref": principal_ref,
            "state_patch": {"done": True},
        }


class Wave7KernelLineageTests(unittest.TestCase):
    def make_kernel(self):
        root = Path(tempfile.mkdtemp())
        return PlanKernel.create(root, "ship verified artifact", ("done",), ("preserve rollback",))

    def test_kernel_bootstraps_explicit_semantic_regimes_and_root_lineage(self):
        kernel = self.make_kernel()
        expected = {
            SemanticRegimeKind.SCHEMA,
            SemanticRegimeKind.WORLD_MODEL,
            SemanticRegimeKind.ENVIRONMENT,
            SemanticRegimeKind.CANONICALIZATION,
            SemanticRegimeKind.SEMANTIC_PROFILE,
        }
        self.assertEqual(set(kernel.semantic_regimes), expected)
        for kind in expected:
            self.assertEqual(kernel.semantic_regimes[kind], kernel.lineage.current_regime(kind).revision_id)
        self.assertEqual(kernel.lineage.current("MissionRevision", "mission").semantic_digest, kernel._mission_semantic_digest())
        self.assertEqual(
            kernel.lineage.current("CanonicalState", "canonical-state").semantic_digest,
            kernel._canonical_state_semantic_digest(),
        )

    def test_future_obligation_action_and_grant_mutations_get_canonical_lineage(self):
        kernel = self.make_kernel()
        family = FutureFamily("primary", "endpoint is healthy", 0.8)
        obligation = StrategicObligation("rollback", "rollback path preserved")
        action = ActionIntent("deploy", "deploy")
        grant = AuthorityGrant("deploy-grant", "agent:a", frozenset({"deploy"}))
        kernel.add_future_family(family)
        kernel.add_obligation(obligation)
        kernel.propose_action(action)
        kernel.add_grant(grant)

        self.assertEqual(kernel.lineage.current("FutureFamily", "primary").logical_id, "primary")
        self.assertEqual(kernel.lineage.current("StrategicObligation", "rollback").logical_id, "rollback")
        self.assertEqual(kernel.lineage.current("ActionIntent", "deploy").logical_id, "deploy")
        self.assertEqual(kernel.lineage.current("AuthorityGrant", "deploy-grant").logical_id, "deploy-grant")

    def test_evidence_adapter_and_region_mutations_get_canonical_lineage(self):
        kernel = self.make_kernel()
        evidence = EvidenceRecord(
            "e:verified",
            "artifact verified",
            EvidencePolarity.SUPPORTS,
            "ci",
            "ci:root",
            1,
            valid_until=20,
            assurance=0.97,
        )
        adapter = AdapterProfile("adapter:deploy", 1, True, True, 0.95)
        region = CandidateRegion("region:ready", {"done": False}, "deploy")

        kernel.add_evidence(evidence)
        kernel.register_adapter(adapter)
        kernel.register_region(region)

        self.assertEqual(kernel.lineage.current("EvidenceRecord", evidence.id).logical_id, evidence.id)
        self.assertEqual(kernel.lineage.current("AdapterProfile", adapter.adapter_id).logical_id, adapter.adapter_id)
        self.assertEqual(kernel.lineage.current("CandidateRegion", region.id).logical_id, region.id)

    def test_mission_revision_supersedes_lineage_without_erasing_history(self):
        kernel = self.make_kernel()
        first = kernel.lineage.current("MissionRevision", "mission")
        kernel.revise_mission(objective="ship verified artifact safely")
        second = kernel.lineage.current("MissionRevision", "mission")
        self.assertNotEqual(first.revision_id, second.revision_id)
        self.assertEqual(second.supersedes_revision_id, first.revision_id)
        self.assertIn(first.revision_id, second.parent_revision_ids)
        self.assertEqual(kernel.lineage.get(first.revision_id), first)

    def test_canonical_commit_creates_new_lineage_revision(self):
        kernel = self.make_kernel()
        kernel.propose_action(ActionIntent("deploy", "deploy"))
        kernel.add_grant(AuthorityGrant("g", "agent:a", frozenset({"deploy"})))
        before = kernel.lineage.current("CanonicalState", "canonical-state")
        auth = kernel.authorize("deploy", "agent:a", ("g",), 1)
        kernel.dispatch(auth.id, "agent:a", CountingAdapter(), 2)
        after = kernel.lineage.current("CanonicalState", "canonical-state")
        self.assertNotEqual(before.revision_id, after.revision_id)
        self.assertEqual(after.supersedes_revision_id, before.revision_id)
        self.assertEqual(after.semantic_digest, kernel._canonical_state_semantic_digest())

    def test_semantic_regime_revision_advances_typed_freshness(self):
        kernel = self.make_kernel()
        domain = "semantic-regime:ENVIRONMENT"
        before_generation = kernel.freshness.generation(domain)
        before = kernel.lineage.current_regime(SemanticRegimeKind.ENVIRONMENT)
        after = kernel.revise_semantic_regime(
            SemanticRegimeKind.ENVIRONMENT,
            semantic_digest="env:tool-api-v2",
            provenance_refs=("host:tool-registry",),
        )
        self.assertNotEqual(before.revision_id, after.revision_id)
        self.assertEqual(after.parent_revision_id, before.revision_id)
        self.assertEqual(kernel.freshness.generation(domain), before_generation + 1)
        self.assertEqual(kernel.semantic_regimes[SemanticRegimeKind.ENVIRONMENT], after.revision_id)

    def test_authorization_binds_exact_regime_bundle_and_drift_blocks_before_adapter_call(self):
        kernel = self.make_kernel()
        kernel.propose_action(ActionIntent("deploy", "deploy"))
        kernel.add_grant(AuthorityGrant("g", "agent:a", frozenset({"deploy"})))
        auth = kernel.authorize("deploy", "agent:a", ("g",), 1)
        binding = kernel.authorization_lineage_bindings[auth.id]
        self.assertEqual(dict(binding.regime_revisions), {
            kind.value: kernel.lineage.current_regime(kind).revision_id for kind in SemanticRegimeKind
        })

        kernel.revise_semantic_regime(
            SemanticRegimeKind.ENVIRONMENT,
            semantic_digest="env:changed",
            provenance_refs=("host:tool-registry",),
        )
        adapter = CountingAdapter()
        with self.assertRaises(AuthorizationError):
            kernel.dispatch(auth.id, "agent:a", adapter, 2)
        self.assertEqual(adapter.calls, 0)

    def test_lineage_layer_does_not_mint_or_dispatch_authority(self):
        kernel = self.make_kernel()
        self.assertFalse(hasattr(kernel.lineage, "authorize"))
        self.assertFalse(hasattr(kernel.lineage, "dispatch"))
        self.assertFalse(hasattr(kernel.lineage.current_regime(SemanticRegimeKind.SCHEMA), "authorization_id"))

    def test_lineage_mutations_use_existing_kernel_writer_lock(self):
        kernel = self.make_kernel()
        lock = kernel._writer_lock
        kernel.revise_semantic_regime(
            SemanticRegimeKind.CANONICALIZATION,
            semantic_digest="canon:v2",
            provenance_refs=("host:canonicalizer",),
        )
        self.assertIs(kernel._writer_lock, lock)


if __name__ == "__main__":
    unittest.main()
