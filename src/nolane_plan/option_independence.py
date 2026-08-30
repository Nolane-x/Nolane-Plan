from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Mapping

from .hashing import digest
from .policy_readiness import PreparednessProfile, PreparednessStructure


class OptionIndependenceError(ValueError):
    pass


def _required(name: str, value: object) -> str:
    text = str(value).strip()
    if not text:
        raise OptionIndependenceError(f"{name} must be non-empty")
    return text


def _canon(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(sorted({str(value).strip() for value in values if str(value).strip()}))


class OptionIndependenceStatus(str, Enum):
    ROBUST_INDEPENDENT = "ROBUST_INDEPENDENT"
    NOMINAL_ONLY = "NOMINAL_ONLY"
    UNKNOWN = "UNKNOWN"
    UNSUPPORTED = "UNSUPPORTED"


@dataclass(frozen=True, slots=True)
class OptionIndependenceCertificate:
    certificate_id: str
    revision_id: str
    route_refs: tuple[str, ...]
    failure_uncertainty_set_ref: str
    shared_dependency_graph_ref: str
    route_dependency_refs: tuple[tuple[str, tuple[str, ...]], ...]
    resource_overlap_refs: tuple[str, ...]
    observation_lineage_overlap_refs: tuple[str, ...]
    control_plane_overlap_refs: tuple[str, ...]
    common_mode_failure_refs: tuple[str, ...]
    shared_dependency_refs: tuple[str, ...]
    coactivation_feasible: bool | None
    assurance_profile: str
    analysis_supported: bool
    status: OptionIndependenceStatus
    blocker_refs: tuple[str, ...]
    canonical_digest: str

    @classmethod
    def evaluate(
        cls,
        *,
        certificate_id: str,
        revision_id: str,
        route_refs: Iterable[str],
        failure_uncertainty_set_ref: str,
        shared_dependency_graph_ref: str,
        route_dependency_refs: Mapping[str, Iterable[str]],
        resource_overlap_refs: Iterable[str],
        observation_lineage_overlap_refs: Iterable[str],
        control_plane_overlap_refs: Iterable[str],
        common_mode_failure_refs: Iterable[str],
        coactivation_feasible: bool | None,
        assurance_profile: str,
        analysis_supported: bool,
    ) -> "OptionIndependenceCertificate":
        routes = _canon(route_refs)
        if len(routes) < 2:
            raise OptionIndependenceError("option independence requires at least two distinct routes")
        if set(route_dependency_refs) != set(routes):
            raise OptionIndependenceError("route dependency map must exactly cover route_refs")

        dependency_rows: list[tuple[str, tuple[str, ...]]] = []
        for route in routes:
            refs = _canon(route_dependency_refs[route])
            if not refs:
                raise OptionIndependenceError(f"route {route} requires explicit dependency refs")
            dependency_rows.append((route, refs))

        dependency_counts: dict[str, int] = {}
        for _, refs in dependency_rows:
            for ref in refs:
                dependency_counts[ref] = dependency_counts.get(ref, 0) + 1
        shared_dependencies = tuple(sorted(ref for ref, count in dependency_counts.items() if count > 1))

        resource_overlap = _canon(resource_overlap_refs)
        observation_overlap = _canon(observation_lineage_overlap_refs)
        control_overlap = _canon(control_plane_overlap_refs)
        common_modes = _canon(common_mode_failure_refs)
        assurance = _required("assurance_profile", assurance_profile)

        blockers: list[str] = []
        blockers.extend(f"shared-dependency:{ref}" for ref in shared_dependencies)
        blockers.extend(f"resource-overlap:{ref}" for ref in resource_overlap)
        blockers.extend(f"observation-lineage-overlap:{ref}" for ref in observation_overlap)
        blockers.extend(f"control-plane-overlap:{ref}" for ref in control_overlap)
        blockers.extend(f"common-mode:{ref}" for ref in common_modes)

        if not analysis_supported:
            status = OptionIndependenceStatus.UNSUPPORTED
            blockers.append("independence-analysis-unsupported")
        elif coactivation_feasible is None:
            status = OptionIndependenceStatus.UNKNOWN
            blockers.append("coactivation-feasibility-unknown")
        elif coactivation_feasible is False:
            status = OptionIndependenceStatus.NOMINAL_ONLY
            blockers.append("coactivation-infeasible")
        elif assurance.lower() not in {"strong", "bounded-worst-case", "closed-subdomain"}:
            status = OptionIndependenceStatus.NOMINAL_ONLY
            blockers.append("independence-assurance-below-strong-floor")
        elif blockers:
            status = OptionIndependenceStatus.NOMINAL_ONLY
        else:
            status = OptionIndependenceStatus.ROBUST_INDEPENDENT

        body = {
            "certificate_id": _required("certificate_id", certificate_id),
            "revision_id": _required("revision_id", revision_id),
            "route_refs": routes,
            "failure_uncertainty_set_ref": _required("failure_uncertainty_set_ref", failure_uncertainty_set_ref),
            "shared_dependency_graph_ref": _required("shared_dependency_graph_ref", shared_dependency_graph_ref),
            "route_dependency_refs": tuple(dependency_rows),
            "resource_overlap_refs": resource_overlap,
            "observation_lineage_overlap_refs": observation_overlap,
            "control_plane_overlap_refs": control_overlap,
            "common_mode_failure_refs": common_modes,
            "shared_dependency_refs": shared_dependencies,
            "coactivation_feasible": coactivation_feasible,
            "assurance_profile": assurance,
            "analysis_supported": bool(analysis_supported),
            "status": status.value,
            "blocker_refs": tuple(sorted(blockers)),
        }
        return cls(
            certificate_id=body["certificate_id"],
            revision_id=body["revision_id"],
            route_refs=routes,
            failure_uncertainty_set_ref=body["failure_uncertainty_set_ref"],
            shared_dependency_graph_ref=body["shared_dependency_graph_ref"],
            route_dependency_refs=body["route_dependency_refs"],
            resource_overlap_refs=resource_overlap,
            observation_lineage_overlap_refs=observation_overlap,
            control_plane_overlap_refs=control_overlap,
            common_mode_failure_refs=common_modes,
            shared_dependency_refs=shared_dependencies,
            coactivation_feasible=coactivation_feasible,
            assurance_profile=assurance,
            analysis_supported=bool(analysis_supported),
            status=status,
            blocker_refs=body["blocker_refs"],
            canonical_digest=digest(body),
        )

    @property
    def supports_robust_uplift(self) -> bool:
        return self.status is OptionIndependenceStatus.ROBUST_INDEPENDENT


@dataclass(frozen=True, slots=True)
class RobustPreparednessAssessment:
    structure: PreparednessStructure
    required_count: int
    profile_digests: tuple[str, ...]
    independence_certificate_digest: str
    nominal_alternative_preparedness: int
    robust_independent_preparedness: int
    robust_uplift_applied: bool
    blocker_refs: tuple[str, ...]
    canonical_digest: str

    @classmethod
    def evaluate(
        cls,
        *,
        profiles: Iterable[PreparednessProfile],
        structure: PreparednessStructure,
        required_count: int,
        independence_certificate: OptionIndependenceCertificate,
    ) -> "RobustPreparednessAssessment":
        rows = tuple(profiles)
        if not rows:
            raise OptionIndependenceError("robust preparedness requires profiles")
        if len(rows) != len(independence_certificate.route_refs):
            raise OptionIndependenceError("profile count must match independence-certificate route count")

        structure_value = structure if isinstance(structure, PreparednessStructure) else PreparednessStructure(structure)
        nominal = PreparednessProfile.aggregate(
            structure_value,
            rows,
            independence_verified=True,
            coexistence_verified=True,
            required_count=required_count,
        )
        robust = PreparednessProfile.aggregate(
            structure_value,
            rows,
            independence_verified=independence_certificate.supports_robust_uplift,
            coexistence_verified=independence_certificate.supports_robust_uplift,
            required_count=required_count,
        )
        applied = independence_certificate.supports_robust_uplift and robust == nominal
        body = {
            "structure": structure_value.value,
            "required_count": int(required_count),
            "profile_digests": tuple(profile.canonical_digest for profile in rows),
            "independence_certificate_digest": independence_certificate.canonical_digest,
            "nominal_alternative_preparedness": nominal,
            "robust_independent_preparedness": robust,
            "robust_uplift_applied": applied,
            "blocker_refs": independence_certificate.blocker_refs,
        }
        return cls(
            structure=structure_value,
            required_count=int(required_count),
            profile_digests=body["profile_digests"],
            independence_certificate_digest=body["independence_certificate_digest"],
            nominal_alternative_preparedness=nominal,
            robust_independent_preparedness=robust,
            robust_uplift_applied=applied,
            blocker_refs=body["blocker_refs"],
            canonical_digest=digest(body),
        )


def _aggregate_with_independence(
    structure: PreparednessStructure,
    profiles: Iterable[PreparednessProfile],
    *,
    required_count: int,
    independence_certificate: OptionIndependenceCertificate,
) -> RobustPreparednessAssessment:
    return RobustPreparednessAssessment.evaluate(
        profiles=profiles,
        structure=structure,
        required_count=required_count,
        independence_certificate=independence_certificate,
    )


# Backward-compatible extension point: legacy aggregate semantics remain unchanged.
# The installation is local to this module to avoid a policy_readiness -> option_independence
# import cycle; importing this strong certificate module exposes the explicit strong API.
if not hasattr(PreparednessProfile, "aggregate_with_independence"):
    setattr(PreparednessProfile, "aggregate_with_independence", staticmethod(_aggregate_with_independence))
