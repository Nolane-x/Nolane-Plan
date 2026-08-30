from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
from typing import Iterable, Mapping

from .hashing import digest


NOT_APPLICABLE = "NOT_APPLICABLE"


def _required(name: str, value: object) -> str:
    text = str(value).strip()
    if not text:
        raise ValueError(f"{name} must be non-empty")
    return text


def _canon(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(sorted({str(value).strip() for value in values if str(value).strip()}))


def _interval(name: str, value) -> tuple[float, float]:
    if value == NOT_APPLICABLE:
        return (0.0, 0.0)
    if value is None:
        raise ValueError(f"{name} must be an interval or explicit NOT_APPLICABLE")
    if not isinstance(value, (tuple, list)) or len(value) != 2:
        raise ValueError(f"{name} must be an interval or explicit NOT_APPLICABLE")
    low, high = float(value[0]), float(value[1])
    if low < 0 or high < low:
        raise ValueError(f"{name} is invalid")
    return (low, high)


class ReactionControllabilityClass(str, Enum):
    IA0_UNANALYZED = "IA0_UNANALYZED"
    IA1_POSSIBLE_TIMELY = "IA1_POSSIBLE_TIMELY"
    IA2_BOUNDED_GUARANTEED_TIMELY = "IA2_BOUNDED_GUARANTEED_TIMELY"
    IA3_DYNAMICALLY_REACTION_CONTROLLABLE = "IA3_DYNAMICALLY_REACTION_CONTROLLABLE"
    IA4_CLOSED_SUBDOMAIN_PROVEN = "IA4_CLOSED_SUBDOMAIN_PROVEN"


@dataclass(frozen=True, slots=True)
class DecisionReactionEnvelope:
    reaction_envelope_id: str
    revision_id: str
    policy_node_or_reveal_ref: str
    reveal_time_interval: tuple[float, float]
    ingestion_latency_interval: tuple[float, float]
    canonical_commit_latency_interval: tuple[float, float]
    relocation_latency_interval: tuple[float, float]
    capsule_compile_latency_interval: tuple[float, float]
    model_or_solver_latency_interval: tuple[float, float]
    verification_latency_interval: tuple[float, float]
    authorization_latency_interval: tuple[float, float]
    dispatch_latency_interval: tuple[float, float]
    external_effect_start_latency_interval: tuple[float, float]
    latest_safe_authorization_time: float
    latest_safe_dispatch_time: float
    latest_safe_effect_time: float
    cancellation_or_preemption_window: tuple[float, float]
    clock_regime_refs: tuple[str, ...]
    model_adequacy_debt_refs: tuple[str, ...]
    best_case_authorization_time: float
    worst_case_authorization_time: float
    best_case_dispatch_time: float
    worst_case_dispatch_time: float
    best_case_effect_time: float
    worst_case_effect_time: float
    best_case_slack: float
    worst_case_slack: float
    controllability_class: ReactionControllabilityClass
    canonical_digest: str

    @classmethod
    def create(
        cls,
        *,
        reaction_envelope_id: str,
        revision_id: str,
        policy_node_or_reveal_ref: str,
        reveal_time_interval,
        ingestion_latency_interval,
        canonical_commit_latency_interval,
        relocation_latency_interval,
        capsule_compile_latency_interval,
        model_or_solver_latency_interval,
        verification_latency_interval,
        authorization_latency_interval,
        dispatch_latency_interval,
        external_effect_start_latency_interval,
        latest_safe_authorization_time: int | float,
        latest_safe_dispatch_time: int | float,
        latest_safe_effect_time: int | float,
        cancellation_or_preemption_window,
        clock_regime_refs: Iterable[str],
        model_adequacy_debt_refs: Iterable[str],
        dynamic_reaction_proof_ref: str | None = None,
        closed_subdomain_proof_ref: str | None = None,
    ) -> "DecisionReactionEnvelope":
        reveal = _interval("reveal_time_interval", reveal_time_interval)
        stage_values = (
            ("ingestion_latency_interval", ingestion_latency_interval),
            ("canonical_commit_latency_interval", canonical_commit_latency_interval),
            ("relocation_latency_interval", relocation_latency_interval),
            ("capsule_compile_latency_interval", capsule_compile_latency_interval),
            ("model_or_solver_latency_interval", model_or_solver_latency_interval),
            ("verification_latency_interval", verification_latency_interval),
            ("authorization_latency_interval", authorization_latency_interval),
            ("dispatch_latency_interval", dispatch_latency_interval),
            ("external_effect_start_latency_interval", external_effect_start_latency_interval),
        )
        intervals = {name: _interval(name, value) for name, value in stage_values}
        cancellation = _interval("cancellation_or_preemption_window", cancellation_or_preemption_window)
        safe_auth = float(latest_safe_authorization_time)
        safe_dispatch = float(latest_safe_dispatch_time)
        safe_effect = float(latest_safe_effect_time)
        if min(safe_auth, safe_dispatch, safe_effect) < 0:
            raise ValueError("safe reaction times cannot be negative")
        if safe_auth > safe_dispatch or safe_dispatch > safe_effect:
            raise ValueError("safe authorization/dispatch/effect times must be monotonic")
        clocks = _canon(clock_regime_refs)
        if not clocks:
            raise ValueError("reaction envelope requires clock/latency regime refs")

        pre_auth_names = (
            "ingestion_latency_interval",
            "canonical_commit_latency_interval",
            "relocation_latency_interval",
            "capsule_compile_latency_interval",
            "model_or_solver_latency_interval",
            "verification_latency_interval",
            "authorization_latency_interval",
        )
        def total(which: int, names: tuple[str, ...]) -> float:
            return reveal[which] + sum(intervals[name][which] for name in names)

        best_auth = total(0, pre_auth_names)
        worst_auth = total(1, pre_auth_names)
        best_dispatch = best_auth + intervals["dispatch_latency_interval"][0]
        worst_dispatch = worst_auth + intervals["dispatch_latency_interval"][1]
        best_effect = best_dispatch + intervals["external_effect_start_latency_interval"][0]
        worst_effect = worst_dispatch + intervals["external_effect_start_latency_interval"][1]
        best_timely = best_auth <= safe_auth and best_dispatch <= safe_dispatch and best_effect <= safe_effect
        worst_timely = worst_auth <= safe_auth and worst_dispatch <= safe_dispatch and worst_effect <= safe_effect

        if closed_subdomain_proof_ref and worst_timely:
            controllability = ReactionControllabilityClass.IA4_CLOSED_SUBDOMAIN_PROVEN
        elif dynamic_reaction_proof_ref and best_timely:
            controllability = ReactionControllabilityClass.IA3_DYNAMICALLY_REACTION_CONTROLLABLE
        elif worst_timely:
            controllability = ReactionControllabilityClass.IA2_BOUNDED_GUARANTEED_TIMELY
        elif best_timely:
            controllability = ReactionControllabilityClass.IA1_POSSIBLE_TIMELY
        else:
            controllability = ReactionControllabilityClass.IA0_UNANALYZED

        debts = _canon(model_adequacy_debt_refs)
        body = {
            "reaction_envelope_id": _required("reaction_envelope_id", reaction_envelope_id),
            "revision_id": _required("revision_id", revision_id),
            "policy_node_or_reveal_ref": _required("policy_node_or_reveal_ref", policy_node_or_reveal_ref),
            "reveal_time_interval": reveal,
            **intervals,
            "latest_safe_authorization_time": safe_auth,
            "latest_safe_dispatch_time": safe_dispatch,
            "latest_safe_effect_time": safe_effect,
            "cancellation_or_preemption_window": cancellation,
            "clock_regime_refs": clocks,
            "model_adequacy_debt_refs": debts,
            "dynamic_reaction_proof_ref": dynamic_reaction_proof_ref,
            "closed_subdomain_proof_ref": closed_subdomain_proof_ref,
            "best_case_authorization_time": best_auth,
            "worst_case_authorization_time": worst_auth,
            "best_case_dispatch_time": best_dispatch,
            "worst_case_dispatch_time": worst_dispatch,
            "best_case_effect_time": best_effect,
            "worst_case_effect_time": worst_effect,
            "controllability_class": controllability.value,
        }
        return cls(
            reaction_envelope_id=body["reaction_envelope_id"],
            revision_id=body["revision_id"],
            policy_node_or_reveal_ref=body["policy_node_or_reveal_ref"],
            reveal_time_interval=reveal,
            ingestion_latency_interval=intervals["ingestion_latency_interval"],
            canonical_commit_latency_interval=intervals["canonical_commit_latency_interval"],
            relocation_latency_interval=intervals["relocation_latency_interval"],
            capsule_compile_latency_interval=intervals["capsule_compile_latency_interval"],
            model_or_solver_latency_interval=intervals["model_or_solver_latency_interval"],
            verification_latency_interval=intervals["verification_latency_interval"],
            authorization_latency_interval=intervals["authorization_latency_interval"],
            dispatch_latency_interval=intervals["dispatch_latency_interval"],
            external_effect_start_latency_interval=intervals["external_effect_start_latency_interval"],
            latest_safe_authorization_time=safe_auth,
            latest_safe_dispatch_time=safe_dispatch,
            latest_safe_effect_time=safe_effect,
            cancellation_or_preemption_window=cancellation,
            clock_regime_refs=clocks,
            model_adequacy_debt_refs=debts,
            best_case_authorization_time=best_auth,
            worst_case_authorization_time=worst_auth,
            best_case_dispatch_time=best_dispatch,
            worst_case_dispatch_time=worst_dispatch,
            best_case_effect_time=best_effect,
            worst_case_effect_time=worst_effect,
            best_case_slack=safe_effect - best_effect,
            worst_case_slack=safe_effect - worst_effect,
            controllability_class=controllability,
            canonical_digest=digest(body),
        )

    @property
    def supports_strong_route_guarantee(self) -> bool:
        return self.controllability_class in {
            ReactionControllabilityClass.IA2_BOUNDED_GUARANTEED_TIMELY,
            ReactionControllabilityClass.IA3_DYNAMICALLY_REACTION_CONTROLLABLE,
            ReactionControllabilityClass.IA4_CLOSED_SUBDOMAIN_PROVEN,
        }


class PreparednessStructure(str, Enum):
    SEQUENCE = "sequence"
    OR = "or"
    K_OF_N = "k_of_n"
    CONTINGENCY = "contingency"


_PREPAREDNESS_AXES = (
    "recognition",
    "trigger",
    "observation",
    "recall",
    "routing",
    "action_contract",
    "authority",
    "resource",
    "temporal_reaction",
    "recovery",
    "policy_coherence",
    "proof_context",
    "continuation",
)


@dataclass(frozen=True, slots=True)
class PreparednessProfile:
    preparedness_profile_id: str
    revision_id: str
    future_region_or_policy_scope: str
    axes: tuple[tuple[str, int], ...]
    model_adequacy_cap: int
    debt_refs: tuple[str, ...]
    validity_regime: str
    canonical_digest: str

    @classmethod
    def create(
        cls,
        *,
        preparedness_profile_id: str,
        revision_id: str,
        future_region_or_policy_scope: str,
        axes: Mapping[str, int],
        model_adequacy_cap: int,
        debt_refs: Iterable[str],
        validity_regime: str,
    ) -> "PreparednessProfile":
        if set(axes) != set(_PREPAREDNESS_AXES):
            missing = sorted(set(_PREPAREDNESS_AXES).difference(axes))
            extra = sorted(set(axes).difference(_PREPAREDNESS_AXES))
            raise ValueError(f"preparedness axes must be complete; missing={missing!r} extra={extra!r}")
        rows = tuple(sorted((str(name), int(value)) for name, value in axes.items()))
        if any(value < 0 or value > 5 for _, value in rows):
            raise ValueError("preparedness axis levels must be within P0..P5")
        cap = int(model_adequacy_cap)
        if cap < 0 or cap > 5:
            raise ValueError("model adequacy cap must be within P0..P5")
        body = {
            "preparedness_profile_id": _required("preparedness_profile_id", preparedness_profile_id),
            "revision_id": _required("revision_id", revision_id),
            "future_region_or_policy_scope": _required("future_region_or_policy_scope", future_region_or_policy_scope),
            "axes": rows,
            "model_adequacy_cap": cap,
            "debt_refs": _canon(debt_refs),
            "validity_regime": _required("validity_regime", validity_regime),
        }
        return cls(**body, canonical_digest=digest(body))

    @property
    def derived_p_level(self) -> int:
        return min([value for _, value in self.axes] + [self.model_adequacy_cap])

    @property
    def bottleneck_axes(self) -> tuple[str, ...]:
        floor = self.derived_p_level
        axes = tuple(name for name, value in self.axes if value == floor)
        if axes:
            return axes
        return ("model_adequacy_cap",)

    def revise_axis(self, axis: str, level: int, *, revision_id: str, debt_ref: str | None = None) -> "PreparednessProfile":
        if axis not in _PREPAREDNESS_AXES:
            raise ValueError(f"unknown preparedness axis: {axis}")
        new_axes = dict(self.axes)
        new_axes[axis] = int(level)
        debts = set(self.debt_refs)
        if debt_ref:
            debts.add(_required("debt_ref", debt_ref))
        return PreparednessProfile.create(
            preparedness_profile_id=self.preparedness_profile_id,
            revision_id=revision_id,
            future_region_or_policy_scope=self.future_region_or_policy_scope,
            axes=new_axes,
            model_adequacy_cap=self.model_adequacy_cap,
            debt_refs=debts,
            validity_regime=self.validity_regime,
        )

    @staticmethod
    def aggregate(
        structure: PreparednessStructure,
        profiles: Iterable["PreparednessProfile"],
        *,
        independence_verified: bool,
        coexistence_verified: bool,
        required_count: int,
    ) -> int:
        rows = tuple(profiles)
        if not rows:
            raise ValueError("preparedness aggregation requires at least one profile")
        levels = sorted((profile.derived_p_level for profile in rows), reverse=True)
        if structure in {PreparednessStructure.SEQUENCE, PreparednessStructure.CONTINGENCY}:
            return min(levels)
        if structure == PreparednessStructure.OR:
            if required_count != 1:
                raise ValueError("OR aggregation requires exactly one sufficient route")
            if independence_verified and coexistence_verified:
                return max(levels)
            return min(levels)
        if structure == PreparednessStructure.K_OF_N:
            if required_count < 1 or required_count > len(rows):
                raise ValueError("K-of-N required_count is invalid")
            if independence_verified and coexistence_verified:
                return levels[required_count - 1]
            return min(levels)
        raise ValueError(f"unsupported preparedness structure: {structure}")


@dataclass(frozen=True, slots=True)
class InformationCapabilityRevision:
    information_capability_id: str
    revision_id: str
    principal_scope_ref: str | None
    information_access_profile_revision: str | None
    channel_or_probe_refs: tuple[str, ...]
    distinguishable_predicate_classes: tuple[str, ...]
    availability_guard: str
    validity_regime: str
    latency_reaction_envelope_refs: tuple[str, ...]
    resource_cost: float
    permission_authority_requirements: tuple[str, ...]
    observer_effects: tuple[str, ...]
    capacity_rate_limits: tuple[str, ...]
    durability: str
    failure_common_mode_dependencies: tuple[str, ...]
    transition_effect_dependencies: tuple[str, ...]
    debt_refs: tuple[str, ...]
    canonical_digest: str

    @classmethod
    def create(
        cls,
        *,
        information_capability_id: str,
        revision_id: str,
        principal_scope_ref: str | None,
        information_access_profile_revision: str | None,
        channel_or_probe_refs: Iterable[str],
        distinguishable_predicate_classes: Iterable[str],
        availability_guard: str,
        validity_regime: str,
        latency_reaction_envelope_refs: Iterable[str],
        resource_cost: float,
        permission_authority_requirements: Iterable[str],
        observer_effects: Iterable[str],
        capacity_rate_limits: Iterable[str],
        durability: str,
        failure_common_mode_dependencies: Iterable[str],
        transition_effect_dependencies: Iterable[str],
        debt_refs: Iterable[str],
    ) -> "InformationCapabilityRevision":
        principal = str(principal_scope_ref).strip() if principal_scope_ref else None
        access = str(information_access_profile_revision).strip() if information_access_profile_revision else None
        if bool(principal) != bool(access):
            raise ValueError("principal-scoped information capability requires both principal and access profile")
        channels = _canon(channel_or_probe_refs)
        predicates = _canon(distinguishable_predicate_classes)
        if not channels or not predicates:
            raise ValueError("information capability requires a channel/probe and distinguishable predicate class")
        cost = float(resource_cost)
        if cost < 0:
            raise ValueError("information capability resource cost cannot be negative")
        body = {
            "information_capability_id": _required("information_capability_id", information_capability_id),
            "revision_id": _required("revision_id", revision_id),
            "principal_scope_ref": principal,
            "information_access_profile_revision": access,
            "channel_or_probe_refs": channels,
            "distinguishable_predicate_classes": predicates,
            "availability_guard": _required("availability_guard", availability_guard),
            "validity_regime": _required("validity_regime", validity_regime),
            "latency_reaction_envelope_refs": _canon(latency_reaction_envelope_refs),
            "resource_cost": cost,
            "permission_authority_requirements": _canon(permission_authority_requirements),
            "observer_effects": _canon(observer_effects),
            "capacity_rate_limits": _canon(capacity_rate_limits),
            "durability": _required("durability", durability),
            "failure_common_mode_dependencies": _canon(failure_common_mode_dependencies),
            "transition_effect_dependencies": _canon(transition_effect_dependencies),
            "debt_refs": _canon(debt_refs),
        }
        return cls(**body, canonical_digest=digest(body))

    def action_preserves_required_information(
        self,
        action_ref: str,
        *,
        robust_information_independent_continuation: bool,
    ) -> bool:
        destructive = str(action_ref) in self.transition_effect_dependencies
        return not destructive or bool(robust_information_independent_continuation)


class TerminalSemantics(str, Enum):
    MISSION_COMPLETE = "MISSION_COMPLETE"
    SAFE_HANDOFF = "SAFE_HANDOFF"
    DEFERRED_CONTINUATION = "DEFERRED_CONTINUATION"
    RECOVERY_BOUNDARY = "RECOVERY_BOUNDARY"
    UNKNOWN_TERMINAL = "UNKNOWN_TERMINAL"


@dataclass(frozen=True, slots=True)
class ContinuationContract:
    continuation_contract_id: str
    revision_id: str
    boundary_region_ref: str
    mission_revision: int
    certified_prefix_horizon: int | float
    terminal_semantics: TerminalSemantics
    required_next_preparedness_profile: str
    remaining_subgoal_obligation_refs: tuple[str, ...]
    refinement_dependencies: tuple[str, ...]
    required_action_space_capability_discovery: tuple[str, ...]
    estimated_refinement_latency: float
    latest_safe_refinement_time: float
    fallback_if_refinement_misses_boundary: str
    continuation_debt_refs: tuple[str, ...]
    assurance_profile: str
    canonical_digest: str

    @classmethod
    def create(
        cls,
        *,
        continuation_contract_id: str,
        revision_id: str,
        boundary_region_ref: str,
        mission_revision: int,
        certified_prefix_horizon: int | float,
        terminal_semantics: TerminalSemantics,
        required_next_preparedness_profile: str,
        remaining_subgoal_obligation_refs: Iterable[str],
        refinement_dependencies: Iterable[str],
        required_action_space_capability_discovery: Iterable[str],
        estimated_refinement_latency: int | float,
        latest_safe_refinement_time: int | float,
        fallback_if_refinement_misses_boundary: str,
        continuation_debt_refs: Iterable[str],
        assurance_profile: str,
    ) -> "ContinuationContract":
        if int(mission_revision) < 1:
            raise ValueError("mission_revision must be positive")
        horizon = float(certified_prefix_horizon)
        latency = float(estimated_refinement_latency)
        safe_time = float(latest_safe_refinement_time)
        if horizon < 0 or latency < 0 or safe_time < 0:
            raise ValueError("continuation horizon/timing values cannot be negative")
        next_profile = _required("required_next_preparedness_profile", required_next_preparedness_profile)
        discovery = _canon(required_action_space_capability_discovery)
        fallback = str(fallback_if_refinement_misses_boundary).strip()
        debts = _canon(continuation_debt_refs)
        if terminal_semantics == TerminalSemantics.SAFE_HANDOFF:
            if not discovery:
                raise ValueError("SAFE_HANDOFF requires action-space/capability discovery requirements")
            if not fallback:
                raise ValueError("SAFE_HANDOFF requires a fallback when refinement misses the boundary")
        if terminal_semantics == TerminalSemantics.DEFERRED_CONTINUATION and not debts:
            raise ValueError("DEFERRED_CONTINUATION must carry explicit continuation debt")
        body = {
            "continuation_contract_id": _required("continuation_contract_id", continuation_contract_id),
            "revision_id": _required("revision_id", revision_id),
            "boundary_region_ref": _required("boundary_region_ref", boundary_region_ref),
            "mission_revision": int(mission_revision),
            "certified_prefix_horizon": horizon,
            "terminal_semantics": terminal_semantics.value,
            "required_next_preparedness_profile": next_profile,
            "remaining_subgoal_obligation_refs": _canon(remaining_subgoal_obligation_refs),
            "refinement_dependencies": _canon(refinement_dependencies),
            "required_action_space_capability_discovery": discovery,
            "estimated_refinement_latency": latency,
            "latest_safe_refinement_time": safe_time,
            "fallback_if_refinement_misses_boundary": fallback,
            "continuation_debt_refs": debts,
            "assurance_profile": _required("assurance_profile", assurance_profile),
        }
        return cls(
            continuation_contract_id=body["continuation_contract_id"],
            revision_id=body["revision_id"],
            boundary_region_ref=body["boundary_region_ref"],
            mission_revision=body["mission_revision"],
            certified_prefix_horizon=horizon,
            terminal_semantics=terminal_semantics,
            required_next_preparedness_profile=next_profile,
            remaining_subgoal_obligation_refs=body["remaining_subgoal_obligation_refs"],
            refinement_dependencies=body["refinement_dependencies"],
            required_action_space_capability_discovery=discovery,
            estimated_refinement_latency=latency,
            latest_safe_refinement_time=safe_time,
            fallback_if_refinement_misses_boundary=fallback,
            continuation_debt_refs=debts,
            assurance_profile=body["assurance_profile"],
            canonical_digest=digest(body),
        )

    def supports_executable_horizon(self, requested_horizon: int | float) -> bool:
        requested = float(requested_horizon)
        if requested <= self.certified_prefix_horizon:
            return True
        return self.terminal_semantics == TerminalSemantics.MISSION_COMPLETE

    def safe_handoff_ready(self, *, now: int | float, capability_available: bool) -> bool:
        if self.terminal_semantics != TerminalSemantics.SAFE_HANDOFF:
            return False
        if not capability_available:
            return False
        if not self.required_action_space_capability_discovery or not self.fallback_if_refinement_misses_boundary:
            return False
        return self.latest_safe_refinement_time - float(now) >= self.estimated_refinement_latency
