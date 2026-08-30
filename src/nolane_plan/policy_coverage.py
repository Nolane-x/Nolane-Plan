from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable

from .hashing import digest
from .policy_certificates import PolicyTotalityCertificate, TotalityMode


class PolicyCoverageError(ValueError):
    pass


def _required(name: str, value: object) -> str:
    text = str(value).strip()
    if not text:
        raise PolicyCoverageError(f"{name} must be non-empty")
    return text


def _canon(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(sorted({str(value).strip() for value in values if str(value).strip()}))


class ModelAdequacyLevel(str, Enum):
    STRONG = "STRONG"
    DEGRADED = "DEGRADED"
    UNKNOWN = "UNKNOWN"
    UNSUPPORTED = "UNSUPPORTED"

    @classmethod
    def parse(cls, value: str | "ModelAdequacyLevel") -> "ModelAdequacyLevel":
        if isinstance(value, cls):
            return value
        try:
            return cls(str(value).strip().upper())
        except ValueError as exc:
            raise PolicyCoverageError(f"unsupported model adequacy level: {value}") from exc


class ResidualOpenWorldStatus(str, Enum):
    CLOSED = "CLOSED"
    ACTIVE = "ACTIVE"
    UNKNOWN = "UNKNOWN"

    @classmethod
    def parse(cls, value: str | "ResidualOpenWorldStatus") -> "ResidualOpenWorldStatus":
        if isinstance(value, cls):
            return value
        try:
            return cls(str(value).strip().upper())
        except ValueError as exc:
            raise PolicyCoverageError(f"unsupported residual open-world status: {value}") from exc


@dataclass(frozen=True, slots=True)
class ExecutablePolicyCoverageAssessment:
    assessment_id: str
    revision_id: str
    policy_scope: str
    policy_totality_certificate_ref: str
    policy_totality_certificate_digest: str
    policy_totality_mode: TotalityMode
    transition_observation_model_adequacy: ModelAdequacyLevel
    residual_open_world_status: ResidualOpenWorldStatus
    residual_debt_refs: tuple[str, ...]
    closed_domain_proof_ref: str | None
    created_sequence: int
    validity_regime: str
    qualifier_refs: tuple[str, ...]
    canonical_digest: str

    @classmethod
    def create(
        cls,
        *,
        assessment_id: str,
        revision_id: str,
        policy_scope: str,
        policy_totality_certificate: PolicyTotalityCertificate,
        transition_observation_model_adequacy: str | ModelAdequacyLevel,
        residual_open_world_status: str | ResidualOpenWorldStatus,
        residual_debt_refs: Iterable[str],
        closed_domain_proof_ref: str | None,
        created_sequence: int,
        validity_regime: str,
    ) -> "ExecutablePolicyCoverageAssessment":
        sequence = int(created_sequence)
        if sequence < 0:
            raise PolicyCoverageError("created_sequence cannot be negative")
        adequacy = ModelAdequacyLevel.parse(transition_observation_model_adequacy)
        residual_status = ResidualOpenWorldStatus.parse(residual_open_world_status)
        debts = _canon(residual_debt_refs)
        closed_proof = _required("closed_domain_proof_ref", closed_domain_proof_ref) if closed_domain_proof_ref else None

        if residual_status is ResidualOpenWorldStatus.ACTIVE and not debts:
            raise PolicyCoverageError("ACTIVE residual open-world status requires explicit residual debt")
        if residual_status is ResidualOpenWorldStatus.CLOSED and debts:
            raise PolicyCoverageError("CLOSED residual open-world status cannot carry residual debt")

        qualifiers: list[str] = []
        if policy_totality_certificate.mode is not TotalityMode.TOTAL:
            qualifiers.append(f"totality:{policy_totality_certificate.mode.value}")
        if adequacy is not ModelAdequacyLevel.STRONG:
            qualifiers.append(f"model-adequacy:{adequacy.value}")
        if residual_status is not ResidualOpenWorldStatus.CLOSED:
            qualifiers.append(f"residual:{residual_status.value}")
        qualifiers.extend(f"residual-debt:{ref}" for ref in debts)
        if not closed_proof:
            qualifiers.append("closed-domain-proof-missing")

        body = {
            "assessment_id": _required("assessment_id", assessment_id),
            "revision_id": _required("revision_id", revision_id),
            "policy_scope": _required("policy_scope", policy_scope),
            "policy_totality_certificate_ref": _required(
                "policy_totality_certificate_ref", policy_totality_certificate.certificate_id
            ),
            "policy_totality_certificate_digest": policy_totality_certificate.canonical_digest,
            "policy_totality_mode": policy_totality_certificate.mode.value,
            "transition_observation_model_adequacy": adequacy.value,
            "residual_open_world_status": residual_status.value,
            "residual_debt_refs": debts,
            "closed_domain_proof_ref": closed_proof,
            "created_sequence": sequence,
            "validity_regime": _required("validity_regime", validity_regime),
            "qualifier_refs": tuple(sorted(qualifiers)),
        }
        return cls(
            assessment_id=body["assessment_id"],
            revision_id=body["revision_id"],
            policy_scope=body["policy_scope"],
            policy_totality_certificate_ref=body["policy_totality_certificate_ref"],
            policy_totality_certificate_digest=body["policy_totality_certificate_digest"],
            policy_totality_mode=policy_totality_certificate.mode,
            transition_observation_model_adequacy=adequacy,
            residual_open_world_status=residual_status,
            residual_debt_refs=debts,
            closed_domain_proof_ref=closed_proof,
            created_sequence=sequence,
            validity_regime=body["validity_regime"],
            qualifier_refs=body["qualifier_refs"],
            canonical_digest=digest(body),
        )

    @property
    def modeled_total(self) -> bool:
        return self.policy_totality_mode is TotalityMode.TOTAL

    @property
    def open_world_complete(self) -> bool:
        return (
            self.modeled_total
            and self.transition_observation_model_adequacy is ModelAdequacyLevel.STRONG
            and self.residual_open_world_status is ResidualOpenWorldStatus.CLOSED
            and not self.residual_debt_refs
            and self.closed_domain_proof_ref is not None
        )
