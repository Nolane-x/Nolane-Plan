from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from nolane_plan import PlanKernel
from nolane_plan.actions import ActionIntent, AuthorityGrant
from nolane_plan.evidence import EvidencePolarity, EvidenceRecord
from nolane_plan.future_resurrection import DormantBranchRevision
from nolane_plan.handoff_stability import HandoffStabilityContract
from nolane_plan.lineage import CanonicalLineageRevision, SemanticRegimeKind
from nolane_plan.lineage_recovery import canonical_semantic_digest
from nolane_plan.types import ReplayError


class Wave7CompactionTests(unittest.TestCase):
    def make_kernel(self, root: Path | None = None) -> PlanKernel:
        root = Path(tempfile.mkdtemp()) if root is None else root
        return PlanKernel.create(root, "compact safely", ("done",), ("preserve rollback",))

    def compact(self, kernel: PlanKernel, manifest_id: str = "compaction:1", **kwargs):
        try:
            return kernel.compact_lineage(manifest_id, **kwargs)
        except Exception as exc:
            self.fail(f"compaction contract is not implemented: {exc}")

    def dormant_branch(self) -> DormantBranchRevision:
        return DormantBranchRevision.create(
            branch_id="branch:hedge",
            revision_id="branch:hedge@1",
            branch_digest="branch:digest:1",
            mission_revision="mission@1",
            assumption_revision_refs=("assumption@1",),
            evidence_revision_refs=("evidence:dormant@1",),
            transition_model_revision="transition@1",
            temporal_feasibility_revision="temporal@1",
            resource_revision_refs=("resource@1",),
            capability_revision_refs=("capability@1",),
            authority_revision_refs=("authority@1",),
            risk_classification="catastrophic",
            resurrection_dependency_refs=("trigger@1",),
            dormant_reason="currently unlikely",
            dormant_generation=4,
            catastrophic_exposure=True,
            sole_hard_route=False,
            unique_hedge=True,
            information_value=1.0,
        )

    def seed_history(self, kernel: PlanKernel):
        kernel.propose_action(ActionIntent("deploy", "deploy"))
        kernel.add_grant(AuthorityGrant("grant", "agent:a", frozenset({"deploy"})))
        authorization = kernel.authorize("deploy", "agent:a", ("grant",), 1)
        kernel.add_evidence(
            EvidenceRecord(
                "evidence:verified",
                "artifact verified",
                EvidencePolarity.SUPPORTS,
                "ci",
                "ci:root",
                1,
                assurance=0.99,
            )
        )
        first = kernel._register_lineage(
            object_family="DerivedArtifact",
            logical_id="artifact:proofed",
            semantic_payload={"revision": 1},
            provenance_refs=("proof:root@1", "evidence:verified"),
            debt_refs=("debt:verify@1",),
        )
        # A real journaled canonical mutation separates immutable revisions so
        # the fixture respects the same sequence monotonicity as production.
        kernel.revise_mission(objective="compact safely with refreshed proof")
        second = kernel._register_lineage(
            object_family="DerivedArtifact",
            logical_id="artifact:proofed",
            semantic_payload={"revision": 2},
            provenance_refs=("proof:root@1", "evidence:verified"),
            debt_refs=("debt:verify@1",),
        )
        return authorization, first, second

    def register_unique_fallback(self, kernel: PlanKernel) -> HandoffStabilityContract:
        contract = HandoffStabilityContract.create(
            contract_id="edge:critical",
            revision_id="edge:critical@1",
            policy_edge_ref="parent->child",
            protected_predicate_refs=("inventory",),
            protected_generation_bindings=(("inventory", 1),),
            lock_or_reservation_refs=(),
            stability_start=0,
            stability_end=100,
            external_writer_assumption_refs=(),
            refresh_required_predicate_refs=("inventory",),
            authorization_time_precondition_refs=("inventory",),
            invalidating_event_refs=(),
            open_side_effect_refs=(),
            fallback_on_instability="fallback:unique@1",
            opacity_debt_refs=(),
            validity_regime="runtime@1",
        )
        kernel.register_handoff_stability_contract(contract)
        return contract

    def test_kernel_exposes_reversible_compaction_api(self):
        kernel = self.make_kernel()
        self.assertTrue(hasattr(kernel, "compact_lineage"))
        self.assertTrue(hasattr(kernel, "reconstruct_compacted_lineage"))

    def test_compaction_cannot_change_mission_schema_world_or_environment_regime(self):
        kernel = self.make_kernel()
        before_mission = kernel.lineage.current("MissionRevision", "mission").revision_id
        before = {
            kind: kernel.lineage.current_regime(kind).revision_id
            for kind in (
                SemanticRegimeKind.SCHEMA,
                SemanticRegimeKind.WORLD_MODEL,
                SemanticRegimeKind.ENVIRONMENT,
            )
        }
        self.compact(kernel)
        self.assertEqual(kernel.lineage.current("MissionRevision", "mission").revision_id, before_mission)
        self.assertEqual(
            {kind: kernel.lineage.current_regime(kind).revision_id for kind in before},
            before,
        )

    def test_active_authority_lineage_cannot_be_destructively_discarded(self):
        kernel = self.make_kernel()
        auth, _, _ = self.seed_history(kernel)
        binding = kernel.authorization_lineage_bindings[auth.id]
        protected = {
            binding.mission_revision_id,
            binding.canonical_state_revision_id,
            binding.action_revision_id,
            *binding.grant_revision_ids,
            *(revision for _, revision in binding.regime_revisions),
        }
        result = self.compact(kernel)
        manifest = kernel.compaction_manifests[result.manifest_id]
        self.assertTrue(protected.issubset(set(manifest.active_authority_revision_ids)))
        regime_ids = {row.revision_id for row in kernel.lineage.all_regimes()}
        for revision_id in protected:
            if revision_id not in regime_ids:
                self.assertEqual(kernel.lineage.get(revision_id).revision_id, revision_id)

    def test_dormant_and_resurrection_refs_are_retained(self):
        kernel = self.make_kernel()
        branch = self.dormant_branch()
        result = self.compact(kernel, dormant_branches=(branch,))
        manifest = kernel.compaction_manifests[result.manifest_id]
        expected = {
            branch.revision_id,
            *branch.assumption_revision_refs,
            *branch.evidence_revision_refs,
            branch.transition_model_revision,
            branch.temporal_feasibility_revision,
            *branch.resource_revision_refs,
            *branch.capability_revision_refs,
            *branch.authority_revision_refs,
            *branch.resurrection_dependency_refs,
        }
        self.assertTrue(expected.issubset(set(manifest.dormant_resurrection_refs)))

    def test_proof_evidence_and_debt_refs_are_retained(self):
        kernel = self.make_kernel()
        self.seed_history(kernel)
        result = self.compact(kernel)
        refs = set(kernel.compaction_manifests[result.manifest_id].proof_evidence_debt_refs)
        self.assertIn("proof:root@1", refs)
        self.assertIn("evidence:verified", refs)
        self.assertIn("debt:verify@1", refs)

    def test_unique_fallback_cannot_be_dropped_merely_due_to_age(self):
        kernel = self.make_kernel()
        self.register_unique_fallback(kernel)
        result = self.compact(kernel)
        manifest = kernel.compaction_manifests[result.manifest_id]
        self.assertIn("fallback:unique@1", manifest.unique_fallback_refs)

    def test_archived_revision_ids_remain_immutable_and_cannot_be_reused(self):
        kernel = self.make_kernel()
        _, first, _ = self.seed_history(kernel)
        result = self.compact(kernel)
        archive = kernel.compaction_archives[result.manifest_id]
        tampered = CanonicalLineageRevision.create(
            object_family=first.object_family,
            logical_id=first.logical_id,
            revision_id=first.revision_id,
            schema_version=first.schema_version,
            created_sequence=first.created_sequence,
            created_at_wall_time=None,
            mission_revision_dependency=first.mission_revision_dependency,
            plan_revision=first.plan_revision,
            world_model_revision=first.world_model_revision,
            environment_regime_revision=first.environment_regime_revision,
            validity_regime=first.validity_regime,
            parent_revision_ids=first.parent_revision_ids,
            provenance_refs=first.provenance_refs,
            assurance_profile=first.assurance_profile,
            debt_refs=first.debt_refs,
            supersedes_revision_id=first.supersedes_revision_id,
            semantic_digest="tampered-semantic",
        )
        with self.assertRaises(Exception):
            archive.register_revision(tampered)

    def test_parent_dag_remains_acyclic_after_compaction_and_reconstruction(self):
        kernel = self.make_kernel()
        self.seed_history(kernel)
        result = self.compact(kernel)
        reconstructed = kernel.reconstruct_compacted_lineage(result.manifest_id)
        rows = {row.revision_id: row for row in reconstructed.all_revisions()}
        for start in rows:
            visiting: set[str] = set()
            visited: set[str] = set()

            def walk(revision_id: str) -> None:
                if revision_id in visiting:
                    self.fail(f"cycle detected from {start}: {revision_id}")
                if revision_id in visited:
                    return
                visiting.add(revision_id)
                row = rows.get(revision_id)
                if row is not None:
                    for parent in row.parent_revision_ids:
                        walk(parent)
                visiting.remove(revision_id)
                visited.add(revision_id)

            walk(start)

    def test_representation_only_compaction_preserves_canonical_semantic_digest(self):
        kernel = self.make_kernel()
        self.seed_history(kernel)
        before = canonical_semantic_digest(kernel)
        result = self.compact(kernel)
        self.assertEqual(result.source_canonical_semantic_digest, before)
        self.assertEqual(result.target_canonical_semantic_digest, before)
        self.assertEqual(canonical_semantic_digest(kernel), before)

    def test_reconstruction_from_active_and_archive_reproduces_source_digest(self):
        kernel = self.make_kernel()
        self.seed_history(kernel)
        before_root = kernel.lineage.semantic_root_digest()
        result = self.compact(kernel)
        reconstructed = kernel.reconstruct_compacted_lineage(result.manifest_id)
        self.assertEqual(reconstructed.semantic_root_digest(), before_root)
        self.assertEqual(
            {row.revision_id for row in reconstructed.all_revisions()},
            {row.revision_id for row in kernel.lineage.all_revisions()},
        )

    def test_compaction_manifest_is_deterministic_and_exact_sequence_bound(self):
        first = self.make_kernel()
        second = self.make_kernel()
        result_a = self.compact(first, "compaction:deterministic")
        result_b = self.compact(second, "compaction:deterministic")
        manifest_a = first.compaction_manifests[result_a.manifest_id]
        manifest_b = second.compaction_manifests[result_b.manifest_id]
        self.assertEqual(manifest_a.canonical_digest, manifest_b.canonical_digest)
        self.assertEqual(manifest_a.created_sequence, result_a.committed_sequence)
        self.assertEqual(result_a.committed_sequence, first.writer_sequence)

    def test_compaction_cannot_create_or_strengthen_action_authority(self):
        kernel = self.make_kernel()
        auth, _, _ = self.seed_history(kernel)
        before_ids = set(kernel.authorizations)
        before_binding = kernel.authorization_lineage_bindings[auth.id]
        self.compact(kernel)
        self.assertEqual(set(kernel.authorizations), before_ids)
        self.assertEqual(kernel.authorization_lineage_bindings[auth.id], before_binding)

    def test_compaction_snapshot_and_replay_are_atomic_and_never_expose_mixed_roots(self):
        root = Path(tempfile.mkdtemp())
        kernel = self.make_kernel(root)
        self.seed_history(kernel)
        before = canonical_semantic_digest(kernel)
        kernel.save_snapshot()
        result = self.compact(kernel, "compaction:suffix")
        reopened = PlanKernel.open(root)
        self.assertIn(result.manifest_id, reopened.compaction_manifests)
        self.assertEqual(canonical_semantic_digest(reopened), before)

        reopened.save_snapshot()
        reopened_again = PlanKernel.open(root)
        self.assertIn(result.manifest_id, reopened_again.compaction_manifests)
        self.assertEqual(
            reopened_again.reconstruct_compacted_lineage(result.manifest_id).semantic_root_digest(),
            reopened_again.lineage.semantic_root_digest(),
        )

        half_root = Path(tempfile.mkdtemp())
        half = self.make_kernel(half_root)
        half.save_snapshot()
        half.journal.append("compaction.representation_prepared", {"manifest_id": "half"})
        with self.assertRaises(ReplayError):
            PlanKernel.open(half_root)


if __name__ == "__main__":
    unittest.main()
