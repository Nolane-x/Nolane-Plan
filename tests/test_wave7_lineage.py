from __future__ import annotations

import unittest

from nolane_plan.lineage import (
    CanonicalLineageRevision,
    LineageError,
    LineageRegistry,
    SemanticRegimeKind,
    SemanticRegimeRevision,
)


class Wave7LineageTests(unittest.TestCase):
    def make_revision(
        self,
        *,
        logical_id: str = "future:primary",
        revision_id: str = "future:primary:r1",
        semantic_digest: str = "semantic-a",
        created_sequence: int = 1,
        parent_revision_ids=(),
        supersedes_revision_id=None,
        wall_time: float | None = 100.0,
    ) -> CanonicalLineageRevision:
        return CanonicalLineageRevision.create(
            object_family="FutureFamily",
            logical_id=logical_id,
            revision_id=revision_id,
            schema_version="schema:v7",
            created_sequence=created_sequence,
            created_at_wall_time=wall_time,
            mission_revision_dependency="mission:r1",
            plan_revision=1,
            world_model_revision="world:r1",
            environment_regime_revision="environment:r1",
            validity_regime="ACTIVE",
            parent_revision_ids=parent_revision_ids,
            provenance_refs=("source:b", "source:a", "source:a"),
            assurance_profile="KERNEL_ACCEPTED",
            debt_refs=("debt:b", "debt:a", "debt:a"),
            supersedes_revision_id=supersedes_revision_id,
            semantic_digest=semantic_digest,
        )

    def test_stable_logical_identity_can_advance_immutable_revision(self):
        registry = LineageRegistry()
        r1 = registry.register(self.make_revision())
        r2 = registry.register(
            self.make_revision(
                revision_id="future:primary:r2",
                semantic_digest="semantic-b",
                created_sequence=2,
                parent_revision_ids=(r1.revision_id,),
                supersedes_revision_id=r1.revision_id,
            )
        )
        self.assertEqual(r1.logical_id, r2.logical_id)
        self.assertEqual(registry.current("FutureFamily", "future:primary"), r2)
        self.assertEqual(registry.get(r1.revision_id), r1)

    def test_revision_id_cannot_be_rebound_to_different_content(self):
        registry = LineageRegistry()
        registry.register(self.make_revision())
        with self.assertRaises(LineageError):
            registry.register(self.make_revision(semantic_digest="changed"))

    def test_revision_id_cannot_alias_another_logical_identity(self):
        registry = LineageRegistry()
        registry.register(self.make_revision())
        with self.assertRaises(LineageError):
            registry.register(
                self.make_revision(
                    logical_id="future:other",
                    revision_id="future:primary:r1",
                    semantic_digest="semantic-other",
                    created_sequence=2,
                )
            )

    def test_parent_must_exist_unless_explicit_legacy_root(self):
        registry = LineageRegistry()
        with self.assertRaises(LineageError):
            registry.register(
                self.make_revision(
                    revision_id="future:primary:r2",
                    created_sequence=2,
                    parent_revision_ids=("missing-parent",),
                )
            )
        legacy = self.make_revision(revision_id="legacy:r1")
        registry.register(legacy, imported_legacy_root=True)
        self.assertEqual(registry.get("legacy:r1"), legacy)

    def test_parent_cycle_is_rejected(self):
        registry = LineageRegistry()
        r1 = registry.register(self.make_revision())
        r2 = registry.register(
            self.make_revision(
                revision_id="future:primary:r2",
                semantic_digest="semantic-b",
                created_sequence=2,
                parent_revision_ids=(r1.revision_id,),
                supersedes_revision_id=r1.revision_id,
            )
        )
        with self.assertRaises(LineageError):
            registry.register(
                self.make_revision(
                    revision_id="future:primary:r3",
                    semantic_digest="semantic-c",
                    created_sequence=3,
                    parent_revision_ids=(r2.revision_id, "future:primary:r3"),
                    supersedes_revision_id=r2.revision_id,
                )
            )

    def test_created_sequence_cannot_move_backwards_for_logical_identity(self):
        registry = LineageRegistry()
        r1 = registry.register(self.make_revision(created_sequence=10))
        with self.assertRaises(LineageError):
            registry.register(
                self.make_revision(
                    revision_id="future:primary:r2",
                    semantic_digest="semantic-b",
                    created_sequence=9,
                    parent_revision_ids=(r1.revision_id,),
                    supersedes_revision_id=r1.revision_id,
                )
            )

    def test_set_like_lineage_refs_are_canonical_and_digest_stable(self):
        a = self.make_revision()
        b = CanonicalLineageRevision.create(
            object_family="FutureFamily",
            logical_id="future:primary",
            revision_id="future:primary:r1",
            schema_version="schema:v7",
            created_sequence=1,
            created_at_wall_time=100.0,
            mission_revision_dependency="mission:r1",
            plan_revision=1,
            world_model_revision="world:r1",
            environment_regime_revision="environment:r1",
            validity_regime="ACTIVE",
            parent_revision_ids=(),
            provenance_refs=("source:a", "source:b"),
            assurance_profile="KERNEL_ACCEPTED",
            debt_refs=("debt:a", "debt:b"),
            supersedes_revision_id=None,
            semantic_digest="semantic-a",
        )
        self.assertEqual(a.provenance_refs, ("source:a", "source:b"))
        self.assertEqual(a.debt_refs, ("debt:a", "debt:b"))
        self.assertEqual(a.lineage_digest, b.lineage_digest)

    def test_lineage_digest_changes_when_correctness_semantic_changes(self):
        a = self.make_revision()
        b = self.make_revision(semantic_digest="semantic-b")
        self.assertNotEqual(a.lineage_digest, b.lineage_digest)

    def test_wall_clock_is_informational_not_revision_identity(self):
        a = self.make_revision(wall_time=100.0)
        b = self.make_revision(wall_time=999.0)
        self.assertEqual(a.lineage_digest, b.lineage_digest)

    def test_semantic_root_digest_is_insertion_order_independent(self):
        r1 = self.make_revision()
        other = CanonicalLineageRevision.create(
            object_family="StrategicObligation",
            logical_id="obligation:rollback",
            revision_id="obligation:rollback:r1",
            schema_version="schema:v7",
            created_sequence=2,
            created_at_wall_time=None,
            mission_revision_dependency="mission:r1",
            plan_revision=1,
            world_model_revision="world:r1",
            environment_regime_revision="environment:r1",
            validity_regime="ACTIVE",
            parent_revision_ids=(),
            provenance_refs=("mission:r1",),
            assurance_profile="KERNEL_ACCEPTED",
            debt_refs=(),
            supersedes_revision_id=None,
            semantic_digest="obligation-semantic",
        )
        left, right = LineageRegistry(), LineageRegistry()
        left.register(r1)
        left.register(other)
        right.register(other)
        right.register(r1)
        self.assertEqual(left.semantic_root_digest(), right.semantic_root_digest())

    def test_semantic_regime_revision_is_immutable_and_typed(self):
        regime = SemanticRegimeRevision.create(
            regime_kind=SemanticRegimeKind.ENVIRONMENT,
            logical_id="environment:host",
            revision_id="environment:r1",
            created_sequence=1,
            parent_revision_id=None,
            semantic_digest="env-semantic",
            provenance_refs=("host:config",),
        )
        registry = LineageRegistry()
        registry.register_regime(regime)
        self.assertEqual(registry.current_regime(SemanticRegimeKind.ENVIRONMENT), regime)
        with self.assertRaises(LineageError):
            registry.register_regime(
                SemanticRegimeRevision.create(
                    regime_kind=SemanticRegimeKind.ENVIRONMENT,
                    logical_id="environment:host",
                    revision_id="environment:r1",
                    created_sequence=2,
                    parent_revision_id=None,
                    semantic_digest="changed",
                    provenance_refs=("host:config",),
                )
            )

    def test_regime_revision_requires_existing_parent_and_monotonic_sequence(self):
        registry = LineageRegistry()
        first = SemanticRegimeRevision.create(
            regime_kind="SCHEMA",
            logical_id="schema:nolane-plan",
            revision_id="schema:r1",
            created_sequence=5,
            parent_revision_id=None,
            semantic_digest="schema-1",
            provenance_refs=("runtime",),
        )
        registry.register_regime(first)
        with self.assertRaises(LineageError):
            registry.register_regime(
                SemanticRegimeRevision.create(
                    regime_kind="SCHEMA",
                    logical_id="schema:nolane-plan",
                    revision_id="schema:r2",
                    created_sequence=4,
                    parent_revision_id="schema:r1",
                    semantic_digest="schema-2",
                    provenance_refs=("runtime",),
                )
            )
        with self.assertRaises(LineageError):
            registry.register_regime(
                SemanticRegimeRevision.create(
                    regime_kind="WORLD_MODEL",
                    logical_id="world:default",
                    revision_id="world:r2",
                    created_sequence=6,
                    parent_revision_id="missing",
                    semantic_digest="world-2",
                    provenance_refs=("runtime",),
                )
            )


if __name__ == "__main__":
    unittest.main()
