from __future__ import annotations

import unittest

from nolane_plan.support import (
    ArtifactAuthorityAssessment,
    InvalidityCause,
    SupportAlternativeSetRevision,
    SupportClause,
    SupportEvaluator,
    SupportNode,
    SupportStatus,
)


class Wave4SupportTests(unittest.TestCase):
    def _node(self, ref: str, *, roots=("root:host",), support_refs=(), current=True, context=("prod",)):
        return SupportNode(
            ref=ref,
            current=current,
            direct_grounding_roots=frozenset(roots),
            support_refs=tuple(support_refs),
            scope="mission",
            assumption_basis=frozenset({"assumption@1"}),
            proof_kind="verification",
            validity_regime="runtime@1",
            context_tags=frozenset(context),
        )

    def _clause(self, clause_id: str, refs, *, min_roots=1, context=("prod",)):
        return SupportClause(
            clause_id=clause_id,
            required_support_refs=tuple(refs),
            scope="mission",
            assumption_basis=frozenset({"assumption@1"}),
            proof_kind="verification",
            grounding_root_requirements=frozenset(),
            validity_regime="runtime@1",
            context_tags=frozenset(context),
            minimum_independent_roots=min_roots,
        )

    def _support_set(self, clauses):
        return SupportAlternativeSetRevision.create(
            support_set_id="support-set",
            revision_id="support-set@1",
            subject_artifact_revision="proof@1",
            clauses=tuple(clauses),
            scope="mission",
            assumption_context_rules=("prod",),
            proof_kind="verification",
            grounding_policy="accepted-roots-only",
            support_evaluation_profile="bounded-dnf@1",
            created_sequence=30,
        )

    def test_one_surviving_or_alternative_keeps_support(self):
        support_set = self._support_set((self._clause("c1", ("e1",)), self._clause("c2", ("e2",))))
        nodes = {"e1": self._node("e1", current=False), "e2": self._node("e2", roots=("root:other",))}
        result = SupportEvaluator.evaluate(support_set, nodes, active_context={"prod"}, evaluated_at_cut="cut@9", generation=5)
        self.assertEqual(result.status, SupportStatus.SUPPORTED)
        self.assertEqual(result.surviving_clause_refs, ("c2",))

    def test_conjunctive_clause_fails_when_any_leaf_is_stale(self):
        support_set = self._support_set((self._clause("c1", ("e1", "e2")),))
        nodes = {"e1": self._node("e1"), "e2": self._node("e2", current=False)}
        result = SupportEvaluator.evaluate(support_set, nodes, active_context={"prod"}, evaluated_at_cut="cut@9", generation=5)
        self.assertEqual(result.status, SupportStatus.UNSUPPORTED)

    def test_empty_alternative_set_is_unsupported(self):
        result = SupportEvaluator.evaluate(self._support_set(()), {}, active_context={"prod"}, evaluated_at_cut="cut@9", generation=5)
        self.assertEqual(result.status, SupportStatus.UNSUPPORTED)

    def test_empty_clause_does_not_create_grounding_root(self):
        support_set = self._support_set((self._clause("empty", ()),))
        result = SupportEvaluator.evaluate(support_set, {}, active_context={"prod"}, evaluated_at_cut="cut@9", generation=5)
        self.assertEqual(result.status, SupportStatus.UNSUPPORTED)

    def test_context_incompatible_alternative_does_not_support_global_claim(self):
        support_set = self._support_set((self._clause("c1", ("e1",), context=("staging",)),))
        nodes = {"e1": self._node("e1", context=("staging",))}
        result = SupportEvaluator.evaluate(support_set, nodes, active_context={"prod"}, evaluated_at_cut="cut@9", generation=5)
        self.assertEqual(result.status, SupportStatus.UNSUPPORTED)

    def test_ungrounded_circular_nodes_do_not_self_support(self):
        support_set = self._support_set((self._clause("c1", ("a",)),))
        nodes = {
            "a": self._node("a", roots=(), support_refs=("b",)),
            "b": self._node("b", roots=(), support_refs=("a",)),
        }
        result = SupportEvaluator.evaluate(support_set, nodes, active_context={"prod"}, evaluated_at_cut="cut@9", generation=5)
        self.assertEqual(result.status, SupportStatus.UNSUPPORTED)

    def test_duplicate_common_root_does_not_fake_independent_support(self):
        support_set = self._support_set((self._clause("c1", ("e1", "e2"), min_roots=2),))
        nodes = {
            "e1": self._node("e1", roots=("root:same",)),
            "e2": self._node("e2", roots=("root:same",)),
        }
        result = SupportEvaluator.evaluate(support_set, nodes, active_context={"prod"}, evaluated_at_cut="cut@9", generation=5)
        self.assertEqual(result.status, SupportStatus.UNSUPPORTED)

    def test_distinct_roots_can_satisfy_independence_floor(self):
        support_set = self._support_set((self._clause("c1", ("e1", "e2"), min_roots=2),))
        nodes = {
            "e1": self._node("e1", roots=("root:one",)),
            "e2": self._node("e2", roots=("root:two",)),
        }
        result = SupportEvaluator.evaluate(support_set, nodes, active_context={"prod"}, evaluated_at_cut="cut@9", generation=5)
        self.assertEqual(result.status, SupportStatus.SUPPORTED)

    def test_no_blocker_does_not_make_unsupported_artifact_usable(self):
        unsupported = SupportEvaluator.evaluate(self._support_set(()), {}, active_context={"prod"}, evaluated_at_cut="cut@9", generation=5)
        authority = ArtifactAuthorityAssessment(unsupported, ())
        self.assertFalse(authority.current_usable)

    def test_active_blocker_prevents_use_even_with_positive_support(self):
        support_set = self._support_set((self._clause("c1", ("e1",)),))
        supported = SupportEvaluator.evaluate(support_set, {"e1": self._node("e1")}, active_context={"prod"}, evaluated_at_cut="cut@9", generation=5)
        blocker = InvalidityCause("verifier-revoked", "VERIFIER_TRUST_REVOKED", active=True, blocking=True)
        self.assertFalse(ArtifactAuthorityAssessment(supported, (blocker,)).current_usable)

    def test_clearing_blocker_cannot_resurrect_when_support_is_gone(self):
        unsupported = SupportEvaluator.evaluate(self._support_set(()), {}, active_context={"prod"}, evaluated_at_cut="cut@9", generation=5)
        cleared = InvalidityCause("old", "PROFILE_STALE", active=False, blocking=True)
        self.assertFalse(ArtifactAuthorityAssessment(unsupported, (cleared,)).current_usable)

    def test_historical_assessment_is_immutable_after_new_retraction(self):
        support_set = self._support_set((self._clause("c1", ("e1",)),))
        old = SupportEvaluator.evaluate(support_set, {"e1": self._node("e1")}, active_context={"prod"}, evaluated_at_cut="cut@9", generation=5)
        new = SupportEvaluator.evaluate(support_set, {"e1": self._node("e1", current=False)}, active_context={"prod"}, evaluated_at_cut="cut@10", generation=6)
        self.assertEqual(old.status, SupportStatus.SUPPORTED)
        self.assertEqual(new.status, SupportStatus.UNSUPPORTED)
        self.assertEqual(old.evaluated_at_cut, "cut@9")


if __name__ == "__main__":
    unittest.main()
