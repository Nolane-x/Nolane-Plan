from __future__ import annotations

from dataclasses import dataclass

from .hashing import digest
from .mission import MissionContract
from .principals import InformationItem, InformationPartitionRevision, PrincipalRegistry
from .types import CapsuleError


@dataclass(frozen=True, slots=True)
class DecisionCapsule:
    id: str
    recipient_principal_ref: str
    information_partition_digest: str
    information_access_profile_revision: int
    plan_snapshot_version: int
    mission_version: int
    canonical_version: int
    evidence_watermark: int
    decision_time: int | float
    item_ids: tuple[str, ...]
    action_ids: tuple[str, ...]
    dependency_digest: str
    expires_at: int | float | None = None


class CapsuleCompiler:
    def __init__(self, principals: PrincipalRegistry):
        self.principals = principals

    def compile(
        self,
        principal_ref: str,
        partition: InformationPartitionRevision,
        mission: MissionContract,
        canonical_version: int,
        action_ids: tuple[str, ...],
        evidence_watermark: int,
        plan_snapshot_version: int = 1,
        expires_at: int | float | None = None,
    ) -> DecisionCapsule:
        if partition.principal_ref != principal_ref:
            raise CapsuleError("partition principal mismatch")
        current_profile = self.principals.profile(principal_ref)
        if current_profile.revision != partition.access_profile_revision:
            raise CapsuleError("partition access profile is stale")
        dependency = digest({
            "principal": principal_ref,
            "partition": partition.digest,
            "access_revision": partition.access_profile_revision,
            "mission": mission.version,
            "canonical": canonical_version,
            "evidence_watermark": evidence_watermark,
            "actions": action_ids,
        })
        body = {
            "recipient": principal_ref,
            "partition": partition.digest,
            "mission": mission.version,
            "canonical": canonical_version,
            "dependency": dependency,
            "decision_time": partition.decision_time,
        }
        return DecisionCapsule(
            digest(body)[:24], principal_ref, partition.digest, partition.access_profile_revision,
            plan_snapshot_version, mission.version, canonical_version, evidence_watermark,
            partition.decision_time, partition.item_ids, tuple(action_ids), dependency, expires_at,
        )

    def validate(
        self,
        capsule: DecisionCapsule,
        principal_ref: str,
        partition: InformationPartitionRevision,
        mission: MissionContract,
        canonical_version: int,
        now: int | float | None = None,
    ) -> bool:
        if capsule.recipient_principal_ref != principal_ref:
            raise CapsuleError("cross-principal capsule reuse is forbidden")
        profile = self.principals.profile(principal_ref)
        if capsule.information_access_profile_revision != profile.revision:
            raise CapsuleError("capsule access profile is stale")
        if capsule.information_partition_digest != partition.digest or partition.principal_ref != principal_ref:
            raise CapsuleError("capsule information partition mismatch")
        if capsule.mission_version != mission.version:
            raise CapsuleError("capsule mission version is stale")
        if capsule.canonical_version != canonical_version:
            raise CapsuleError("capsule canonical state is stale")
        if capsule.expires_at is not None and now is not None and now > capsule.expires_at:
            raise CapsuleError("capsule expired")
        return True

    def hydrate(self, capsule: DecisionCapsule, principal_ref: str, item: InformationItem, decision_time: int | float):
        if capsule.recipient_principal_ref != principal_ref:
            raise CapsuleError("recipient mismatch")
        if not self.principals.info_available(item, principal_ref, decision_time):
            raise CapsuleError("hydration would escalate principal information scope")
        return item
