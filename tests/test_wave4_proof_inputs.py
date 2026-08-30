from __future__ import annotations

import unittest

from nolane_plan.proof_inputs import (
    DependencyCaptureAssurance,
    ExternalReadPolicy,
    ProofInputEnvelopeRevision,
    ProofInputError,
)


class Wave4ProofInputTests(unittest.TestCase):
    def _envelope(self, **overrides):
        args = dict(
            input_envelope_id="env-1",
            revision_id="env-1@1",
            procedure_kind="constraint-check",
            procedure_capability_revision="checker@3",
            subject_revision_refs=("action@1",),
            explicit_input_revision_refs=("mission@2", "policy@4"),
            query_domain_revision_refs=("grants-domain@7",),
            collection_membership_revision_refs=("namespace@5",),
            semantic_profile_refs=("semantics@2",),
            assumption_basis_refs=("assumptions@1",),
            trusted_axiom_model_refs=("axioms@1",),
            canonical_unit_numeric_profile_refs=("numeric@1",),
            execution_environment_profile_refs=("python@3.13",),
            external_read_policy=ExternalReadPolicy.DENY_UNDECLARED,
            captured_external_evidence_refs=(),
            resource_budget_profile_refs=("budget@1",),
            created_from_decision_cut="cut@9",
            capture_assurance=DependencyCaptureAssurance.FULL_ENVELOPE_ENFORCED,
            capture_mechanism_ref="runtime:envelope-fence@1",
        )
        args.update(overrides)
        return ProofInputEnvelopeRevision.create(**args)

    def test_full_envelope_is_strong_when_actual_reads_are_declared(self):
        env = self._envelope()
        self.assertTrue(env.strong_dependency_complete)
        env.assert_observed_reads_captured({"mission@2", "policy@4", "action@1"})

    def test_full_envelope_rejects_hidden_read(self):
        env = self._envelope()
        with self.assertRaises(ProofInputError):
            env.assert_observed_reads_captured({"mission@2", "ambient-secret@1"})

    def test_self_report_is_provenance_not_strong_completeness(self):
        env = self._envelope(
            capture_assurance=DependencyCaptureAssurance.SELF_REPORTED_DECLARED,
            capture_mechanism_ref=None,
        )
        self.assertFalse(env.strong_dependency_complete)
        with self.assertRaises(ProofInputError):
            env.require_strong_capture()

    def test_trusted_dynamic_capture_requires_independent_capture_mechanism(self):
        with self.assertRaises(ProofInputError):
            self._envelope(
                capture_assurance=DependencyCaptureAssurance.TRUSTED_DYNAMIC_CAPTURE,
                capture_mechanism_ref=None,
                external_read_policy=ExternalReadPolicy.CAPTURE_REQUIRED,
            )

    def test_trusted_dynamic_capture_accepts_promoted_external_revision(self):
        env = self._envelope(
            capture_assurance=DependencyCaptureAssurance.TRUSTED_DYNAMIC_CAPTURE,
            capture_mechanism_ref="capture-agent@4",
            external_read_policy=ExternalReadPolicy.CAPTURE_REQUIRED,
            captured_external_evidence_refs=("weather-observation@8",),
        )
        env.require_strong_capture()
        env.assert_observed_reads_captured({"mission@2", "weather-observation@8"})

    def test_dynamic_capture_rejects_uncaptured_live_read(self):
        env = self._envelope(
            capture_assurance=DependencyCaptureAssurance.TRUSTED_DYNAMIC_CAPTURE,
            capture_mechanism_ref="capture-agent@4",
            external_read_policy=ExternalReadPolicy.CAPTURE_REQUIRED,
            captured_external_evidence_refs=("weather-observation@8",),
        )
        with self.assertRaises(ProofInputError):
            env.assert_observed_reads_captured({"live-network-value@now"})

    def test_opaque_and_unsupported_capture_cannot_claim_strong_reuse(self):
        for assurance in (
            DependencyCaptureAssurance.DEPENDENCY_OPAQUE,
            DependencyCaptureAssurance.UNSUPPORTED_CAPTURE,
        ):
            with self.subTest(assurance=assurance):
                env = self._envelope(
                    capture_assurance=assurance,
                    capture_mechanism_ref=None,
                    external_read_policy=ExternalReadPolicy.ALLOW_OPAQUE,
                )
                self.assertFalse(env.strong_dependency_complete)

    def test_canonical_digest_is_stable_under_ref_ordering(self):
        first = self._envelope(explicit_input_revision_refs=("mission@2", "policy@4"))
        second = self._envelope(explicit_input_revision_refs=("policy@4", "mission@2"))
        self.assertEqual(first.canonical_input_digest, second.canonical_input_digest)

    def test_envelope_revision_identity_participates_in_digest(self):
        first = self._envelope(revision_id="env-1@1")
        second = self._envelope(revision_id="env-1@2")
        self.assertNotEqual(first.canonical_input_digest, second.canonical_input_digest)


if __name__ == "__main__":
    unittest.main()
