from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable

from .hashing import digest


class ControlPlaneResourceError(ValueError):
    pass


def _required(name: str, value: object) -> str:
    text = str(value).strip()
    if not text:
        raise ControlPlaneResourceError(f"{name} must be non-empty")
    return text


def _canon(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(sorted({str(value).strip() for value in values if str(value).strip()}))


def _nonnegative(name: str, value: int | float) -> float:
    number = float(value)
    if number < 0:
        raise ControlPlaneResourceError(f"{name} must be non-negative")
    return number


def _positive(name: str, value: int | float) -> float:
    number = float(value)
    if number <= 0:
        raise ControlPlaneResourceError(f"{name} must be positive")
    return number


def _interval(name: str, value) -> tuple[float, float]:
    if not isinstance(value, (tuple, list)) or len(value) != 2:
        raise ControlPlaneResourceError(f"{name} must be a two-element interval")
    start, end = float(value[0]), float(value[1])
    if start < 0 or end < start:
        raise ControlPlaneResourceError(f"{name} is invalid")
    return (start, end)


class ControlPlaneResourceKind(str, Enum):
    SERIAL = "SERIAL"
    CONCURRENCY = "CONCURRENCY"
    RATE_LIMIT = "RATE_LIMIT"
    CAPACITY_WINDOW = "CAPACITY_WINDOW"
    AUTHORITY_HUMAN = "AUTHORITY_HUMAN"
    KERNEL_WRITER = "KERNEL_WRITER"

    @classmethod
    def parse(cls, value: str | "ControlPlaneResourceKind") -> "ControlPlaneResourceKind":
        if isinstance(value, cls):
            return value
        try:
            return cls(str(value).strip().upper())
        except ValueError as exc:
            raise ControlPlaneResourceError(f"unsupported control-plane resource kind: {value}") from exc


@dataclass(frozen=True, slots=True)
class ControlPlaneResourceRevision:
    resource_id: str
    revision_id: str
    resource_kind: ControlPlaneResourceKind
    capacity_units: float
    concurrency_limit: int
    service_rate_per_second: float
    rate_window_seconds: float
    availability_interval: tuple[float, float]
    priority_policy_ref: str
    reservation_policy_ref: str
    regime_ref: str
    assurance_profile: str
    opaque_dimensions: tuple[str, ...]
    conservative_capacity_bound: float | None
    validity_regime: str
    canonical_digest: str

    @classmethod
    def create(
        cls,
        *,
        resource_id: str,
        revision_id: str,
        resource_kind: str | ControlPlaneResourceKind,
        capacity_units: int | float,
        concurrency_limit: int,
        service_rate_per_second: int | float,
        rate_window_seconds: int | float,
        availability_interval,
        priority_policy_ref: str,
        reservation_policy_ref: str,
        regime_ref: str,
        assurance_profile: str,
        opaque_dimensions: Iterable[str],
        conservative_capacity_bound: int | float | None,
        validity_regime: str,
    ) -> "ControlPlaneResourceRevision":
        kind = ControlPlaneResourceKind.parse(resource_kind)
        capacity = _nonnegative("capacity_units", capacity_units)
        concurrency = int(concurrency_limit)
        if concurrency < 0:
            raise ControlPlaneResourceError("concurrency_limit must be non-negative")
        service_rate = _nonnegative("service_rate_per_second", service_rate_per_second)
        rate_window = _positive("rate_window_seconds", rate_window_seconds)
        availability = _interval("availability_interval", availability_interval)
        opaque = _canon(opaque_dimensions)
        conservative = None
        if conservative_capacity_bound is not None:
            conservative = _nonnegative("conservative_capacity_bound", conservative_capacity_bound)
            if conservative > capacity:
                raise ControlPlaneResourceError("conservative_capacity_bound cannot exceed declared capacity")
        body = {
            "resource_id": _required("resource_id", resource_id),
            "revision_id": _required("revision_id", revision_id),
            "resource_kind": kind.value,
            "capacity_units": capacity,
            "concurrency_limit": concurrency,
            "service_rate_per_second": service_rate,
            "rate_window_seconds": rate_window,
            "availability_interval": availability,
            "priority_policy_ref": _required("priority_policy_ref", priority_policy_ref),
            "reservation_policy_ref": _required("reservation_policy_ref", reservation_policy_ref),
            "regime_ref": _required("regime_ref", regime_ref),
            "assurance_profile": _required("assurance_profile", assurance_profile),
            "opaque_dimensions": opaque,
            "conservative_capacity_bound": conservative,
            "validity_regime": _required("validity_regime", validity_regime),
        }
        return cls(
            resource_id=body["resource_id"],
            revision_id=body["revision_id"],
            resource_kind=kind,
            capacity_units=capacity,
            concurrency_limit=concurrency,
            service_rate_per_second=service_rate,
            rate_window_seconds=rate_window,
            availability_interval=availability,
            priority_policy_ref=body["priority_policy_ref"],
            reservation_policy_ref=body["reservation_policy_ref"],
            regime_ref=body["regime_ref"],
            assurance_profile=body["assurance_profile"],
            opaque_dimensions=opaque,
            conservative_capacity_bound=conservative,
            validity_regime=body["validity_regime"],
            canonical_digest=digest(body),
        )

    @property
    def supports_strong_bound(self) -> bool:
        return not self.opaque_dimensions or self.conservative_capacity_bound is not None

    @property
    def effective_capacity_units(self) -> float:
        if self.conservative_capacity_bound is None:
            return self.capacity_units
        return min(self.capacity_units, self.conservative_capacity_bound)

    def available_service(self, start: float, end: float) -> float:
        if end < start:
            raise ControlPlaneResourceError("service interval is inverted")
        available_start, available_end = self.availability_interval
        overlap = max(0.0, min(float(end), available_end) - max(float(start), available_start))
        if overlap <= 0:
            return 0.0
        if self.resource_kind in {
            ControlPlaneResourceKind.SERIAL,
            ControlPlaneResourceKind.KERNEL_WRITER,
            ControlPlaneResourceKind.CONCURRENCY,
            ControlPlaneResourceKind.AUTHORITY_HUMAN,
        }:
            capacity = self.effective_capacity_units
            if self.resource_kind in {ControlPlaneResourceKind.SERIAL, ControlPlaneResourceKind.KERNEL_WRITER}:
                capacity = min(capacity, 1.0)
            return overlap * self.service_rate_per_second * capacity
        if self.resource_kind == ControlPlaneResourceKind.RATE_LIMIT:
            windows = overlap / self.rate_window_seconds
            return windows * self.effective_capacity_units
        return overlap * self.service_rate_per_second * self.effective_capacity_units


@dataclass(frozen=True, slots=True)
class ReactionResourceDemand:
    resource_ref: str
    required_service: float
    required_concurrency_units: int
    release_offset_interval: tuple[float, float]
    demand_window: tuple[float, float]
    mandatory: bool
    canonical_digest: str

    @classmethod
    def create(
        cls,
        *,
        resource_ref: str,
        required_service: int | float,
        required_concurrency_units: int,
        release_offset_interval,
        demand_window,
        mandatory: bool,
    ) -> "ReactionResourceDemand":
        service = _nonnegative("required_service", required_service)
        concurrency = int(required_concurrency_units)
        if concurrency < 0:
            raise ControlPlaneResourceError("required_concurrency_units must be non-negative")
        release = _interval("release_offset_interval", release_offset_interval)
        window = _interval("demand_window", demand_window)
        body = {
            "resource_ref": _required("resource_ref", resource_ref),
            "required_service": service,
            "required_concurrency_units": concurrency,
            "release_offset_interval": release,
            "demand_window": window,
            "mandatory": bool(mandatory),
        }
        return cls(**body, canonical_digest=digest(body))


@dataclass(frozen=True, slots=True)
class ReactionJobContract:
    reaction_job_id: str
    revision_id: str
    policy_scope: str
    mission_revision: str
    information_partition_revision: str
    reaction_envelope_ref: str
    release_window: tuple[float, float]
    deadline: float
    resource_demands: tuple[ReactionResourceDemand, ...]
    coexistence_tags: tuple[str, ...]
    correlation_refs: tuple[str, ...]
    priority_class: str
    reservation_refs: tuple[str, ...]
    risk_class: str
    model_adequacy_debt_refs: tuple[str, ...]
    validity_regime: str
    canonical_digest: str

    @classmethod
    def create(
        cls,
        *,
        reaction_job_id: str,
        revision_id: str,
        policy_scope: str,
        mission_revision: str,
        information_partition_revision: str,
        reaction_envelope_ref: str,
        release_window,
        deadline: int | float,
        resource_demands: Iterable[ReactionResourceDemand],
        coexistence_tags: Iterable[str],
        correlation_refs: Iterable[str],
        priority_class: str,
        reservation_refs: Iterable[str],
        risk_class: str,
        model_adequacy_debt_refs: Iterable[str],
        validity_regime: str,
    ) -> "ReactionJobContract":
        release = _interval("release_window", release_window)
        deadline_value = _nonnegative("deadline", deadline)
        if deadline_value < release[1]:
            raise ControlPlaneResourceError("reaction job deadline cannot precede latest release")
        demands = tuple(sorted(tuple(resource_demands), key=lambda item: (item.resource_ref, item.canonical_digest)))
        if not demands:
            raise ControlPlaneResourceError("reaction job requires at least one resource demand")
        seen = set()
        for demand in demands:
            key = (demand.resource_ref, demand.canonical_digest)
            if key in seen:
                raise ControlPlaneResourceError("duplicate reaction resource demand")
            seen.add(key)
        body = {
            "reaction_job_id": _required("reaction_job_id", reaction_job_id),
            "revision_id": _required("revision_id", revision_id),
            "policy_scope": _required("policy_scope", policy_scope),
            "mission_revision": _required("mission_revision", mission_revision),
            "information_partition_revision": _required(
                "information_partition_revision", information_partition_revision
            ),
            "reaction_envelope_ref": _required("reaction_envelope_ref", reaction_envelope_ref),
            "release_window": release,
            "deadline": deadline_value,
            "resource_demand_digests": tuple(item.canonical_digest for item in demands),
            "coexistence_tags": _canon(coexistence_tags),
            "correlation_refs": _canon(correlation_refs),
            "priority_class": _required("priority_class", priority_class),
            "reservation_refs": _canon(reservation_refs),
            "risk_class": _required("risk_class", risk_class),
            "model_adequacy_debt_refs": _canon(model_adequacy_debt_refs),
            "validity_regime": _required("validity_regime", validity_regime),
        }
        return cls(
            reaction_job_id=body["reaction_job_id"],
            revision_id=body["revision_id"],
            policy_scope=body["policy_scope"],
            mission_revision=body["mission_revision"],
            information_partition_revision=body["information_partition_revision"],
            reaction_envelope_ref=body["reaction_envelope_ref"],
            release_window=release,
            deadline=deadline_value,
            resource_demands=demands,
            coexistence_tags=body["coexistence_tags"],
            correlation_refs=body["correlation_refs"],
            priority_class=body["priority_class"],
            reservation_refs=body["reservation_refs"],
            risk_class=body["risk_class"],
            model_adequacy_debt_refs=body["model_adequacy_debt_refs"],
            validity_regime=body["validity_regime"],
            canonical_digest=digest(body),
        )


@dataclass(frozen=True, slots=True)
class ControlPlaneReservation:
    reservation_id: str
    revision_id: str
    resource_ref: str
    policy_scope: str
    job_refs: tuple[str, ...]
    start_time: float
    end_time: float
    reserved_service: float
    reserved_concurrency_units: int
    priority_class: str
    preemptible: bool
    risk_justification_ref: str
    cross_future_value_ref: str
    validity_regime: str
    canonical_digest: str

    @classmethod
    def create(
        cls,
        *,
        reservation_id: str,
        revision_id: str,
        resource_ref: str,
        policy_scope: str,
        job_refs: Iterable[str],
        start_time: int | float,
        end_time: int | float,
        reserved_service: int | float,
        reserved_concurrency_units: int,
        priority_class: str,
        preemptible: bool,
        risk_justification_ref: str,
        cross_future_value_ref: str,
        validity_regime: str,
    ) -> "ControlPlaneReservation":
        start = _nonnegative("start_time", start_time)
        end = _nonnegative("end_time", end_time)
        if end <= start:
            raise ControlPlaneResourceError("reservation end_time must be after start_time")
        service = _nonnegative("reserved_service", reserved_service)
        concurrency = int(reserved_concurrency_units)
        if concurrency < 0:
            raise ControlPlaneResourceError("reserved_concurrency_units must be non-negative")
        jobs = _canon(job_refs)
        if not jobs:
            raise ControlPlaneResourceError("reservation requires at least one job ref")
        body = {
            "reservation_id": _required("reservation_id", reservation_id),
            "revision_id": _required("revision_id", revision_id),
            "resource_ref": _required("resource_ref", resource_ref),
            "policy_scope": _required("policy_scope", policy_scope),
            "job_refs": jobs,
            "start_time": start,
            "end_time": end,
            "reserved_service": service,
            "reserved_concurrency_units": concurrency,
            "priority_class": _required("priority_class", priority_class),
            "preemptible": bool(preemptible),
            "risk_justification_ref": _required("risk_justification_ref", risk_justification_ref),
            "cross_future_value_ref": _required("cross_future_value_ref", cross_future_value_ref),
            "validity_regime": _required("validity_regime", validity_regime),
        }
        return cls(**body, canonical_digest=digest(body))
