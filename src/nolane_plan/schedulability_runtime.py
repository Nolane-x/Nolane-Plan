from __future__ import annotations

from typing import Any

from .control_plane import ControlPlaneResourceRevision, ReactionJobContract
from .handoff_liveness import HandoffLivenessCertificate
from .handoff_stability import EdgeActivationAssessment, HandoffStabilityContract
from .option_independence import OptionIndependenceCertificate, RobustPreparednessAssessment
from .policy_coverage import ExecutablePolicyCoverageAssessment
from .schedulability import ReactionSchedulabilityCertificate
from .schedulability_codec import (
    activation_doc,
    coverage_doc,
    independence_doc,
    job_doc,
    liveness_doc,
    resource_doc,
    robust_preparedness_doc,
    schedulability_doc,
    stability_doc,
)
from .types import AuthorizationError


def _install_state(self) -> None:
    self.schedulability_writer_lock = self._writer_lock
    self.control_plane_resources: dict[str, ControlPlaneResourceRevision] = {}
    self.control_plane_resource_revisions: dict[str, ControlPlaneResourceRevision] = {}
    self.reaction_jobs: dict[str, ReactionJobContract] = {}
    self.reaction_job_revisions: dict[str, ReactionJobContract] = {}
    self.schedulability_certificates: dict[str, ReactionSchedulabilityCertificate] = {}
    self.policy_coverage_assessments: dict[str, ExecutablePolicyCoverageAssessment] = {}
    self.option_independence_certificates: dict[str, OptionIndependenceCertificate] = {}
    self.robust_preparedness_assessments: dict[str, RobustPreparednessAssessment] = {}
    self.handoff_liveness_certificates: dict[str, HandoffLivenessCertificate] = {}
    self.handoff_stability_contracts: dict[str, HandoffStabilityContract] = {}
    self.edge_activation_assessments: dict[str, EdgeActivationAssessment] = {}
    self.schedulability_authorization_bindings: dict[str, dict[str, str]] = {}


def _register_control_plane_resource(self, resource: ControlPlaneResourceRevision) -> ControlPlaneResourceRevision:
    with self._writer_lock:
        if resource.revision_id in self.control_plane_resource_revisions:
            raise ValueError(f"control-plane resource revision already exists: {resource.revision_id}")
        self.control_plane_resource_revisions[resource.revision_id] = resource
        self.control_plane_resources[resource.resource_id] = resource
        self._record("schedulability.resource_registered", resource_doc(resource))
        return resource


def _register_reaction_job(self, job: ReactionJobContract) -> ReactionJobContract:
    with self._writer_lock:
        if job.revision_id in self.reaction_job_revisions:
            raise ValueError(f"reaction job revision already exists: {job.revision_id}")
        if job.mission_revision != str(self.mission.current.version):
            raise ValueError("reaction job mission revision is stale")
        self.reaction_job_revisions[job.revision_id] = job
        self.reaction_jobs[job.reaction_job_id] = job
        self._record("schedulability.job_registered", job_doc(job))
        return job


def _certificate_current_objects(self, certificate: ReactionSchedulabilityCertificate):
    jobs: list[ReactionJobContract] = []
    resources: list[ControlPlaneResourceRevision] = []
    for job_id, expected_digest in certificate.reaction_job_digests:
        job = self.reaction_jobs.get(job_id)
        if job is None or job.canonical_digest != expected_digest:
            raise AuthorizationError(f"reaction job revision drifted or is unavailable: {job_id}")
        jobs.append(job)
    for resource_id, expected_digest in certificate.control_resource_digests:
        resource = self.control_plane_resources.get(resource_id)
        if resource is None or resource.canonical_digest != expected_digest:
            raise AuthorizationError(f"control-plane resource revision drifted or is unavailable: {resource_id}")
        resources.append(resource)
    if not certificate.is_current(jobs=jobs, resources=resources):
        raise AuthorizationError("schedulability certificate is stale against current jobs/resources")
    return tuple(jobs), tuple(resources)


def _register_schedulability_certificate(self, certificate: ReactionSchedulabilityCertificate) -> ReactionSchedulabilityCertificate:
    with self._writer_lock:
        if certificate.revision_id in self.schedulability_certificates:
            raise ValueError(f"schedulability certificate revision already exists: {certificate.revision_id}")
        if certificate.mission_revision != str(self.mission.current.version):
            raise ValueError("schedulability certificate mission revision is stale")
        try:
            self._certificate_current_objects(certificate)
        except AuthorizationError as exc:
            raise ValueError(str(exc)) from exc
        self.schedulability_certificates[certificate.revision_id] = certificate
        self._record("schedulability.certificate_registered", schedulability_doc(certificate))
        return certificate


def _register_policy_coverage_assessment(self, assessment: ExecutablePolicyCoverageAssessment) -> ExecutablePolicyCoverageAssessment:
    with self._writer_lock:
        if assessment.revision_id in self.policy_coverage_assessments:
            raise ValueError(f"policy coverage revision already exists: {assessment.revision_id}")
        self.policy_coverage_assessments[assessment.revision_id] = assessment
        self._record("schedulability.coverage_registered", coverage_doc(assessment))
        return assessment


def _register_option_independence_certificate(self, certificate: OptionIndependenceCertificate) -> OptionIndependenceCertificate:
    with self._writer_lock:
        if certificate.revision_id in self.option_independence_certificates:
            raise ValueError(f"option independence revision already exists: {certificate.revision_id}")
        self.option_independence_certificates[certificate.revision_id] = certificate
        self._record("schedulability.independence_registered", independence_doc(certificate))
        return certificate


def _register_robust_preparedness_assessment(self, assessment: RobustPreparednessAssessment) -> RobustPreparednessAssessment:
    with self._writer_lock:
        key = assessment.canonical_digest
        if key in self.robust_preparedness_assessments:
            raise ValueError("robust preparedness assessment already exists")
        self.robust_preparedness_assessments[key] = assessment
        self._record("schedulability.robust_preparedness_registered", robust_preparedness_doc(assessment))
        return assessment


def _register_handoff_liveness_certificate(self, certificate: HandoffLivenessCertificate) -> HandoffLivenessCertificate:
    with self._writer_lock:
        if certificate.revision_id in self.handoff_liveness_certificates:
            raise ValueError(f"handoff liveness revision already exists: {certificate.revision_id}")
        self.handoff_liveness_certificates[certificate.revision_id] = certificate
        self._record("schedulability.liveness_registered", liveness_doc(certificate))
        return certificate


def _register_handoff_stability_contract(self, contract: HandoffStabilityContract) -> HandoffStabilityContract:
    with self._writer_lock:
        if contract.revision_id in self.handoff_stability_contracts:
            raise ValueError(f"handoff stability revision already exists: {contract.revision_id}")
        self.handoff_stability_contracts[contract.revision_id] = contract
        self._record("schedulability.stability_registered", stability_doc(contract))
        return contract


def _register_edge_activation_assessment(self, assessment: EdgeActivationAssessment) -> EdgeActivationAssessment:
    with self._writer_lock:
        if not any(contract.canonical_digest == assessment.contract_digest for contract in self.handoff_stability_contracts.values()):
            raise ValueError("edge activation assessment references an unknown stability contract digest")
        key = assessment.canonical_digest
        if key in self.edge_activation_assessments:
            raise ValueError("edge activation assessment already exists")
        self.edge_activation_assessments[key] = assessment
        self._record("schedulability.edge_activation_registered", activation_doc(assessment))
        return assessment


def _require_wave6_bundle(
    self,
    *,
    action_id: str,
    schedulability_revision: str,
    coverage_revision: str,
    liveness_revision: str | None,
    stability_contract_revision: str | None,
    edge_activation_digest: str | None,
    independence_revision: str | None,
    require_safe_handoff: bool,
    require_closed_world: bool,
    require_robust_redundancy: bool,
):
    try:
        sched = self.schedulability_certificates[schedulability_revision]
        coverage = self.policy_coverage_assessments[coverage_revision]
    except KeyError as exc:
        raise AuthorizationError("Wave-6 authority lineage is incomplete") from exc
    if sched.mission_revision != str(self.mission.current.version):
        raise AuthorizationError("schedulability certificate mission revision is stale")
    if sched.policy_scope != f"action:{action_id}":
        raise AuthorizationError("schedulability certificate policy scope does not match action")
    if not sched.supports_strong_joint_guarantee:
        raise AuthorizationError("joint reaction schedulability is below the strong authority floor")
    self._certificate_current_objects(sched)
    if coverage.policy_scope != f"action:{action_id}":
        raise AuthorizationError("policy coverage scope does not match action")
    if require_closed_world and not coverage.open_world_complete:
        raise AuthorizationError("open-world policy coverage is not complete")

    liveness = None
    if require_safe_handoff:
        if not liveness_revision:
            raise AuthorizationError("SAFE_HANDOFF authority requires a liveness certificate")
        liveness = self.handoff_liveness_certificates.get(liveness_revision)
        if liveness is None or not liveness.supports_safe_handoff:
            raise AuthorizationError("handoff liveness does not support SAFE_HANDOFF authority")
    elif liveness_revision:
        liveness = self.handoff_liveness_certificates.get(liveness_revision)
        if liveness is None:
            raise AuthorizationError("handoff liveness certificate is unavailable")

    contract = None
    activation = None
    if stability_contract_revision or edge_activation_digest:
        if not stability_contract_revision or not edge_activation_digest:
            raise AuthorizationError("edge activation requires both stability contract and activation assessment")
        contract = self.handoff_stability_contracts.get(stability_contract_revision)
        activation = self.edge_activation_assessments.get(edge_activation_digest)
        if contract is None or activation is None:
            raise AuthorizationError("edge stability authority lineage is incomplete")
        if activation.contract_digest != contract.canonical_digest:
            raise AuthorizationError("edge activation assessment is bound to another stability contract")
        if not activation.supports_activation:
            raise AuthorizationError("policy edge is not stable at activation time")

    independence = None
    if require_robust_redundancy:
        if not independence_revision:
            raise AuthorizationError("robust redundancy authority requires an independence certificate")
        independence = self.option_independence_certificates.get(independence_revision)
        if independence is None or not independence.supports_robust_uplift:
            raise AuthorizationError("option set is not robust-independent under the declared failure set")
    elif independence_revision:
        independence = self.option_independence_certificates.get(independence_revision)
        if independence is None:
            raise AuthorizationError("option independence certificate is unavailable")
    return sched, coverage, liveness, contract, activation, independence


def _authorize_schedulable_policy(
    self,
    *,
    action_id: str,
    acting_principal_ref: str,
    grant_ids: tuple[str, ...],
    now: int | float,
    proof_artifact_revision: str,
    active_context,
    policy_node_revision: str,
    selection_record_id: str,
    sufficiency_revision: str,
    seal_revision: str,
    executability_revision: str,
    schedulability_revision: str,
    coverage_revision: str,
    liveness_revision: str | None = None,
    stability_contract_revision: str | None = None,
    edge_activation_digest: str | None = None,
    independence_revision: str | None = None,
    require_safe_handoff: bool = False,
    require_closed_world: bool = False,
    require_robust_redundancy: bool = False,
    capsule_id: str | None = None,
    adapter_id: str | None = None,
    **kwargs: Any,
):
    with self._writer_lock:
        sched, coverage, liveness, contract, activation, independence = self._require_wave6_bundle(
            action_id=action_id, schedulability_revision=schedulability_revision, coverage_revision=coverage_revision,
            liveness_revision=liveness_revision, stability_contract_revision=stability_contract_revision,
            edge_activation_digest=edge_activation_digest, independence_revision=independence_revision,
            require_safe_handoff=bool(require_safe_handoff), require_closed_world=bool(require_closed_world),
            require_robust_redundancy=bool(require_robust_redundancy),
        )
        authorization = self.authorize_sealed_policy(
            action_id=action_id, acting_principal_ref=acting_principal_ref, grant_ids=grant_ids, now=now,
            proof_artifact_revision=proof_artifact_revision, active_context=active_context,
            policy_node_revision=policy_node_revision, selection_record_id=selection_record_id,
            sufficiency_revision=sufficiency_revision, seal_revision=seal_revision,
            executability_revision=executability_revision, capsule_id=capsule_id, adapter_id=adapter_id, **kwargs,
        )
        binding = {
            "schedulability_revision": sched.revision_id, "schedulability_digest": sched.canonical_digest,
            "coverage_revision": coverage.revision_id, "coverage_digest": coverage.canonical_digest,
            "liveness_revision": liveness.revision_id if liveness else "",
            "liveness_digest": liveness.canonical_digest if liveness else "",
            "stability_contract_revision": contract.revision_id if contract else "",
            "stability_contract_digest": contract.canonical_digest if contract else "",
            "edge_activation_digest": activation.canonical_digest if activation else "",
            "independence_revision": independence.revision_id if independence else "",
            "independence_digest": independence.canonical_digest if independence else "",
        }
        self.schedulability_authorization_bindings[authorization.id] = binding
        self._record("schedulability.authorization_bound", {
            "authorization_id": authorization.id, "action_id": action_id,
            "acting_principal_ref": acting_principal_ref, **binding,
        })
        return authorization


def install_schedulability_runtime(kernel_cls) -> None:
    if getattr(kernel_cls, "_wave6_schedulability_runtime_installed", False):
        return
    original_init = kernel_cls.__init__

    def __init__(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        _install_state(self)

    kernel_cls.__init__ = __init__
    kernel_cls.register_control_plane_resource = _register_control_plane_resource
    kernel_cls.register_reaction_job = _register_reaction_job
    kernel_cls._certificate_current_objects = _certificate_current_objects
    kernel_cls.register_schedulability_certificate = _register_schedulability_certificate
    kernel_cls.register_policy_coverage_assessment = _register_policy_coverage_assessment
    kernel_cls.register_option_independence_certificate = _register_option_independence_certificate
    kernel_cls.register_robust_preparedness_assessment = _register_robust_preparedness_assessment
    kernel_cls.register_handoff_liveness_certificate = _register_handoff_liveness_certificate
    kernel_cls.register_handoff_stability_contract = _register_handoff_stability_contract
    kernel_cls.register_edge_activation_assessment = _register_edge_activation_assessment
    kernel_cls._require_wave6_bundle = _require_wave6_bundle
    kernel_cls.authorize_schedulable_policy = _authorize_schedulable_policy
    kernel_cls._wave6_schedulability_runtime_installed = True
