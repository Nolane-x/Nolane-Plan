from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from nolane_plan.actions import ActionIntent, AuthorityGrant
from nolane_plan.execution import AdapterProfile, TransactionState
from nolane_plan.kernel import PlanKernel
from nolane_plan.principals import InformationItem
from nolane_plan.types import RiskClass


class _AmbiguousAdapter:
    adapter_id = "payments"
    adapter_revision = 1

    def execute(self, action, principal_ref):
        raise TimeoutError("connection lost after dispatch")


class Wave2ReplayResumeTests(unittest.TestCase):
    def test_reopen_replays_post_snapshot_unknown_outcome_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            k = PlanKernel.create(root, "charge exactly once")
            k.register_principal("agent:p0", {"public"})
            item = InformationItem("proof", True, frozenset({"public"}))
            k.publish_information(item)
            k.observe_information("agent:p0", item.id, 0)
            action = ActionIntent(
                "charge", "charge", risk_class=RiskClass.CONSEQUENTIAL,
                idempotent=False, executor_sensitive=True,
            )
            k.propose_action(action)
            k.add_grant(AuthorityGrant("g", "agent:p0", frozenset({"charge"}), expires_at=100))
            k.register_adapter(AdapterProfile("payments", 1, True, True, 1.0))
            capsule = k.compile_capsule("agent:p0", 1, ("charge",))
            auth = k.authorize("charge", "agent:p0", ("g",), 1, capsule_id=capsule.id, adapter_id="payments")
            k.save_snapshot()

            with self.assertRaises(TimeoutError):
                k.dispatch(auth.id, "agent:p0", _AmbiguousAdapter(), 2)

            reopened = PlanKernel.open(root)
            tx = reopened.transaction_for_authorization(auth.id)
            self.assertEqual(tx.state, TransactionState.RECONCILIATION_REQUIRED)
            self.assertTrue(reopened.journal.verify())

            reopened.reconcile_action(auth.id, outcome_applied=True, state_patch={"charged": True}, trusted=True)
            self.assertTrue(reopened.canonical_state["charged"])
            self.assertEqual(reopened.transaction_for_authorization(auth.id).state, TransactionState.COMMITTED)

    def test_open_rejects_snapshot_not_bound_to_journal_prefix(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            k = PlanKernel.create(root, "x")
            k.save_snapshot()
            doc = root.joinpath("snapshot.json").read_text(encoding="utf-8")
            # Valid JSON but a semantic digest mismatch must never be ignored.
            root.joinpath("snapshot.json").write_text(doc.replace('"canonical_version": 1', '"canonical_version": 9'), encoding="utf-8")
            with self.assertRaises(Exception):
                PlanKernel.open(root)


if __name__ == "__main__":
    unittest.main()
