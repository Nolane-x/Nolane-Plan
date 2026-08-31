from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from nolane_plan import PlanKernel
from nolane_plan.actions import ActionIntent, AuthorityGrant
from nolane_plan.compaction_runtime import (
    _authority_lineage_refs,
    _make_archive,
    _proof_evidence_debt_refs,
    _unique_fallback_refs,
)
from nolane_plan.destructive_compaction import (
    DestructiveCompactionCoordinator,
    DestructiveCompactionError,
    DestructiveCompactionPhase,
    InjectedCompactionFault,
)
from nolane_plan.lineage_recovery import canonical_semantic_digest
from nolane_plan.production_store import (
    InMemoryProductionStore,
    StorageCapabilityProfile,
    StorageConflict,
)


class Wave9DestructiveCompactionTests(unittest.TestCase):
    def strong_store(self) -> InMemoryProductionStore:
        profile = StorageCapabilityProfile.create(
            backend_id="memory-strong",
            revision=1,
            atomic_replace=True,
            durable_acknowledgement=True,
            compare_and_swap=True,
            fencing_tokens=True,
            transactional_batch=True,
            destructive_delete=True,
            crash_recovery_durable=True,
        )
        return InMemoryProductionStore(profile, require_strong_multiwriter=True)

    def seeded_kernel(self) -> PlanKernel:
        kernel = PlanKernel.create(Path(tempfile.mkdtemp()), "destructive compaction")
        kernel.propose_action(ActionIntent("deploy", "deploy"))
        kernel.add_grant(AuthorityGrant("grant", "agent:a", frozenset({"deploy"})))
        kernel.authorize("deploy", "agent:a", ("grant",), 1)
        return kernel

    def fixture(self):
        kernel = self.seeded_kernel()
        archive = _make_archive(kernel)
        retained = tuple(sorted({
            *_authority_lineage_refs(kernel),
            *_proof_evidence_debt_refs(kernel),
            *_unique_fallback_refs(kernel),
        }))
        return kernel, archive, retained

    def prepare(self, coordinator: DestructiveCompactionCoordinator, epoch, kernel, archive, retained):
        return coordinator.prepare(
            compaction_id="dc:1",
            source_representation_id="source:r1",
            target_representation_id="target:r1",
            source_archive=archive,
            source_canonical_semantic_digest=canonical_semantic_digest(kernel),
            active_authority_refs=_authority_lineage_refs(kernel),
            dormant_resurrection_refs=(),
            proof_evidence_debt_refs=_proof_evidence_debt_refs(kernel),
            unique_fallback_refs=_unique_fallback_refs(kernel),
            authority_epoch=epoch,
        )

    def test_prepare_is_durable_and_captures_exact_retention_closure(self) -> None:
        kernel, archive, retained = self.fixture()
        store = self.strong_store()
        epoch = store.acquire_epoch("compactor", expected_epoch=None)
        coordinator = DestructiveCompactionCoordinator(store)
        result = self.prepare(coordinator, epoch, kernel, archive, retained)

        self.assertEqual(result.phase, DestructiveCompactionPhase.PREPARED)
        state = coordinator.recover("dc:1")
        self.assertEqual(state.phase, DestructiveCompactionPhase.PREPARED)
        self.assertEqual(set(state.intent.retained_refs), set(retained))
        self.assertEqual(state.intent.source_archive_digest, archive.canonical_digest)
        self.assertEqual(coordinator.production_pointer(), "source:r1")
        self.assertEqual(set(coordinator.representation_ids()), {"source:r1"})

    def test_shadow_must_reconstruct_exact_source_semantics_before_switch(self) -> None:
        kernel, archive, retained = self.fixture()
        store = self.strong_store()
        epoch = store.acquire_epoch("compactor", expected_epoch=None)
        coordinator = DestructiveCompactionCoordinator(store)
        self.prepare(coordinator, epoch, kernel, archive, retained)

        result = coordinator.write_shadow("dc:1", archive, authority_epoch=epoch)
        self.assertEqual(result.phase, DestructiveCompactionPhase.SHADOW_WRITTEN)
        self.assertEqual(coordinator.production_pointer(), "source:r1")
        self.assertEqual(set(coordinator.representation_ids()), {"source:r1", "target:r1"})

        other = PlanKernel.create(Path(tempfile.mkdtemp()), "different semantics")
        other_archive = _make_archive(other)
        store2 = self.strong_store()
        epoch2 = store2.acquire_epoch("compactor", expected_epoch=None)
        coordinator2 = DestructiveCompactionCoordinator(store2)
        self.prepare(coordinator2, epoch2, kernel, archive, retained)
        with self.assertRaises(DestructiveCompactionError):
            coordinator2.write_shadow("dc:1", other_archive, authority_epoch=epoch2)
        self.assertEqual(coordinator2.production_pointer(), "source:r1")

    def test_switch_is_one_cas_pointer_change_and_source_still_exists(self) -> None:
        kernel, archive, retained = self.fixture()
        store = self.strong_store()
        epoch = store.acquire_epoch("compactor", expected_epoch=None)
        coordinator = DestructiveCompactionCoordinator(store)
        self.prepare(coordinator, epoch, kernel, archive, retained)
        coordinator.write_shadow("dc:1", archive, authority_epoch=epoch)
        before_revision = store.current_revision()
        result = coordinator.commit_switch("dc:1", authority_epoch=epoch)

        self.assertEqual(result.phase, DestructiveCompactionPhase.SWITCH_COMMITTED)
        self.assertEqual(store.current_revision(), before_revision + 1)
        self.assertEqual(coordinator.production_pointer(), "target:r1")
        self.assertEqual(set(coordinator.representation_ids()), {"source:r1", "target:r1"})
        self.assertEqual(result.switch_receipt.expected_storage_revision, before_revision)
        self.assertEqual(result.switch_receipt.committed_storage_revision, before_revision + 1)

    def test_source_retirement_is_forbidden_before_switch_and_exact_after_switch(self) -> None:
        kernel, archive, retained = self.fixture()
        store = self.strong_store()
        epoch = store.acquire_epoch("compactor", expected_epoch=None)
        coordinator = DestructiveCompactionCoordinator(store)
        self.prepare(coordinator, epoch, kernel, archive, retained)
        coordinator.write_shadow("dc:1", archive, authority_epoch=epoch)

        with self.assertRaises(DestructiveCompactionError):
            coordinator.retire_source("dc:1", authority_epoch=epoch)
        self.assertIn("source:r1", coordinator.representation_ids())

        coordinator.commit_switch("dc:1", authority_epoch=epoch)
        result = coordinator.retire_source("dc:1", authority_epoch=epoch)
        self.assertEqual(result.phase, DestructiveCompactionPhase.SOURCE_RETIRED)
        self.assertEqual(result.retirement_manifest.delete_representation_ids, ("source:r1",))
        self.assertEqual(coordinator.production_pointer(), "target:r1")
        self.assertEqual(coordinator.representation_ids(), ("target:r1",))

    def test_repeated_retirement_is_idempotent_and_cannot_broaden_deletion_set(self) -> None:
        kernel, archive, retained = self.fixture()
        store = self.strong_store()
        epoch = store.acquire_epoch("compactor", expected_epoch=None)
        coordinator = DestructiveCompactionCoordinator(store)
        self.prepare(coordinator, epoch, kernel, archive, retained)
        coordinator.write_shadow("dc:1", archive, authority_epoch=epoch)
        coordinator.commit_switch("dc:1", authority_epoch=epoch)
        first = coordinator.retire_source("dc:1", authority_epoch=epoch)
        revision = store.current_revision()
        second = coordinator.retire_source("dc:1", authority_epoch=epoch)

        self.assertEqual(first.retirement_manifest.canonical_digest, second.retirement_manifest.canonical_digest)
        self.assertEqual(store.current_revision(), revision)
        self.assertEqual(coordinator.representation_ids(), ("target:r1",))

    def test_stale_writer_cannot_switch_or_retire_after_epoch_advance(self) -> None:
        kernel, archive, retained = self.fixture()
        store = self.strong_store()
        old_epoch = store.acquire_epoch("compactor-a", expected_epoch=None)
        coordinator = DestructiveCompactionCoordinator(store)
        self.prepare(coordinator, old_epoch, kernel, archive, retained)
        coordinator.write_shadow("dc:1", archive, authority_epoch=old_epoch)
        store.acquire_epoch("writer-b", expected_epoch=old_epoch.epoch)

        with self.assertRaises(StorageConflict):
            coordinator.commit_switch("dc:1", authority_epoch=old_epoch)
        self.assertEqual(coordinator.production_pointer(), "source:r1")

    def test_fault_after_each_durable_phase_recovers_only_that_phase(self) -> None:
        phases = (
            DestructiveCompactionPhase.PREPARED,
            DestructiveCompactionPhase.SHADOW_WRITTEN,
            DestructiveCompactionPhase.SWITCH_COMMITTED,
            DestructiveCompactionPhase.SOURCE_RETIRED,
            DestructiveCompactionPhase.VERIFIED,
        )
        for fault_phase in phases:
            with self.subTest(fault_phase=fault_phase.value):
                kernel, archive, retained = self.fixture()
                store = self.strong_store()
                epoch = store.acquire_epoch("compactor", expected_epoch=None)
                coordinator = DestructiveCompactionCoordinator(store)
                with self.assertRaises(InjectedCompactionFault):
                    if fault_phase == DestructiveCompactionPhase.PREPARED:
                        self.prepare_with_fault(coordinator, epoch, kernel, archive, fault_phase)
                    else:
                        self.prepare(coordinator, epoch, kernel, archive, retained)
                        if fault_phase == DestructiveCompactionPhase.SHADOW_WRITTEN:
                            coordinator.write_shadow("dc:1", archive, authority_epoch=epoch, fault_after=fault_phase)
                        else:
                            coordinator.write_shadow("dc:1", archive, authority_epoch=epoch)
                            if fault_phase == DestructiveCompactionPhase.SWITCH_COMMITTED:
                                coordinator.commit_switch("dc:1", authority_epoch=epoch, fault_after=fault_phase)
                            else:
                                coordinator.commit_switch("dc:1", authority_epoch=epoch)
                                if fault_phase == DestructiveCompactionPhase.SOURCE_RETIRED:
                                    coordinator.retire_source("dc:1", authority_epoch=epoch, fault_after=fault_phase)
                                else:
                                    coordinator.retire_source("dc:1", authority_epoch=epoch)
                                    coordinator.verify("dc:1", authority_epoch=epoch, fault_after=fault_phase)
                reopened = DestructiveCompactionCoordinator(store)
                self.assertEqual(reopened.recover("dc:1").phase, fault_phase)

    def prepare_with_fault(self, coordinator, epoch, kernel, archive, phase):
        return coordinator.prepare(
            compaction_id="dc:1",
            source_representation_id="source:r1",
            target_representation_id="target:r1",
            source_archive=archive,
            source_canonical_semantic_digest=canonical_semantic_digest(kernel),
            active_authority_refs=_authority_lineage_refs(kernel),
            dormant_resurrection_refs=(),
            proof_evidence_debt_refs=_proof_evidence_debt_refs(kernel),
            unique_fallback_refs=_unique_fallback_refs(kernel),
            authority_epoch=epoch,
            fault_after=phase,
        )

    def test_tampered_internal_retirement_manifest_fails_closed_with_valid_outer_cas(self) -> None:
        kernel, archive, retained = self.fixture()
        store = self.strong_store()
        epoch = store.acquire_epoch("compactor", expected_epoch=None)
        coordinator = DestructiveCompactionCoordinator(store)
        self.prepare(coordinator, epoch, kernel, archive, retained)
        coordinator.write_shadow("dc:1", archive, authority_epoch=epoch)
        coordinator.commit_switch("dc:1", authority_epoch=epoch)
        coordinator.retire_source("dc:1", authority_epoch=epoch)

        payload = store.read_payload()
        payload["destructive_compactions"]["dc:1"]["retirement_manifest"]["canonical_digest"] = "tampered"
        store.conditional_commit(epoch, expected_revision=store.current_revision(), payload=payload)
        with self.assertRaises(DestructiveCompactionError):
            DestructiveCompactionCoordinator(store).recover("dc:1")

    def test_mixed_switch_phase_and_source_pointer_fails_closed(self) -> None:
        kernel, archive, retained = self.fixture()
        store = self.strong_store()
        epoch = store.acquire_epoch("compactor", expected_epoch=None)
        coordinator = DestructiveCompactionCoordinator(store)
        self.prepare(coordinator, epoch, kernel, archive, retained)
        coordinator.write_shadow("dc:1", archive, authority_epoch=epoch)
        coordinator.commit_switch("dc:1", authority_epoch=epoch)

        payload = store.read_payload()
        payload["production_pointer"] = "source:r1"
        store.conditional_commit(epoch, expected_revision=store.current_revision(), payload=payload)
        with self.assertRaises(DestructiveCompactionError):
            DestructiveCompactionCoordinator(store).recover("dc:1")

    def test_final_verification_reconstructs_target_and_preserves_retained_refs(self) -> None:
        kernel, archive, retained = self.fixture()
        store = self.strong_store()
        epoch = store.acquire_epoch("compactor", expected_epoch=None)
        coordinator = DestructiveCompactionCoordinator(store)
        self.prepare(coordinator, epoch, kernel, archive, retained)
        coordinator.write_shadow("dc:1", archive, authority_epoch=epoch)
        coordinator.commit_switch("dc:1", authority_epoch=epoch)
        coordinator.retire_source("dc:1", authority_epoch=epoch)
        result = coordinator.verify("dc:1", authority_epoch=epoch)

        self.assertEqual(result.phase, DestructiveCompactionPhase.VERIFIED)
        self.assertEqual(result.source_semantic_root_digest, result.target_semantic_root_digest)
        self.assertEqual(result.source_canonical_semantic_digest, result.target_canonical_semantic_digest)
        target = coordinator.production_representation()
        self.assertEqual(set(target.retained_refs), set(retained))
        self.assertEqual(target.archive.reconstruct().semantic_root_digest(), kernel.lineage.semantic_root_digest())


if __name__ == "__main__":
    unittest.main()
