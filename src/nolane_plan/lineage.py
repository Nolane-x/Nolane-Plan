from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable

from .hashing import digest


class LineageError(ValueError):
    """Raised when canonical lineage would become ambiguous or mutable."""


def _required(name: str, value: object) -> str:
    text = str(value).strip()
    if not text:
        raise LineageError(f"{name} must be non-empty")
    return text


def _canon(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(sorted({str(value).strip() for value in values if str(value).strip()}))


class SemanticRegimeKind(str, Enum):
    SCHEMA = "SCHEMA"
    WORLD_MODEL = "WORLD_MODEL"
    ENVIRONMENT = "ENVIRONMENT"
    CANONICALIZATION = "CANONICALIZATION"
    SEMANTIC_PROFILE = "SEMANTIC_PROFILE"

    @classmethod
    def parse(cls, value: str | "SemanticRegimeKind") -> "SemanticRegimeKind":
        if isinstance(value, cls):
            return value
        try:
            return cls(str(value).strip().upper())
        except ValueError as exc:
            raise LineageError(f"unsupported semantic regime kind: {value}") from exc


@dataclass(frozen=True, slots=True)
class CanonicalLineageRevision:
    object_family: str
    logical_id: str
    revision_id: str
    schema_version: str
    created_sequence: int
    created_at_wall_time: float | None
    mission_revision_dependency: str | None
    plan_revision: int
    world_model_revision: str
    environment_regime_revision: str
    validity_regime: str
    parent_revision_ids: tuple[str, ...]
    provenance_refs: tuple[str, ...]
    assurance_profile: str
    debt_refs: tuple[str, ...]
    supersedes_revision_id: str | None
    semantic_digest: str
    lineage_digest: str

    @classmethod
    def create(
        cls,
        *,
        object_family: str,
        logical_id: str,
        revision_id: str,
        schema_version: str,
        created_sequence: int,
        created_at_wall_time: float | None,
        mission_revision_dependency: str | None,
        plan_revision: int,
        world_model_revision: str,
        environment_regime_revision: str,
        validity_regime: str,
        parent_revision_ids: Iterable[str],
        provenance_refs: Iterable[str],
        assurance_profile: str,
        debt_refs: Iterable[str],
        supersedes_revision_id: str | None,
        semantic_digest: str,
    ) -> "CanonicalLineageRevision":
        sequence = int(created_sequence)
        plan = int(plan_revision)
        if sequence < 0:
            raise LineageError("created_sequence must be non-negative")
        if plan < 1:
            raise LineageError("plan_revision must be positive")
        parents = _canon(parent_revision_ids)
        revision = _required("revision_id", revision_id)
        if revision in parents:
            raise LineageError("revision cannot be its own parent")
        supersedes = None if supersedes_revision_id is None else _required(
            "supersedes_revision_id", supersedes_revision_id
        )
        mission_dependency = (
            None
            if mission_revision_dependency is None
            else _required("mission_revision_dependency", mission_revision_dependency)
        )
        body = {
            "object_family": _required("object_family", object_family),
            "logical_id": _required("logical_id", logical_id),
            "revision_id": revision,
            "schema_version": _required("schema_version", schema_version),
            "created_sequence": sequence,
            # Wall time is informational by contract and therefore is not part of
            # the canonical lineage identity or causal ordering digest.
            "mission_revision_dependency": mission_dependency,
            "plan_revision": plan,
            "world_model_revision": _required("world_model_revision", world_model_revision),
            "environment_regime_revision": _required(
                "environment_regime_revision", environment_regime_revision
            ),
            "validity_regime": _required("validity_regime", validity_regime),
            "parent_revision_ids": parents,
            "provenance_refs": _canon(provenance_refs),
            "assurance_profile": _required("assurance_profile", assurance_profile),
            "debt_refs": _canon(debt_refs),
            "supersedes_revision_id": supersedes,
            "semantic_digest": _required("semantic_digest", semantic_digest),
        }
        return cls(
            object_family=body["object_family"],
            logical_id=body["logical_id"],
            revision_id=body["revision_id"],
            schema_version=body["schema_version"],
            created_sequence=sequence,
            created_at_wall_time=None if created_at_wall_time is None else float(created_at_wall_time),
            mission_revision_dependency=mission_dependency,
            plan_revision=plan,
            world_model_revision=body["world_model_revision"],
            environment_regime_revision=body["environment_regime_revision"],
            validity_regime=body["validity_regime"],
            parent_revision_ids=parents,
            provenance_refs=body["provenance_refs"],
            assurance_profile=body["assurance_profile"],
            debt_refs=body["debt_refs"],
            supersedes_revision_id=supersedes,
            semantic_digest=body["semantic_digest"],
            lineage_digest=digest(body),
        )


@dataclass(frozen=True, slots=True)
class SemanticRegimeRevision:
    regime_kind: SemanticRegimeKind
    logical_id: str
    revision_id: str
    created_sequence: int
    parent_revision_id: str | None
    semantic_digest: str
    provenance_refs: tuple[str, ...]
    canonical_digest: str

    @classmethod
    def create(
        cls,
        *,
        regime_kind: str | SemanticRegimeKind,
        logical_id: str,
        revision_id: str,
        created_sequence: int,
        parent_revision_id: str | None,
        semantic_digest: str,
        provenance_refs: Iterable[str],
    ) -> "SemanticRegimeRevision":
        kind = SemanticRegimeKind.parse(regime_kind)
        sequence = int(created_sequence)
        if sequence < 0:
            raise LineageError("created_sequence must be non-negative")
        revision = _required("revision_id", revision_id)
        parent = None if parent_revision_id is None else _required("parent_revision_id", parent_revision_id)
        if parent == revision:
            raise LineageError("regime revision cannot be its own parent")
        body = {
            "regime_kind": kind.value,
            "logical_id": _required("logical_id", logical_id),
            "revision_id": revision,
            "created_sequence": sequence,
            "parent_revision_id": parent,
            "semantic_digest": _required("semantic_digest", semantic_digest),
            "provenance_refs": _canon(provenance_refs),
        }
        return cls(
            regime_kind=kind,
            logical_id=body["logical_id"],
            revision_id=revision,
            created_sequence=sequence,
            parent_revision_id=parent,
            semantic_digest=body["semantic_digest"],
            provenance_refs=body["provenance_refs"],
            canonical_digest=digest(body),
        )


class LineageRegistry:
    """Immutable lineage history plus explicit current logical/regime pointers.

    The registry is deliberately authority-neutral. It records exact identity and
    ancestry; callers decide whether a current lineage revision is required for
    a particular proof/authorization path.
    """

    def __init__(self) -> None:
        self._revisions: dict[str, CanonicalLineageRevision] = {}
        self._current: dict[tuple[str, str], str] = {}
        self._regimes: dict[str, SemanticRegimeRevision] = {}
        self._current_regimes: dict[SemanticRegimeKind, str] = {}
        self._revision_owners: dict[str, tuple[str, str, str]] = {}

    def _claim_revision_id(self, revision_id: str, owner: tuple[str, str, str]) -> None:
        current_owner = self._revision_owners.get(revision_id)
        if current_owner is not None and current_owner != owner:
            raise LineageError(
                f"revision_id {revision_id!r} is already owned by {current_owner!r}"
            )
        self._revision_owners[revision_id] = owner

    def get(self, revision_id: str) -> CanonicalLineageRevision:
        try:
            return self._revisions[revision_id]
        except KeyError as exc:
            raise LineageError(f"unknown lineage revision: {revision_id}") from exc

    def current(self, object_family: str, logical_id: str) -> CanonicalLineageRevision:
        key = (_required("object_family", object_family), _required("logical_id", logical_id))
        try:
            return self._revisions[self._current[key]]
        except KeyError as exc:
            raise LineageError(f"no current lineage revision for {key!r}") from exc

    def all_revisions(self) -> tuple[CanonicalLineageRevision, ...]:
        return tuple(sorted(self._revisions.values(), key=lambda row: (row.created_sequence, row.revision_id)))

    def register(
        self,
        revision: CanonicalLineageRevision,
        *,
        imported_legacy_root: bool = False,
        make_current: bool = True,
    ) -> CanonicalLineageRevision:
        owner = ("object", revision.object_family, revision.logical_id)
        existing = self._revisions.get(revision.revision_id)
        if existing is not None:
            if existing != revision:
                raise LineageError("revision_id cannot be rebound to different lineage content")
            return existing
        self._claim_revision_id(revision.revision_id, owner)

        if not imported_legacy_root:
            for parent in revision.parent_revision_ids:
                if parent not in self._revisions:
                    raise LineageError(f"unknown parent lineage revision: {parent}")
        for parent in revision.parent_revision_ids:
            if parent == revision.revision_id:
                raise LineageError("lineage parent cycle detected")

        key = (revision.object_family, revision.logical_id)
        current_id = self._current.get(key)
        if current_id is not None:
            current = self._revisions[current_id]
            if revision.created_sequence <= current.created_sequence:
                raise LineageError("created_sequence must advance for a new logical revision")
            if revision.supersedes_revision_id is not None and revision.supersedes_revision_id != current.revision_id:
                raise LineageError("supersedes_revision_id must name the current logical revision")
        elif revision.supersedes_revision_id is not None:
            if revision.supersedes_revision_id not in self._revisions:
                raise LineageError("superseded revision does not exist")
            superseded = self._revisions[revision.supersedes_revision_id]
            if (superseded.object_family, superseded.logical_id) != key:
                raise LineageError("cannot supersede a different logical object")

        # Parent graph is append-only. Since all ordinary parents must pre-exist,
        # only a self-edge could form a new cycle at insertion time; legacy import
        # is still checked for references that are already known.
        if imported_legacy_root:
            for parent in revision.parent_revision_ids:
                if parent in self._revisions and self._would_reach(parent, revision.revision_id):
                    raise LineageError("lineage parent cycle detected")

        self._revisions[revision.revision_id] = revision
        if make_current:
            self._current[key] = revision.revision_id
        return revision

    def _would_reach(self, start_revision_id: str, target_revision_id: str) -> bool:
        seen: set[str] = set()
        stack = [start_revision_id]
        while stack:
            current = stack.pop()
            if current == target_revision_id:
                return True
            if current in seen:
                continue
            seen.add(current)
            row = self._revisions.get(current)
            if row is not None:
                stack.extend(row.parent_revision_ids)
        return False

    def register_regime(self, revision: SemanticRegimeRevision) -> SemanticRegimeRevision:
        owner = ("regime", revision.regime_kind.value, revision.logical_id)
        existing = self._regimes.get(revision.revision_id)
        if existing is not None:
            if existing != revision:
                raise LineageError("regime revision_id cannot be rebound to different content")
            return existing
        self._claim_revision_id(revision.revision_id, owner)

        current_id = self._current_regimes.get(revision.regime_kind)
        if revision.parent_revision_id is not None:
            parent = self._regimes.get(revision.parent_revision_id)
            if parent is None:
                raise LineageError("unknown semantic-regime parent revision")
            if parent.regime_kind != revision.regime_kind:
                raise LineageError("semantic-regime parent kind mismatch")
        if current_id is not None:
            current = self._regimes[current_id]
            if revision.logical_id != current.logical_id:
                raise LineageError("semantic regime logical identity cannot be silently rebound")
            if revision.created_sequence <= current.created_sequence:
                raise LineageError("semantic-regime created_sequence must advance")
            if revision.parent_revision_id != current.revision_id:
                raise LineageError("new semantic-regime revision must descend from current revision")
        elif revision.parent_revision_id is not None:
            # A first current pointer may only point to a parent when the parent is
            # already historical in this registry; normal registration makes the
            # first record a root.
            parent = self._regimes[revision.parent_revision_id]
            if parent.created_sequence >= revision.created_sequence:
                raise LineageError("semantic-regime created_sequence must advance")

        self._regimes[revision.revision_id] = revision
        self._current_regimes[revision.regime_kind] = revision.revision_id
        return revision

    def current_regime(self, kind: str | SemanticRegimeKind) -> SemanticRegimeRevision:
        parsed = SemanticRegimeKind.parse(kind)
        try:
            return self._regimes[self._current_regimes[parsed]]
        except KeyError as exc:
            raise LineageError(f"no current semantic regime for {parsed.value}") from exc

    def all_regimes(self) -> tuple[SemanticRegimeRevision, ...]:
        return tuple(sorted(self._regimes.values(), key=lambda row: (row.created_sequence, row.revision_id)))

    def semantic_root_digest(self) -> str:
        current_objects = tuple(
            sorted(
                (
                    family,
                    logical_id,
                    revision_id,
                    self._revisions[revision_id].lineage_digest,
                )
                for (family, logical_id), revision_id in self._current.items()
            )
        )
        current_regimes = tuple(
            sorted(
                (
                    kind.value,
                    revision_id,
                    self._regimes[revision_id].canonical_digest,
                )
                for kind, revision_id in self._current_regimes.items()
            )
        )
        return digest({"objects": current_objects, "regimes": current_regimes})
