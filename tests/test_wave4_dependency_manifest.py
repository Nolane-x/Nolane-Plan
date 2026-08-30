from __future__ import annotations

import unittest

from nolane_plan.freshness import FreshnessDomainLedger
from nolane_plan.proof_dependencies import ProofDependencyManifestRevision
from nolane_plan.proof_inputs import DependencyCaptureAssurance, ExternalReadPolicy, ProofInputEnvelopeRevision
from nolane_plan.query_domain import QueryDomainLedger


class Wave4DependencyManifestTests(unittest.TestCase):
    def setUp(self):
        self.freshness = FreshnessDomainLedger()
        for domain in ("mission", "policy", "proof-profile"):
            self.freshness.ensure(domain)
        self.query_domains = QueryDomainLedger()
        self.query = self.query_domains.create(
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
            created_sequence=1,
        )

    def _envelope(self, assurance=DependencyCaptureAssurance.FULL_ENVELOPE_ENFORCED):
        return ProofInputEnvelopeRevision.create(
            input_envelope_id="env",
            revision_id="env@1",
            procedure_kind="checker",
            procedure_capability_revision="checker@2",
            explicit_input_revision_refs=("mission@2", "policy@4"),
            query_domain_revision_refs=(self.query.revision_id,),
            semantic_profile_refs=("semantic@1",),
            execution_environment_profile_refs=("python@3.13",),
            external_read_policy=(
                ExternalReadPolicy.DENY_UNDECLARED
                if assurance == DependencyCaptureAssurance.FULL_ENVELOPE_ENFORCED
                else ExternalReadPolicy.ALLOW_OPAQUE
            ),
            created_from_decision_cut="cut@7",
            capture_assurance=assurance,
            capture_mechanism_ref=("runtime:fence@1" if assurance == DependencyCaptureAssurance.FULL_ENVELOPE_ENFORCED else None),
        )

    def _manifest(self, **overrides):
        args = dict(
            manifest_id="manifest",
            revision_id="manifest@1",
            artifact_revision="proof@1",
            proof_obligation_revision="obligation@3",
            producer_capability_revision="checker@2",
            input_envelope=self._envelope(),
            positive_revision_dependencies={"mission": "mission@2", "policy": "policy@4"},
            dependency_domains=("mission", "policy", "proof-profile"),
            query_domain_revisions=(self.query,),
            semantic_profile_dependencies=("semantic@1",),
            trust_checker_normalizer_dependencies=("checker-trust@2", "normalizer@1"),
            assumption_basis_dependencies=("assumption@1",),
            execution_semantic_profile_dependencies=("python@3.13",),
            captured_external_evidence_refs=(),
            capture_gaps=(),
            created_sequence=20,
            evaluated_at_cut="cut@7",
        )
        args.update(overrides)
        return ProofDependencyManifestRevision.capture(self.freshness, **args)

    def test_strong_manifest_is_current_when_every_bound_surface_matches(self):
        manifest = self._manifest()
        self.assertTrue(
            manifest.strong_reuse_eligible(
                freshness=self.freshness,
                exact_current_revisions={"mission": "mission@2", "policy": "policy@4"},
                query_domains=self.query_domains,
                current_trust_profile_refs={"checker-trust@2", "normalizer@1", "semantic@1", "python@3.13"},
                minimum_query_assurance=0.8,
            )
        )

    def test_exact_revision_drift_blocks_reuse(self):
        manifest = self._manifest()
        self.assertFalse(
            manifest.strong_reuse_eligible(
                freshness=self.freshness,
                exact_current_revisions={"mission": "mission@3", "policy": "policy@4"},
                query_domains=self.query_domains,
                current_trust_profile_refs={"checker-trust@2", "normalizer@1", "semantic@1", "python@3.13"},
            )
        )

    def test_generation_drift_blocks_reuse_even_if_cached_revisions_look_same(self):
        manifest = self._manifest()
        self.freshness.bump("policy")
        self.assertFalse(
            manifest.dependencies_current(
                freshness=self.freshness,
                exact_current_revisions={"mission": "mission@2", "policy": "policy@4"},
                query_domains=self.query_domains,
                current_trust_profile_refs={"checker-trust@2", "normalizer@1", "semantic@1", "python@3.13"},
            )
        )

    def test_query_domain_drift_blocks_negative_dependency_reuse(self):
        manifest = self._manifest()
        self.query_domains.advance_membership("grants", query_snapshot_id="snapshot-2")
        self.assertFalse(
            manifest.dependencies_current(
                freshness=self.freshness,
                exact_current_revisions={"mission": "mission@2", "policy": "policy@4"},
                query_domains=self.query_domains,
                current_trust_profile_refs={"checker-trust@2", "normalizer@1", "semantic@1", "python@3.13"},
            )
        )

    def test_trust_or_semantic_profile_drift_blocks_reuse(self):
        manifest = self._manifest()
        self.assertFalse(
            manifest.dependencies_current(
                freshness=self.freshness,
                exact_current_revisions={"mission": "mission@2", "policy": "policy@4"},
                query_domains=self.query_domains,
                current_trust_profile_refs={"checker-trust@3", "normalizer@1", "semantic@1", "python@3.13"},
            )
        )

    def test_capture_gap_blocks_strong_reuse(self):
        manifest = self._manifest(capture_gaps=("ambient-network-state",))
        self.assertFalse(manifest.capture_complete)

    def test_self_reported_manifest_cannot_be_elevated_to_strong(self):
        manifest = self._manifest(input_envelope=self._envelope(DependencyCaptureAssurance.SELF_REPORTED_DECLARED))
        self.assertFalse(manifest.capture_complete)

    def test_conservative_overapproximation_is_allowed(self):
        manifest = self._manifest(dependency_domains=("mission", "policy", "proof-profile", "unused-conservative"))
        self.assertTrue(manifest.freshness_vector.capture_assurance == DependencyCaptureAssurance.FULL_ENVELOPE_ENFORCED)
        self.freshness.bump("unused-conservative")
        self.assertFalse(manifest.freshness_vector.current(self.freshness))

    def test_manifest_digest_binds_capture_assurance_and_query_domain(self):
        strong = self._manifest()
        weak = self._manifest(
            revision_id="manifest@2",
            input_envelope=self._envelope(DependencyCaptureAssurance.SELF_REPORTED_DECLARED),
        )
        self.assertNotEqual(strong.canonical_digest, weak.canonical_digest)


if __name__ == "__main__":
    unittest.main()
