from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from .hashing import digest


@dataclass(frozen=True, slots=True)
class AccessProfile:
    revision: int
    principal_ref: str
    allowed_tags: frozenset[str]


@dataclass(frozen=True, slots=True)
class InformationItem:
    id: str
    payload: Any
    tags: frozenset[str]
    visible_at: int | float = 0
    valid_until: int | float | None = None
    provenance: str = "host"
    assurance: float = 1.0


@dataclass(frozen=True, slots=True)
class DeliveryRecord:
    item_id: str
    principal_ref: str
    observed_at: int | float


@dataclass(frozen=True, slots=True)
class InformationPartitionRevision:
    revision: int
    principal_ref: str
    access_profile_revision: int
    decision_time: int | float
    item_ids: tuple[str, ...]
    digest: str


@dataclass(frozen=True, slots=True)
class DecisionEpoch:
    id: str
    principal_ref: str
    information_partition_digest: str
    canonical_version: int
    mission_version: int
    decision_time: int | float


class PrincipalRegistry:
    def __init__(self) -> None:
        self._profiles: dict[str, AccessProfile] = {}
        self._deliveries: dict[tuple[str, str], DeliveryRecord] = {}
        self._partition_revision = 0

    def register(self, principal_ref: str, allowed_tags: Iterable[str]) -> AccessProfile:
        if not principal_ref.strip():
            raise ValueError("principal_ref must be canonical and non-empty")
        current = self._profiles.get(principal_ref)
        rev = 1 if current is None else current.revision + 1
        profile = AccessProfile(rev, principal_ref, frozenset(allowed_tags))
        self._profiles[principal_ref] = profile
        return profile

    def update_access(self, principal_ref: str, allowed_tags: Iterable[str]) -> AccessProfile:
        if principal_ref not in self._profiles:
            raise KeyError(principal_ref)
        return self.register(principal_ref, allowed_tags)

    def profile(self, principal_ref: str) -> AccessProfile:
        return self._profiles[principal_ref]

    def observe(self, principal_ref: str, item_id: str, observed_at: int | float) -> DeliveryRecord:
        if principal_ref not in self._profiles:
            raise KeyError(principal_ref)
        record = DeliveryRecord(item_id, principal_ref, observed_at)
        self._deliveries[(principal_ref, item_id)] = record
        return record

    def info_available(self, item: InformationItem, principal_ref: str, decision_time: int | float, minimum_assurance: float = 0.0) -> bool:
        profile = self._profiles.get(principal_ref)
        if profile is None:
            return False
        if item.visible_at > decision_time:
            return False
        if item.valid_until is not None and decision_time > item.valid_until:
            return False
        if item.assurance < minimum_assurance:
            return False
        if not item.tags.issubset(profile.allowed_tags):
            return False
        delivery = self._deliveries.get((principal_ref, item.id))
        if delivery is None or delivery.observed_at > decision_time:
            return False
        return True

    def build_partition(self, principal_ref: str, items: Iterable[InformationItem], decision_time: int | float, minimum_assurance: float = 0.0) -> InformationPartitionRevision:
        profile = self.profile(principal_ref)
        item_ids = tuple(sorted(item.id for item in items if self.info_available(item, principal_ref, decision_time, minimum_assurance)))
        self._partition_revision += 1
        body = {
            "principal_ref": principal_ref,
            "access_profile_revision": profile.revision,
            "decision_time": decision_time,
            "item_ids": item_ids,
        }
        return InformationPartitionRevision(self._partition_revision, principal_ref, profile.revision, decision_time, item_ids, digest(body))

    def decision_epoch(self, principal_ref: str, partition: InformationPartitionRevision, canonical_version: int, mission_version: int) -> DecisionEpoch:
        if partition.principal_ref != principal_ref:
            raise ValueError("partition principal mismatch")
        body = {
            "principal": principal_ref,
            "partition": partition.digest,
            "canonical_version": canonical_version,
            "mission_version": mission_version,
            "decision_time": partition.decision_time,
        }
        return DecisionEpoch(digest(body)[:24], principal_ref, partition.digest, canonical_version, mission_version, partition.decision_time)
