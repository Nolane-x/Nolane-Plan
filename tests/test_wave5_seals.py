from __future__ import annotations

import unittest

from nolane_plan.seals import (
    ArtifactAssurance,
    CompositionStatus,
    DecisionSufficiencyCertificate,
    ProofContextComponent,
    SealCompiler,
    SealStatus,
)


class Wave5SealTests(unittest.TestCase):
    def _sufficiency(self, *, debt_refs=(), complete=True) -> DecisionSufficiencyCertificate:
        return DecisionSufficiencyCertificate.create(
            certificate_id="sufficiency@1",
            revision_id="sufficiency@1",
            scope_ref="action:deploy",
            action_ref="deploy:red",
            decision_epoch_ref="epoch@1",
            decision_principal_ref="agent:a",
            information_partition_revision="partition@1",
            exact_object_revisions={"mission": "mission@1", "policy": "node@1", "proof": "proof@1"},
            included_object_refs=("mission@1", "node@1", "proof@1"),
            excluded_known_object_refs=("far-future-draft@9",),
            compiler_profile_ref="closure@1",
            adequacy_limits=("bounded-reference-world",),
            debt_refs=debt_refs,
            complete=complete,
            created_sequence=20,
            validity_regime="runtime@1",
        )

    def _component(self, ref: str, worlds, assurance=ArtifactAssurance.CHECKED, debt_refs=()):
        return ProofContextComponent.create(
            component_ref=ref,
            assurance=assurance,
            assumptions=("assumption@1",),
            scope="action:deploy",
            guarantee="G2",
            debt_refs=debt_refs,
            risk_refs=("risk@1",),
            authority_refs=("authority@1",),
            resource_refs=("gpu@1",),
            external_regime_refs=("runtime@1",),
            validity_horizon=(10, 50),
            constraint_theory="finite-world-set",
            allowed_worlds=worlds,
        )

    def _seal(self, revision_id="seal@1"):
        return SealCompiler.issue(
            seal_id="seal",
            revision_id=revision_id,
            plan_root_revision="plan@1",
            mission_revision=1,
            canonical_state_version=1,
            action_closure_refs=("deploy:red", "node@1", "proof@1"),
            sufficiency=self._sufficiency(),
            proof_contexts=(self._component("checker", ("w1",)),),
            required_assurance=ArtifactAssurance.CHECKED,
            accepted_debt_refs=(),
            compiler_pass_manifest=("P0", "P1", "P2"),
            invariant_digest="invariants@1",
            created_sequence=21,
            validity_regime="runtime@1",
        )

    def test_assurance_order_forbids_self_promotion(self):
        self.assertLess(ArtifactAssurance.DRAFT.rank, ArtifactAssurance.CHECKED.rank)
        with self.assertRaises(ValueError):
            SealCompiler.issue(
                seal_id="seal@bad",
                revision_id="seal@bad",
                plan_root_revision="plan@1",
                mission_revision=1,
                canonical_state_version=1,
                action_closure_refs=("deploy:red", "node@1", "proof@1"),
                sufficiency=self._sufficiency(),
                proof_contexts=(self._component("planner", ("w1",), assurance=ArtifactAssurance.DRAFT),),
                required_assurance=ArtifactAssurance.CHECKED,
                accepted_debt_refs=(),
                compiler_pass_manifest=("P0", "P1", "P2"),
                invariant_digest="invariants@1",
                created_sequence=21,
                validity_regime="runtime@1",
            )

    def test_decision_sufficiency_is_scope_specific_not_global_minimality(self):
        cert = self._sufficiency()
        self.assertTrue(cert.complete)
        self.assertEqual(cert.scope_ref, "action:deploy")
        self.assertIn("far-future-draft@9", cert.excluded_known_object_refs)

    def test_unrelated_far_future_draft_does_not_block_action_local_seal(self):
        seal = SealCompiler.issue(
            seal_id="seal@1",
            revision_id="seal@1",
            plan_root_revision="plan@1",
            mission_revision=1,
            canonical_state_version=1,
            action_closure_refs=("deploy:red", "node@1", "proof@1"),
            sufficiency=self._sufficiency(),
            proof_contexts=(self._component("checker", ("w1", "w2")),),
            required_assurance=ArtifactAssurance.CHECKED,
            accepted_debt_refs=(),
            compiler_pass_manifest=("P0", "P1", "P2"),
            invariant_digest="invariants@1",
            created_sequence=21,
            validity_regime="runtime@1",
        )
        self.assertEqual(seal.status, SealStatus.SEALED)
        self.assertNotIn("far-future-draft@9", seal.action_closure_refs)

    def test_pairwise_compatible_but_globally_inconsistent_contexts_fail(self):
        a = self._component("A", ("w1", "w2"))
        b = self._component("B", ("w2", "w3"))
        c = self._component("C", ("w1", "w3"))
        result = SealCompiler.compose_contexts((a, b, c), accepted_debt_refs=())
        self.assertEqual(result.status, CompositionStatus.NONCOMPOSABLE_CONFLICT)
        self.assertTrue(result.conflict_component_refs)

    def test_unknown_constraint_theory_never_becomes_composable(self):
        opaque = ProofContextComponent.create(
            component_ref="opaque",
            assurance=ArtifactAssurance.CHECKED,
            assumptions=(),
            scope="action:deploy",
            guarantee="G2",
            debt_refs=(),
            risk_refs=(),
            authority_refs=(),
            resource_refs=(),
            external_regime_refs=(),
            validity_horizon=(10, 50),
            constraint_theory="opaque-solver",
            allowed_worlds=(),
        )
        result = SealCompiler.compose_contexts((opaque,), accepted_debt_refs=())
        self.assertIn(result.status, {CompositionStatus.COMPOSITION_UNKNOWN, CompositionStatus.UNSUPPORTED_CONSTRAINT_THEORY})

    def test_unaccepted_debt_blocks_strong_seal(self):
        with self.assertRaises(ValueError):
            SealCompiler.issue(
                seal_id="seal@debt",
                revision_id="seal@debt",
                plan_root_revision="plan@1",
                mission_revision=1,
                canonical_state_version=1,
                action_closure_refs=("deploy:red", "node@1", "proof@1"),
                sufficiency=self._sufficiency(debt_refs=("debt:open",)),
                proof_contexts=(self._component("checker", ("w1",), debt_refs=("debt:open",)),),
                required_assurance=ArtifactAssurance.CHECKED,
                accepted_debt_refs=(),
                compiler_pass_manifest=("P0", "P1", "P2"),
                invariant_digest="invariants@1",
                created_sequence=21,
                validity_regime="runtime@1",
            )

    def test_explicitly_accepted_debt_remains_on_seal(self):
        seal = SealCompiler.issue(
            seal_id="seal@debt-ok",
            revision_id="seal@debt-ok",
            plan_root_revision="plan@1",
            mission_revision=1,
            canonical_state_version=1,
            action_closure_refs=("deploy:red", "node@1", "proof@1"),
            sufficiency=self._sufficiency(debt_refs=("debt:accepted",)),
            proof_contexts=(self._component("checker", ("w1",), debt_refs=("debt:accepted",)),),
            required_assurance=ArtifactAssurance.CHECKED,
            accepted_debt_refs=("debt:accepted",),
            compiler_pass_manifest=("P0", "P1", "P2"),
            invariant_digest="invariants@1",
            created_sequence=21,
            validity_regime="runtime@1",
        )
        self.assertEqual(seal.status, SealStatus.SEALED_WITH_ACCEPTED_DEBT)
        self.assertEqual(seal.accepted_debt_refs, ("debt:accepted",))

    def test_incomplete_sufficiency_cannot_issue_seal(self):
        with self.assertRaises(ValueError):
            SealCompiler.issue(
                seal_id="seal@incomplete",
                revision_id="seal@incomplete",
                plan_root_revision="plan@1",
                mission_revision=1,
                canonical_state_version=1,
                action_closure_refs=("deploy:red", "node@1", "proof@1"),
                sufficiency=self._sufficiency(complete=False),
                proof_contexts=(self._component("checker", ("w1",)),),
                required_assurance=ArtifactAssurance.CHECKED,
                accepted_debt_refs=(),
                compiler_pass_manifest=("P0", "P1", "P2"),
                invariant_digest="invariants@1",
                created_sequence=21,
                validity_regime="runtime@1",
            )

    def test_seal_digest_binds_exact_action_closure(self):
        common = dict(
            seal_id="seal",
            plan_root_revision="plan@1",
            mission_revision=1,
            canonical_state_version=1,
            sufficiency=self._sufficiency(),
            proof_contexts=(self._component("checker", ("w1",)),),
            required_assurance=ArtifactAssurance.CHECKED,
            accepted_debt_refs=(),
            compiler_pass_manifest=("P0", "P1", "P2"),
            invariant_digest="invariants@1",
            created_sequence=21,
            validity_regime="runtime@1",
        )
        a = SealCompiler.issue(revision_id="seal@1", action_closure_refs=("deploy:red", "node@1", "proof@1"), **common)
        b = SealCompiler.issue(revision_id="seal@2", action_closure_refs=("deploy:red", "node@1", "proof@2"), **common)
        self.assertNotEqual(a.canonical_digest, b.canonical_digest)

    def test_seal_invalidation_is_monotonic_and_recomputes_digest(self):
        sealed = self._seal("seal@1")
        stale = sealed.invalidate(SealStatus.STALE, revision_id="seal@2")
        self.assertEqual(stale.status, SealStatus.STALE)
        self.assertEqual(stale.revision_id, "seal@2")
        self.assertNotEqual(stale.canonical_digest, sealed.canonical_digest)

        revoked = stale.invalidate(SealStatus.REVOKED, revision_id="seal@3")
        self.assertEqual(revoked.status, SealStatus.REVOKED)
        self.assertNotEqual(revoked.canonical_digest, stale.canonical_digest)

        with self.assertRaises(ValueError):
            stale.invalidate(SealStatus.SEALED, revision_id="seal@4")
        with self.assertRaises(ValueError):
            revoked.invalidate(SealStatus.STALE, revision_id="seal@5")


if __name__ == "__main__":
    unittest.main()
