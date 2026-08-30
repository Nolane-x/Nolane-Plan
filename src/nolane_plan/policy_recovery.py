from __future__ import annotations

from pathlib import Path
from typing import Any

from .hashing import digest
from .mission import MissionContract, MissionLedger
from .persistence import HashJournal, SnapshotStore
from .policy_codec import (
    epoch_doc,
    epoch_from_doc,
    executability_doc,
    executability_from_doc,
    frontier_doc,
    frontier_from_doc,
    node_doc,
    node_from_doc,
    partition_doc,
    partition_from_doc,
    seal_doc,
    seal_from_doc,
    selection_doc,
    selection_from_doc,
    sufficiency_doc,
    sufficiency_from_doc,
)
from .proof_recovery import PROOF_SNAPSHOT_SCHEMA, _replay_entry as _replay_proof_entry, _restore_proof_state
from .resume import SNAPSHOT_SCHEMA as BASE_SNAPSHOT_SCHEMA
from .resume import _find_snapshot_prefix, _restore_state
from .trust_recovery import TRUST_SNAPSHOT_SCHEMA, _restore_trust_state
from .types import ReplayError


POLICY_SNAPSHOT_SCHEMA = "nolane-plan-runtime-snapshot-v5"


def _policy_state(self) -> dict[str, Any]:
    return {
        "frontiers": [frontier_doc(value) for value in sorted(self.policy_frontiers.values(), key=lambda x: x.revision_id)],
        "partitions": [partition_doc(value) for value in sorted(self.policy_partitions.values(), key=lambda x: x.revision_id)],
        "epochs": [epoch_doc(value) for value in sorted(self.policy_epochs.values(), key=lambda x: x.epoch_id)],
        "nodes": [node_doc(value) for value in sorted(self.policy_nodes.values(), key=lambda x: x.revision_id)],
        "selections": [selection_doc(value) for value in sorted(self.policy_selections.values(), key=lambda x: x.record_id)],
        "sufficiency": [sufficiency_doc(value) for value in sorted(self.policy_sufficiency.values(), key=lambda x: x.revision_id)],
        "seals": [seal_doc(value) for value in sorted(self.policy_seals.values(), key=lambda x: x.revision_id)],
        "executability": [
            executability_doc(value) for value in sorted(self.policy_executability.values(), key=lambda x: x.revision_id)
        ],
        "authorization_bindings": {
            authorization_id: dict(binding)
            for authorization_id, binding in sorted(self.policy_authorization_bindings.items())
        },
    }


def _snapshot_state(self, base_snapshot_state) -> dict[str, Any]:
    state = dict(base_snapshot_state(self))
    state["snapshot_schema"] = POLICY_SNAPSHOT_SCHEMA
    state["policy"] = _policy_state(self)
    return state


def _restore_policy_state(kernel, policy: dict[str, Any]) -> None:
    kernel.policy_frontiers = {}
    kernel.policy_partitions = {}
    kernel.policy_epochs = {}
    kernel.policy_nodes = {}
    kernel.policy_selections = {}
    kernel.policy_sufficiency = {}
    kernel.policy_seals = {}
    kernel.policy_executability = {}
    kernel.policy_authorization_bindings = {}

    for row in policy.get("frontiers", ()):
        value = frontier_from_doc(dict(row))
        if value.revision_id in kernel.policy_frontiers:
            raise ReplayError("duplicate observation frontier in policy snapshot")
        kernel.policy_frontiers[value.revision_id] = value

    for row in policy.get("partitions", ()):
        value = partition_from_doc(dict(row))
        if value.revision_id in kernel.policy_partitions:
            raise ReplayError("duplicate information partition in policy snapshot")
        kernel.policy_partitions[value.revision_id] = value

    for row in policy.get("epochs", ()):
        value = epoch_from_doc(dict(row))
        if value.epoch_id in kernel.policy_epochs:
            raise ReplayError("duplicate decision epoch in policy snapshot")
        partition = kernel.policy_partitions.get(value.information_partition_revision)
        frontier = kernel.policy_frontiers.get(value.observation_frontier_revision)
        if partition is None or frontier is None:
            raise ReplayError("decision epoch references missing policy information state")
        if partition.decision_epoch_ref != value.epoch_id:
            raise ReplayError("decision epoch/partition lineage mismatch")
        kernel.policy_epochs[value.epoch_id] = value

    for row in policy.get("nodes", ()):
        value = node_from_doc(dict(row))
        if value.revision_id in kernel.policy_nodes:
            raise ReplayError("duplicate policy node in snapshot")
        epoch = kernel.policy_epochs.get(value.decision_epoch_ref)
        partition = kernel.policy_partitions.get(value.information_partition_revision)
        frontier = kernel.policy_frontiers.get(value.observation_frontier_revision)
        if epoch is None or partition is None or frontier is None:
            raise ReplayError("policy node references missing epoch/partition/frontier")
        if value.mission_revision != epoch.mission_revision or value.plan_snapshot_version != epoch.plan_snapshot_version:
            raise ReplayError("policy node semantic snapshot disagrees with decision epoch")
        if value.action_space_revision != epoch.available_action_space_revision:
            raise ReplayError("policy node action-space revision disagrees with decision epoch")
        kernel.policy_nodes[value.revision_id] = value

    for row in policy.get("selections", ()):
        value = selection_from_doc(dict(row))
        if value.record_id in kernel.policy_selections:
            raise ReplayError("duplicate selection record in policy snapshot")
        if value.information_partition_revision not in kernel.policy_partitions:
            raise ReplayError("selection record references missing information partition")
        if value.chosen_action_ref not in kernel.actions:
            raise ReplayError("selection record references missing action")
        kernel.policy_selections[value.record_id] = value

    for row in policy.get("sufficiency", ()):
        value = sufficiency_from_doc(dict(row))
        if value.revision_id in kernel.policy_sufficiency:
            raise ReplayError("duplicate decision sufficiency certificate in snapshot")
        if value.decision_epoch_ref not in kernel.policy_epochs:
            raise ReplayError("decision sufficiency references missing epoch")
        if value.information_partition_revision not in kernel.policy_partitions:
            raise ReplayError("decision sufficiency references missing partition")
        if value.action_ref not in kernel.actions:
            raise ReplayError("decision sufficiency references missing action")
        kernel.policy_sufficiency[value.revision_id] = value

    for row in policy.get("seals", ()):
        value = seal_from_doc(dict(row))
        if value.revision_id in kernel.policy_seals:
            raise ReplayError("duplicate PlanSeal in snapshot")
        sufficiency = kernel.policy_sufficiency.get(value.sufficiency_certificate_revision)
        if sufficiency is None or sufficiency.canonical_digest != value.sufficiency_certificate_digest:
            raise ReplayError("PlanSeal references missing or mismatched sufficiency lineage")
        kernel.policy_seals[value.revision_id] = value

    for row in policy.get("executability", ()):
        value = executability_from_doc(dict(row))
        if value.revision_id in kernel.policy_executability:
            raise ReplayError("duplicate policy executability assessment in snapshot")
        manifest = value.closure_manifest
        if manifest.policy_revision not in kernel.policy_nodes:
            raise ReplayError("executability assessment references missing policy node")
        if manifest.information_partition_revision not in kernel.policy_partitions:
            raise ReplayError("executability assessment references missing information partition")
        kernel.policy_executability[value.revision_id] = value

    for authorization_id, raw_binding in policy.get("authorization_bindings", {}).items():
        authorization_id = str(authorization_id)
        binding = {str(key): str(value) for key, value in dict(raw_binding).items()}
        if authorization_id not in kernel.authorizations:
            raise ReplayError("policy authorization binding references missing action authorization")
        if authorization_id not in kernel.authorization_identity_bindings:
            raise ReplayError("policy authorization binding lacks restored host identity lineage")
        if authorization_id not in kernel.proof_authorization_bindings:
            raise ReplayError("policy authorization binding lacks restored proof authority lineage")
        _validate_policy_binding(kernel, binding)
        kernel.policy_authorization_bindings[authorization_id] = binding


def _validate_policy_binding(kernel, binding: dict[str, str]) -> None:
    node = kernel.policy_nodes.get(binding.get("policy_node_revision", ""))
    selection = kernel.policy_selections.get(binding.get("selection_record_id", ""))
    sufficiency = kernel.policy_sufficiency.get(binding.get("sufficiency_revision", ""))
    seal = kernel.policy_seals.get(binding.get("seal_revision", ""))
    executability = kernel.policy_executability.get(binding.get("executability_revision", ""))
    if node is None or node.canonical_digest != binding.get("policy_node_digest"):
        raise ReplayError("policy authorization binding has stale policy-node lineage")
    if selection is None or selection.canonical_digest != binding.get("selection_digest"):
        raise ReplayError("policy authorization binding has stale selection lineage")
    if sufficiency is None or sufficiency.canonical_digest != binding.get("sufficiency_digest"):
        raise ReplayError("policy authorization binding has stale sufficiency lineage")
    if seal is None or seal.canonical_digest != binding.get("seal_digest"):
        raise ReplayError("policy authorization binding has stale PlanSeal lineage")
    if executability is None or executability.canonical_digest != binding.get("executability_digest"):
        raise ReplayError("policy authorization binding has stale executability lineage")


def _replay_policy_registration(kernel, event: str, payload: dict[str, Any]) -> bool:
    if event == "policy.frontier_registered":
        value = frontier_from_doc(dict(payload))
        if value.revision_id in kernel.policy_frontiers:
            raise ReplayError("duplicate observation frontier during replay")
        kernel.policy_frontiers[value.revision_id] = value
        return True
    if event == "policy.partition_registered":
        value = partition_from_doc(dict(payload))
        if value.revision_id in kernel.policy_partitions:
            raise ReplayError("duplicate information partition during replay")
        kernel.policy_partitions[value.revision_id] = value
        return True
    if event == "policy.epoch_registered":
        value = epoch_from_doc(dict(payload))
        partition = kernel.policy_partitions.get(value.information_partition_revision)
        frontier = kernel.policy_frontiers.get(value.observation_frontier_revision)
        if partition is None or frontier is None or partition.decision_epoch_ref != value.epoch_id:
            raise ReplayError("decision epoch replay has incomplete information lineage")
        if value.epoch_id in kernel.policy_epochs:
            raise ReplayError("duplicate decision epoch during replay")
        kernel.policy_epochs[value.epoch_id] = value
        return True
    if event == "policy.node_registered":
        value = node_from_doc(dict(payload))
        epoch = kernel.policy_epochs.get(value.decision_epoch_ref)
        if epoch is None:
            raise ReplayError("policy node replay references missing epoch")
        if value.information_partition_revision not in kernel.policy_partitions:
            raise ReplayError("policy node replay references missing partition")
        if value.observation_frontier_revision not in kernel.policy_frontiers:
            raise ReplayError("policy node replay references missing observation frontier")
        if value.mission_revision != epoch.mission_revision or value.plan_snapshot_version != epoch.plan_snapshot_version:
            raise ReplayError("policy node replay semantic snapshot mismatch")
        if value.revision_id in kernel.policy_nodes:
            raise ReplayError("duplicate policy node during replay")
        kernel.policy_nodes[value.revision_id] = value
        return True
    if event == "policy.selection_registered":
        value = selection_from_doc(dict(payload))
        if value.information_partition_revision not in kernel.policy_partitions or value.chosen_action_ref not in kernel.actions:
            raise ReplayError("selection replay has incomplete partition/action lineage")
        if value.record_id in kernel.policy_selections:
            raise ReplayError("duplicate selection record during replay")
        kernel.policy_selections[value.record_id] = value
        return True
    if event == "policy.sufficiency_registered":
        value = sufficiency_from_doc(dict(payload))
        if value.decision_epoch_ref not in kernel.policy_epochs or value.information_partition_revision not in kernel.policy_partitions:
            raise ReplayError("decision sufficiency replay has incomplete epoch/partition lineage")
        if value.action_ref not in kernel.actions:
            raise ReplayError("decision sufficiency replay references missing action")
        if value.revision_id in kernel.policy_sufficiency:
            raise ReplayError("duplicate decision sufficiency during replay")
        kernel.policy_sufficiency[value.revision_id] = value
        return True
    if event == "policy.seal_registered":
        value = seal_from_doc(dict(payload))
        sufficiency = kernel.policy_sufficiency.get(value.sufficiency_certificate_revision)
        if sufficiency is None or sufficiency.canonical_digest != value.sufficiency_certificate_digest:
            raise ReplayError("PlanSeal replay has incomplete sufficiency lineage")
        if value.revision_id in kernel.policy_seals:
            raise ReplayError("duplicate PlanSeal during replay")
        kernel.policy_seals[value.revision_id] = value
        return True
    if event == "policy.executability_registered":
        value = executability_from_doc(dict(payload))
        manifest = value.closure_manifest
        if manifest.policy_revision not in kernel.policy_nodes or manifest.information_partition_revision not in kernel.policy_partitions:
            raise ReplayError("executability replay has incomplete policy/partition lineage")
        if value.revision_id in kernel.policy_executability:
            raise ReplayError("duplicate executability assessment during replay")
        kernel.policy_executability[value.revision_id] = value
        return True
    return False


def _replay_policy_entry(kernel, entry) -> bool:
    event = entry.event_type
    payload = entry.payload
    if _replay_policy_registration(kernel, event, payload):
        return True
    if event == "policy.authorization_bound":
        authorization_id = str(payload["authorization_id"])
        if authorization_id not in kernel.authorizations:
            raise ReplayError("policy authorization replay references missing action authorization")
        if authorization_id not in kernel.authorization_identity_bindings:
            raise ReplayError("policy authorization replay lacks host identity lineage")
        if authorization_id not in kernel.proof_authorization_bindings:
            raise ReplayError("policy authorization replay lacks proof authority lineage")
        binding = {
            "policy_node_revision": str(payload["policy_node_revision"]),
            "policy_node_digest": str(payload["policy_node_digest"]),
            "selection_record_id": str(payload["selection_record_id"]),
            "selection_digest": str(payload["selection_digest"]),
            "sufficiency_revision": str(payload["sufficiency_revision"]),
            "sufficiency_digest": str(payload["sufficiency_digest"]),
            "seal_revision": str(payload["seal_revision"]),
            "seal_digest": str(payload["seal_digest"]),
            "executability_revision": str(payload["executability_revision"]),
            "executability_digest": str(payload["executability_digest"]),
        }
        _validate_policy_binding(kernel, binding)
        kernel.policy_authorization_bindings[authorization_id] = binding
        return True
    return False


def _replay_entry(kernel, entry) -> None:
    if entry.event_type.startswith("policy."):
        if not _replay_policy_entry(kernel, entry):
            raise ReplayError(f"unsupported Wave 5 policy replay event: {entry.event_type}")
        return
    _replay_proof_entry(kernel, entry)


def _open(cls, root: Path):
    root = Path(root)
    journal = HashJournal(root / "journal.jsonl")
    journal.verify(raise_on_error=True)
    state = SnapshotStore(root / "snapshot.json").load()
    schema = state.get("snapshot_schema")
    supported = {BASE_SNAPSHOT_SCHEMA, TRUST_SNAPSHOT_SCHEMA, PROOF_SNAPSHOT_SCHEMA, POLICY_SNAPSHOT_SCHEMA}
    if schema not in supported:
        raise ReplayError("unsupported or missing snapshot schema")
    entries = journal.entries()
    prefix_length = _find_snapshot_prefix(entries, str(state.get("journal_head", "")))

    mission_doc = state.get("mission") or {}
    if not mission_doc:
        raise ReplayError("snapshot has no mission contract")
    mission = MissionLedger(MissionContract(
        int(mission_doc["version"]), str(mission_doc["objective"]),
        tuple(mission_doc.get("success_conditions", ())), tuple(mission_doc.get("hard_constraints", ())),
        tuple(mission_doc.get("soft_preferences", ())), tuple(mission_doc.get("anti_goals", ())),
        mission_doc.get("risk_budget"),
    ))
    kernel = cls(root, mission)
    core_state = dict(state)
    core_state["snapshot_schema"] = BASE_SNAPSHOT_SCHEMA
    core_state.pop("trust", None)
    core_state.pop("proof", None)
    core_state.pop("policy", None)
    _restore_state(kernel, core_state)
    if schema in {TRUST_SNAPSHOT_SCHEMA, PROOF_SNAPSHOT_SCHEMA, POLICY_SNAPSHOT_SCHEMA}:
        _restore_trust_state(kernel, dict(state.get("trust") or {}))
    if schema in {PROOF_SNAPSHOT_SCHEMA, POLICY_SNAPSHOT_SCHEMA}:
        proof = state.get("proof")
        if not isinstance(proof, dict):
            raise ReplayError("proof-capable snapshot is missing proof lineage state")
        _restore_proof_state(kernel, proof)
    if schema == POLICY_SNAPSHOT_SCHEMA:
        policy = state.get("policy")
        if not isinstance(policy, dict):
            raise ReplayError("v5 snapshot is missing policy closure state")
        _restore_policy_state(kernel, policy)
    for entry in entries[prefix_length:]:
        _replay_entry(kernel, entry)
    return kernel


def install_policy_recovery(kernel_cls) -> None:
    if getattr(kernel_cls, "_wave5_policy_recovery_installed", False):
        return
    base_snapshot_state = kernel_cls.snapshot_state

    def snapshot_state(self):
        return _snapshot_state(self, base_snapshot_state)

    def save_snapshot(self):
        with self._writer_lock:
            state = snapshot_state(self)
            self.snapshots.save(state)
            self._record("snapshot.saved", {
                "snapshot_schema": POLICY_SNAPSHOT_SCHEMA,
                "snapshot_digest": digest(state),
                "bound_journal_head": state["journal_head"],
            })
            return state

    kernel_cls.snapshot_state = snapshot_state
    kernel_cls.save_snapshot = save_snapshot
    kernel_cls.open = classmethod(_open)
    kernel_cls._wave5_policy_recovery_installed = True
