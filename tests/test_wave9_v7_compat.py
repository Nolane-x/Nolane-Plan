from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from nolane_plan import PlanKernel
from nolane_plan.actions import ActionIntent, AuthorityGrant
from nolane_plan.lineage_snapshot import LINEAGE_SNAPSHOT_SCHEMA
from nolane_plan.lineage_recovery import canonical_semantic_digest


class Wave9V7CompatibilityTests(unittest.TestCase):
    def test_explicit_v7_snapshot_remains_readable_without_inventing_wave9_authority(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            path = Path(root)
            kernel = PlanKernel.create(path, "v7 compatibility under Wave 9")
            kernel.propose_action(ActionIntent("deploy", "deploy"))
            kernel.add_grant(AuthorityGrant("grant", "agent", frozenset({"deploy"})))
            authorization = kernel.authorize("deploy", "agent", ("grant",), 1)
            expected_semantic = canonical_semantic_digest(kernel)

            current = kernel.snapshot_state()
            self.assertEqual(current["snapshot_schema"], "nolane-plan-runtime-snapshot-v9")
            legacy = dict(current)
            legacy["snapshot_schema"] = LINEAGE_SNAPSHOT_SCHEMA
            legacy.pop("wave9", None)
            kernel.snapshots.save(legacy)

            restored = PlanKernel.open(path)
            self.assertEqual(canonical_semantic_digest(restored), expected_semantic)
            self.assertIn(authorization.id, restored.authorizations)
            self.assertEqual(restored.execution_contracts, {})
            self.assertEqual(restored.authorization_execution_contract_bindings, {})
            self.assertEqual(restored.observed_authority_epochs, {})
            self.assertEqual(restored.authorization_authority_epoch_bindings, {})
            self.assertEqual(restored.destructive_compaction_observations, {})


if __name__ == "__main__":
    unittest.main()
