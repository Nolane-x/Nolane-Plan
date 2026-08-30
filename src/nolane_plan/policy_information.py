from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from .hashing import digest


def _canon(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(sorted({str(value).strip() for value in values if str(value).strip()}))


def _nonempty(name: str, value: Any) -> str:
    text = str(value).strip()
    if not text:
        raise ValueError(f"{name} must be non-empty")
    return text


def _canon_classes(values: Mapping[str, Iterable[str]]) -> tuple[tuple[str, tuple[str, ...]], ...]:
    rows: list[tuple[str, tuple[str, ...]]] = []
    seen_histories: set[str] = set()
    for class_ref, histories in values.items():
        class_id = _nonempty("information class", class_ref)
        members = _canon(histories)
        if not members:
            raise ValueError(f"information class {class_id!r} must contain at least one history")
        overlap = seen_histories.intersection(members)
        if overlap:
            raise ValueError(f"history cannot appear in more than one information class: {sorted(overlap)!r}")
        seen_histories.update(members)
        rows.append((class_id, members))
    return tuple(sorted(rows))


@dataclass(frozen=True, slots=True)
class InformationPartitionRevision:
    logical_id: str
    revision_id: str
    mission_revision: int
    decision_epoch_ref: str
    principal_scope_ref: str
    information_access_profile_revision: str
    principal_observation_history_digest: str
    principal_delivery_frontier_refs: tuple[str, ...]
    canonical_state_version: int
    observation_history_digest: str
    observable_predicate_set: tuple[str, ...]
    hidden_or_unrevealed_predicate_set: tuple[str, ...]
    information_equivalence_classes: tuple[tuple[str, tuple[str, ...]], ...]
    reveal_event_refs: tuple[str, ...]
    observation_model_refs: tuple[str, ...]
    perfect_recall_basis_ref: str
    abstraction_certificate_refs: tuple[str, ...]
    debt_refs: tuple[str, ...]
    validity_regime: str
    canonical_digest: str

    @classmethod
    def create(
        cls,
        *,
        logical_id: str,
        revision_id: str,
        mission_revision: int,
        decision_epoch_ref: str,
        principal_scope_ref: str,
        information_access_profile_revision: str,
        principal_observation_history_digest: str,
        principal_delivery_frontier_refs: Iterable[str],
        canonical_state_version: int,
        observation_history_digest: str,
        observable_predicate_set: Iterable[str],
        hidden_or_unrevealed_predicate_set: Iterable[str],
        information_equivalence_classes: Mapping[str, Iterable[str]],
        reveal_event_refs: Iterable[str],
        observation_model_refs: Iterable[str],
        perfect_recall_basis_ref: str,
        abstraction_certificate_refs: Iterable[str],
        debt_refs: Iterable[str],
        validity_regime: str,
    ) -> "InformationPartitionRevision":
        logical = _nonempty("logical_id", logical_id)
        revision = _nonempty("revision_id", revision_id)
        epoch = _nonempty("decision_epoch_ref", decision_epoch_ref)
        principal = _nonempty("principal_scope_ref", principal_scope_ref)
        access = _nonempty("information_access_profile_revision", information_access_profile_revision)
        principal_history = _nonempty("principal_observation_history_digest", principal_observation_history_digest)
        observation_history = _nonempty("observation_history_digest", observation_history_digest)
        recall = _nonempty("perfect_recall_basis_ref", perfect_recall_basis_ref)
        regime = _nonempty("validity_regime", validity_regime)
        if int(mission_revision) < 1:
            raise ValueError("mission_revision must be positive")
        if int(canonical_state_version) < 1:
            raise ValueError("canonical_state_version must be positive")

        observable = _canon(observable_predicate_set)
        hidden = _canon(hidden_or_unrevealed_predicate_set)
        if set(observable).intersection(hidden):
            raise ValueError("a predicate cannot be both observable and hidden/unrevealed")
        classes = _canon_classes(information_equivalence_classes)
        deliveries = _canon(principal_delivery_frontier_refs)
        reveals = _canon(reveal_event_refs)
        models = _canon(observation_model_refs)
        abstractions = _canon(abstraction_certificate_refs)
        debts = _canon(debt_refs)
        body = {
            "logical_id": logical,
            "revision_id": revision,
            "mission_revision": int(mission_revision),
            "decision_epoch_ref": epoch,
            "principal_scope_ref": principal,
            "information_access_profile_revision": access,
            "principal_observation_history_digest": principal_history,
            "principal_delivery_frontier_refs": deliveries,
            "canonical_state_version": int(canonical_state_version),
            "observation_history_digest": observation_history,
            "observable_predicate_set": observable,
            "hidden_or_unrevealed_predicate_set": hidden,
            "information_equivalence_classes": classes,
            "reveal_event_refs": reveals,
            "observation_model_refs": models,
            "perfect_recall_basis_ref": recall,
            "abstraction_certificate_refs": abstractions,
            "debt_refs": debts,
            "validity_regime": regime,
        }
        return cls(**body, canonical_digest=digest(body))

    def histories_for_class(self, class_ref: str) -> tuple[str, ...]:
        target = str(class_ref)
        for key, histories in self.information_equivalence_classes:
            if key == target:
                return histories
        raise KeyError(target)


@dataclass(frozen=True, slots=True)
class DecisionEpoch:
    epoch_id: str
    plan_snapshot_version: int
    mission_revision: int
    decision_principal_ref: str
    strategic_location_revision: int
    information_partition_revision: str
    principal_information_access_profile_revision: str
    available_action_space_revision: str
    active_authority_profile: str
    active_obligation_basis: str
    risk_policy_revision: str
    observation_frontier_revision: str
    temporal_window: tuple[int | float, int | float]
    bound_principal_scope_ref: str
    canonical_digest: str

    @classmethod
    def create(
        cls,
        *,
        epoch_id: str,
        plan_snapshot_version: int,
        mission_revision: int,
        decision_principal_ref: str,
        strategic_location_revision: int,
        information_partition_revision: str,
        principal_information_access_profile_revision: str,
        available_action_space_revision: str,
        active_authority_profile: str,
        active_obligation_basis: str,
        risk_policy_revision: str,
        observation_frontier_revision: str,
        temporal_window: tuple[int | float, int | float],
        bound_principal_scope_ref: str | None = None,
    ) -> "DecisionEpoch":
        epoch = _nonempty("epoch_id", epoch_id)
        principal = _nonempty("decision_principal_ref", decision_principal_ref)
        bound_principal = principal if bound_principal_scope_ref is None else _nonempty(
            "bound_principal_scope_ref", bound_principal_scope_ref
        )
        if principal != bound_principal:
            raise ValueError("decision epoch principal and bound principal scope differ")
        if int(plan_snapshot_version) < 1 or int(mission_revision) < 1 or int(strategic_location_revision) < 1:
            raise ValueError("epoch version fields must be positive")
        if len(temporal_window) != 2:
            raise ValueError("temporal_window must contain (start, end)")
        start, end = temporal_window
        if start < 0 or end < start:
            raise ValueError("decision epoch temporal window is invalid")
        body = {
            "epoch_id": epoch,
            "plan_snapshot_version": int(plan_snapshot_version),
            "mission_revision": int(mission_revision),
            "decision_principal_ref": principal,
            "strategic_location_revision": int(strategic_location_revision),
            "information_partition_revision": _nonempty("information_partition_revision", information_partition_revision),
            "principal_information_access_profile_revision": _nonempty(
                "principal_information_access_profile_revision", principal_information_access_profile_revision
            ),
            "available_action_space_revision": _nonempty("available_action_space_revision", available_action_space_revision),
            "active_authority_profile": _nonempty("active_authority_profile", active_authority_profile),
            "active_obligation_basis": _nonempty("active_obligation_basis", active_obligation_basis),
            "risk_policy_revision": _nonempty("risk_policy_revision", risk_policy_revision),
            "observation_frontier_revision": _nonempty("observation_frontier_revision", observation_frontier_revision),
            "temporal_window": (start, end),
            "bound_principal_scope_ref": bound_principal,
        }
        return cls(**body, canonical_digest=digest(body))


@dataclass(frozen=True, slots=True)
class RevealEvent:
    reveal_event_id: str
    revision_id: str
    principal_scope_ref: str
    revealed_predicates: tuple[str, ...]
    observation_model_revision: str
    availability_time_or_condition: int | float | str
    false_positive_semantics: str
    false_negative_semantics: str
    observer_effects: tuple[str, ...]
    validity_regime: str
    refines_information_classes: tuple[str, ...]
    canonical_digest: str

    @classmethod
    def create(
        cls,
        *,
        reveal_event_id: str,
        revision_id: str,
        principal_scope_ref: str,
        revealed_predicates: Iterable[str],
        observation_model_revision: str,
        availability_time_or_condition: int | float | str,
        false_positive_semantics: str,
        false_negative_semantics: str,
        observer_effects: Iterable[str],
        validity_regime: str,
        refines_information_classes: Iterable[str],
    ) -> "RevealEvent":
        if isinstance(availability_time_or_condition, (int, float)) and availability_time_or_condition < 0:
            raise ValueError("reveal availability time cannot be negative")
        if isinstance(availability_time_or_condition, str) and not availability_time_or_condition.strip():
            raise ValueError("reveal availability condition must be non-empty")
        body = {
            "reveal_event_id": _nonempty("reveal_event_id", reveal_event_id),
            "revision_id": _nonempty("revision_id", revision_id),
            "principal_scope_ref": _nonempty("principal_scope_ref", principal_scope_ref),
            "revealed_predicates": _canon(revealed_predicates),
            "observation_model_revision": _nonempty("observation_model_revision", observation_model_revision),
            "availability_time_or_condition": availability_time_or_condition,
            "false_positive_semantics": _nonempty("false_positive_semantics", false_positive_semantics),
            "false_negative_semantics": _nonempty("false_negative_semantics", false_negative_semantics),
            "observer_effects": _canon(observer_effects),
            "validity_regime": _nonempty("validity_regime", validity_regime),
            "refines_information_classes": _canon(refines_information_classes),
        }
        if not body["revealed_predicates"]:
            raise ValueError("reveal event must reveal at least one predicate")
        if not body["refines_information_classes"]:
            raise ValueError("reveal event must refine at least one information class")
        return cls(**body, canonical_digest=digest(body))

    def available_by(self, decision_time: int | float) -> bool | None:
        value = self.availability_time_or_condition
        if isinstance(value, (int, float)):
            return value <= decision_time
        return None


@dataclass(frozen=True, slots=True)
class ObservationFrontierRevision:
    frontier_id: str
    revision_id: str
    principal_scope_ref: str
    information_access_profile_revision: str
    currently_available_observations: tuple[str, ...]
    pending_observations: tuple[str, ...]
    reveal_event_refs: tuple[str, ...]
    latest_safe_observation_times: tuple[tuple[str, int | float], ...]
    observation_costs: tuple[tuple[str, float], ...]
    observation_side_effects: tuple[str, ...]
    observation_dependencies: tuple[str, ...]
    unobservable_predicates: tuple[str, ...]
    conditionally_observable_predicates: tuple[str, ...]
    frontier_debt_refs: tuple[str, ...]
    validity_regime: str
    canonical_digest: str

    @classmethod
    def create(
        cls,
        *,
        frontier_id: str,
        revision_id: str,
        principal_scope_ref: str,
        information_access_profile_revision: str,
        currently_available_observations: Iterable[str],
        pending_observations: Iterable[str],
        reveal_event_refs: Iterable[str],
        latest_safe_observation_times: Mapping[str, int | float],
        observation_costs: Mapping[str, float],
        observation_side_effects: Iterable[str],
        observation_dependencies: Iterable[str],
        unobservable_predicates: Iterable[str],
        conditionally_observable_predicates: Iterable[str],
        frontier_debt_refs: Iterable[str],
        validity_regime: str,
    ) -> "ObservationFrontierRevision":
        latest: list[tuple[str, int | float]] = []
        for key, value in latest_safe_observation_times.items():
            name = _nonempty("latest-safe observation predicate", key)
            if value < 0:
                raise ValueError("latest safe observation time cannot be negative")
            latest.append((name, value))
        costs: list[tuple[str, float]] = []
        for key, value in observation_costs.items():
            name = _nonempty("observation cost predicate", key)
            cost = float(value)
            if cost < 0:
                raise ValueError("observation cost cannot be negative")
            costs.append((name, cost))
        current = _canon(currently_available_observations)
        pending = _canon(pending_observations)
        unobservable = _canon(unobservable_predicates)
        conditional = _canon(conditionally_observable_predicates)
        if set(current).intersection(unobservable):
            raise ValueError("currently available observation cannot be unobservable")
        body = {
            "frontier_id": _nonempty("frontier_id", frontier_id),
            "revision_id": _nonempty("revision_id", revision_id),
            "principal_scope_ref": _nonempty("principal_scope_ref", principal_scope_ref),
            "information_access_profile_revision": _nonempty(
                "information_access_profile_revision", information_access_profile_revision
            ),
            "currently_available_observations": current,
            "pending_observations": pending,
            "reveal_event_refs": _canon(reveal_event_refs),
            "latest_safe_observation_times": tuple(sorted(latest)),
            "observation_costs": tuple(sorted(costs)),
            "observation_side_effects": _canon(observation_side_effects),
            "observation_dependencies": _canon(observation_dependencies),
            "unobservable_predicates": unobservable,
            "conditionally_observable_predicates": conditional,
            "frontier_debt_refs": _canon(frontier_debt_refs),
            "validity_regime": _nonempty("validity_regime", validity_regime),
        }
        return cls(**body, canonical_digest=digest(body))


@dataclass(frozen=True, slots=True)
class NonAnticipativityViolation:
    code: str
    information_class_ref: str
    detail: str


@dataclass(frozen=True, slots=True)
class NonAnticipativityAssessment:
    valid: bool
    partition_revision: str
    epoch_id: str
    decision_principal_ref: str
    violations: tuple[NonAnticipativityViolation, ...]
    debt_refs: tuple[str, ...]
    assessment_digest: str


class NonAnticipativityValidator:
    @staticmethod
    def validate(
        partition: InformationPartitionRevision,
        epoch: DecisionEpoch,
        *,
        action_semantics_by_history: Mapping[str, str],
        reveal_events: Iterable[RevealEvent],
        decision_time: int | float,
    ) -> NonAnticipativityAssessment:
        violations: list[NonAnticipativityViolation] = []
        debts: set[str] = set()
        reveals = tuple(reveal_events)

        if partition.principal_scope_ref != epoch.decision_principal_ref:
            violations.append(
                NonAnticipativityViolation(
                    "PRINCIPAL_PARTITION_MISMATCH",
                    "*",
                    "decision epoch and information partition bind different principals",
                )
            )
        if partition.information_access_profile_revision != epoch.principal_information_access_profile_revision:
            violations.append(
                NonAnticipativityViolation(
                    "PRINCIPAL_ACCESS_MISMATCH",
                    "*",
                    "decision epoch and information partition bind different access revisions",
                )
            )

        for class_ref, histories in partition.information_equivalence_classes:
            action_semantics = {
                str(action_semantics_by_history[history])
                for history in histories
                if history in action_semantics_by_history
            }
            if len(action_semantics) <= 1:
                continue

            class_reveals = tuple(event for event in reveals if class_ref in event.refines_information_classes)
            principal_reveals = tuple(
                event for event in class_reveals if event.principal_scope_ref == partition.principal_scope_ref
            )
            if class_reveals and not principal_reveals:
                violations.append(
                    NonAnticipativityViolation(
                        "PRINCIPAL_REVEAL_UNAVAILABLE",
                        class_ref,
                        "a reveal exists but is not available to the bound decision principal",
                    )
                )

            current_reveal = False
            unresolved_condition = False
            late_reveal = False
            for event in principal_reveals:
                available = event.available_by(decision_time)
                if available is True:
                    current_reveal = True
                    break
                if available is None:
                    unresolved_condition = True
                else:
                    late_reveal = True

            if current_reveal:
                continue
            if unresolved_condition:
                debts.add("NONANTICIPATIVITY_DEBT:AMBIGUOUS_REVEAL")
            if late_reveal:
                debts.add("NONANTICIPATIVITY_DEBT:LATE_REVEAL")
            violations.append(
                NonAnticipativityViolation(
                    "NONANTICIPATIVITY_VIOLATION",
                    class_ref,
                    "information-equivalent histories choose different action semantics before a grounded reveal",
                )
            )

        body = {
            "partition_revision": partition.revision_id,
            "epoch_id": epoch.epoch_id,
            "decision_principal_ref": epoch.decision_principal_ref,
            "decision_time": decision_time,
            "violations": tuple((v.code, v.information_class_ref, v.detail) for v in violations),
            "debt_refs": tuple(sorted(debts)),
        }
        return NonAnticipativityAssessment(
            valid=not violations,
            partition_revision=partition.revision_id,
            epoch_id=epoch.epoch_id,
            decision_principal_ref=epoch.decision_principal_ref,
            violations=tuple(violations),
            debt_refs=tuple(sorted(debts)),
            assessment_digest=digest(body),
        )
