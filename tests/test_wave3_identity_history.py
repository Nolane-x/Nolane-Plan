from __future__ import annotations

import unittest

from nolane_plan.identity import IdentityError, PrincipalAttestation, PrincipalIdentityLedger


class Wave3IdentityHistoryTests(unittest.TestCase):
    def test_binding_cannot_justify_a_decision_before_host_accepted_it(self):
        ledger = PrincipalIdentityLedger()
        attestation = PrincipalAttestation.create(
            attestation_id="identity-late",
            canonical_principal_ref="agent:a",
            source="host-runtime",
            source_subject="subject-a",
            revision=1,
            issued_at=1,
            valid_until=100,
            assurance=0.95,
            session_ref="session-1",
        )
        ledger.accept(attestation, now=20)

        with self.assertRaises(IdentityError):
            ledger.current("agent:a", now=19, minimum_assurance=0.8)
        self.assertEqual(
            ledger.current("agent:a", now=20, minimum_assurance=0.8).attestation_id,
            "identity-late",
        )


if __name__ == "__main__":
    unittest.main()
