from __future__ import annotations

import unittest

from nolane_plan.option_independence import (
    OptionIndependenceCertificate,
    OptionIndependenceStatus,
    RobustPreparednessAssessment,
)
from nolane_plan.policy_readiness import PreparednessProfile, PreparednessStructure


AXES = {
    "recognition": 4,
    "trigger": 4,
    "observation": 4,
    "recall": 4,
    "routing": 4,
    "action_contract": 4,
    "authority": 4,
    "resource": 4,
    "temporal_reaction": 4,
    "recovery": 4,
    "policy_coherence": 4,
    "proof_context": 4,
    "continuation": 4,
}


class Wave6OptionIndependenceTests(unittest.TestCase):
    def profile(self, ref: str, level: int = 4):
        axes = {name: level for name in AXES}
        return PreparednessProfile.create(
            preparedness_profile_id=ref,
            revision_id=f"{ref}-r1",
            future_region_or_policy_scope="policy-1",
            axes=axes,
            model_adequacy_cap=level,
            debt_refs=(),
            validity_regime="mission-1",
        )

    def test_shared_credential_collapses_robust_independence(self):
        cert = OptionIndependenceCertificate.evaluate(
            certificate_id="ind-1",
            revision_id="ind-r1",
            route_refs=("route-a", "route-b"),
            failure_uncertainty_set_ref="credential-loss",
            shared_dependency_graph_ref="deps-r1",
            route_dependency_refs={
                "route-a": ("credential:prod", "provider:a"),
                "route-b": ("credential:prod", "provider:b"),
            },
            resource_overlap_refs=(),
            observation_lineage_overlap_refs=(),
            control_plane_overlap_refs=(),
            common_mode_failure_refs=("credential:prod",),
            coactivation_feasible=True,
            assurance_profile="strong",
            analysis_supported=True,
        )
        self.assertEqual(cert.status, OptionIndependenceStatus.NOMINAL_ONLY)
        self.assertFalse(cert.supports_robust_uplift)

        result = RobustPreparednessAssessment.evaluate(
            profiles=(self.profile("p-a"), self.profile("p-b")),
            structure=PreparednessStructure.OR,
            required_count=1,
            independence_certificate=cert,
        )
        self.assertEqual(result.nominal_alternative_preparedness, 4)
        self.assertLessEqual(result.robust_independent_preparedness, 4)
        self.assertFalse(result.robust_uplift_applied)

    def test_distinct_verified_dependencies_can_support_robust_or_uplift(self):
        cert = OptionIndependenceCertificate.evaluate(
            certificate_id="ind-1",
            revision_id="ind-r1",
            route_refs=("route-a", "route-b"),
            failure_uncertainty_set_ref="provider-loss",
            shared_dependency_graph_ref="deps-r1",
            route_dependency_refs={
                "route-a": ("credential:a", "provider:a"),
                "route-b": ("credential:b", "provider:b"),
            },
            resource_overlap_refs=(),
            observation_lineage_overlap_refs=(),
            control_plane_overlap_refs=(),
            common_mode_failure_refs=(),
            coactivation_feasible=True,
            assurance_profile="strong",
            analysis_supported=True,
        )
        self.assertEqual(cert.status, OptionIndependenceStatus.ROBUST_INDEPENDENT)
        result = RobustPreparednessAssessment.evaluate(
            profiles=(self.profile("p-a", 5), self.profile("p-b", 3)),
            structure=PreparednessStructure.OR,
            required_count=1,
            independence_certificate=cert,
        )
        self.assertEqual(result.nominal_alternative_preparedness, 5)
        self.assertEqual(result.robust_independent_preparedness, 5)
        self.assertTrue(result.robust_uplift_applied)

    def test_k_of_n_requires_coactivation_and_independent_routes(self):
        cert = OptionIndependenceCertificate.evaluate(
            certificate_id="ind-1",
            revision_id="ind-r1",
            route_refs=("a", "b", "c"),
            failure_uncertainty_set_ref="single-provider-loss",
            shared_dependency_graph_ref="deps-r1",
            route_dependency_refs={"a": ("a",), "b": ("b",), "c": ("c",)},
            resource_overlap_refs=(),
            observation_lineage_overlap_refs=(),
            control_plane_overlap_refs=(),
            common_mode_failure_refs=(),
            coactivation_feasible=False,
            assurance_profile="strong",
            analysis_supported=True,
        )
        self.assertEqual(cert.status, OptionIndependenceStatus.NOMINAL_ONLY)
        result = RobustPreparednessAssessment.evaluate(
            profiles=(self.profile("a", 5), self.profile("b", 4), self.profile("c", 2)),
            structure=PreparednessStructure.K_OF_N,
            required_count=2,
            independence_certificate=cert,
        )
        self.assertFalse(result.robust_uplift_applied)
        self.assertEqual(result.robust_independent_preparedness, 2)

    def test_unknown_or_unsupported_independence_never_becomes_robust(self):
        unknown = OptionIndependenceCertificate.evaluate(
            certificate_id="ind-u",
            revision_id="ind-u-r1",
            route_refs=("a", "b"),
            failure_uncertainty_set_ref="unknown-failure-set",
            shared_dependency_graph_ref="deps-r1",
            route_dependency_refs={"a": ("a",), "b": ("b",)},
            resource_overlap_refs=(),
            observation_lineage_overlap_refs=(),
            control_plane_overlap_refs=(),
            common_mode_failure_refs=(),
            coactivation_feasible=None,
            assurance_profile="partial",
            analysis_supported=True,
        )
        self.assertEqual(unknown.status, OptionIndependenceStatus.UNKNOWN)

        unsupported = OptionIndependenceCertificate.evaluate(
            certificate_id="ind-x",
            revision_id="ind-x-r1",
            route_refs=("a", "b"),
            failure_uncertainty_set_ref="failure-set",
            shared_dependency_graph_ref="deps-r1",
            route_dependency_refs={"a": ("a",), "b": ("b",)},
            resource_overlap_refs=(),
            observation_lineage_overlap_refs=(),
            control_plane_overlap_refs=(),
            common_mode_failure_refs=(),
            coactivation_feasible=True,
            assurance_profile="partial",
            analysis_supported=False,
        )
        self.assertEqual(unsupported.status, OptionIndependenceStatus.UNSUPPORTED)

    def test_resource_observation_or_control_plane_overlap_can_collapse_robustness(self):
        for field in (
            "resource_overlap_refs",
            "observation_lineage_overlap_refs",
            "control_plane_overlap_refs",
        ):
            kwargs = dict(
                certificate_id=f"ind-{field}",
                revision_id="r1",
                route_refs=("a", "b"),
                failure_uncertainty_set_ref="single-common-mode",
                shared_dependency_graph_ref="deps-r1",
                route_dependency_refs={"a": ("a",), "b": ("b",)},
                resource_overlap_refs=(),
                observation_lineage_overlap_refs=(),
                control_plane_overlap_refs=(),
                common_mode_failure_refs=(),
                coactivation_feasible=True,
                assurance_profile="strong",
                analysis_supported=True,
            )
            kwargs[field] = ("shared-x",)
            cert = OptionIndependenceCertificate.evaluate(**kwargs)
            self.assertEqual(cert.status, OptionIndependenceStatus.NOMINAL_ONLY)

    def test_certificate_is_failure_set_relative_and_digest_bound(self):
        base = OptionIndependenceCertificate.evaluate(
            certificate_id="ind-1",
            revision_id="ind-r1",
            route_refs=("a", "b"),
            failure_uncertainty_set_ref="provider-loss",
            shared_dependency_graph_ref="deps-r1",
            route_dependency_refs={"a": ("a",), "b": ("b",)},
            resource_overlap_refs=(),
            observation_lineage_overlap_refs=(),
            control_plane_overlap_refs=(),
            common_mode_failure_refs=(),
            coactivation_feasible=True,
            assurance_profile="strong",
            analysis_supported=True,
        )
        changed = OptionIndependenceCertificate.evaluate(
            certificate_id="ind-1",
            revision_id="ind-r1",
            route_refs=("a", "b"),
            failure_uncertainty_set_ref="credential-loss",
            shared_dependency_graph_ref="deps-r1",
            route_dependency_refs={"a": ("a",), "b": ("b",)},
            resource_overlap_refs=(),
            observation_lineage_overlap_refs=(),
            control_plane_overlap_refs=(),
            common_mode_failure_refs=(),
            coactivation_feasible=True,
            assurance_profile="strong",
            analysis_supported=True,
        )
        self.assertNotEqual(base.canonical_digest, changed.canonical_digest)

    def test_preparedness_profile_exposes_certificate_bound_strong_aggregation(self):
        cert = OptionIndependenceCertificate.evaluate(
            certificate_id="ind-1",
            revision_id="ind-r1",
            route_refs=("a", "b"),
            failure_uncertainty_set_ref="provider-loss",
            shared_dependency_graph_ref="deps-r1",
            route_dependency_refs={"a": ("a",), "b": ("b",)},
            resource_overlap_refs=(),
            observation_lineage_overlap_refs=(),
            control_plane_overlap_refs=(),
            common_mode_failure_refs=(),
            coactivation_feasible=True,
            assurance_profile="strong",
            analysis_supported=True,
        )
        result = PreparednessProfile.aggregate_with_independence(
            PreparednessStructure.OR,
            (self.profile("a", 5), self.profile("b", 3)),
            required_count=1,
            independence_certificate=cert,
        )
        self.assertEqual(result.robust_independent_preparedness, 5)


if __name__ == "__main__":
    unittest.main()
