from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable

from .hashing import digest


class GlobalExclusionStatus(str, Enum):
    EXCLUDED = "EXCLUDED"
    NOT_EXCLUDED = "NOT_EXCLUDED"
    UNKNOWN = "UNKNOWN"


class CompletenessAssurance(str, Enum):
    COMPLETE_BOUNDED = "COMPLETE_BOUNDED"
    INCOMPLETE = "INCOMPLETE"
    OPAQUE = "OPAQUE"
    ACTION_LOCAL_ONLY = "ACTION_LOCAL_ONLY"

    @classmethod
    def parse(cls, value: str | "CompletenessAssurance") -> "CompletenessAssurance":
        if isinstance(value, cls):
            return value
        try:
            return cls(str(value).strip().upper())
        except ValueError as exc:
            raise ValueError(f"unsupported candidate-universe completeness assurance: {value}") from exc


def _required(name: str, value: object) -> str:
    text = str(value).strip()
    if not text:
        raise ValueError(f"{name} must be non-empty")
    return text


def _canon(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(sorted({str(value).strip() for value in values if str(value).strip()}))


@dataclass(frozen=True, slots=True)
class GlobalExclusionAssessment:
    """Bounded exclusion result over an explicitly versioned candidate universe.

    Empty survivors prove exclusion only when the candidate universe is explicitly
    COMPLETE_BOUNDED.  Local, incomplete, or opaque enumeration remains UNKNOWN and
    can never be promoted into a global absence/exclusion claim.
    """

    candidate_universe_revision: str
    candidate_refs: tuple[str, ...]
    surviving_refs: tuple[str, ...]
    completeness_assurance: CompletenessAssurance
    status: GlobalExclusionStatus
    canonical_digest: str

    @classmethod
    def create(
        cls,
        *,
        candidate_universe_revision: str,
        candidate_refs: Iterable[str],
        surviving_refs: Iterable[str],
        completeness_assurance: str | CompletenessAssurance,
    ) -> "GlobalExclusionAssessment":
        universe = _required("candidate_universe_revision", candidate_universe_revision)
        candidates = _canon(candidate_refs)
        survivors = _canon(surviving_refs)
        assurance = CompletenessAssurance.parse(completeness_assurance)
        unknown_survivors = set(survivors).difference(candidates)
        if unknown_survivors:
            raise ValueError(
                f"surviving candidates are outside the declared candidate universe: {sorted(unknown_survivors)!r}"
            )

        if assurance is CompletenessAssurance.COMPLETE_BOUNDED:
            status = GlobalExclusionStatus.NOT_EXCLUDED if survivors else GlobalExclusionStatus.EXCLUDED
        else:
            status = GlobalExclusionStatus.UNKNOWN

        body = {
            "candidate_universe_revision": universe,
            "candidate_refs": candidates,
            "surviving_refs": survivors,
            "completeness_assurance": assurance.value,
            "status": status.value,
        }
        return cls(
            candidate_universe_revision=universe,
            candidate_refs=candidates,
            surviving_refs=survivors,
            completeness_assurance=assurance,
            status=status,
            canonical_digest=digest(body),
        )
