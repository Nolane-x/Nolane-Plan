from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from nolane_plan import PlanKernel
from nolane_plan.actions import ActionIntent, AuthorityGrant
from nolane_plan.execution import AdapterProfile
from nolane_plan.hashing import digest
from nolane_plan.lineage import SemanticRegimeKind
from nolane_plan.migration import FieldMigrationDisposition, MigrationDisposition, MigrationManifest
from nolane_plan.schedulability_recovery import SCHEDULABILITY_SNAPSHOT_SCHEMA
from nolane_plan.types import AuthorizationError, ReplayError


V7_SNAPSHOT_SCHEMA = "nolane-plan-runtime-snapshot-v7"


class SuccessfulAdapter:
    def execute(self, action, principal_ref):
        return {
            "ok": True,
            "postconditions_verified": True,
            "executing_principal_ref": principal_ref,
            "state_patch": {"done": True},
        }


class Wave7SnapshotTests(unittest.TestCase):
    def make_kernel(self) -> PlanKernel:
        root = Path(tempfile.mkdtemp())
        return PlanKernel.create(root, "ship", ("done",), ("preserve rollback",))

    def make_manifest(self) -> MigrationManifest:
        return MigrationManifest.create(
            manifest_id="migration:v7-to-v7b",
            source_schema_revision="schema:nolane-plan:v7",
            target_schema_revision="schema:nolane-plan:v7b",
            target_schema_semantic_digest="schema-v7b-semantic",
            changed_correctness_fields=(("PolicyNodeRevision", "guard_semantics"),),
            field_dispositions=(
                FieldMigrationDisposition(
                    "PolicyNodeRevision",
                    "guard_semantics",
                    MigrationDisposition.INVALIDATED_REQUIRES_RECHECK,
                ),
            ),
            identity_mappings=(),
            checked_invariants=("principal_scope", "no_authority_promotion"),
            revoked_certificate_refs=("seal:old",),
            revoked_authorization_refs=(),
            new_debt_refs=("debt:migration-review",),
            replay_fixture_digests=("fixture:abc",),
            rollback_procedure_ref="rollback:restore-v7-root",
            backup_ref="backup:v7",
            unsupported_legacy_cases=("schema:v3-opaque",),
            external_effect_history_refs=("receipt:external-1",),
            provenance_refs=("migration:test",),
        )

    def add_authority(self, kernel: PlanKernel):
        kernel.propose_action(ActionIntent("deploy", "deploy"))
        kernel.add_grant(AuthorityGrant("g", "agent:a", frozenset({"deploy"})))
        return kernel.authorize("deploy", "agent:a", ("g",), 1)

    def write_v6_snapshot(self, kernel: PlanKernel) -> dict:
        state = dict(kernel.snapshot_state())
        state["snapshot_schema"] = SCHEDULABILITY_SNAPSHOT_SCHEMA
        state.pop("lineage", None)
        kernel.snapshots.save(state)
        return state

    def test_v7_snapshot_persists_lineage_regimes_migration_compaction_and_replay_registry(self):
        kernel = self.make_kernel()
        auth = self.add_authority(kernel)
        kernel.apply_semantic_migration(self.make_manifest(), now=2)
        expected_root = kernel.lineage.semantic_root_digest()

        state = kernel.save_snapshot()

        self.assertEqual(state["snapshot_schema"], V7_SNAPSHOT_SCHEMA)
        wave7 = state["lineage"]
        self.assertTrue(wave7["revisions"])
        self.assertTrue(wave7["regimes"])
        self.assertIn("migration:v7-to-v7b", wave7["migration"]["manifests"])
        self.assertIn(auth.id, wave7["migration"]["recheck_required_authorizations"])
        self.assertIn("manifests", wave7["compaction"])
        self.assertIn("archive", wave7["compaction"])
        self.assertTrue(wave7["replay_registry"]["specs"])
        self.assertTrue(wave7["replay_registry"]["canonical_digest"])
        self.assertEqual(wave7["semantic_root_digest"], expected_root)

    def test_v7_restore_verifies_migration_manifest_digest(self):
        kernel = self.make_kernel()
        kernel.apply_semantic_migration(self.make_manifest(), now=2)
        state = kernel.save_snapshot()
        manifest = state["lineage"]["migration"]["manifests"]["migration:v7-to-v7b"]
        manifest["target_schema_semantic_digest"] = "tampered"
        kernel.snapshots.save(state)

        with self.assertRaises(ReplayError):
            PlanKernel.open(kernel.root)

    def test_v6_snapshot_imports_current_objects_deterministically(self):
        kernel = self.make_kernel()
        kernel.propose_action(ActionIntent("deploy", "deploy"))
        kernel.add_grant(AuthorityGrant("g", "agent:a", frozenset({"deploy"})))
        kernel.register_adapter(AdapterProfile("adapter:deploy", 1, True, True, 0.95))
        self.write_v6_snapshot(kernel)

        restored = PlanKernel.open(kernel.root)

        self.assertEqual(restored.actions["deploy"], kernel.actions["deploy"])
        self.assertEqual(restored.grants["g"], kernel.grants["g"])
        self.assertEqual(restored.adapters["adapter:deploy"], kernel.adapters["adapter:deploy"])
        self.assertEqual(restored.lineage.current("ActionIntent", "deploy").logical_id, "deploy")
        self.assertEqual(restored.lineage.current("AuthorityGrant", "g").logical_id, "g")
        self.assertEqual(restored.lineage.current("AdapterProfile", "adapter:deploy").logical_id, "adapter:deploy")

    def test_v6_import_does_not_invent_historical_parents(self):
        kernel = self.make_kernel()
        kernel.propose_action(ActionIntent("deploy", "deploy"))
        kernel.add_grant(AuthorityGrant("g", "agent:a", frozenset({"deploy"})))
        self.write_v6_snapshot(kernel)

        restored = PlanKernel.open(kernel.root)
        action_root = restored.lineage.current("ActionIntent", "deploy")
        grant_root = restored.lineage.current("AuthorityGrant", "g")

        self.assertEqual(action_root.parent_revision_ids, ())
        self.assertIsNone(action_root.supersedes_revision_id)
        self.assertEqual(grant_root.parent_revision_ids, ())
        self.assertIsNone(grant_root.supersedes_revision_id)
        self.assertIn("snapshot-v6-import", action_root.provenance_refs)
        self.assertIn("snapshot-v6-import", grant_root.provenance_refs)

    def test_v6_authority_is_recheck_required_when_exact_lineage_is_unavailable(self):
        kernel = self.make_kernel()
        auth = self.add_authority(kernel)
        self.write_v6_snapshot(kernel)

        restored = PlanKernel.open(kernel.root)

        self.assertIn(auth.id, restored.migration_recheck_required_authorizations)
        with self.assertRaises(AuthorizationError):
            restored.dispatch(auth.id, "agent:a", SuccessfulAdapter(), 2)

    def test_v7_snapshot_preserves_historical_receipts_as_immutable_queryable_records(self):
        kernel = self.make_kernel()
        auth = self.add_authority(kernel)
        receipt = kernel.dispatch(auth.id, "agent:a", SuccessfulAdapter(), 2)
        kernel.save_snapshot()

        restored = PlanKernel.open(kernel.root)

        self.assertIn(receipt.id, restored.receipts)
        self.assertEqual(restored.receipts[receipt.id], receipt)
        with self.assertRaises(Exception):
            restored.receipts[receipt.id].transport_ok = False

    def test_corrupt_lineage_record_fails_closed_even_with_recomputed_outer_digest(self):
        kernel = self.make_kernel()
        kernel.propose_action(ActionIntent("deploy", "deploy"))
        state = kernel.save_snapshot()
        rows = state["lineage"]["revisions"]
        action_row = next(row for row in rows if row["object_family"] == "ActionIntent")
        action_row["semantic_digest"] = digest({"tampered": True})
        kernel.snapshots.save(state)

        with self.assertRaises(ReplayError):
            PlanKernel.open(kernel.root)

    def test_stale_regime_after_restart_does_not_resurrect_old_authorization(self):
        kernel = self.make_kernel()
        auth = self.add_authority(kernel)
        kernel.revise_semantic_regime(
            SemanticRegimeKind.ENVIRONMENT,
            semantic_digest="environment:changed",
            provenance_refs=("test:environment-change",),
        )
        kernel.save_snapshot()

        restored = PlanKernel.open(kernel.root)

        self.assertIn(auth.id, restored.authorization_lineage_bindings)
        with self.assertRaises(AuthorizationError):
            restored.dispatch(auth.id, "agent:a", SuccessfulAdapter(), 2)

    def test_current_logical_pointers_remain_distinct_from_immutable_history(self):
        kernel = self.make_kernel()
        kernel.register_adapter(AdapterProfile("adapter:deploy", 1, True, True, 0.8))
        first = kernel.lineage.current("AdapterProfile", "adapter:deploy")
        kernel.register_adapter(AdapterProfile("adapter:deploy", 2, True, True, 0.95))
        second = kernel.lineage.current("AdapterProfile", "adapter:deploy")
        kernel.save_snapshot()

        restored = PlanKernel.open(kernel.root)
        current = restored.lineage.current("AdapterProfile", "adapter:deploy")
        historical = {
            row.revision_id: row
            for row in restored.lineage.all_revisions()
            if row.object_family == "AdapterProfile" and row.logical_id == "adapter:deploy"
        }

        self.assertNotEqual(first.revision_id, second.revision_id)
        self.assertEqual(current.revision_id, second.revision_id)
        self.assertIn(first.revision_id, historical)
        self.assertIn(second.revision_id, historical)
        self.assertEqual(historical[first.revision_id], first)

    def test_repeated_identical_v6_import_yields_identical_semantic_root(self):
        kernel = self.make_kernel()
        kernel.propose_action(ActionIntent("deploy", "deploy"))
        kernel.add_grant(AuthorityGrant("g", "agent:a", frozenset({"deploy"})))
        self.write_v6_snapshot(kernel)

        first = PlanKernel.open(kernel.root)
        second = PlanKernel.open(kernel.root)

        self.assertEqual(first.lineage.semantic_root_digest(), second.lineage.semantic_root_digest())
        self.assertEqual(
            first.lineage.current("ActionIntent", "deploy").revision_id,
            second.lineage.current("ActionIntent", "deploy").revision_id,
        )


if __name__ == "__main__":
    unittest.main()
