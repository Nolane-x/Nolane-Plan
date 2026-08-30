from __future__ import annotations

from pathlib import Path
from typing import Any

from .hashing import digest
from .mission import MissionContract, MissionLedger
from .persistence import HashJournal, SnapshotStore
from .policy_recovery import POLICY_SNAPSHOT_SCHEMA, _replay_entry as _replay_policy_entry, _restore_policy_state
from .proof_recovery import PROOF_SNAPSHOT_SCHEMA, _restore_proof_state
from .resume import SNAPSHOT_SCHEMA as BASE_SNAPSHOT_SCHEMA
from .resume import _find_snapshot_prefix, _restore_state
from .schedulability_codec import (
    activation_doc,
    activation_from_doc,
    coverage_doc,
    coverage_from_doc,
    independence_doc,
    independence_from_doc,
    job_doc,
    job_from_doc,
    liveness_doc,
    liveness_from_doc,
    resource_doc,
    resource_from_doc,
    robust_preparedness_doc,
    robust_preparedness_from_doc,
    schedulability_doc,
    schedulability_from_doc,
    stability_doc,
    stability_from_doc,
)
from .trust_recovery import TRUST_SNAPSHOT_SCHEMA, _restore_trust_state
from .types import ReplayError


SCHEDULABILITY_SNAPSHOT_SCHEMA = "nolane-plan-runtime-snapshot-v6"


def _schedulability_state(self) -> dict[str, Any]:
    return {
        "resource_revisions": [
            resource_doc(value)
            for value in sorted(self.control_plane_resource_revisions.values(), key=lambda x: x.revision_id)
        ],
        "current_resource_revisions": {
            resource_id: value.revision_id for resource_id, value in sorted(self.control_plane_resources.items())
        },
        "job_revisions": [
            job_doc(value) for value in sorted(self.reaction_job_revisions.values(), key=lambda x: x.revision_id)
        ],
        "current_job_revisions": {
            job_id: value.revision_id for job_id, value in sorted(self.reaction_jobs.items())
        },
        "certificates": [
            schedulability_doc(value)
            for value in sorted(self.schedulability_certificates.values(), key=lambda x: x.revision_id)
        ],
        "coverage": [
            coverage_doc(value)
            for value in sorted(self.policy_coverage_assessments.values(), key=lambda x: x.revision_id)
        ],
        "independence": [
            independence_doc(value)
            for value in sorted(self.option_independence_certificates.values(), key=lambda x: x.revision_id)
        ],
        "robust_preparedness": [
            robust_preparedness_doc(value)
            for value in sorted(self.robust_preparedness_assessments.values(), key=lambda x: x.canonical_digest)
        ],
        "liveness": [
            liveness_doc(value)
            for value in sorted(self.handoff_liveness_certificates.values(), key=lambda x: x.revision_id)
        ],
        "stability": [
            stability_doc(value)
            for value in sorted(self.handoff_stability_contracts.values(), key=lambda x: x.revision_id)
        ],
        "edge_activation": [
            activation_doc(value)
            for value in sorted(self.edge_activation_assessments.values(), key=lambda x: x.canonical_digest)
        ],
        "authorization_bindings": {
            authorization_id: dict(binding)
            for authorization_id, binding in sorted(self.schedulability_authorization_bindings.items())
        },
    }


def _snapshot_state(self, base_snapshot_state) -> dict[str, Any]:
    state = dict(base_snapshot_state(self))
    state["snapshot_schema"] = SCHEDULABILITY_SNAPSHOT_SCHEMA
    state["schedulability"] = _schedulability_state(self)
    return state


def _historical_digest_exists(rows, logical_attr: str, logical_id: str, expected_digest: str) -> bool:
    return any(getattr(value, logical_attr) == logical_id and value.canonical_digest == expected_digest for value in rows.values())


def _validate_certificate_lineage(kernel, certificate) -> None:
    for job_id, expected_digest in certificate.reaction_job_digests:
        if not _historical_digest_exists(kernel.reaction_job_revisions, "reaction_job_id", job_id, expected_digest):
            raise ReplayError("schedulability certificate references missing historical reaction-job lineage")
    for resource_id, expected_digest in certificate.control_resource_digests:
        if not _historical_digest_exists(kernel.control_plane_resource_revisions, "resource_id", resource_id, expected_digest):
            raise ReplayError("schedulability certificate references missing historical control-resource lineage")


def _validate_wave6_binding(kernel, binding: dict[str, str]) -> None:
    sched = kernel.schedulability_certificates.get(binding.get("schedulability_revision", ""))
    coverage = kernel.policy_coverage_assessments.get(binding.get("coverage_revision", ""))
    if sched is None or sched.canonical_digest != binding.get("schedulability_digest"):
        raise ReplayError("Wave-6 authorization binding has stale schedulability lineage")
    if coverage is None or coverage.canonical_digest != binding.get("coverage_digest"):
        raise ReplayError("Wave-6 authorization binding has stale coverage lineage")
    liveness_revision = binding.get("liveness_revision", "")
    if liveness_revision:
        value = kernel.handoff_liveness_certificates.get(liveness_revision)
        if value is None or value.canonical_digest != binding.get("liveness_digest"):
            raise ReplayError("Wave-6 authorization binding has stale liveness lineage")
    stability_revision = binding.get("stability_contract_revision", "")
    if stability_revision:
        value = kernel.handoff_stability_contracts.get(stability_revision)
        if value is None or value.canonical_digest != binding.get("stability_contract_digest"):
            raise ReplayError("Wave-6 authorization binding has stale stability lineage")
    activation_digest = binding.get("edge_activation_digest", "")
    if activation_digest and activation_digest not in kernel.edge_activation_assessments:
        raise ReplayError("Wave-6 authorization binding has missing edge-activation lineage")
    independence_revision = binding.get("independence_revision", "")
    if independence_revision:
        value = kernel.option_independence_certificates.get(independence_revision)
        if value is None or value.canonical_digest != binding.get("independence_digest"):
            raise ReplayError("Wave-6 authorization binding has stale independence lineage")


def _restore_schedulability_state(kernel, state: dict[str, Any]) -> None:
    kernel.control_plane_resources = {}
    kernel.control_plane_resource_revisions = {}
    kernel.reaction_jobs = {}
    kernel.reaction_job_revisions = {}
    kernel.schedulability_certificates = {}
    kernel.policy_coverage_assessments = {}
    kernel.option_independence_certificates = {}
    kernel.robust_preparedness_assessments = {}
    kernel.handoff_liveness_certificates = {}
    kernel.handoff_stability_contracts = {}
    kernel.edge_activation_assessments = {}
    kernel.schedulability_authorization_bindings = {}

    for row in state.get("resource_revisions", ()):
        value = resource_from_doc(dict(row))
        if value.revision_id in kernel.control_plane_resource_revisions:
            raise ReplayError("duplicate control-resource revision in v6 snapshot")
        kernel.control_plane_resource_revisions[value.revision_id] = value
    for resource_id, revision_id in dict(state.get("current_resource_revisions", {})).items():
        value = kernel.control_plane_resource_revisions.get(str(revision_id))
        if value is None or value.resource_id != str(resource_id):
            raise ReplayError("current control-resource pointer has invalid revision lineage")
        kernel.control_plane_resources[str(resource_id)] = value

    for row in state.get("job_revisions", ()):
        value = job_from_doc(dict(row))
        if value.revision_id in kernel.reaction_job_revisions:
            raise ReplayError("duplicate reaction-job revision in v6 snapshot")
        kernel.reaction_job_revisions[value.revision_id] = value
    for job_id, revision_id in dict(state.get("current_job_revisions", {})).items():
        value = kernel.reaction_job_revisions.get(str(revision_id))
        if value is None or value.reaction_job_id != str(job_id):
            raise ReplayError("current reaction-job pointer has invalid revision lineage")
        kernel.reaction_jobs[str(job_id)] = value

    for row in state.get("certificates", ()):
        value = schedulability_from_doc(dict(row))
        if value.revision_id in kernel.schedulability_certificates:
            raise ReplayError("duplicate schedulability certificate in v6 snapshot")
        _validate_certificate_lineage(kernel, value)
        kernel.schedulability_certificates[value.revision_id] = value

    for row in state.get("coverage", ()):
        value = coverage_from_doc(dict(row))
        if value.revision_id in kernel.policy_coverage_assessments:
            raise ReplayError("duplicate policy coverage assessment in v6 snapshot")
        kernel.policy_coverage_assessments[value.revision_id] = value

    for row in state.get("independence", ()):
        value = independence_from_doc(dict(row))
        if value.revision_id in kernel.option_independence_certificates:
            raise ReplayError("duplicate option-independence certificate in v6 snapshot")
        kernel.option_independence_certificates[value.revision_id] = value

    for row in state.get("robust_preparedness", ()):
        value = robust_preparedness_from_doc(dict(row))
        if value.canonical_digest in kernel.robust_preparedness_assessments:
            raise ReplayError("duplicate robust preparedness assessment in v6 snapshot")
        if not any(
            item.canonical_digest == value.independence_certificate_digest
            for item in kernel.option_independence_certificates.values()
        ):
            raise ReplayError("robust preparedness assessment references missing independence lineage")
        kernel.robust_preparedness_assessments[value.canonical_digest] = value

    for row in state.get("liveness", ()):
        value = liveness_from_doc(dict(row))
        if value.revision_id in kernel.handoff_liveness_certificates:
            raise ReplayError("duplicate liveness certificate in v6 snapshot")
        kernel.handoff_liveness_certificates[value.revision_id] = value

    for row in state.get("stability", ()):
        value = stability_from_doc(dict(row))
        if value.revision_id in kernel.handoff_stability_contracts:
            raise ReplayError("duplicate stability contract in v6 snapshot")
        kernel.handoff_stability_contracts[value.revision_id] = value

    for row in state.get("edge_activation", ()):
        value = activation_from_doc(dict(row))
        if value.canonical_digest in kernel.edge_activation_assessments:
            raise ReplayError("duplicate edge activation assessment in v6 snapshot")
        if not any(item.canonical_digest == value.contract_digest for item in kernel.handoff_stability_contracts.values()):
            raise ReplayError("edge activation assessment references missing stability contract")
        kernel.edge_activation_assessments[value.canonical_digest] = value

    for authorization_id, raw_binding in dict(state.get("authorization_bindings", {})).items():
        authorization_id = str(authorization_id)
        binding = {str(key): str(value) for key, value in dict(raw_binding).items()}
        if authorization_id not in kernel.authorizations:
            raise ReplayError("Wave-6 authorization binding references missing authorization")
        if authorization_id not in kernel.authorization_identity_bindings:
            raise ReplayError("Wave-6 authorization binding lacks host identity lineage")
        if authorization_id not in kernel.proof_authorization_bindings:
            raise ReplayError("Wave-6 authorization binding lacks proof lineage")
        if authorization_id not in kernel.policy_authorization_bindings:
            raise ReplayError("Wave-6 authorization binding lacks sealed-policy lineage")
        _validate_wave6_binding(kernel, binding)
        kernel.schedulability_authorization_bindings[authorization_id] = binding


def _replay_schedulability_entry(kernel, entry) -> bool:
    event = entry.event_type
    payload = dict(entry.payload)
    if event == "schedulability.resource_registered":
        value = resource_from_doc(payload)
        if value.revision_id in kernel.control_plane_resource_revisions:
            raise ReplayError("duplicate control-resource revision during replay")
        kernel.control_plane_resource_revisions[value.revision_id] = value
        kernel.control_plane_resources[value.resource_id] = value
        return True
    if event == "schedulability.job_registered":
        value = job_from_doc(payload)
        if value.revision_id in kernel.reaction_job_revisions:
            raise ReplayError("duplicate reaction-job revision during replay")
        kernel.reaction_job_revisions[value.revision_id] = value
        kernel.reaction_jobs[value.reaction_job_id] = value
        return True
    if event == "schedulability.certificate_registered":
        value = schedulability_from_doc(payload)
        if value.revision_id in kernel.schedulability_certificates:
            raise ReplayError("duplicate schedulability certificate during replay")
        _validate_certificate_lineage(kernel, value)
        try:
            kernel._certificate_current_objects(value)
        except Exception as exc:
            raise ReplayError("schedulability certificate was not current when replayed") from exc
        kernel.schedulability_certificates[value.revision_id] = value
        return True
    if event == "schedulability.coverage_registered":
        value = coverage_from_doc(payload)
        if value.revision_id in kernel.policy_coverage_assessments:
            raise ReplayError("duplicate coverage assessment during replay")
        kernel.policy_coverage_assessments[value.revision_id] = value
        return True
    if event == "schedulability.independence_registered":
        value = independence_from_doc(payload)
        if value.revision_id in kernel.option_independence_certificates:
            raise ReplayError("duplicate independence certificate during replay")
        kernel.option_independence_certificates[value.revision_id] = value
        return True
    if event == "schedulability.robust_preparedness_registered":
        value = robust_preparedness_from_doc(payload)
        if not any(
            item.canonical_digest == value.independence_certificate_digest
            for item in kernel.option_independence_certificates.values()
        ):
            raise ReplayError("robust preparedness replay lacks independence lineage")
        kernel.robust_preparedness_assessments[value.canonical_digest] = value
        return True
    if event == "schedulability.liveness_registered":
        value = liveness_from_doc(payload)
        if value.revision_id in kernel.handoff_liveness_certificates:
            raise ReplayError("duplicate liveness certificate during replay")
        kernel.handoff_liveness_certificates[value.revision_id] = value
        return True
    if event == "schedulability.stability_registered":
        value = stability_from_doc(payload)
        if value.revision_id in kernel.handoff_stability_contracts:
            raise ReplayError("duplicate stability contract during replay")
        kernel.handoff_stability_contracts[value.revision_id] = value
        return True
    if event == "schedulability.edge_activation_registered":
        value = activation_from_doc(payload)
        if not any(item.canonical_digest == value.contract_digest for item in kernel.handoff_stability_contracts.values()):
            raise ReplayError("edge activation replay lacks stability contract lineage")
        if value.canonical_digest in kernel.edge_activation_assessments:
            raise ReplayError("duplicate edge activation assessment during replay")
        kernel.edge_activation_assessments[value.canonical_digest] = value
        return True
    if event == "schedulability.authorization_bound":
        authorization_id = str(payload["authorization_id"])
        if authorization_id not in kernel.authorizations:
            raise ReplayError("Wave-6 authorization replay references missing authorization")
        if authorization_id not in kernel.authorization_identity_bindings or authorization_id not in kernel.proof_authorization_bindings:
            raise ReplayError("Wave-6 authorization replay lacks identity/proof lineage")
        if authorization_id not in kernel.policy_authorization_bindings:
            raise ReplayError("Wave-6 authorization replay lacks sealed-policy lineage")
        keys = (
            "schedulability_revision", "schedulability_digest", "coverage_revision", "coverage_digest",
            "liveness_revision", "liveness_digest", "stability_contract_revision", "stability_contract_digest",
            "edge_activation_digest", "independence_revision", "independence_digest",
        )
        binding = {key: str(payload.get(key, "")) for key in keys}
        _validate_wave6_binding(kernel, binding)
        kernel.schedulability_authorization_bindings[authorization_id] = binding
        return True
    return False


def _replay_entry(kernel, entry) -> None:
    if entry.event_type.startswith("schedulability."):
        if not _replay_schedulability_entry(kernel, entry):
            raise ReplayError(f"unsupported Wave 6 schedulability replay event: {entry.event_type}")
        return
    _replay_policy_entry(kernel, entry)


def _open(cls, root: Path):
    root = Path(root)
    journal = HashJournal(root / "journal.jsonl")
    journal.verify(raise_on_error=True)
    state = SnapshotStore(root / "snapshot.json").load()
    schema = state.get("snapshot_schema")
    supported = {
        BASE_SNAPSHOT_SCHEMA, TRUST_SNAPSHOT_SCHEMA, PROOF_SNAPSHOT_SCHEMA,
        POLICY_SNAPSHOT_SCHEMA, SCHEDULABILITY_SNAPSHOT_SCHEMA,
    }
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
    core_state.pop("schedulability", None)
    _restore_state(kernel, core_state)

    if schema in {TRUST_SNAPSHOT_SCHEMA, PROOF_SNAPSHOT_SCHEMA, POLICY_SNAPSHOT_SCHEMA, SCHEDULABILITY_SNAPSHOT_SCHEMA}:
        _restore_trust_state(kernel, dict(state.get("trust") or {}))
    if schema in {PROOF_SNAPSHOT_SCHEMA, POLICY_SNAPSHOT_SCHEMA, SCHEDULABILITY_SNAPSHOT_SCHEMA}:
        proof = state.get("proof")
        if not isinstance(proof, dict):
            raise ReplayError("proof-capable snapshot is missing proof lineage state")
        _restore_proof_state(kernel, proof)
    if schema in {POLICY_SNAPSHOT_SCHEMA, SCHEDULABILITY_SNAPSHOT_SCHEMA}:
        policy = state.get("policy")
        if not isinstance(policy, dict):
            raise ReplayError("policy-capable snapshot is missing policy closure state")
        _restore_policy_state(kernel, policy)
    if schema == SCHEDULABILITY_SNAPSHOT_SCHEMA:
        wave6 = state.get("schedulability")
        if not isinstance(wave6, dict):
            raise ReplayError("v6 snapshot is missing schedulability/liveness state")
        _restore_schedulability_state(kernel, wave6)

    for entry in entries[prefix_length:]:
        _replay_entry(kernel, entry)
    return kernel


def install_schedulability_recovery(kernel_cls) -> None:
    if getattr(kernel_cls, "_wave6_schedulability_recovery_installed", False):
        return
    base_snapshot_state = kernel_cls.snapshot_state

    def snapshot_state(self):
        return _snapshot_state(self, base_snapshot_state)

    def save_snapshot(self):
        with self._writer_lock:
            state = snapshot_state(self)
            self.snapshots.save(state)
            self._record("snapshot.saved", {
                "snapshot_schema": SCHEDULABILITY_SNAPSHOT_SCHEMA,
                "snapshot_digest": digest(state),
                "bound_journal_head": state["journal_head"],
            })
            return state

    kernel_cls.snapshot_state = snapshot_state
    kernel_cls.save_snapshot = save_snapshot
    kernel_cls.open = classmethod(_open)
    kernel_cls._wave6_schedulability_recovery_installed = True
