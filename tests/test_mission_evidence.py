import unittest

from nolane_plan.evidence import EvidenceLedger, EvidencePolarity, EvidenceRecord
from nolane_plan.mission import MissionLedger


class MissionEvidenceTests(unittest.TestCase):
    def test_mission_revision_increments_version_and_preserves_history(self):
        ledger = MissionLedger.create("ship artifact", success_conditions=("launches",), hard_constraints=("no secret leak",))
        old = ledger.current
        new = ledger.revise(objective="ship verified artifact")
        self.assertEqual(new.version, old.version + 1)
        self.assertEqual(ledger.history[0].objective, "ship artifact")

    def test_evidence_independence_groups_common_lineage(self):
        ledger = EvidenceLedger()
        ledger.add(EvidenceRecord("e1", "build-ok", EvidencePolarity.SUPPORTS, "tool-a", "root-x", 1, assurance=0.9))
        ledger.add(EvidenceRecord("e2", "build-ok", EvidencePolarity.SUPPORTS, "tool-b", "root-x", 2, assurance=0.9))
        ledger.add(EvidenceRecord("e3", "build-ok", EvidencePolarity.SUPPORTS, "tool-c", "root-y", 3, assurance=0.9))
        self.assertEqual(ledger.independent_support_count("build-ok", at_time=4), 2)

    def test_revoked_evidence_is_not_current(self):
        ledger = EvidenceLedger()
        ledger.add(EvidenceRecord("e1", "x", EvidencePolarity.SUPPORTS, "s", "r", 1))
        ledger.revoke("e1", reason="source invalidated")
        self.assertFalse(ledger.is_current("e1", at_time=2))
        self.assertGreater(ledger.generation, 1)

    def test_contradiction_is_not_absence(self):
        ledger = EvidenceLedger()
        ledger.add(EvidenceRecord("e1", "x", EvidencePolarity.CONTRADICTS, "s", "r", 1))
        summary = ledger.claim_summary("x", at_time=2)
        self.assertEqual(summary[EvidencePolarity.CONTRADICTS], 1)
        self.assertEqual(summary[EvidencePolarity.UNKNOWN], 0)


if __name__ == "__main__": unittest.main()
