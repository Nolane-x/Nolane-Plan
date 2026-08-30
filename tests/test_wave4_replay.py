from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from nolane_plan import PlanKernel
from nolane_plan.actions import ActionIntent, AuthorityGrant
from nolane_plan.identity import PrincipalAttestation
from nolane_plan.proof_inputs import DependencyCaptureAssurance, ExternalReadPolicy, ProofInputEnvelopeRevision
from nolane_plan.semantic_barrier import MutationImpactProfileRevision
from nolane_plan.support import InvalidityCause, SupportAlternativeSetRevision, SupportClause, SupportNode
from nolane_plan.types import AuthorizationError, ReplayError, RiskClass


class Wave4ReplayTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _base_kernel(self) -> PlanKernel:
        kernel = PlanKernel.create(self.root, "Wave 4 replay authority")
        attestation = PrincipalAttestation.create(
            attestation_id="identity-a",
            canonical_principal_ref="agent:a",
            source="host-runtime",
            source_subject="subject-a",
            revision=1,
            issued_at=1,
            valid_until=1000,
            assurance=0.95,
            session_ref="session-a",
        )
        kernel.bind_principal(attestation, allowed_tags=set(), now=10)
        kernel.propose_action(ActionIntent("act", "deploy", RiskClass.CONSEQUENTIAL))
        kernel.add_grant(AuthorityGrant("grant", "agent:a", frozenset({"deploy"})))
        kernel.register_semantic_source(
            "policy",
            revision_id="policy@1",
            value={"mode": "safe"},
            dependency_domains=("source:policy", "proof:policy"),
        )
        kernel.register_proof_profile_refs(
            "semantic@1", "checker-trust@2", "normalizer@1", "python@3.13"
        )
        return kernel

    def _install_proof(self, kernel: PlanKernel) -> None:
        query = kernel.create_proof_query_domain(
            query_domain_id="grants",
            scope_revision="scope@1",
            index_schema_revision="index@1",
            completeness_contract="complete-enumeration@1",
            filter_predicate_revision="conflict@1",
            alias_equivalence_regime="alias@1",
            visibility_permission_regime="view@1",
            mutation_impact_profile_revision="impact@1",
            query_snapshot_id="snapshot-1",
            snapshot_complete=True,
            opaque=False,
            visibility_assurance=0.95,
        )
        envelope = ProofInputEnvelopeRevision.create(
            input_envelope_id="env",
            revision_id="env@1",
            procedure_kind="constraint-check",
            procedure_capability_revision="checker@2",
            explicit_input_revision_refs=("policy@1",),
            query_domain_revision_refs=(query.revision_id,),
            semantic_profile_refs=("semantic@1",),
            execution_environment_profile_refs=("python@3.13",),
            external_read_policy=ExternalReadPolicy.DENY_UNDECLARED,
            created_from_decision_cut=kernel.current_cut().id,
            capture_assurance=DependencyCaptureAssurance.FULL_ENVELOPE_ENFORCED,
            capture_mechanism_ref="runtime:fence@1",
        )
        kernel.register_proof_input(envelope)
        kernel.capture_proof_manifest(
            manifest_id="manifest",
            revision_id="manifest@1",
            artifact_revision="proof@1",
            proof_obligation_revision="obligation@1",
            producer_capability_revision="checker@2",
            input_envelope_revision=envelope.revision_id,
            positive_revision_dependencies={"policy": "policy@1"},
            dependency_domains=("source:policy", "proof:policy"),
            query_domain_ids=("grants",),
            semantic_profile_dependencies=("semantic@1",),
            trust_checker_normalizer_dependencies=("checker-trust@2", "normalizer@1"),
            execution_semantic_profile_dependencies=("python@3.13",),
        )
        kernel.register_support_node(
            SupportNode(
                ref="evidence@1",
                current=True,
                direct_grounding_roots=frozenset({"root:host"}),
                support_refs=(),
                scope="mission",
                assumption_basis=frozenset({"assumption@1"}),
                proof_kind="verification",
                validity_regime="runtime@1",
                context_tags=frozenset({"prod"}),
            )
        )
        kernel.register_support_set(
            SupportAlternativeSetRevision.create(
                support_set_id="support",
                revision_id="support@1",
                subject_artifact_revision="proof@1",
                clauses=(
                    SupportClause(
                        "clause@1",
                        ("evidence@1",),
                        "mission",
                        frozenset({"assumption@1"}),
                        "verification",
                        frozenset(),
                        "runtime@1",
                        frozenset({"prod"}),
                        1,
                    ),
                ),
                scope="mission",
                assumption_context_rules=("prod",),
                proof_kind="verification",
                grounding_policy="accepted-roots-only",
                support_evaluation_profile="bounded-dnf@1",
                created_sequence=kernel.writer_sequence,
            )
        )

    def _authorize(self, kernel: PlanKernel):
        return kernel.authorize_proof_carrying(
            "act",
            "agent:a",
            ("grant",),
            now=50,
            proof_artifact_revision="proof@1",
            active_context={"prod"},
        )

    def test_clean_v4_snapshot_round_trip_preserves_proof_authority(self):
        kernel = self._base_kernel()
        self._install_proof(kernel)
        before = kernel.evaluate_proof_authority("proof@1", active_context={"prod"})
        state = kernel.save_snapshot()
        self.assertEqual(state["snapshot_schema"], "nolane-plan-runtime-snapshot-v5")

        reopened = PlanKernel.open(self.root)
        after = reopened.evaluate_proof_authority("proof@1", active_context={"prod"})
        self.assertTrue(after.current_usable)
        self.assertEqual(
            reopened.proof_manifests["proof@1"].canonical_digest,
            kernel.proof_manifests["proof@1"].canonical_digest,
        )
        self.assertEqual(
            reopened.support_sets["proof@1"].canonical_digest,
            kernel.support_sets["proof@1"].canonical_digest,
        )
        self.assertNotEqual(before.support.assessment_digest, "")
        authorization = self._authorize(reopened)
        self.assertIn(authorization.id, reopened.proof_authorization_bindings)

    def test_stale_before_snapshot_does_not_resurrect_after_restart(self):
        kernel = self._base_kernel()
        self._install_proof(kernel)
        kernel.mutate_semantic_source(
            "policy",
            new_revision_id="policy@2",
            new_value={"mode": "changed"},
            impact_profile=MutationImpactProfileRevision(
                "policy-impact@2", "policy", ("source:policy", "proof:policy"), True, ()
            ),
        )
        kernel.save_snapshot()

        reopened = PlanKernel.open(self.root)
        self.assertEqual(reopened.semantic_barrier.read_source("policy").revision_id, "policy@2")
        with self.assertRaises(AuthorizationError):
            self._authorize(reopened)

    def test_post_snapshot_semantic_mutation_replays_and_stales_proof(self):
        kernel = self._base_kernel()
        self._install_proof(kernel)
        kernel.save_snapshot()
        kernel.mutate_semantic_source(
            "policy",
            new_revision_id="policy@2",
            new_value={"mode": "changed"},
            impact_profile=MutationImpactProfileRevision(
                "policy-impact@2", "policy", ("source:policy", "proof:policy"), True, ()
            ),
        )

        reopened = PlanKernel.open(self.root)
        self.assertEqual(reopened.semantic_barrier.read_source("policy").revision_id, "policy@2")
        self.assertEqual(reopened.proof_exact_revisions["policy"], "policy@2")
        with self.assertRaises(AuthorizationError):
            self._authorize(reopened)

    def test_post_snapshot_query_membership_replays_and_stales_negative_dependency(self):
        kernel = self._base_kernel()
        self._install_proof(kernel)
        kernel.save_snapshot()
        kernel.advance_proof_query_membership("grants", query_snapshot_id="snapshot-2")

        reopened = PlanKernel.open(self.root)
        self.assertEqual(reopened.query_domains.latest("grants").membership_generation, 2)
        with self.assertRaises(AuthorizationError):
            self._authorize(reopened)

    def test_post_snapshot_proof_lineage_can_be_reconstructed_from_journal(self):
        kernel = self._base_kernel()
        kernel.save_snapshot()
        self._install_proof(kernel)

        reopened = PlanKernel.open(self.root)
        self.assertIn("proof@1", reopened.proof_manifests)
        self.assertIn("proof@1", reopened.support_sets)
        self.assertTrue(
            reopened.evaluate_proof_authority("proof@1", active_context={"prod"}).current_usable
        )

    def test_blocking_invalidity_survives_snapshot_and_blocks_authority(self):
        kernel = self._base_kernel()
        self._install_proof(kernel)
        kernel.set_proof_invalidity_causes(
            "proof@1",
            (InvalidityCause("revoked", "VERIFIER_TRUST_REVOKED", True, True),),
        )
        kernel.save_snapshot()

        reopened = PlanKernel.open(self.root)
        with self.assertRaises(AuthorizationError):
            self._authorize(reopened)

    def test_tampered_internal_manifest_digest_fails_closed_even_with_valid_outer_snapshot_digest(self):
        kernel = self._base_kernel()
        self._install_proof(kernel)
        kernel.save_snapshot()
        state = kernel.snapshots.load()
        state["proof"]["manifests"][0]["canonical_digest"] = "tampered"
        kernel.snapshots.save(state)

        with self.assertRaises(ReplayError):
            PlanKernel.open(self.root)


if __name__ == "__main__":
    unittest.main()
