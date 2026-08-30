from __future__ import annotations

from typing import Any, Iterable

from .hashing import digest
from .policy_executability import ExecutabilityStatus, PolicyExecutabilityAssessment
from .policy_information import DecisionEpoch, InformationPartitionRevision, ObservationFrontierRevision
from .policy_ir import PolicyNodeRevision
from .seals import DecisionSufficiencyCertificate, PlanSeal, SealStatus
from .selection import SelectionRecord, SelectionStatus
from .types import AuthorizationError


_BOUNDED_EXECUTABILITY = {
    ExecutabilityStatus.EXEC_BOUNDED,
    ExecutabilityStatus.EXEC_BOUNDED_WITH_ACCEPTED_DEBT,
}
_CURRENT_SEALS = {SealStatus.SEALED, SealStatus.SEALED_WITH_ACCEPTED_DEBT}


def _install_state(self) -> None:
    self.policy_writer_lock = self._writer_lock
    self.policy_frontiers: dict[str, ObservationFrontierRevision] = {}
    self.policy_partitions: dict[str, InformationPartitionRevision] = {}
    self.policy_epochs: dict[str, DecisionEpoch] = {}
    self.policy_nodes: dict[str, PolicyNodeRevision] = {}
    self.policy_selections: dict[str, SelectionRecord] = {}
    self.policy_sufficiency: dict[str, DecisionSufficiencyCertificate] = {}
    self.policy_seals: dict[str, PlanSeal] = {}
    self.policy_executability: dict[str, PolicyExecutabilityAssessment] = {}
    self.policy_authorization_bindings: dict[str, dict[str, str]] = {}


def _current_policy_access_revision(self, principal_ref: str) -> str:
    profile = self.principals.profile(principal_ref)
    return f"principal-access:{profile.principal_ref}@{profile.revision}"


def _current_policy_action_space_revision(self) -> str:
    rows = tuple(
        sorted(
            (
                action.id,
                action.family,
                action.risk_class.value,
                tuple(action.parameters),
                tuple(action.preconditions),
                tuple(action.required_capabilities),
                bool(action.idempotent),
                bool(action.executor_sensitive),
            )
            for action in self.actions.values()
        )
    )
    return f"action-space:{digest(rows)}"


def _register_policy_frontier(self, frontier: ObservationFrontierRevision) -> ObservationFrontierRevision:
    with self._writer_lock:
        if frontier.revision_id in self.policy_frontiers:
            raise ValueError(f"policy frontier revision already exists: {frontier.revision_id}")
        if frontier.principal_scope_ref not in self.principals._profiles:
            raise ValueError("policy frontier binds an unknown principal")
        if frontier.information_access_profile_revision != self.current_policy_access_revision(frontier.principal_scope_ref):
            raise ValueError("policy frontier binds a stale principal access revision")
        self.policy_frontiers[frontier.revision_id] = frontier
        self._record(
            "policy.frontier_registered",
            {
                "revision_id": frontier.revision_id,
                "principal_ref": frontier.principal_scope_ref,
                "access_revision": frontier.information_access_profile_revision,
                "canonical_digest": frontier.canonical_digest,
            },
        )
        return frontier


def _register_information_partition(self, partition: InformationPartitionRevision) -> InformationPartitionRevision:
    with self._writer_lock:
        if partition.revision_id in self.policy_partitions:
            raise ValueError(f"information partition revision already exists: {partition.revision_id}")
        if partition.principal_scope_ref not in self.principals._profiles:
            raise ValueError("information partition binds an unknown principal")
        if partition.mission_revision != self.mission.current.version:
            raise ValueError("information partition mission revision is stale")
        if partition.canonical_state_version != self.canonical_version:
            raise ValueError("information partition canonical revision is stale")
        if partition.information_access_profile_revision != self.current_policy_access_revision(partition.principal_scope_ref):
            raise ValueError("information partition binds a stale principal access revision")
        self.policy_partitions[partition.revision_id] = partition
        self._record(
            "policy.partition_registered",
            {
                "revision_id": partition.revision_id,
                "epoch_ref": partition.decision_epoch_ref,
                "principal_ref": partition.principal_scope_ref,
                "canonical_digest": partition.canonical_digest,
            },
        )
        return partition


def _register_decision_epoch(self, epoch: DecisionEpoch) -> DecisionEpoch:
    with self._writer_lock:
        if epoch.epoch_id in self.policy_epochs:
            raise ValueError(f"decision epoch already exists: {epoch.epoch_id}")
        partition = self.policy_partitions.get(epoch.information_partition_revision)
        frontier = self.policy_frontiers.get(epoch.observation_frontier_revision)
        if partition is None or frontier is None:
            raise ValueError("decision epoch requires registered partition and observation frontier")
        current_access = self.current_policy_access_revision(epoch.decision_principal_ref)
        if epoch.decision_principal_ref != partition.principal_scope_ref or epoch.decision_principal_ref != frontier.principal_scope_ref:
            raise ValueError("decision epoch principal scope is incoherent")
        if epoch.bound_principal_scope_ref != epoch.decision_principal_ref:
            raise ValueError("decision epoch bound principal scope is incoherent")
        if epoch.principal_information_access_profile_revision != current_access:
            raise ValueError("decision epoch binds a stale access revision")
        if partition.information_access_profile_revision != current_access or frontier.information_access_profile_revision != current_access:
            raise ValueError("decision epoch information surfaces bind different access revisions")
        if epoch.mission_revision != self.mission.current.version:
            raise ValueError("decision epoch mission revision is stale")
        if epoch.plan_snapshot_version != self.plan_snapshot_version:
            raise ValueError("decision epoch plan snapshot is stale")
        if epoch.strategic_location_revision != self._location_revision:
            raise ValueError("decision epoch strategic location is stale")
        if epoch.available_action_space_revision != self.current_policy_action_space_revision():
            raise ValueError("decision epoch action-space revision is stale")
        if partition.decision_epoch_ref != epoch.epoch_id:
            raise ValueError("information partition is bound to another decision epoch")
        self.policy_epochs[epoch.epoch_id] = epoch
        self._record(
            "policy.epoch_registered",
            {
                "epoch_id": epoch.epoch_id,
                "principal_ref": epoch.decision_principal_ref,
                "partition_revision": epoch.information_partition_revision,
                "action_space_revision": epoch.available_action_space_revision,
                "canonical_digest": epoch.canonical_digest,
            },
        )
        return epoch


def _register_policy_node(self, node: PolicyNodeRevision) -> PolicyNodeRevision:
    with self._writer_lock:
        if node.revision_id in self.policy_nodes:
            raise ValueError(f"policy node revision already exists: {node.revision_id}")
        epoch = self.policy_epochs.get(node.decision_epoch_ref)
        partition = self.policy_partitions.get(node.information_partition_revision)
        frontier = self.policy_frontiers.get(node.observation_frontier_revision)
        if epoch is None or partition is None or frontier is None:
            raise ValueError("policy node requires registered epoch, partition and observation frontier")
        # Registration records the artifact; authority validation decides whether its
        # principal/snapshot bindings are usable.  This keeps invalid artifacts auditable.
        if node.mission_revision != epoch.mission_revision or node.plan_snapshot_version != epoch.plan_snapshot_version:
            raise ValueError("policy node semantic snapshot differs from decision epoch")
        if node.strategic_location_revision != epoch.strategic_location_revision:
            raise ValueError("policy node strategic location differs from decision epoch")
        if node.action_space_revision != epoch.available_action_space_revision:
            raise ValueError("policy node action space differs from decision epoch")
        if node.observation_frontier_revision != epoch.observation_frontier_revision:
            raise ValueError("policy node observation frontier differs from decision epoch")
        missing_actions = set(node.candidate_action_contracts).difference(self.actions)
        if missing_actions:
            raise ValueError(f"policy node references unknown action contracts: {sorted(missing_actions)!r}")
        self.policy_nodes[node.revision_id] = node
        self._record(
            "policy.node_registered",
            {
                "revision_id": node.revision_id,
                "principal_ref": node.decision_principal_ref,
                "epoch_ref": node.decision_epoch_ref,
                "partition_revision": node.information_partition_revision,
                "sealed": node.sealed,
                "canonical_digest": node.canonical_digest,
            },
        )
        return node


def _register_selection_record(self, record: SelectionRecord) -> SelectionRecord:
    with self._writer_lock:
        if record.record_id in self.policy_selections:
            raise ValueError(f"selection record already exists: {record.record_id}")
        if record.information_partition_revision not in self.policy_partitions:
            raise ValueError("selection record references an unknown information partition")
        if record.chosen_action_ref not in self.actions:
            raise ValueError("selection record references an unknown action")
        self.policy_selections[record.record_id] = record
        self._record(
            "policy.selection_registered",
            {
                "record_id": record.record_id,
                "transaction_id": record.transaction_id,
                "principal_ref": record.decision_principal_ref,
                "partition_revision": record.information_partition_revision,
                "action_space_revision": record.action_space_revision,
                "chosen_action_ref": record.chosen_action_ref,
                "status": record.status.value,
                "canonical_digest": record.canonical_digest,
            },
        )
        return record


def _register_decision_sufficiency(self, certificate: DecisionSufficiencyCertificate) -> DecisionSufficiencyCertificate:
    with self._writer_lock:
        if certificate.revision_id in self.policy_sufficiency:
            raise ValueError(f"decision sufficiency revision already exists: {certificate.revision_id}")
        if certificate.decision_epoch_ref not in self.policy_epochs:
            raise ValueError("decision sufficiency references an unknown epoch")
        if certificate.information_partition_revision not in self.policy_partitions:
            raise ValueError("decision sufficiency references an unknown information partition")
        if certificate.action_ref not in self.actions:
            raise ValueError("decision sufficiency references an unknown action")
        self.policy_sufficiency[certificate.revision_id] = certificate
        self._record(
            "policy.sufficiency_registered",
            {
                "revision_id": certificate.revision_id,
                "action_ref": certificate.action_ref,
                "epoch_ref": certificate.decision_epoch_ref,
                "principal_ref": certificate.decision_principal_ref,
                "complete": certificate.complete,
                "canonical_digest": certificate.canonical_digest,
            },
        )
        return certificate


def _register_plan_seal(self, seal: PlanSeal) -> PlanSeal:
    with self._writer_lock:
        if seal.revision_id in self.policy_seals:
            raise ValueError(f"PlanSeal revision already exists: {seal.revision_id}")
        sufficiency = self.policy_sufficiency.get(seal.sufficiency_certificate_revision)
        if sufficiency is None:
            raise ValueError("PlanSeal references an unknown sufficiency certificate")
        if seal.sufficiency_certificate_digest != sufficiency.canonical_digest:
            raise ValueError("PlanSeal sufficiency digest mismatch")
        self.policy_seals[seal.revision_id] = seal
        self._record(
            "policy.seal_registered",
            {
                "revision_id": seal.revision_id,
                "mission_revision": seal.mission_revision,
                "canonical_state_version": seal.canonical_state_version,
                "sufficiency_revision": seal.sufficiency_certificate_revision,
                "status": seal.status.value,
                "canonical_digest": seal.canonical_digest,
            },
        )
        return seal


def _register_policy_executability(self, assessment: PolicyExecutabilityAssessment) -> PolicyExecutabilityAssessment:
    with self._writer_lock:
        if assessment.revision_id in self.policy_executability:
            raise ValueError(f"policy executability revision already exists: {assessment.revision_id}")
        if assessment.closure_manifest.policy_revision not in self.policy_nodes:
            raise ValueError("policy executability references an unknown policy node")
        self.policy_executability[assessment.revision_id] = assessment
        self._record(
            "policy.executability_registered",
            {
                "revision_id": assessment.revision_id,
                "scope_ref": assessment.scope_ref,
                "policy_revision": assessment.closure_manifest.policy_revision,
                "status": assessment.status.value,
                "canonical_digest": assessment.canonical_digest,
            },
        )
        return assessment


def _current_selection_status(self, record: SelectionRecord) -> SelectionStatus:
    current = {domain: self.freshness.generation(domain) for domain, _ in record.dependency_generations}
    return record.status_against(current)


def _require_registered_policy_bundle(
    self,
    *,
    action_id: str,
    acting_principal_ref: str,
    now: int | float,
    proof_artifact_revision: str,
    policy_node_revision: str,
    selection_record_id: str,
    sufficiency_revision: str,
    seal_revision: str,
    executability_revision: str,
) -> tuple[PolicyNodeRevision, SelectionRecord, DecisionSufficiencyCertificate, PlanSeal, PolicyExecutabilityAssessment]:
    try:
        node = self.policy_nodes[policy_node_revision]
        selection = self.policy_selections[selection_record_id]
        sufficiency = self.policy_sufficiency[sufficiency_revision]
        seal = self.policy_seals[seal_revision]
        executability = self.policy_executability[executability_revision]
        epoch = self.policy_epochs[node.decision_epoch_ref]
        partition = self.policy_partitions[node.information_partition_revision]
        frontier = self.policy_frontiers[node.observation_frontier_revision]
    except KeyError as exc:
        raise AuthorizationError("sealed policy authority lineage is incomplete") from exc

    current_access = self.current_policy_access_revision(acting_principal_ref)
    current_action_space = self.current_policy_action_space_revision()

    if node.decision_principal_ref != acting_principal_ref:
        raise AuthorizationError("policy node decision principal mismatch")
    if acting_principal_ref not in node.execution_principal_requirement_or_set:
        raise AuthorizationError("acting principal is outside policy execution-principal requirement")
    if action_id not in node.candidate_action_contracts or action_id not in node.selected_action_contract_or_policy_set:
        raise AuthorizationError("action is outside the sealed policy node action closure")
    if not node.sealed:
        raise AuthorizationError("policy node is not sealed")

    if epoch.decision_principal_ref != acting_principal_ref or epoch.bound_principal_scope_ref != acting_principal_ref:
        raise AuthorizationError("decision epoch principal binding is stale")
    if epoch.plan_snapshot_version != self.plan_snapshot_version:
        raise AuthorizationError("decision epoch plan snapshot is stale")
    if epoch.mission_revision != self.mission.current.version:
        raise AuthorizationError("decision epoch mission revision is stale")
    if epoch.strategic_location_revision != self._location_revision:
        raise AuthorizationError("decision epoch strategic location is stale")
    if epoch.principal_information_access_profile_revision != current_access:
        raise AuthorizationError("decision epoch principal access revision is stale")
    if epoch.available_action_space_revision != current_action_space:
        raise AuthorizationError("decision epoch action-space revision is stale")
    if not (epoch.temporal_window[0] <= now <= epoch.temporal_window[1]):
        raise AuthorizationError("decision epoch is outside its temporal authority window")

    if partition.principal_scope_ref != acting_principal_ref:
        raise AuthorizationError("information partition principal binding mismatch")
    if partition.decision_epoch_ref != epoch.epoch_id:
        raise AuthorizationError("information partition decision-epoch binding mismatch")
    if partition.mission_revision != self.mission.current.version or partition.canonical_state_version != self.canonical_version:
        raise AuthorizationError("information partition semantic snapshot is stale")
    if partition.information_access_profile_revision != current_access:
        raise AuthorizationError("information partition access revision is stale")
    if frontier.principal_scope_ref != acting_principal_ref or frontier.information_access_profile_revision != current_access:
        raise AuthorizationError("observation frontier principal/access binding is stale")

    if node.mission_revision != self.mission.current.version or node.plan_snapshot_version != self.plan_snapshot_version:
        raise AuthorizationError("policy node semantic snapshot is stale")
    if node.strategic_location_revision != self._location_revision:
        raise AuthorizationError("policy node strategic location is stale")
    if node.action_space_revision != current_action_space:
        raise AuthorizationError("policy node action space is stale")

    if selection.decision_principal_ref != acting_principal_ref:
        raise AuthorizationError("selection record principal mismatch")
    if selection.information_partition_revision != partition.revision_id:
        raise AuthorizationError("selection record partition mismatch")
    if selection.action_space_revision != current_action_space:
        raise AuthorizationError("selection record action-space revision is stale")
    if selection.chosen_action_ref != action_id:
        raise AuthorizationError("selection record chose another action")
    if self._current_selection_status(selection) != SelectionStatus.ADVISORY:
        raise AuthorizationError("selection record is stale or superseded")

    if not sufficiency.complete:
        raise AuthorizationError("decision sufficiency is incomplete")
    if sufficiency.action_ref != action_id or sufficiency.scope_ref != f"action:{action_id}":
        raise AuthorizationError("decision sufficiency action/scope mismatch")
    if sufficiency.decision_epoch_ref != epoch.epoch_id:
        raise AuthorizationError("decision sufficiency epoch mismatch")
    if sufficiency.decision_principal_ref != acting_principal_ref:
        raise AuthorizationError("decision sufficiency principal mismatch")
    if sufficiency.information_partition_revision != partition.revision_id:
        raise AuthorizationError("decision sufficiency partition mismatch")
    exact = dict(sufficiency.exact_object_revisions)
    if exact.get("policy") != node.revision_id or exact.get("proof") != proof_artifact_revision:
        raise AuthorizationError("decision sufficiency exact-object closure mismatch")
    required_closure = {action_id, node.revision_id, proof_artifact_revision}
    if not required_closure.issubset(set(sufficiency.included_object_refs)):
        raise AuthorizationError("decision sufficiency omits a required action-closure object")

    if seal.status not in _CURRENT_SEALS:
        raise AuthorizationError("PlanSeal is stale or revoked")
    if seal.mission_revision != self.mission.current.version or seal.canonical_state_version != self.canonical_version:
        raise AuthorizationError("PlanSeal semantic snapshot is stale")
    if seal.sufficiency_certificate_revision != sufficiency.revision_id:
        raise AuthorizationError("PlanSeal sufficiency revision mismatch")
    if seal.sufficiency_certificate_digest != sufficiency.canonical_digest:
        raise AuthorizationError("PlanSeal sufficiency digest mismatch")
    if not required_closure.issubset(set(seal.action_closure_refs)):
        raise AuthorizationError("PlanSeal omits a required action-closure object")

    manifest = executability.closure_manifest
    if executability.status not in _BOUNDED_EXECUTABILITY:
        raise AuthorizationError("policy executability is not bounded")
    if executability.scope_ref != f"action:{action_id}":
        raise AuthorizationError("policy executability scope mismatch")
    if manifest.mission_revision != self.mission.current.version:
        raise AuthorizationError("policy executability mission revision is stale")
    if manifest.plan_snapshot_version != self.plan_snapshot_version:
        raise AuthorizationError("policy executability plan snapshot is stale")
    if manifest.policy_revision != node.revision_id:
        raise AuthorizationError("policy executability policy revision mismatch")
    if manifest.information_partition_revision != partition.revision_id:
        raise AuthorizationError("policy executability partition mismatch")
    if manifest.action_space_revision != current_action_space:
        raise AuthorizationError("policy executability action-space revision is stale")
    if manifest.seal_status != seal.status:
        raise AuthorizationError("policy executability seal state differs from current PlanSeal")
    expected_snapshot = {
        "mission": str(self.mission.current.version),
        "plan": str(self.plan_snapshot_version),
        "policy": node.revision_id,
        "partition": partition.revision_id,
        "actions": current_action_space,
    }
    if dict(manifest.bound_snapshot_revisions) != expected_snapshot:
        raise AuthorizationError("policy executability binds a mixed or stale semantic snapshot")

    return node, selection, sufficiency, seal, executability


def _authorize_sealed_policy(
    self,
    *,
    action_id: str,
    acting_principal_ref: str,
    grant_ids: tuple[str, ...],
    now: int | float,
    proof_artifact_revision: str,
    active_context: Iterable[str],
    policy_node_revision: str,
    selection_record_id: str,
    sufficiency_revision: str,
    seal_revision: str,
    executability_revision: str,
    capsule_id: str | None = None,
    adapter_id: str | None = None,
    **kwargs: Any,
):
    with self._writer_lock:
        node, selection, sufficiency, seal, executability = self._require_registered_policy_bundle(
            action_id=action_id,
            acting_principal_ref=acting_principal_ref,
            now=now,
            proof_artifact_revision=proof_artifact_revision,
            policy_node_revision=policy_node_revision,
            selection_record_id=selection_record_id,
            sufficiency_revision=sufficiency_revision,
            seal_revision=seal_revision,
            executability_revision=executability_revision,
        )
        authorization = self.authorize_proof_carrying(
            action_id,
            acting_principal_ref,
            grant_ids,
            now,
            proof_artifact_revision=proof_artifact_revision,
            active_context=active_context,
            capsule_id=capsule_id,
            adapter_id=adapter_id,
            **kwargs,
        )
        binding = {
            "policy_node_revision": node.revision_id,
            "policy_node_digest": node.canonical_digest,
            "selection_record_id": selection.record_id,
            "selection_digest": selection.canonical_digest,
            "sufficiency_revision": sufficiency.revision_id,
            "sufficiency_digest": sufficiency.canonical_digest,
            "seal_revision": seal.revision_id,
            "seal_digest": seal.canonical_digest,
            "executability_revision": executability.revision_id,
            "executability_digest": executability.canonical_digest,
        }
        self.policy_authorization_bindings[authorization.id] = binding
        self._record(
            "policy.authorization_bound",
            {
                "authorization_id": authorization.id,
                "action_id": action_id,
                "acting_principal_ref": acting_principal_ref,
                **binding,
            },
        )
        return authorization


def install_policy_runtime(kernel_cls) -> None:
    """Install Wave-5 sealed-policy gates without adding a second correctness writer."""
    if getattr(kernel_cls, "_wave5_policy_runtime_installed", False):
        return
    original_init = kernel_cls.__init__

    def __init__(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        _install_state(self)

    kernel_cls.__init__ = __init__
    kernel_cls.current_policy_access_revision = _current_policy_access_revision
    kernel_cls.current_policy_action_space_revision = _current_policy_action_space_revision
    kernel_cls.register_policy_frontier = _register_policy_frontier
    kernel_cls.register_information_partition = _register_information_partition
    kernel_cls.register_decision_epoch = _register_decision_epoch
    kernel_cls.register_policy_node = _register_policy_node
    kernel_cls.register_selection_record = _register_selection_record
    kernel_cls.register_decision_sufficiency = _register_decision_sufficiency
    kernel_cls.register_plan_seal = _register_plan_seal
    kernel_cls.register_policy_executability = _register_policy_executability
    kernel_cls._current_selection_status = _current_selection_status
    kernel_cls._require_registered_policy_bundle = _require_registered_policy_bundle
    kernel_cls.authorize_sealed_policy = _authorize_sealed_policy
    kernel_cls._wave5_policy_runtime_installed = True
