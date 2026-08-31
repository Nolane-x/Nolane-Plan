from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from nolane_plan import PlanKernel
from nolane_plan.actions import ActionIntent, AuthorityGrant
from nolane_plan.execution import AdapterProfile
from nolane_plan.execution_contract import (
    CancellationClass,
    DispatchAcknowledgementClass,
    ExecutionContract,
    IdempotencyGuaranteeClass,
    OutcomeFinalityClass,
)
from nolane_plan.hashing import digest
from nolane_plan.multiwriter import MultiWriterCoordinator, WriteIntent, WriterIdentity
from nolane_plan.production_store import InMemoryProductionStore, StorageCapabilityProfile
from nolane_plan.types import ReplayError, RiskClass


class Wave9ReplayRestartTests(unittest.TestCase):
    def store(self, backend_id: str = "wave9-restart-store") -> InMemoryProductionStore:
        return InMemoryProductionStore(
            StorageCapabilityProfile.create(
                backend_id=backend_id,
                revision=1,
                atomic_replace=True,
                durable_acknowledgement=True,
                compare_and_swap=True,
                fencing_tokens=True,
                transactional_batch=True,
                destructive_delete=True,
                crash_recovery_durable=True,
            ),
            require_strong_multiwriter=True,
        )

    def writer(self, writer_id: str) -> WriterIdentity:
        return WriterIdentity.create(
            writer_id=writer_id,
            principal_ref="agent",
            process_instance_ref=f"process:{writer_id}:1",
        )

    def execution_contract(self) -> ExecutionContract:
        return ExecutionContract.create(
            adapter_id="remote",
            adapter_revision=1,
            dispatch_acknowledgement=DispatchAcknowledgementClass.DURABLE_REMOTE,
            idempotency_guarantee=IdempotencyGuaranteeClass.REMOTE_DEDUPLICATED,
            deduplication_keys=True,
            remote_fencing_tokens=True,
            cancellation_class=CancellationClass.FENCED_EFFECT,
            cancellation_ack_assurance=0.9,
            compensation_supported=True,
            reconciliation_observable=True,
            outcome_finality=OutcomeFinalityClass.OBSERVABLE,
        )

    def prepare_authorization(self, kernel: PlanKernel):
        kernel.register_adapter(AdapterProfile("remote", 1, False, False, 1.0))
        contract = kernel.register_execution_contract(self.execution_contract())
        action = ActionIntent("effect", "effect", RiskClass.REVERSIBLE, idempotent=False)
        kernel.propose_action(action)
        kernel.add_grant(AuthorityGrant("grant", "agent", frozenset({"effect"})))
        authorization = kernel.authorize("effect", "agent", ("grant",), 1, adapter_id="remote")
        kernel.bind_authorization_execution_contract(authorization.id)
        return contract, authorization

    def prepare_multiwriter_state(self, kernel: PlanKernel, store: InMemoryProductionStore):
        contract, authorization = self.prepare_authorization(kernel)
        coordinator = MultiWriterCoordinator(store)
        lease = kernel.acquire_authority_epoch(coordinator, self.writer("w1"), None)
        binding = kernel.bind_authorization_authority_epoch(authorization.id, lease)
        intent = WriteIntent.create(
            intent_id="intent:restart",
            writer_id="w1",
            operation_kind="canonical_update",
            payload={"value": 1},
            idempotent=True,
            idempotency_key="restart:1",
            conflict_scope="canonical:restart",
            external_effect_possible=False,
        )
        decision = kernel.conditional_correctness_commit(coordinator, intent, lease, expected_revision=0)
        return contract, authorization, coordinator, lease, binding, decision

    def test_pre_snapshot_execution_and_multiwriter_state_survives_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            path = Path(root)
            kernel = PlanKernel.create(path, "Wave 9 snapshot round trip")
            store = self.store()
            contract, authorization, _, lease, binding, decision = self.prepare_multiwriter_state(kernel, store)
            kernel.save_snapshot()

            restored = PlanKernel.open(path)
            contract_key = "remote@1"
            self.assertEqual(restored.execution_contracts[contract_key].canonical_digest, contract.canonical_digest)
            self.assertEqual(
                restored.authorization_execution_contract_bindings[authorization.id],
                contract.canonical_digest,
            )
            self.assertEqual(
                restored.observed_authority_epochs[lease.epoch.canonical_digest].canonical_digest,
                lease.canonical_digest,
            )
            self.assertEqual(
                restored.authorization_authority_epoch_bindings[authorization.id].canonical_digest,
                binding.canonical_digest,
            )
            observations = tuple(restored.multiwriter_commit_observations.values())
            self.assertEqual(len(observations), 1)
            self.assertEqual(observations[0].storage_revision, decision.storage_revision)
            self.assertFalse(hasattr(restored, "production_store"))

    def test_pre_snapshot_destructive_compaction_observation_survives_without_recreating_store(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            path = Path(root)
            kernel = PlanKernel.create(path, "Wave 9 compaction snapshot")
            kernel.propose_action(ActionIntent("deploy", "deploy"))
            kernel.add_grant(AuthorityGrant("grant:deploy", "agent", frozenset({"deploy"})))
            kernel.authorize("deploy", "agent", ("grant:deploy",), 1)
            store = self.store("wave9-compaction-restart-store")
            epoch = store.acquire_epoch("compactor", None)
            kernel.prepare_destructive_compaction(
                store,
                epoch,
                compaction_id="dc:snapshot",
                source_representation_id="source:r1",
                target_representation_id="target:r1",
            )
            expected = kernel.destructive_compaction_observations["dc:snapshot"]
            kernel.save_snapshot()

            restored = PlanKernel.open(path)
            self.assertEqual(restored.destructive_compaction_observations["dc:snapshot"], expected)
            self.assertFalse(hasattr(restored, "production_store"))
            self.assertEqual(store.read_payload()["production_pointer"], "source:r1")

    def test_snapshot_epoch_n_plus_epoch_n1_suffix_replays_exactly(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            path = Path(root)
            kernel = PlanKernel.create(path, "Wave 9 snapshot plus suffix")
            store = self.store()
            _, authorization, coordinator, lease1, binding1, _ = self.prepare_multiwriter_state(kernel, store)
            kernel.save_snapshot()

            lease2 = kernel.acquire_authority_epoch(coordinator, self.writer("w2"), lease1.epoch.epoch)
            binding2 = kernel.bind_authorization_authority_epoch(authorization.id, lease2)
            self.assertNotEqual(binding1.canonical_digest, binding2.canonical_digest)

            restored = PlanKernel.open(path)
            self.assertEqual(restored.latest_observed_authority_epoch.canonical_digest, lease2.canonical_digest)
            self.assertEqual(
                restored.authorization_authority_epoch_bindings[authorization.id].canonical_digest,
                binding2.canonical_digest,
            )
            self.assertEqual(len(restored.observed_authority_epochs), 2)

    def test_wave9_snapshot_envelope_has_internal_digest_and_tamper_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            path = Path(root)
            kernel = PlanKernel.create(path, "Wave 9 tamper")
            store = self.store()
            _, authorization, _, _, _, _ = self.prepare_multiwriter_state(kernel, store)
            state = kernel.save_snapshot()
            self.assertEqual(state["snapshot_schema"], "nolane-plan-runtime-snapshot-v9")
            wave9 = state["wave9"]
            self.assertEqual(wave9["canonical_digest"], digest({k: v for k, v in wave9.items() if k != "canonical_digest"}))

            snapshot_path = path / "snapshot.json"
            document = json.loads(snapshot_path.read_text(encoding="utf-8"))
            binding = document["state"]["wave9"]["multiwriter"]["authorization_epoch_bindings"][authorization.id]
            binding["epoch"] = int(binding["epoch"]) + 1
            document["digest"] = digest(document["state"])
            snapshot_path.write_text(json.dumps(document, sort_keys=True, separators=(",", ":")), encoding="utf-8")
            with self.assertRaises(ReplayError):
                PlanKernel.open(path)


if __name__ == "__main__":
    unittest.main()
