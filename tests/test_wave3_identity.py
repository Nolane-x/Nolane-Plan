from __future__ import annotations

import unittest

from nolane_plan.identity import IdentityError, PrincipalAttestation, PrincipalIdentityLedger


class Wave3IdentityTests(unittest.TestCase):
    def _attestation(
        self,
        *,
        attestation_id: str = "att-1",
        canonical_principal_ref: str = "agent:planner-1",
        source: str = "host-runtime",
        source_subject: str = "subject-17",
        revision: int = 1,
        issued_at: float = 10,
        valid_until: float | None = 100,
        assurance: float = 0.95,
        session_ref: str | None = "session-a",
    ) -> PrincipalAttestation:
        return PrincipalAttestation.create(
            attestation_id=attestation_id,
            canonical_principal_ref=canonical_principal_ref,
            source=source,
            source_subject=source_subject,
            revision=revision,
            issued_at=issued_at,
            valid_until=valid_until,
            assurance=assurance,
            session_ref=session_ref,
        )

    def test_canonical_source_subject_is_stable_across_sessions(self):
        ledger = PrincipalIdentityLedger()
        first = ledger.accept(self._attestation(session_ref="session-a"), now=20)
        second = ledger.accept(self._attestation(attestation_id="att-2", revision=2, session_ref="session-b"), now=30)

        self.assertEqual(first.canonical_principal_ref, second.canonical_principal_ref)
        self.assertEqual(second.binding_revision, 2)
        self.assertNotEqual(first.attestation_id, second.attestation_id)

    def test_source_subject_cannot_be_rebound_to_different_principal(self):
        ledger = PrincipalIdentityLedger()
        ledger.accept(self._attestation(), now=20)

        with self.assertRaises(IdentityError):
            ledger.accept(
                self._attestation(
                    attestation_id="att-evil",
                    canonical_principal_ref="agent:admin",
                    revision=2,
                ),
                now=30,
            )

    def test_expiry_and_revocation_remove_strong_current_identity(self):
        ledger = PrincipalIdentityLedger()
        ledger.accept(self._attestation(valid_until=40), now=20)
        self.assertEqual(ledger.current("agent:planner-1", now=39, minimum_assurance=0.9).assurance, 0.95)

        with self.assertRaises(IdentityError):
            ledger.current("agent:planner-1", now=41, minimum_assurance=0.9)

        ledger.accept(self._attestation(attestation_id="att-2", revision=2, valid_until=100), now=50)
        ledger.revoke("att-2", revoked_at=55)
        with self.assertRaises(IdentityError):
            ledger.current("agent:planner-1", now=56, minimum_assurance=0.9)

    def test_role_or_model_narration_is_not_a_principal_attestation(self):
        ledger = PrincipalIdentityLedger()
        with self.assertRaises(IdentityError):
            ledger.accept_narrated_identity("admin", now=10)

    def test_low_assurance_identity_cannot_meet_strong_floor(self):
        ledger = PrincipalIdentityLedger()
        ledger.accept(self._attestation(assurance=0.4), now=20)
        with self.assertRaises(IdentityError):
            ledger.current("agent:planner-1", now=30, minimum_assurance=0.8)


if __name__ == "__main__":
    unittest.main()
