from __future__ import annotations

import unittest

from nolane_plan.communication import CommunicationError, CommunicationLedger, CommunicationState


class Wave3CommunicationTests(unittest.TestCase):
    def _sent(self, ledger: CommunicationLedger, *, receipt_id: str = "msg-1", valid_until: float | None = 100):
        return ledger.sent(
            receipt_id=receipt_id,
            source_principal_ref="agent:a",
            recipient_principal_ref="agent:b",
            semantic_payload_refs=("info:test-result",),
            sent_at=10,
            valid_until=valid_until,
            access_condition="recipient-authorized",
            provenance="host-channel",
        )

    def test_sent_message_is_not_decision_usable_information(self):
        ledger = CommunicationLedger()
        receipt = self._sent(ledger)
        self.assertEqual(receipt.state, CommunicationState.SENT)
        self.assertFalse(ledger.decision_usable(receipt.id, "agent:b", decision_time=20))

    def test_delivery_without_observation_is_not_yet_recipient_knowledge(self):
        ledger = CommunicationLedger()
        receipt = self._sent(ledger)
        delivered = ledger.delivered(receipt.id, delivered_at=20, evidence_ref="provider:delivery-1")
        self.assertEqual(delivered.state, CommunicationState.DELIVERED)
        self.assertFalse(ledger.decision_usable(receipt.id, "agent:b", decision_time=25))

    def test_observation_is_recipient_bound_and_not_retroactive(self):
        ledger = CommunicationLedger()
        receipt = self._sent(ledger)
        ledger.delivered(receipt.id, delivered_at=20, evidence_ref="provider:delivery-1")
        observed = ledger.observed(receipt.id, observed_at=30, evidence_ref="host:observe-1")

        self.assertEqual(observed.state, CommunicationState.OBSERVED)
        self.assertFalse(ledger.decision_usable(receipt.id, "agent:b", decision_time=29))
        self.assertTrue(ledger.decision_usable(receipt.id, "agent:b", decision_time=30))
        self.assertFalse(ledger.decision_usable(receipt.id, "agent:a", decision_time=30))
        self.assertFalse(ledger.decision_usable(receipt.id, "agent:c", decision_time=30))

    def test_observe_before_delivery_fails_closed(self):
        ledger = CommunicationLedger()
        receipt = self._sent(ledger)
        with self.assertRaises(CommunicationError):
            ledger.observed(receipt.id, observed_at=20, evidence_ref="host:observe-early")

    def test_expired_transfer_is_not_decision_usable(self):
        ledger = CommunicationLedger()
        receipt = self._sent(ledger, valid_until=25)
        ledger.delivered(receipt.id, delivered_at=20, evidence_ref="provider:delivery-1")
        ledger.observed(receipt.id, observed_at=21, evidence_ref="host:observe-1")
        self.assertTrue(ledger.decision_usable(receipt.id, "agent:b", decision_time=24))
        self.assertFalse(ledger.decision_usable(receipt.id, "agent:b", decision_time=26))

    def test_delivery_timestamps_must_be_monotonic(self):
        ledger = CommunicationLedger()
        receipt = self._sent(ledger)
        with self.assertRaises(CommunicationError):
            ledger.delivered(receipt.id, delivered_at=9, evidence_ref="provider:impossible")

        ledger.delivered(receipt.id, delivered_at=20, evidence_ref="provider:delivery-1")
        with self.assertRaises(CommunicationError):
            ledger.observed(receipt.id, observed_at=19, evidence_ref="host:impossible")


if __name__ == "__main__":
    unittest.main()
