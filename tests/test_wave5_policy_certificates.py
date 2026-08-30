from __future__ import annotations

import unittest

from nolane_plan.policy_certificates import (
    DecisionHistorySignature,
    DecisionRecallCertificate,
    OutcomeSupport,
    PolicyEdgeCertificate,
    PolicyTotalityCertificate,
    RecallLevel,
    SuccessorHandler,
    TotalityMode,
)


class Wave5PolicyCertificateTests(unittest.TestCase):
    def _history(self, ref: str, **changes) -> DecisionHistorySignature:
        fields = dict(
            history_ref=ref,
            current_information_class="info:same",
            current_action_semantics="deploy:red",
            transition_signature="transition@1",
            observation_capability_signature="observe@1",
            obligation_signature="obligations@1",
            resource_authority_signature="resource-authority@1",
            risk_signature="risk@1",
            action_space_signature="actions@1",
            continuation_signature="continue@1",
        )
        fields.update(changes)
        return DecisionHistorySignature.create(**fields)

    def test_same_current_action_but_different_downstream_transition_fails_recursive_recall(self):
        cert = DecisionRecallCertificate.evaluate(
            certificate_id="recall@1",
            revision_id="recall@1",
            policy_revision="policy@1",
            horizon_ref="horizon@1",
            histories=(
                self._history("h1"),
                self._history("h2", transition_signature="transition@2"),
            ),
            alias_classes={"memory:same": ("h1", "h2")},
            created_sequence=10,
            validity_regime="runtime@1",
        )
        self.assertEqual(cert.level, RecallLevel.RECALL_INSUFFICIENT)
        self.assertIn("RECALL_DOWNSTREAM_MISMATCH", {w.code for w in cert.counterexamples})

    def test_full_recursive_signature_equivalence_can_certify_recall(self):
        cert = DecisionRecallCertificate.evaluate(
            certificate_id="recall@ok",
            revision_id="recall@ok",
            policy_revision="policy@1",
            horizon_ref="horizon@1",
            histories=(self._history("h1"), self._history("h2")),
            alias_classes={"memory:same": ("h1", "h2")},
            created_sequence=10,
            validity_regime="runtime@1",
        )
        self.assertEqual(cert.level, RecallLevel.RECALL_SUFFICIENT)
        self.assertFalse(cert.counterexamples)

    def test_missing_history_in_alias_class_is_recall_unknown_not_sufficient(self):
        cert = DecisionRecallCertificate.evaluate(
            certificate_id="recall@unknown",
            revision_id="recall@unknown",
            policy_revision="policy@1",
            horizon_ref="horizon@1",
            histories=(self._history("h1"),),
            alias_classes={"memory:same": ("h1", "missing")},
            created_sequence=10,
            validity_regime="runtime@1",
        )
        self.assertEqual(cert.level, RecallLevel.RECALL_UNKNOWN)

    def test_supported_timeout_without_successor_is_totality_failure(self):
        cert = PolicyTotalityCertificate.evaluate(
            certificate_id="totality@timeout",
            revision_id="totality@timeout",
            policy_revision="policy@1",
            action_node_revision="node@1",
            outcomes=(
                OutcomeSupport("SUCCESS", "modeled", True, False),
                OutcomeSupport("TIMEOUT", "modeled", True, False),
            ),
            handlers=(SuccessorHandler("SUCCESS", "node-success@1", "successor", False),),
            solver_status="PROVED",
            created_sequence=11,
            validity_regime="runtime@1",
        )
        self.assertEqual(cert.mode, TotalityMode.INCOMPLETE)
        self.assertEqual(cert.counterexamples[0].outcome_ref, "TIMEOUT")

    def test_legitimate_residual_handler_closes_only_declared_residual_support(self):
        cert = PolicyTotalityCertificate.evaluate(
            certificate_id="totality@residual",
            revision_id="totality@residual",
            policy_revision="policy@1",
            action_node_revision="node@1",
            outcomes=(
                OutcomeSupport("SUCCESS", "modeled", True, False),
                OutcomeSupport("RESIDUAL", "residual", True, True),
            ),
            handlers=(
                SuccessorHandler("SUCCESS", "node-success@1", "successor", False),
                SuccessorHandler("RESIDUAL", "recovery@1", "residual_handler", True),
            ),
            solver_status="PROVED",
            created_sequence=11,
            validity_regime="runtime@1",
        )
        self.assertEqual(cert.mode, TotalityMode.TOTAL)
        self.assertFalse(cert.counterexamples)

    def test_generic_continue_primary_catchall_cannot_launder_totality(self):
        cert = PolicyTotalityCertificate.evaluate(
            certificate_id="totality@catchall",
            revision_id="totality@catchall",
            policy_revision="policy@1",
            action_node_revision="node@1",
            outcomes=(OutcomeSupport("TIMEOUT", "modeled", True, False),),
            handlers=(SuccessorHandler("*", "node-primary@1", "continue_primary", False),),
            solver_status="PROVED",
            created_sequence=11,
            validity_regime="runtime@1",
        )
        self.assertEqual(cert.mode, TotalityMode.INCOMPLETE)
        self.assertIn("GENERIC_CATCHALL_NOT_TOTALITY_PROOF", {w.code for w in cert.counterexamples})

    def test_solver_unknown_or_unsupported_never_means_total(self):
        unknown = PolicyTotalityCertificate.evaluate(
            certificate_id="totality@unknown",
            revision_id="totality@unknown",
            policy_revision="policy@1",
            action_node_revision="node@1",
            outcomes=(OutcomeSupport("SUCCESS", "modeled", True, False),),
            handlers=(SuccessorHandler("SUCCESS", "node-success@1", "successor", False),),
            solver_status="UNKNOWN",
            created_sequence=11,
            validity_regime="runtime@1",
        )
        unsupported = PolicyTotalityCertificate.evaluate(
            certificate_id="totality@unsupported",
            revision_id="totality@unsupported",
            policy_revision="policy@1",
            action_node_revision="node@1",
            outcomes=(OutcomeSupport("SUCCESS", "modelled", True, False),),
            handlers=(SuccessorHandler("SUCCESS", "node-success@1", "successor", False),),
            solver_status="UNSUPPORTED",
            created_sequence=11,
            validity_regime="runtime@1",
        )
        self.assertEqual(unknown.mode, TotalityMode.UNKNOWN)
        self.assertEqual(unsupported.mode, TotalityMode.UNSUPPORTED)

    def test_individually_valid_nodes_do_not_imply_stitchable_edge(self):
        cert = PolicyEdgeCertificate.evaluate(
            certificate_id="edge@bad",
            revision_id="edge@bad",
            parent_policy_node_revision="parent@1",
            child_policy_node_revision="child@1",
            edge_guard_ref="guard@1",
            parent_post_contract={
                "mission": "mission@1",
                "information": "info@1",
                "authority": "read-only@1",
                "risk": "risk@1",
                "temporal_window": "[10,20]",
            },
            child_entry_contract={
                "mission": "mission@1",
                "information": "info@1",
                "authority": "deploy@1",
                "risk": "risk@1",
                "temporal_window": "[10,20]",
            },
            created_sequence=12,
            validity_regime="runtime@1",
        )
        self.assertFalse(cert.valid)
        self.assertIn("authority", cert.counterexample.mismatched_fields)

    def test_exact_refinement_contract_can_stitch(self):
        contract = {
            "mission": "mission@1",
            "location": "location@1",
            "information": "info@1",
            "obligations": "obligations@1",
            "resources": "resources@1",
            "authority": "deploy@1",
            "risk": "risk@1",
            "temporal_window": "[10,20]",
            "side_effect_state": "none",
            "action_space": "actions@1",
            "adequacy": "bounded@1",
            "preparedness": "P3",
        }
        cert = PolicyEdgeCertificate.evaluate(
            certificate_id="edge@ok",
            revision_id="edge@ok",
            parent_policy_node_revision="parent@1",
            child_policy_node_revision="child@1",
            edge_guard_ref="guard@1",
            parent_post_contract=contract,
            child_entry_contract=contract,
            created_sequence=12,
            validity_regime="runtime@1",
        )
        self.assertTrue(cert.valid)
        self.assertIsNone(cert.counterexample)


if __name__ == "__main__":
    unittest.main()
