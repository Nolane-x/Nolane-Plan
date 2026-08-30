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
from nolane_plan.types import AuthorizationError, RiskClass


class Wave4KernelProofAuthorityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.kernel = PlanKernel.create(self.root, "proof authority")
        att = PrincipalAttestation.create(
            attestation_id="id-a",
            canonical_principal_ref="agent:a",
            source="host-runtime",
            source_subject="subject-a",
            revision=1,
            issued_at=1,
            valid_until=1000,
            assurance=0.95,
            session_ref="session-a",
        )
        self.kernel.bind_principal(att, allowed_tags=set(), now=10)
        self.kernel.propose_action(ActionIntent("act", "deploy", RiskClass.CONSEQUENTIAL))
        self.kernel.add_grant(AuthorityGrant("grant", "agent:a", frozenset({"deploy"})))
        self.kernel.register_semantic_source(
            "policy",
            revision_id="policy@1",
            value={"mode": "safe"},
            dependency_domains=("source:policy", "proof:policy"),
        )
        self.kernel.register_proof_profile_refs(
            "semantic@1", "checker-trust@2", "normalizer@1", "python@3.13"
        )
        self.query = self.kernel.create_proof_query_domain(
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
        self._install_proof()

    def tearDown(self):
        self.tmp.cleanup()

    def _envelope(self, assurance=DependencyCaptureAssurance.FULL_ENVELOPE_ENFORCED):
        return ProofInputEnvelopeRevision.create(
            input_envelope_id="env",
            revision_id=f"env@{assurance.value}",
            procedure_kind="constraint-check",
            procedure_capability_revision="checker@2",
            explicit_input_revision_refs=("policy@1",),
            query_domain_revision_refs=(self.query.revision_id,),
            semantic_profile_refs=("semantic@1",),
            execution_environment_profile_refs=("python@3.13",),
            external_read_policy=(
                ExternalReadPolicy.DENY_UNDECLARED
                if assurance == DependencyCaptureAssurance.FULL_ENVELOPE_ENFORCED
                else ExternalReadPolicy.ALLOW_OPAQUE
            ),
            created_from_decision_cut=self.kernel.current_cut().id,
            capture_assurance=assurance,
            capture_mechanism_ref=("runtime:fence@1" if assurance == DependencyCaptureAssurance.FULL_ENVELOPE_ENFORCED else None),
        )

    def _install_proof(self, assurance=DependencyCaptureAssurance.FULL_ENVELOPE_ENFORCED):
        env = self._envelope(assurance)
        self.kernel.register_proof_input(env)
        self.kernel.capture_proof_manifest(
            manifest_id="manifest",
            revision_id=f"manifest@{assurance.value}",
            artifact_revision="proof@1",
            proof_obligation_revision="obligation@1",
            producer_capability_revision="checker@2",
            input_envelope_revision=env.revision_id,
            positive_revision_dependencies={"policy": "policy@1"},
            dependency_domains=("source:policy", "proof:policy"),
            query_domain_ids=("grants",),
            semantic_profile_dependencies=("semantic@1",),
            trust_checker_normalizer_dependencies=("checker-trust@2", "normalizer@1"),
            execution_semantic_profile_dependencies=("python@3.13",),
            capture_gaps=(),
        )
        self.kernel.register_support_node(
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
        self.kernel.register_support_set(
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
                created_sequence=self.kernel.writer_sequence,
            )
        )

    def _authorize(self):
        return self.kernel.authorize_proof_carrying(
            "act",
            "agent:a",
            ("grant",),
            now=50,
            proof_artifact_revision="proof@1",
            active_context={"prod"},
        )

    def test_valid_current_proof_can_authorize(self):
        authorization = self._authorize()
        self.assertEqual(authorization.acting_principal_ref, "agent:a")
        self.assertIn(authorization.id, self.kernel.proof_authorization_bindings)

    def test_unsupported_proof_blocks_authorization(self):
        self.kernel.support_nodes["evidence@1"] = SupportNode(
            ref="evidence@1",
            current=False,
            direct_grounding_roots=frozenset({"root:host"}),
            support_refs=(),
            scope="mission",
            assumption_basis=frozenset({"assumption@1"}),
            proof_kind="verification",
            validity_regime="runtime@1",
            context_tags=frozenset({"prod"}),
        )
        with self.assertRaises(AuthorizationError):
            self._authorize()

    def test_active_blocking_invalidity_blocks_even_supported_proof(self):
        self.kernel.set_proof_invalidity_causes(
            "proof@1",
            (InvalidityCause("revoked", "VERIFIER_TRUST_REVOKED", True, True),),
        )
        with self.assertRaises(AuthorizationError):
            self._authorize()

    def test_semantic_source_mutation_stales_proof_before_authorization(self):
        before = len(self.kernel.authorizations)
        self.kernel.mutate_semantic_source(
            "policy",
            new_revision_id="policy@2",
            new_value={"mode": "changed"},
            impact_profile=MutationImpactProfileRevision(
                "policy-impact@2", "policy", ("source:policy", "proof:policy"), True, ()
            ),
        )
        with self.assertRaises(AuthorizationError):
            self._authorize()
        self.assertEqual(len(self.kernel.authorizations), before)

    def test_query_membership_drift_stales_negative_dependency(self):
        self.kernel.advance_proof_query_membership("grants", query_snapshot_id="snapshot-2")
        with self.assertRaises(AuthorizationError):
            self._authorize()

    def test_self_reported_capture_cannot_reach_proof_authority(self):
        weak = self._envelope(DependencyCaptureAssurance.SELF_REPORTED_DECLARED)
        self.kernel.register_proof_input(weak)
        self.kernel.capture_proof_manifest(
            manifest_id="weak-manifest",
            revision_id="weak-manifest@1",
            artifact_revision="weak-proof@1",
            proof_obligation_revision="obligation@1",
            producer_capability_revision="checker@2",
            input_envelope_revision=weak.revision_id,
            positive_revision_dependencies={"policy": "policy@1"},
            dependency_domains=("source:policy",),
            query_domain_ids=(),
        )
        self.kernel.register_support_set(
            SupportAlternativeSetRevision.create(
                support_set_id="weak-support",
                revision_id="weak-support@1",
                subject_artifact_revision="weak-proof@1",
                clauses=(),
                scope="mission",
                assumption_context_rules=("prod",),
                proof_kind="verification",
                grounding_policy="accepted-roots-only",
                support_evaluation_profile="bounded-dnf@1",
                created_sequence=self.kernel.writer_sequence,
            )
        )
        with self.assertRaises(AuthorizationError):
            self.kernel.authorize_proof_carrying(
                "act", "agent:a", ("grant",), now=50,
                proof_artifact_revision="weak-proof@1", active_context={"prod"}
            )

    def test_semantic_barrier_uses_exact_kernel_writer_lock(self):
        self.assertIs(self.kernel.semantic_barrier._lock, self.kernel._writer_lock)


if __name__ == "__main__":
    unittest.main()
