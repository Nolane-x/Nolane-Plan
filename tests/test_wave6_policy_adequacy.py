from __future__ import annotations

import unittest

from nolane_plan.policy_certificates import OutcomeSupport, PolicyTotalityCertificate, SuccessorHandler, TotalityMode
from nolane_plan.policy_coverage import (
    ExecutablePolicyCoverageAssessment,
    ModelAdequacyLevel,
    ResidualOpenWorldStatus,
)


class Wave6PolicyAdequacyTests(unittest.TestCase):
    def totality(self):
        cert = PolicyTotalityCertificate.evaluate(
            certificate_id="totality-1",
            revision_id="totality-r1",
            policy_revision="policy-r1",
            action_node_revision="node-r1",
            outcomes=(OutcomeSupport("SUCCESS", "modeled", True, False),),
            handlers=(SuccessorHandler("SUCCESS", "next", "successor", False),),
            solver_status="PROVED",
            created_sequence=1,
            validity_regime="mission-1",
        )
        self.assertEqual(cert.mode, TotalityMode.TOTAL)
        return cert

    def test_total_over_modeled_support_can_still_have_open_world_residual_debt(self):
        assessment = ExecutablePolicyCoverageAssessment.create(
            assessment_id="coverage-1",
            revision_id="coverage-r1",
            policy_scope="policy-r1",
            policy_totality_certificate=self.totality(),
            transition_observation_model_adequacy=ModelAdequacyLevel.DEGRADED,
            residual_open_world_status=ResidualOpenWorldStatus.ACTIVE,
            residual_debt_refs=("unmodeled-timeout",),
            closed_domain_proof_ref=None,
            created_sequence=2,
            validity_regime="mission-1",
        )
        self.assertTrue(assessment.modeled_total)
        self.assertFalse(assessment.open_world_complete)
        self.assertTrue(assessment.qualifier_refs)

    def test_totality_without_closed_domain_proof_is_not_open_world_complete(self):
        assessment = ExecutablePolicyCoverageAssessment.create(
            assessment_id="coverage-1",
            revision_id="coverage-r1",
            policy_scope="policy-r1",
            policy_totality_certificate=self.totality(),
            transition_observation_model_adequacy=ModelAdequacyLevel.STRONG,
            residual_open_world_status=ResidualOpenWorldStatus.CLOSED,
            residual_debt_refs=(),
            closed_domain_proof_ref=None,
            created_sequence=2,
            validity_regime="mission-1",
        )
        self.assertTrue(assessment.modeled_total)
        self.assertFalse(assessment.open_world_complete)

    def test_closed_domain_proof_plus_strong_model_and_no_residual_can_close_axis(self):
        assessment = ExecutablePolicyCoverageAssessment.create(
            assessment_id="coverage-1",
            revision_id="coverage-r1",
            policy_scope="policy-r1",
            policy_totality_certificate=self.totality(),
            transition_observation_model_adequacy=ModelAdequacyLevel.STRONG,
            residual_open_world_status=ResidualOpenWorldStatus.CLOSED,
            residual_debt_refs=(),
            closed_domain_proof_ref="closed-domain-proof-1",
            created_sequence=2,
            validity_regime="mission-1",
        )
        self.assertTrue(assessment.open_world_complete)
        self.assertEqual(assessment.qualifier_refs, ())

    def test_incomplete_or_unknown_totality_never_closes_open_world_axis(self):
        incomplete = PolicyTotalityCertificate.evaluate(
            certificate_id="totality-x",
            revision_id="totality-x-r1",
            policy_revision="policy-r1",
            action_node_revision="node-r1",
            outcomes=(OutcomeSupport("TIMEOUT", "modeled", True, False),),
            handlers=(),
            solver_status="PROVED",
            created_sequence=1,
            validity_regime="mission-1",
        )
        assessment = ExecutablePolicyCoverageAssessment.create(
            assessment_id="coverage-x",
            revision_id="coverage-x-r1",
            policy_scope="policy-r1",
            policy_totality_certificate=incomplete,
            transition_observation_model_adequacy=ModelAdequacyLevel.STRONG,
            residual_open_world_status=ResidualOpenWorldStatus.CLOSED,
            residual_debt_refs=(),
            closed_domain_proof_ref="closed-domain-proof-1",
            created_sequence=2,
            validity_regime="mission-1",
        )
        self.assertFalse(assessment.modeled_total)
        self.assertFalse(assessment.open_world_complete)

    def test_active_residual_requires_debt_and_closed_residual_rejects_debt(self):
        with self.assertRaises(ValueError):
            ExecutablePolicyCoverageAssessment.create(
                assessment_id="coverage-x",
                revision_id="coverage-x-r1",
                policy_scope="policy-r1",
                policy_totality_certificate=self.totality(),
                transition_observation_model_adequacy=ModelAdequacyLevel.DEGRADED,
                residual_open_world_status=ResidualOpenWorldStatus.ACTIVE,
                residual_debt_refs=(),
                closed_domain_proof_ref=None,
                created_sequence=2,
                validity_regime="mission-1",
            )
        with self.assertRaises(ValueError):
            ExecutablePolicyCoverageAssessment.create(
                assessment_id="coverage-x",
                revision_id="coverage-x-r1",
                policy_scope="policy-r1",
                policy_totality_certificate=self.totality(),
                transition_observation_model_adequacy=ModelAdequacyLevel.STRONG,
                residual_open_world_status=ResidualOpenWorldStatus.CLOSED,
                residual_debt_refs=("contradictory-debt",),
                closed_domain_proof_ref="proof",
                created_sequence=2,
                validity_regime="mission-1",
            )


if __name__ == "__main__":
    unittest.main()
