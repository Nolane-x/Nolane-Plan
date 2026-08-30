from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from itertools import combinations
from typing import Iterable, Mapping

from .control_plane import (
    ControlPlaneResourceKind,
    ControlPlaneResourceRevision,
    ReactionJobContract,
    ReactionResourceDemand,
)
from .hashing import digest


class ReactionSchedulabilityError(ValueError):
    pass


class ReactionSchedulabilityLevel(str, Enum):
    RS0_UNANALYZED = "RS0_UNANALYZED"
    RS1_EACH_JOB_INDIVIDUALLY_FEASIBLE = "RS1_EACH_JOB_INDIVIDUALLY_FEASIBLE"
    RS2_DECLARED_COHORT_FEASIBLE = "RS2_DECLARED_COHORT_FEASIBLE"
    RS3_ROBUST_COHORT_SCHEDULABLE = "RS3_ROBUST_COHORT_SCHEDULABLE"
    RS4_CLOSED_SUBDOMAIN_PROVEN = "RS4_CLOSED_SUBDOMAIN_PROVEN"


class SchedulabilityAnalysisMode(str, Enum):
    EXACT_BOUNDED = "EXACT_BOUNDED"
    CONSERVATIVE_OVERAPPROX = "CONSERVATIVE_OVERAPPROX"
    INTERVAL_ROBUST = "INTERVAL_ROBUST"
    SCENARIO_STRESS = "SCENARIO_STRESS"
    UNSUPPORTED = "UNSUPPORTED"

    @classmethod
    def parse(cls, value: str | "SchedulabilityAnalysisMode") -> "SchedulabilityAnalysisMode":
        if isinstance(value, cls):
            return value
        try:
            return cls(str(value).strip().upper())
        except ValueError as exc:
            raise ReactionSchedulabilityError(f"unsupported schedulability analysis mode: {value}") from exc


@dataclass(frozen=True, slots=True)
class OverloadWitness:
    resource_ref: str
    window_start: float
    window_end: float
    available_service: float
    required_service: float
    available_concurrency_units: int
    required_concurrency_units: int
    job_refs: tuple[str, ...]
    reason: str


@dataclass(frozen=True, slots=True)
class ReactionSchedulabilityCertificate:
    certificate_id: str
    revision_id: str
    policy_scope: str
    mission_revision: str
    information_partition_revision: str
    reaction_job_digests: tuple[tuple[str, str], ...]
    control_resource_digests: tuple[tuple[str, str], ...]
    coexistence_constraint_refs: tuple[str, ...]
    resource_reservation_refs: tuple[str, ...]
    scheduling_model_id: str
    scheduling_model_version: str
    analysis_mode: SchedulabilityAnalysisMode
    worst_case_or_interval_assumptions: tuple[str, ...]
    proof_or_solver_ref: str
    overload_witnesses: tuple[OverloadWitness, ...]
    assurance_profile: str
    model_adequacy_debt_refs: tuple[str, ...]
    validity_regime: str
    level: ReactionSchedulabilityLevel
    closed_subdomain_proof_ref: str | None
    canonical_digest: str

    @property
    def supports_strong_joint_guarantee(self) -> bool:
        return self.level in {
            ReactionSchedulabilityLevel.RS2_DECLARED_COHORT_FEASIBLE,
            ReactionSchedulabilityLevel.RS3_ROBUST_COHORT_SCHEDULABLE,
            ReactionSchedulabilityLevel.RS4_CLOSED_SUBDOMAIN_PROVEN,
        }

    def is_current(
        self,
        *,
        jobs: Iterable[ReactionJobContract],
        resources: Iterable[ControlPlaneResourceRevision],
    ) -> bool:
        job_rows = tuple(sorted((item.reaction_job_id, item.canonical_digest) for item in jobs))
        resource_rows = tuple(sorted((item.resource_id, item.canonical_digest) for item in resources))
        return job_rows == self.reaction_job_digests and resource_rows == self.control_resource_digests


class ReactionSchedulabilityEvaluator:
    """Bounded planning-level joint demand analysis.

    This intentionally is not a general real-time scheduler. It enumerates only
    finite co-reachable cohorts up to ``MAX_EXACT_JOBS`` and checks conservative
    service/concurrency demand over the job windows bound into the contracts.
    """

    MAX_EXACT_JOBS = 16

    @staticmethod
    def _required(name: str, value: object) -> str:
        text = str(value).strip()
        if not text:
            raise ReactionSchedulabilityError(f"{name} must be non-empty")
        return text

    @staticmethod
    def _canon(values: Iterable[str]) -> tuple[str, ...]:
        return tuple(sorted({str(value).strip() for value in values if str(value).strip()}))

    @staticmethod
    def _pair_key(left: str, right: str) -> tuple[str, str]:
        if left == right:
            raise ReactionSchedulabilityError("mutual exclusion pair requires distinct jobs")
        return tuple(sorted((str(left), str(right))))  # type: ignore[return-value]

    @classmethod
    def _job_demand_window(
        cls,
        job: ReactionJobContract,
        demand: ReactionResourceDemand,
    ) -> tuple[float, float]:
        start = job.release_window[0] + demand.release_offset_interval[0] + demand.demand_window[0]
        end = min(
            job.deadline,
            job.release_window[1] + demand.release_offset_interval[1] + demand.demand_window[1],
        )
        if end < start:
            return (start, start)
        return (start, end)

    @classmethod
    def _cohort_is_allowed(
        cls,
        cohort: tuple[ReactionJobContract, ...],
        exclusions: set[tuple[str, str]],
    ) -> bool:
        refs = tuple(item.reaction_job_id for item in cohort)
        return not any(cls._pair_key(left, right) in exclusions for left, right in combinations(refs, 2))

    @classmethod
    def _cohorts(
        cls,
        jobs: tuple[ReactionJobContract, ...],
        exclusions: set[tuple[str, str]],
    ) -> tuple[tuple[ReactionJobContract, ...], ...]:
        cohorts: list[tuple[ReactionJobContract, ...]] = []
        for size in range(1, len(jobs) + 1):
            for cohort in combinations(jobs, size):
                if cls._cohort_is_allowed(cohort, exclusions):
                    cohorts.append(tuple(cohort))
        return tuple(cohorts)

    @classmethod
    def _witnesses_for_cohort(
        cls,
        cohort: tuple[ReactionJobContract, ...],
        resources: Mapping[str, ControlPlaneResourceRevision],
    ) -> tuple[OverloadWitness, ...]:
        witnesses: list[OverloadWitness] = []
        demands_by_resource: dict[str, list[tuple[ReactionJobContract, ReactionResourceDemand]]] = {}
        for job in cohort:
            for demand in job.resource_demands:
                demands_by_resource.setdefault(demand.resource_ref, []).append((job, demand))

        for resource_ref, rows in sorted(demands_by_resource.items()):
            resource = resources.get(resource_ref)
            if resource is None:
                witnesses.append(
                    OverloadWitness(
                        resource_ref=resource_ref,
                        window_start=min(job.release_window[0] for job, _ in rows),
                        window_end=max(job.deadline for job, _ in rows),
                        available_service=0.0,
                        required_service=sum(d.required_service for _, d in rows),
                        available_concurrency_units=0,
                        required_concurrency_units=sum(d.required_concurrency_units for _, d in rows),
                        job_refs=tuple(sorted(job.reaction_job_id for job, _ in rows)),
                        reason="missing_resource_revision",
                    )
                )
                continue
            if not resource.supports_strong_bound:
                witnesses.append(
                    OverloadWitness(
                        resource_ref=resource_ref,
                        window_start=min(job.release_window[0] for job, _ in rows),
                        window_end=max(job.deadline for job, _ in rows),
                        available_service=0.0,
                        required_service=sum(d.required_service for _, d in rows),
                        available_concurrency_units=resource.concurrency_limit,
                        required_concurrency_units=sum(d.required_concurrency_units for _, d in rows),
                        job_refs=tuple(sorted(job.reaction_job_id for job, _ in rows)),
                        reason="opaque_resource_without_conservative_bound",
                    )
                )
                continue

            starts: list[float] = []
            ends: list[float] = []
            required_service = 0.0
            required_concurrency = 0
            job_refs: list[str] = []
            for job, demand in rows:
                start, end = cls._job_demand_window(job, demand)
                starts.append(start)
                ends.append(end)
                required_service += demand.required_service
                required_concurrency += demand.required_concurrency_units
                job_refs.append(job.reaction_job_id)
            window_start = min(starts)
            window_end = max(ends)
            available_service = resource.available_service(window_start, window_end)

            concurrency_cap = resource.concurrency_limit
            if resource.resource_kind in {
                ControlPlaneResourceKind.SERIAL,
                ControlPlaneResourceKind.KERNEL_WRITER,
            }:
                concurrency_cap = min(concurrency_cap, 1)

            reasons: list[str] = []
            if required_service > available_service + 1e-12:
                reasons.append("service_demand_exceeds_bound")
            if required_concurrency > concurrency_cap:
                reasons.append("concurrency_demand_exceeds_bound")
            if reasons:
                witnesses.append(
                    OverloadWitness(
                        resource_ref=resource_ref,
                        window_start=window_start,
                        window_end=window_end,
                        available_service=available_service,
                        required_service=required_service,
                        available_concurrency_units=concurrency_cap,
                        required_concurrency_units=required_concurrency,
                        job_refs=tuple(sorted(job_refs)),
                        reason="+".join(reasons),
                    )
                )
        return tuple(witnesses)

    @classmethod
    def evaluate(
        cls,
        *,
        certificate_id: str,
        revision_id: str,
        policy_scope: str,
        mission_revision: str,
        information_partition_revision: str,
        jobs: Iterable[ReactionJobContract],
        resources: Iterable[ControlPlaneResourceRevision],
        mutually_exclusive_pairs: Iterable[tuple[str, str]],
        coexistence_known: bool,
        resource_reservation_refs: Iterable[str],
        scheduling_model_id: str,
        scheduling_model_version: str,
        analysis_mode: str | SchedulabilityAnalysisMode,
        worst_case_or_interval_assumptions: Iterable[str],
        proof_or_solver_ref: str,
        assurance_profile: str,
        model_adequacy_debt_refs: Iterable[str],
        validity_regime: str,
        closed_subdomain_proof_ref: str | None = None,
    ) -> ReactionSchedulabilityCertificate:
        mode = SchedulabilityAnalysisMode.parse(analysis_mode)
        job_rows = tuple(sorted(tuple(jobs), key=lambda item: item.reaction_job_id))
        resource_rows = tuple(sorted(tuple(resources), key=lambda item: item.resource_id))
        if not job_rows:
            raise ReactionSchedulabilityError("schedulability analysis requires at least one job")
        if len({item.reaction_job_id for item in job_rows}) != len(job_rows):
            raise ReactionSchedulabilityError("reaction job ids must be unique")
        if len({item.resource_id for item in resource_rows}) != len(resource_rows):
            raise ReactionSchedulabilityError("control resource ids must be unique")

        debts = set(cls._canon(model_adequacy_debt_refs))
        exclusions = {cls._pair_key(left, right) for left, right in mutually_exclusive_pairs}
        job_ids = {item.reaction_job_id for item in job_rows}
        if any(left not in job_ids or right not in job_ids for left, right in exclusions):
            raise ReactionSchedulabilityError("mutual exclusion references an unknown job")
        coexistence_refs = tuple(f"mutex:{left}:{right}" for left, right in sorted(exclusions))
        if not coexistence_known:
            exclusions = set()
            debts.add("coexistence-unknown")
        if len(job_rows) > cls.MAX_EXACT_JOBS:
            debts.add("cohort-enumeration-bound-exceeded")
        if mode == SchedulabilityAnalysisMode.UNSUPPORTED:
            debts.add("schedulability-analysis-unsupported")

        resource_map = {item.resource_id: item for item in resource_rows}
        individual_witnesses: list[OverloadWitness] = []
        for job in job_rows:
            individual_witnesses.extend(cls._witnesses_for_cohort((job,), resource_map))
        all_individually_feasible = not individual_witnesses

        joint_witnesses: tuple[OverloadWitness, ...] = ()
        exact_enumerable = len(job_rows) <= cls.MAX_EXACT_JOBS
        if mode != SchedulabilityAnalysisMode.UNSUPPORTED and exact_enumerable and all_individually_feasible:
            witnesses: list[OverloadWitness] = []
            for cohort in cls._cohorts(job_rows, exclusions):
                if len(cohort) <= 1:
                    continue
                witnesses.extend(cls._witnesses_for_cohort(cohort, resource_map))
            # Keep the most discriminating witness per resource/window/job set.
            unique: dict[tuple[object, ...], OverloadWitness] = {}
            for witness in witnesses:
                key = (witness.resource_ref, witness.window_start, witness.window_end, witness.job_refs, witness.reason)
                unique[key] = witness
            joint_witnesses = tuple(sorted(unique.values(), key=lambda w: (w.resource_ref, w.window_start, w.job_refs)))

        if mode == SchedulabilityAnalysisMode.UNSUPPORTED or not all_individually_feasible:
            level = ReactionSchedulabilityLevel.RS0_UNANALYZED
            overload_witnesses = tuple(individual_witnesses or joint_witnesses)
        elif not exact_enumerable:
            level = ReactionSchedulabilityLevel.RS1_EACH_JOB_INDIVIDUALLY_FEASIBLE
            overload_witnesses = ()
        elif joint_witnesses:
            level = ReactionSchedulabilityLevel.RS1_EACH_JOB_INDIVIDUALLY_FEASIBLE
            overload_witnesses = joint_witnesses
        elif not coexistence_known:
            # Conservatively treating all jobs as co-reachable can prove feasibility,
            # but unknown correlation still blocks a strong semantic claim.
            level = ReactionSchedulabilityLevel.RS1_EACH_JOB_INDIVIDUALLY_FEASIBLE
            overload_witnesses = ()
        elif mode == SchedulabilityAnalysisMode.SCENARIO_STRESS:
            level = ReactionSchedulabilityLevel.RS1_EACH_JOB_INDIVIDUALLY_FEASIBLE
            overload_witnesses = ()
        elif mode == SchedulabilityAnalysisMode.INTERVAL_ROBUST:
            level = (
                ReactionSchedulabilityLevel.RS4_CLOSED_SUBDOMAIN_PROVEN
                if closed_subdomain_proof_ref
                else ReactionSchedulabilityLevel.RS3_ROBUST_COHORT_SCHEDULABLE
            )
            overload_witnesses = ()
        else:
            level = ReactionSchedulabilityLevel.RS2_DECLARED_COHORT_FEASIBLE
            overload_witnesses = ()

        body = {
            "certificate_id": cls._required("certificate_id", certificate_id),
            "revision_id": cls._required("revision_id", revision_id),
            "policy_scope": cls._required("policy_scope", policy_scope),
            "mission_revision": cls._required("mission_revision", mission_revision),
            "information_partition_revision": cls._required(
                "information_partition_revision", information_partition_revision
            ),
            "reaction_job_digests": tuple((item.reaction_job_id, item.canonical_digest) for item in job_rows),
            "control_resource_digests": tuple((item.resource_id, item.canonical_digest) for item in resource_rows),
            "coexistence_constraint_refs": coexistence_refs,
            "resource_reservation_refs": cls._canon(resource_reservation_refs),
            "scheduling_model_id": cls._required("scheduling_model_id", scheduling_model_id),
            "scheduling_model_version": cls._required("scheduling_model_version", scheduling_model_version),
            "analysis_mode": mode.value,
            "worst_case_or_interval_assumptions": cls._canon(worst_case_or_interval_assumptions),
            "proof_or_solver_ref": cls._required("proof_or_solver_ref", proof_or_solver_ref),
            "overload_witnesses": tuple(
                (
                    w.resource_ref,
                    w.window_start,
                    w.window_end,
                    w.available_service,
                    w.required_service,
                    w.available_concurrency_units,
                    w.required_concurrency_units,
                    w.job_refs,
                    w.reason,
                )
                for w in overload_witnesses
            ),
            "assurance_profile": cls._required("assurance_profile", assurance_profile),
            "model_adequacy_debt_refs": tuple(sorted(debts)),
            "validity_regime": cls._required("validity_regime", validity_regime),
            "level": level.value,
            "closed_subdomain_proof_ref": (
                cls._required("closed_subdomain_proof_ref", closed_subdomain_proof_ref)
                if closed_subdomain_proof_ref
                else None
            ),
        }
        return ReactionSchedulabilityCertificate(
            certificate_id=body["certificate_id"],
            revision_id=body["revision_id"],
            policy_scope=body["policy_scope"],
            mission_revision=body["mission_revision"],
            information_partition_revision=body["information_partition_revision"],
            reaction_job_digests=body["reaction_job_digests"],
            control_resource_digests=body["control_resource_digests"],
            coexistence_constraint_refs=body["coexistence_constraint_refs"],
            resource_reservation_refs=body["resource_reservation_refs"],
            scheduling_model_id=body["scheduling_model_id"],
            scheduling_model_version=body["scheduling_model_version"],
            analysis_mode=mode,
            worst_case_or_interval_assumptions=body["worst_case_or_interval_assumptions"],
            proof_or_solver_ref=body["proof_or_solver_ref"],
            overload_witnesses=overload_witnesses,
            assurance_profile=body["assurance_profile"],
            model_adequacy_debt_refs=body["model_adequacy_debt_refs"],
            validity_regime=body["validity_regime"],
            level=level,
            closed_subdomain_proof_ref=body["closed_subdomain_proof_ref"],
            canonical_digest=digest(body),
        )
