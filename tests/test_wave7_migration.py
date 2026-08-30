from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from nolane_plan import PlanKernel
from nolane_plan.actions import ActionIntent, AuthorityGrant
from nolane_plan.execution import TransactionState
from nolane_plan.lineage import SemanticRegimeKind
from nolane_plan.lineage_recovery import canonical_semantic_digest
from nolane_plan.migration import (
    FieldMigrationDisposition,
    IdentityMapping,
    MigrationBridgeEvidence,
    MigrationDisposition,
    MigrationError,
    MigrationManifest,
)


class Wave7MigrationTests(unittest.TestCase):
    def make_manifest(self, **overrides):
        defaults = dict(
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
        defaults.update(overrides)
        return MigrationManifest.create(**defaults)

    def test_disposition_vocabulary_is_exact(self):
        self.assertEqual(
            {item.value for item in MigrationDisposition},
            {
                "PRESERVED_EXACTLY",
                "RECOMPUTED_FROM_CANONICAL_INPUTS",
                "INVALIDATED_REQUIRES_RECHECK",
                "ESCALATED_TO_DEBT",
                "ARCHIVED_READ_ONLY",
                "UNSUPPORTED_FAIL_CLOSED",
            },
        )

    def test_changed_correctness_field_without_disposition_fails_closed(self):
        with self.assertRaises(MigrationError):
            self.make_manifest(
                changed_correctness_fields=(
                    ("PolicyNodeRevision", "guard_semantics"),
                    ("PlanSeal", "validity_regime"),
                )
            )

    def test_silent_none_or_empty_default_does_not_cover_missing_field(self):
        with self.assertRaises(MigrationError):
            MigrationManifest.create(
                manifest_id="m",
                source_schema_revision="schema:a",
                target_schema_revision="schema:b",
                target_schema_semantic_digest="schema-b",
                changed_correctness_fields=(("X", "critical"),),
                field_dispositions=(),
                identity_mappings=(),
                checked_invariants=(),
                revoked_certificate_refs=(),
                revoked_authorization_refs=(),
                new_debt_refs=(),
                replay_fixture_digests=(),
                rollback_procedure_ref="rollback:x",
                backup_ref="backup:x",
                unsupported_legacy_cases=(),
                external_effect_history_refs=(),
                provenance_refs=(),
            )

    def test_identity_change_requires_explicit_identity_mapping(self):
        disposition = FieldMigrationDisposition(
            "PolicyNodeRevision",
            "logical_id",
            MigrationDisposition.PRESERVED_EXACTLY,
        )
        with self.assertRaises(MigrationError):
            self.make_manifest(
                changed_correctness_fields=(("PolicyNodeRevision", "logical_id"),),
                field_dispositions=(disposition,),
            )
        manifest = self.make_manifest(
            changed_correctness_fields=(("PolicyNodeRevision", "logical_id"),),
            field_dispositions=(disposition,),
            identity_mappings=(
                IdentityMapping(
                    "PolicyNodeRevision",
                    "policy:old",
                    "policy:new",
                    "policy:old:r1",
                    "policy:new:r1",
                ),
            ),
        )
        self.assertEqual(len(manifest.identity_mappings), 1)

    def test_escalated_debt_requires_explicit_debt_ref(self):
        with self.assertRaises(MigrationError):
            self.make_manifest(
                field_dispositions=(
                    FieldMigrationDisposition(
                        "PolicyNodeRevision",
                        "guard_semantics",
                        MigrationDisposition.ESCALATED_TO_DEBT,
                    ),
                )
            )
        manifest = self.make_manifest(
            field_dispositions=(
                FieldMigrationDisposition(
                    "PolicyNodeRevision",
                    "guard_semantics",
                    MigrationDisposition.ESCALATED_TO_DEBT,
                    debt_ref="debt:guard-recheck",
                ),
            ),
            new_debt_refs=("debt:guard-recheck",),
        )
        self.assertIn("debt:guard-recheck", manifest.new_debt_refs)

    def test_source_and_target_schema_must_differ(self):
        with self.assertRaises(MigrationError):
            self.make_manifest(target_schema_revision="schema:nolane-plan:v7")

    def test_manifest_digest_is_order_stable_for_set_like_contracts(self):
        a = self.make_manifest(
            checked_invariants=("z", "a"),
            new_debt_refs=("debt:z", "debt:a"),
            unsupported_legacy_cases=("legacy:z", "legacy:a"),
        )
        b = self.make_manifest(
            checked_invariants=("a", "z"),
            new_debt_refs=("debt:a", "debt:z"),
            unsupported_legacy_cases=("legacy:a", "legacy:z"),
        )
        self.assertEqual(a.canonical_digest, b.canonical_digest)

    def test_unsupported_legacy_case_is_explicit_fail_closed(self):
        manifest = self.make_manifest(unsupported_legacy_cases=("schema:v3-opaque",))
        self.assertFalse(manifest.supports_legacy_case("schema:v3-opaque"))
        self.assertTrue(manifest.supports_legacy_case("schema:v6"))

    def test_kernel_migration_switches_schema_and_invalidates_existing_authority(self):
        root = Path(tempfile.mkdtemp())
        kernel = PlanKernel.create(root, "ship", ("done",))
        kernel.propose_action(ActionIntent("deploy", "deploy"))
        kernel.add_grant(AuthorityGrant("g", "agent:a", frozenset({"deploy"})))
        auth = kernel.authorize("deploy", "agent:a", ("g",), 1)
        old_schema = kernel.lineage.current_regime(SemanticRegimeKind.SCHEMA).revision_id

        result = kernel.apply_semantic_migration(self.make_manifest(), now=2)
        self.assertEqual(result.source_schema_revision, old_schema)
        self.assertEqual(
            kernel.lineage.current_regime(SemanticRegimeKind.SCHEMA).revision_id,
            "schema:nolane-plan:v7b",
        )
        self.assertIn(auth.id, result.invalidated_authorization_ids)
        self.assertIn(auth.id, kernel.migration_recheck_required_authorizations)
        self.assertFalse(hasattr(result, "authorization_id"))

    def test_post_snapshot_migration_replays_exact_target_revision_and_digest(self):
        root = Path(tempfile.mkdtemp())
        kernel = PlanKernel.create(root, "ship", ("done",))
        kernel.save_snapshot()
        manifest = self.make_manifest()
        result = kernel.apply_semantic_migration(manifest, now=2)
        live_digest = canonical_semantic_digest(kernel)

        reopened = PlanKernel.open(root)

        self.assertEqual(result.target_schema_revision, manifest.target_schema_revision)
        self.assertEqual(
            reopened.lineage.current_regime(SemanticRegimeKind.SCHEMA).revision_id,
            manifest.target_schema_revision,
        )
        self.assertEqual(canonical_semantic_digest(reopened), live_digest)
        self.assertEqual(
            reopened.migration_history[-1].target_schema_revision,
            manifest.target_schema_revision,
        )

    def test_migration_refuses_ambiguous_external_action_without_verified_bridge(self):
        root = Path(tempfile.mkdtemp())
        kernel = PlanKernel.create(root, "ship", ("done",))
        kernel.propose_action(ActionIntent("deploy", "deploy", idempotent=False))
        kernel.add_grant(AuthorityGrant("g", "agent:a", frozenset({"deploy"})))
        auth = kernel.authorize("deploy", "agent:a", ("g",), 1)
        tx = kernel.transaction_for_authorization(auth.id)
        kernel.transactions.record_dispatch(tx.id, "adapter:x", 1)
        self.assertEqual(kernel.transactions.get(tx.id).state, TransactionState.DISPATCH_RECORDED)

        with self.assertRaises(MigrationError):
            kernel.apply_semantic_migration(self.make_manifest(), now=2)

        bridge = MigrationBridgeEvidence.create(
            evidence_ref="bridge:verified",
            source_schema_revision="schema:nolane-plan:v7",
            target_schema_revision="schema:nolane-plan:v7b",
            transaction_ids=(tx.id,),
            verified=True,
        )
        result = kernel.apply_semantic_migration(self.make_manifest(), now=2, bridge=bridge)
        self.assertEqual(result.target_schema_revision, "schema:nolane-plan:v7b")

    def test_migration_retains_external_effect_history_and_rollback_metadata(self):
        manifest = self.make_manifest(
            external_effect_history_refs=("receipt:b", "receipt:a"),
            rollback_procedure_ref="rollback:root-only-not-world",
            backup_ref="backup:pre-migration",
        )
        self.assertEqual(manifest.external_effect_history_refs, ("receipt:a", "receipt:b"))
        self.assertEqual(manifest.rollback_procedure_ref, "rollback:root-only-not-world")
        self.assertEqual(manifest.backup_ref, "backup:pre-migration")


if __name__ == "__main__":
    unittest.main()
