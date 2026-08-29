from __future__ import annotations

from typing import Any

from .artifacts import ArtifactBinding
from .communication import CommunicationLedger, CommunicationReceipt
from .execution import DispatchAttestation, ReconciliationEvidence, verify_dispatch_attestation
from .freshness import DependencyStamp
from .identity import IdentityError, PrincipalAttestation, PrincipalIdentityLedger
from .types import AuthorizationError


_STRONG_IDENTITY_FLOOR = 0.8


def _identity_domain(principal_ref: str) -> str:
    return f"principal-identity:{principal_ref}"


def _communication_domain(principal_ref: str) -> str:
    return f"communication:{principal_ref}"


def _install_state(self) -> None:
    self.identities = PrincipalIdentityLedger()
    self.communications = CommunicationLedger()
    self.authorization_identity_bindings: dict[str, str] = {}
    self.authorization_identity_attestations: dict[str, str] = {}
    self.dispatch_attestations: dict[str, DispatchAttestation] = {}
    self.reconciliation_evidence: dict[str, ReconciliationEvidence] = {}


def _bind_principal(
    self,
    attestation: PrincipalAttestation,
    *,
    allowed_tags: set[str],
    now: int | float,
):
    with self._writer_lock:
        binding = self.identities.accept(attestation, now=now)
        principal_ref = binding.canonical_principal_ref
        identity_domain = _identity_domain(principal_ref)
        principal_domain = f"principal:{principal_ref}"
        communication_domain = _communication_domain(principal_ref)
        self.freshness.ensure(identity_domain)
        self.freshness.ensure(principal_domain)
        self.freshness.ensure(communication_domain)

        profile = self.principals._profiles.get(principal_ref)
        if profile is None:
            profile = self.principals.register(principal_ref, allowed_tags)
        elif profile.allowed_tags != frozenset(allowed_tags):
            profile = self.principals.update_access(principal_ref, allowed_tags)

        self.plan_snapshot_version += 1
        self._bump(identity_domain, principal_domain, "plan")
        self._record("principal.identity_bound", {
            "principal_ref": principal_ref,
            "binding_id": binding.binding_id,
            "binding_revision": binding.binding_revision,
            "attestation_id": binding.attestation_id,
            "source": binding.source,
            "source_subject": binding.source_subject,
            "assurance": binding.assurance,
            "identity_generation": self.freshness.generation(identity_domain),
            "access_revision": profile.revision,
        })
        return binding


def _revoke_principal_attestation(self, attestation_id: str, *, revoked_at: int | float) -> None:
    with self._writer_lock:
        attestation = self.identities.attestation(attestation_id)
        self.identities.revoke(attestation_id, revoked_at=revoked_at)
        principal_ref = attestation.canonical_principal_ref
        identity_domain = _identity_domain(principal_ref)
        self.freshness.ensure(identity_domain)
        self.plan_snapshot_version += 1
        self._bump(identity_domain, f"principal:{principal_ref}", "plan")
        self._record("principal.identity_revoked", {
            "principal_ref": principal_ref,
            "attestation_id": attestation_id,
            "revoked_at": revoked_at,
            "identity_generation": self.freshness.generation(identity_domain),
        })


def _transfer_information(
    self,
    *,
    receipt_id: str,
    source_principal_ref: str,
    recipient_principal_ref: str,
    item_id: str,
    sent_at: int | float,
    delivered_at: int | float | None = None,
    observed_at: int | float | None = None,
    delivery_evidence_ref: str | None = None,
    observation_evidence_ref: str | None = None,
    valid_until: int | float | None = None,
    access_condition: str | None = None,
    minimum_identity_assurance: float = _STRONG_IDENTITY_FLOOR,
) -> CommunicationReceipt:
    with self._writer_lock:
        if item_id not in self.information_items:
            raise KeyError(item_id)
        self.identities.current(
            source_principal_ref,
            now=sent_at,
            minimum_assurance=minimum_identity_assurance,
        )
        if recipient_principal_ref not in self.principals._profiles:
            raise IdentityError("recipient has no registered principal access profile")

        receipt = self.communications.sent(
            receipt_id=receipt_id,
            source_principal_ref=source_principal_ref,
            recipient_principal_ref=recipient_principal_ref,
            semantic_payload_refs=(item_id,),
            sent_at=sent_at,
            valid_until=valid_until,
            access_condition=access_condition,
            provenance="nolane-plan:host-grounded-transfer",
        )
        self._record("communication.sent", {
            "receipt_id": receipt.id,
            "source_principal_ref": source_principal_ref,
            "recipient_principal_ref": recipient_principal_ref,
            "item_id": item_id,
            "sent_at": sent_at,
            "valid_until": valid_until,
        })

        if delivered_at is not None:
            if not delivery_evidence_ref:
                raise AuthorizationError("grounded delivery requires delivery evidence")
            receipt = self.communications.delivered(
                receipt.id,
                delivered_at=delivered_at,
                evidence_ref=delivery_evidence_ref,
            )
            self._record("communication.delivered", {
                "receipt_id": receipt.id,
                "recipient_principal_ref": recipient_principal_ref,
                "delivered_at": delivered_at,
                "evidence_ref": delivery_evidence_ref,
            })

        if observed_at is not None:
            if delivered_at is None:
                raise AuthorizationError("recipient observation requires grounded delivery")
            if not observation_evidence_ref:
                raise AuthorizationError("grounded observation requires observation evidence")
            self.identities.current(
                recipient_principal_ref,
                now=observed_at,
                minimum_assurance=minimum_identity_assurance,
            )
            receipt = self.communications.observed(
                receipt.id,
                observed_at=observed_at,
                evidence_ref=observation_evidence_ref,
            )
            self.principals.observe(recipient_principal_ref, item_id, observed_at)
            communication_domain = _communication_domain(recipient_principal_ref)
            self.freshness.ensure(communication_domain)
            self._bump(communication_domain, f"principal:{recipient_principal_ref}")
            self._record("communication.observed", {
                "receipt_id": receipt.id,
                "recipient_principal_ref": recipient_principal_ref,
                "item_id": item_id,
                "observed_at": observed_at,
                "evidence_ref": observation_evidence_ref,
                "communication_generation": self.freshness.generation(communication_domain),
            })
        return receipt


def _compile_strong_capsule(
    self,
    principal_ref: str,
    decision_time: int | float,
    action_ids: tuple[str, ...],
    *,
    minimum_identity_assurance: float = _STRONG_IDENTITY_FLOOR,
):
    with self._writer_lock:
        binding = self.identities.current(
            principal_ref,
            now=decision_time,
            minimum_assurance=minimum_identity_assurance,
        )
        identity_domain = _identity_domain(principal_ref)
        communication_domain = _communication_domain(principal_ref)
        self.freshness.ensure(identity_domain)
        self.freshness.ensure(communication_domain)
        capsule = self.compile_capsule(principal_ref, decision_time, action_ids)
        original = self.artifacts.get(capsule.id)
        original_domains = tuple(domain for domain, _ in original.dependency_stamp.generations)
        strong_domains = tuple(dict.fromkeys((*original_domains, identity_domain, communication_domain)))
        self.artifacts._items[capsule.id] = ArtifactBinding(
            original.id,
            original.kind,
            original.produced_sequence,
            DependencyStamp.capture(self.freshness, strong_domains),
            original.decision_cut_id,
        )
        self._record("capsule.identity_bound", {
            "capsule_id": capsule.id,
            "principal_ref": principal_ref,
            "principal_binding_id": binding.binding_id,
            "principal_attestation_id": binding.attestation_id,
            "identity_generation": self.freshness.generation(identity_domain),
            "communication_generation": self.freshness.generation(communication_domain),
        })
        return capsule


def _authorize_strong(
    self,
    action_id: str,
    acting_principal_ref: str,
    grant_ids: tuple[str, ...],
    now: int | float,
    *,
    capsule_id: str | None = None,
    adapter_id: str | None = None,
    minimum_identity_assurance: float = _STRONG_IDENTITY_FLOOR,
    **kwargs: Any,
):
    with self._writer_lock:
        binding = self.identities.current(
            acting_principal_ref,
            now=now,
            minimum_assurance=minimum_identity_assurance,
        )
        identity_domain = _identity_domain(acting_principal_ref)
        self.freshness.ensure(identity_domain)
        if capsule_id is not None:
            artifact = self.artifacts.get(capsule_id)
            domains = {domain for domain, _ in artifact.dependency_stamp.generations}
            if identity_domain not in domains:
                raise AuthorizationError("strong authorization requires an identity-bound decision capsule")
        authorization = self.authorize(
            action_id,
            acting_principal_ref,
            grant_ids,
            now,
            capsule_id=capsule_id,
            adapter_id=adapter_id,
            **kwargs,
        )
        self.authorization_identity_bindings[authorization.id] = binding.binding_id
        self.authorization_identity_attestations[authorization.id] = binding.attestation_id
        self._record("action.authorization_identity_bound", {
            "authorization_id": authorization.id,
            "acting_principal_ref": acting_principal_ref,
            "principal_binding_id": binding.binding_id,
            "principal_attestation_id": binding.attestation_id,
            "identity_generation": self.freshness.generation(identity_domain),
        })
        return authorization


def _dispatch_strong(
    self,
    authorization_id: str,
    presented_principal_ref: str,
    adapter,
    dispatch_attestation: DispatchAttestation,
    now: int | float,
    *,
    emergency_authorized: bool = False,
    minimum_identity_assurance: float = _STRONG_IDENTITY_FLOOR,
):
    with self._writer_lock:
        authorization = self.authorizations[authorization_id]
        if authorization.acting_principal_ref != presented_principal_ref:
            raise AuthorizationError("strong dispatch presented principal mismatch")
        binding = self.identities.current(
            presented_principal_ref,
            now=now,
            minimum_assurance=minimum_identity_assurance,
        )
        authorized_binding_id = self.authorization_identity_bindings.get(authorization_id)
        if authorized_binding_id is None:
            raise AuthorizationError("authorization has no strong host identity binding")
        if binding.binding_id != authorized_binding_id:
            raise AuthorizationError("principal identity changed after authorization; re-authorization required")
        tx = self.transaction_for_authorization(authorization_id)
        adapter_id = authorization.adapter_id or getattr(adapter, "adapter_id", None)
        adapter_revision = authorization.adapter_revision or getattr(adapter, "adapter_revision", None)
        if adapter_id is None or adapter_revision is None:
            raise AuthorizationError("strong dispatch requires an adapter identity and revision")
        verify_dispatch_attestation(
            dispatch_attestation,
            authorization_id=authorization_id,
            transaction_id=tx.id,
            action_id=authorization.action_id,
            expected_principal_ref=authorization.acting_principal_ref,
            adapter_id=adapter_id,
            adapter_revision=int(adapter_revision),
            principal_binding=binding,
            minimum_assurance=minimum_identity_assurance,
        )
        self.dispatch_attestations[authorization_id] = dispatch_attestation
        self._record("action.dispatch_attested", {
            "authorization_id": authorization_id,
            "transaction_id": tx.id,
            "action_id": authorization.action_id,
            "principal_ref": binding.canonical_principal_ref,
            "principal_binding_id": binding.binding_id,
            "principal_attestation_id": binding.attestation_id,
            "dispatch_attestation_id": dispatch_attestation.attestation_id,
            "adapter_id": adapter_id,
            "adapter_revision": int(adapter_revision),
            "assurance": dispatch_attestation.assurance,
        })
        return self.dispatch(
            authorization_id,
            presented_principal_ref,
            adapter,
            now,
            emergency_authorized=emergency_authorized,
        )


def _reconcile_strong(
    self,
    authorization_id: str,
    evidence: ReconciliationEvidence,
    *,
    state_patch: dict[str, Any] | None = None,
    minimum_assurance: float = _STRONG_IDENTITY_FLOOR,
):
    with self._writer_lock:
        tx = self.transaction_for_authorization(authorization_id)
        self.identities.current(
            tx.principal_ref,
            now=evidence.observed_at,
            minimum_assurance=minimum_identity_assurance,
        )
        if evidence.evidence_id in self.reconciliation_evidence:
            raise AuthorizationError("reconciliation evidence was already consumed")
        reconciled = self.transactions.reconcile_with_evidence(
            tx.id,
            evidence,
            minimum_assurance=minimum_identity_assurance,
        )
        self.reconciliation_evidence[evidence.evidence_id] = evidence
        self._record("action.reconciled_evidence", {
            "transaction_id": tx.id,
            "authorization_id": authorization_id,
            "evidence_id": evidence.evidence_id,
            "outcome_applied": evidence.outcome_applied,
            "principal_ref": evidence.canonical_principal_ref,
            "adapter_id": evidence.adapter_id,
            "adapter_revision": evidence.adapter_revision,
            "assurance": evidence.assurance,
        })
        if evidence.outcome_applied:
            self._commit_action_patch(tx.id, dict(state_patch or {}), None)
        return self.transactions.get(tx.id) if evidence.outcome_applied else reconciled


def install_trust_runtime(kernel_cls) -> None:
    """Install Wave-3 trust semantics without creating a second correctness writer."""
    if getattr(kernel_cls, "_wave3_trust_runtime_installed", False):
        return
    original_init = kernel_cls.__init__

    def __init__(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        _install_state(self)

    kernel_cls.__init__ = __init__
    kernel_cls.bind_principal = _bind_principal
    kernel_cls.revoke_principal_attestation = _revoke_principal_attestation
    kernel_cls.transfer_information = _transfer_information
    kernel_cls.compile_strong_capsule = _compile_strong_capsule
    kernel_cls.authorize_strong = _authorize_strong
    kernel_cls.dispatch_strong = _dispatch_strong
    kernel_cls.reconcile_strong = _reconcile_strong
    kernel_cls._wave3_trust_runtime_installed = True
