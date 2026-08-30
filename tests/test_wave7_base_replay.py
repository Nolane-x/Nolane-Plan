from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from nolane_plan import PlanKernel
from nolane_plan.actions import ActionIntent, AuthorityGrant
from nolane_plan.evidence import EvidencePolarity, EvidenceRecord
from nolane_plan.execution import AdapterProfile, TransactionState
from nolane_plan.future import FutureFamily
from nolane_plan.lineage import SemanticRegimeKind
from nolane_plan.lineage_recovery import canonical_semantic_digest
from nolane_plan.obligations import StrategicObligation
from nolane_plan.principals import InformationItem
from nolane_plan.relocation import CandidateRegion
from nolane_plan.resources import SharedCommitment
from nolane_plan.types import ReplayError, RiskClass


class Wave7BaseReplayTests(unittest.TestCase):
    def test_post_snapshot_base_mutations_replay_to_same_semantic_digest(self):
        root = Path(tempfile.mkdtemp())
        kernel = PlanKernel.create(root, "ship", ("done",), ("preserve rollback",))
        kernel.save_snapshot()

        kernel.register_principal("agent:a", {"public"})
        kernel.update_principal_access("agent:a", {"public", "ops"})
        kernel.publish_information(
            InformationItem(
                "build:verified",
                {"sha": "abc123", "verified": True},
                frozenset({"ops"}),
                visible_at=1,
                valid_until=50,
                provenance="ci:run",
                assurance=0.97,
            )
        )
        kernel.observe_information("agent:a", "build:verified", 2)
        kernel.add_evidence(
            EvidenceRecord(
                "e:build",
                "build verified",
                EvidencePolarity.SUPPORTS,
                "ci",
                "ci:independent-root",
                2,
                valid_until=50,
                assurance=0.96,
            )
        )
        kernel.add_future_family(
            FutureFamily(
                "future:api-up",
                "api available",
                probability=0.7,
                support=0.8,
                assumptions=("network-stable",),
                impact=3.0,
            )
        )
        kernel.add_obligation(
            StrategicObligation(
                "obligation:rollback",
                "rollback remains available",
                deadline=40,
                required_capability="git",
                hard=True,
                lineage=("mission:ship",),
            )
        )
        kernel.propose_action(
            ActionIntent(
                "action:deploy",
                "deploy",
                risk_class=RiskClass.CONSEQUENTIAL,
                parameters=(("target", "staging"),),
                preconditions=("build verified",),
                required_capabilities=("deploy",),
                idempotent=True,
                executor_sensitive=False,
            )
        )
        kernel.add_grant(
            AuthorityGrant(
                "grant:deploy",
                "agent:a",
                frozenset({"deploy"}),
                expires_at=30,
                risk_classes=frozenset({RiskClass.CONSEQUENTIAL}),
            )
        )
        kernel.register_adapter(AdapterProfile("adapter:deploy", 1, True, True, 0.95))
        kernel.register_region(CandidateRegion("region:ready", {"done": False}, "deploy"))
        kernel.reserve(SharedCommitment("repo:main", "agent:a", 0, 10, exclusive=True))
        auth = kernel.authorize(
            "action:deploy",
            "agent:a",
            ("grant:deploy",),
            3,
            adapter_id="adapter:deploy",
        )
        kernel.report_model_class_anomaly("unexpected provider regime", 0.35)
        kernel.revise_semantic_regime(
            SemanticRegimeKind.ENVIRONMENT,
            semantic_digest="environment:test:r2",
            provenance_refs=("test:environment-change",),
        )
        kernel.revise_mission(objective="ship safely")

        expected_digest = canonical_semantic_digest(kernel)
        restored = PlanKernel.open(root)

        self.assertEqual(canonical_semantic_digest(restored), expected_digest)
        self.assertEqual(restored.mission.current.objective, "ship safely")
        self.assertEqual(restored.principals.profile("agent:a").revision, 2)
        self.assertEqual(restored.information_items["build:verified"].assurance, 0.97)
        self.assertEqual(restored.evidence.records["e:build"].lineage_root, "ci:independent-root")
        self.assertEqual(restored.future.families["future:api-up"].impact, 3.0)
        self.assertEqual(restored.obligations._items["obligation:rollback"].required_capability, "git")
        self.assertEqual(restored.actions["action:deploy"].parameters, (("target", "staging"),))
        self.assertEqual(restored.grants["grant:deploy"].risk_classes, frozenset({RiskClass.CONSEQUENTIAL}))
        self.assertEqual(restored.adapters["adapter:deploy"].capability_digest, kernel.adapters["adapter:deploy"].capability_digest)
        self.assertEqual(restored.regions[0].decision_signature, "deploy")
        self.assertEqual(restored.reservations.commitments, kernel.reservations.commitments)
        self.assertIn(auth.id, restored.authorizations)
        self.assertEqual(restored.transaction_for_authorization(auth.id).state, TransactionState.AUTHORIZED)
        self.assertEqual(
            restored.lineage.current_regime(SemanticRegimeKind.ENVIRONMENT).semantic_digest,
            "environment:test:r2",
        )

    def test_unknown_correctness_event_in_suffix_fails_closed(self):
        root = Path(tempfile.mkdtemp())
        kernel = PlanKernel.create(root, "ship")
        kernel.save_snapshot()
        kernel.journal.append("wave7.unknown_correctness_event", {"critical": True})
        with self.assertRaises(ReplayError):
            PlanKernel.open(root)

    def test_replay_order_is_sequence_driven_not_payload_time(self):
        root = Path(tempfile.mkdtemp())
        kernel = PlanKernel.create(root, "first")
        kernel.save_snapshot()
        kernel.revise_mission(objective="second")
        kernel.revise_mission(objective="third")
        restored = PlanKernel.open(root)
        self.assertEqual(restored.mission.current.objective, "third")
        self.assertEqual(restored.mission.current.version, kernel.mission.current.version)


if __name__ == "__main__":
    unittest.main()
