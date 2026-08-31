from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from nolane_plan import PlanKernel
from nolane_plan.lineage_snapshot import LINEAGE_SNAPSHOT_SCHEMA
from nolane_plan.policy_recovery import POLICY_SNAPSHOT_SCHEMA
from nolane_plan.proof_recovery import PROOF_SNAPSHOT_SCHEMA
from nolane_plan.resume import SNAPSHOT_SCHEMA as BASE_SNAPSHOT_SCHEMA
from nolane_plan.schedulability_recovery import SCHEDULABILITY_SNAPSHOT_SCHEMA
from nolane_plan.trust_recovery import TRUST_SNAPSHOT_SCHEMA
from nolane_plan.wave8_migration_matrix import (
    SUPPORTED_MIGRATION_EDGES,
    fixture_digest,
    load_fixture,
    materialize_historical_snapshot,
)


EXPECTED_SOURCES = (
    BASE_SNAPSHOT_SCHEMA,
    TRUST_SNAPSHOT_SCHEMA,
    PROOF_SNAPSHOT_SCHEMA,
    POLICY_SNAPSHOT_SCHEMA,
    SCHEDULABILITY_SNAPSHOT_SCHEMA,
)


class Wave8MigrationMatrixTests(unittest.TestCase):
    def test_matrix_freezes_exact_repository_owned_v2_through_v6_edges_to_v7(self):
        self.assertEqual(5, len(SUPPORTED_MIGRATION_EDGES))
        self.assertEqual(EXPECTED_SOURCES, tuple(edge.source_schema for edge in SUPPORTED_MIGRATION_EDGES))
        self.assertEqual(
            (LINEAGE_SNAPSHOT_SCHEMA,) * 5,
            tuple(edge.target_schema for edge in SUPPORTED_MIGRATION_EDGES),
        )
        self.assertEqual(5, len({edge.fixture_ref for edge in SUPPORTED_MIGRATION_EDGES}))
        self.assertEqual(5, len({edge.source_schema for edge in SUPPORTED_MIGRATION_EDGES}))

    def test_checked_in_fixture_recipes_have_stable_digest_and_exact_schema_binding(self):
        for edge in SUPPORTED_MIGRATION_EDGES:
            with self.subTest(source=edge.source_schema):
                first = load_fixture(edge)
                second = load_fixture(edge)
                self.assertEqual(first, second)
                self.assertEqual(edge.source_schema, first["source_schema"])
                self.assertEqual(edge.target_schema, first["target_schema"])
                self.assertEqual(fixture_digest(edge), fixture_digest(edge))
                self.assertEqual(first["fixture_digest"], fixture_digest(edge))
                self.assertTrue(first["drop_layers"] or edge.source_schema == SCHEDULABILITY_SNAPSHOT_SCHEMA)

    def test_materialized_historical_snapshots_open_deterministically_and_never_invent_newer_layers(self):
        for edge in SUPPORTED_MIGRATION_EDGES:
            with self.subTest(source=edge.source_schema):
                root = Path(tempfile.mkdtemp())
                kernel = PlanKernel.create(root, f"migration matrix {edge.source_schema}")
                state = materialize_historical_snapshot(kernel, edge)
                self.assertEqual(edge.source_schema, state["snapshot_schema"])

                first = PlanKernel.open(root)
                second = PlanKernel.open(root)
                self.assertEqual(first.lineage.semantic_root_digest(), second.lineage.semantic_root_digest())
                self.assertEqual(first.mission.current, second.mission.current)

                fixture = load_fixture(edge)
                for registry_name in fixture["must_restore_empty"]:
                    self.assertEqual({}, getattr(first, registry_name))

    def test_every_edge_declares_explicit_conservative_dispositions_and_unsupported_cases(self):
        allowed = {
            "PRESERVED_EXACTLY",
            "RECOMPUTED_FROM_CANONICAL_INPUTS",
            "INVALIDATED_REQUIRES_RECHECK",
            "ESCALATED_TO_DEBT",
            "ARCHIVED_READ_ONLY",
            "UNSUPPORTED_FAIL_CLOSED",
        }
        for edge in SUPPORTED_MIGRATION_EDGES:
            with self.subTest(source=edge.source_schema):
                self.assertTrue(edge.expected_dispositions)
                self.assertTrue(set(edge.expected_dispositions).issubset(allowed))
                self.assertTrue(edge.unsupported_cases)

    def test_v6_authority_is_never_promoted_when_exact_v7_lineage_is_unavailable(self):
        edge = next(
            edge for edge in SUPPORTED_MIGRATION_EDGES
            if edge.source_schema == SCHEDULABILITY_SNAPSHOT_SCHEMA
        )
        root = Path(tempfile.mkdtemp())
        kernel = PlanKernel.create(root, "legacy authority")
        from nolane_plan.actions import ActionIntent, AuthorityGrant

        kernel.propose_action(ActionIntent("deploy", "deploy"))
        kernel.add_grant(AuthorityGrant("grant", "agent:a", frozenset({"deploy"})))
        authorization = kernel.authorize("deploy", "agent:a", ("grant",), 1)
        materialize_historical_snapshot(kernel, edge)

        restored = PlanKernel.open(root)
        self.assertIn(authorization.id, restored.migration_recheck_required_authorizations)
        self.assertNotIn(authorization.id, restored.authorization_lineage_bindings)

    def test_unknown_historical_schema_is_not_silently_added_to_supported_matrix(self):
        sources = {edge.source_schema for edge in SUPPORTED_MIGRATION_EDGES}
        self.assertNotIn("nolane-plan-runtime-snapshot-v1", sources)
        self.assertNotIn("nolane-plan-runtime-snapshot-v8", sources)


if __name__ == "__main__":
    unittest.main()
