from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Mapping

from .hashing import digest


class HandoffStabilityError(ValueError):
    pass


def _required(name: str, value: object) -> str:
    text = str(value).strip()
    if not text:
        raise HandoffStabilityError(f"{name} must be non-empty")
    return text


def _canon(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(sorted({str(value).strip() for value in values if str(value).strip()}))


def _time(name: str, value: int | float) -> float:
    number = float(value)
    if number < 0:
        raise HandoffStabilityError(f"{name} must be non-negative")
    return number


@dataclass(frozen=True, slots=True)
class HandoffStabilityContract:
    contract_id: str
    revision_id: str
    policy_edge_ref: str
    protected_predicate_refs: tuple[str, ...]
    protected_generation_bindings: tuple[tuple[str, int], ...]
    lock_or_reservation_refs: tuple[str, ...]
    stability_start: float
    stability_end: float
    external_writer_assumption_refs: tuple[str, ...]
    refresh_required_predicate_refs: tuple[str, ...]
    authorization_time_precondition_refs: tuple[str, ...]
    invalidating_event_refs: tuple[str, ...]
    open_side_effect_refs: tuple[str, ...]
    fallback_on_instability: str
    opacity_debt_refs: tuple[str, ...]
    validity_regime: str
    canonical_digest: str

    @classmethod
    def create(
        cls,
        *,
        contract_id: str,
        revision_id: str,
        policy_edge_ref: str,
        protected_predicate_refs: Iterable[str],
        protected_generation_bindings: Iterable[tuple[str, int]],
        lock_or_reservation_refs: Iterable[str],
        stability_start: int | float,
        stability_end: int | float,
        external_writer_assumption_refs: Iterable[str],
        refresh_required_predicate_refs: Iterable[str],
        authorization_time_precondition_refs: Iterable[str],
        invalidating_event_refs: Iterable[str],
        open_side_effect_refs: Iterable[str],
        fallback_on_instability: str,
        opacity_debt_refs: Iterable[str],
        validity_regime: str,
    ) -> "HandoffStabilityContract":
        predicates = _canon(protected_predicate_refs)
        if not predicates:
            raise HandoffStabilityError("stability contract requires protected predicates")
        bindings: list[tuple[str, int]] = []
        seen = set()
        for raw_domain, raw_generation in protected_generation_bindings:
            domain = _required("generation domain", raw_domain)
            generation = int(raw_generation)
            if generation < 0:
                raise HandoffStabilityError("protected generation cannot be negative")
            if domain in seen:
                raise HandoffStabilityError("duplicate protected generation domain")
            seen.add(domain)
            bindings.append((domain, generation))
        if not bindings:
            raise HandoffStabilityError("stability contract requires protected generation bindings")
        bindings.sort()
        start = _time("stability_start", stability_start)
        end = _time("stability_end", stability_end)
        if end < start:
            raise HandoffStabilityError("stability window is inverted")
        refresh = _canon(refresh_required_predicate_refs)
        if not set(refresh).issubset(set(predicates)):
            raise HandoffStabilityError("refresh-required predicates must be protected predicates")
        auth_preconditions = _canon(authorization_time_precondition_refs)
        if not set(auth_preconditions).issubset(set(predicates)):
            raise HandoffStabilityError("authorization preconditions must be protected predicates")
        body = {
            "contract_id": _required("contract_id", contract_id),
            "revision_id": _required("revision_id", revision_id),
            "policy_edge_ref": _required("policy_edge_ref", policy_edge_ref),
            "protected_predicate_refs": predicates,
            "protected_generation_bindings": tuple(bindings),
            "lock_or_reservation_refs": _canon(lock_or_reservation_refs),
            "stability_start": start,
            "stability_end": end,
            "external_writer_assumption_refs": _canon(external_writer_assumption_refs),
            "refresh_required_predicate_refs": refresh,
            "authorization_time_precondition_refs": auth_preconditions,
            "invalidating_event_refs": _canon(invalidating_event_refs),
            "open_side_effect_refs": _canon(open_side_effect_refs),
            "fallback_on_instability": _required("fallback_on_instability", fallback_on_instability),
            "opacity_debt_refs": _canon(opacity_debt_refs),
            "validity_regime": _required("validity_regime", validity_regime),
        }
        return cls(**body, canonical_digest=digest(body))


class EdgeActivationStatus(str, Enum):
    STABLE = "STABLE"
    REFRESHED = "REFRESHED"
    REFRESH_REQUIRED = "REFRESH_REQUIRED"
    INVALID = "INVALID"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class EdgeActivationAssessment:
    contract_digest: str
    status: EdgeActivationStatus
    required_refresh_predicates: tuple[str, ...]
    blocker_refs: tuple[str, ...]
    refreshed_predicates: tuple[str, ...]
    fallback_ref: str
    assessed_at: float
    canonical_digest: str

    @property
    def supports_activation(self) -> bool:
        return self.status in {EdgeActivationStatus.STABLE, EdgeActivationStatus.REFRESHED}


class HandoffStabilityEvaluator:
    @staticmethod
    def _predicates_for_domains(
        contract: HandoffStabilityContract,
        domains: Iterable[str],
    ) -> set[str]:
        refreshable = set(contract.refresh_required_predicate_refs)
        result: set[str] = set()
        for domain in domains:
            matches = {
                predicate
                for predicate in refreshable
                if predicate == domain
                or predicate.startswith(f"{domain}-")
                or predicate.startswith(f"{domain}:")
            }
            result.update(matches or refreshable)
        return result

    @classmethod
    def assess(
        cls,
        *,
        contract: HandoffStabilityContract,
        current_generations: Mapping[str, int],
        refreshed_predicates: Iterable[str],
        active_lock_or_reservation_refs: Iterable[str],
        observed_invalidating_events: Iterable[str],
        resolved_side_effect_refs: Iterable[str],
        current_external_writer_assumption_refs: Iterable[str],
        now: int | float,
    ) -> EdgeActivationAssessment:
        instant = _time("now", now)
        refreshed = set(_canon(refreshed_predicates))
        active_locks = set(_canon(active_lock_or_reservation_refs))
        invalidating = set(_canon(observed_invalidating_events))
        resolved_effects = set(_canon(resolved_side_effect_refs))
        writers = set(_canon(current_external_writer_assumption_refs))

        blockers: list[str] = []
        required_refresh: set[str] = set()

        triggered_invalidators = invalidating.intersection(contract.invalidating_event_refs)
        if triggered_invalidators:
            blockers.extend(f"invalidating_event:{ref}" for ref in sorted(triggered_invalidators))
            status = EdgeActivationStatus.INVALID
        elif contract.opacity_debt_refs:
            blockers.extend(f"opacity:{ref}" for ref in contract.opacity_debt_refs)
            status = EdgeActivationStatus.UNKNOWN
        else:
            expected = dict(contract.protected_generation_bindings)
            drifted_domains = {
                domain
                for domain, generation in expected.items()
                if int(current_generations.get(domain, -1)) != generation
            }
            required_refresh.update(cls._predicates_for_domains(contract, drifted_domains))
            if drifted_domains:
                blockers.extend(f"generation_drift:{domain}" for domain in sorted(drifted_domains))

            if instant < contract.stability_start or instant > contract.stability_end:
                required_refresh.update(contract.refresh_required_predicate_refs)
                blockers.append("stability_window_not_current")

            missing_locks = set(contract.lock_or_reservation_refs).difference(active_locks)
            if missing_locks:
                required_refresh.update(contract.refresh_required_predicate_refs)
                blockers.append("lock_or_reservation_not_current")

            expected_writers = set(contract.external_writer_assumption_refs)
            if writers != expected_writers:
                required_refresh.update(contract.refresh_required_predicate_refs)
                blockers.append("external_writer_assumption_drift")

            unresolved_effects = set(contract.open_side_effect_refs).difference(resolved_effects)
            if unresolved_effects:
                required_refresh.update(contract.refresh_required_predicate_refs)
                blockers.extend(f"open_side_effect:{ref}" for ref in sorted(unresolved_effects))

            still_required = required_refresh.difference(refreshed)
            if still_required:
                status = EdgeActivationStatus.REFRESH_REQUIRED
            elif required_refresh:
                status = EdgeActivationStatus.REFRESHED
                blockers = [item for item in blockers if not item.startswith("generation_drift:")]
                blockers = [
                    item
                    for item in blockers
                    if item
                    not in {
                        "stability_window_not_current",
                        "external_writer_assumption_drift",
                    }
                    and not item.startswith("open_side_effect:")
                ]
            else:
                status = EdgeActivationStatus.STABLE

        body = {
            "contract_digest": contract.canonical_digest,
            "status": status.value,
            "required_refresh_predicates": tuple(sorted(required_refresh.difference(refreshed))),
            "blocker_refs": tuple(blockers),
            "refreshed_predicates": tuple(sorted(refreshed)),
            "fallback_ref": contract.fallback_on_instability,
            "assessed_at": instant,
        }
        return EdgeActivationAssessment(
            contract_digest=body["contract_digest"],
            status=status,
            required_refresh_predicates=body["required_refresh_predicates"],
            blocker_refs=body["blocker_refs"],
            refreshed_predicates=body["refreshed_predicates"],
            fallback_ref=body["fallback_ref"],
            assessed_at=instant,
            canonical_digest=digest(body),
        )
