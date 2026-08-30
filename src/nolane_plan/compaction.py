from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from .hashing import digest
from .lineage import CanonicalLineageRevision, LineageRegistry, SemanticRegimeKind, SemanticRegimeRevision


class CompactionError(ValueError):
    """Raised when representation compaction would change or lose semantics."""


def _required(name: str, value: object) -> str:
    text = str(value).strip()
    if not text:
        raise CompactionError(f"{name} must be non-empty")
    return text


def _canon(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(sorted({str(value).strip() for value in values if str(value).strip()}))


def lineage_revision_doc(row: CanonicalLineageRevision) -> dict[str, Any]:
    return {
        "object_family": row.object_family,
        "logical_id": row.logical_id,
        "revision_id": row.revision_id,
        "schema_version": row.schema_version,
        "created_sequence": row.created_sequence,
        "created_at_wall_time": row.created_at_wall_time,
        "mission_revision_dependency": row.mission_revision_dependency,
        "plan_revision": row.plan_revision,
        "world_model_revision": row.world_model_revision,
        "environment_regime_revision": row.environment_regime_revision,
        "validity_regime": row.validity_regime,
        "parent_revision_ids": list(row.parent_revision_ids),
        "provenance_refs": list(row.provenance_refs),
        "assurance_profile": row.assurance_profile,
        "debt_refs": list(row.debt_refs),
        "supersedes_revision_id": row.supersedes_revision_id,
        "semantic_digest": row.semantic_digest,
        "lineage_digest": row.lineage_digest,
    }


def lineage_revision_from_doc(raw: dict[str, Any]) -> CanonicalLineageRevision:
    row = CanonicalLineageRevision.create(
        object_family=str(raw["object_family"]),
        logical_id=str(raw["logical_id"]),
        revision_id=str(raw["revision_id"]),
        schema_version=str(raw["schema_version"]),
        created_sequence=int(raw["created_sequence"]),
        created_at_wall_time=raw.get("created_at_wall_time"),
        mission_revision_dependency=raw.get("mission_revision_dependency"),
        plan_revision=int(raw["plan_revision"]),
        world_model_revision=str(raw["world_model_revision"]),
        environment_regime_revision=str(raw["environment_regime_revision"]),
        validity_regime=str(raw["validity_regime"]),
        parent_revision_ids=tuple(str(x) for x in raw.get("parent_revision_ids", ())),
        provenance_refs=tuple(str(x) for x in raw.get("provenance_refs", ())),
        assurance_profile=str(raw["assurance_profile"]),
        debt_refs=tuple(str(x) for x in raw.get("debt_refs", ())),
        supersedes_revision_id=raw.get("supersedes_revision_id"),
        semantic_digest=str(raw["semantic_digest"]),
    )
    if row.lineage_digest != str(raw.get("lineage_digest", "")):
        raise CompactionError("archived lineage revision digest mismatch")
    return row


def regime_doc(row: SemanticRegimeRevision) -> dict[str, Any]:
    return {
        "regime_kind": row.regime_kind.value,
        "logical_id": row.logical_id,
        "revision_id": row.revision_id,
        "created_sequence": row.created_sequence,
        "parent_revision_id": row.parent_revision_id,
        "semantic_digest": row.semantic_digest,
        "provenance_refs": list(row.provenance_refs),
        "canonical_digest": row.canonical_digest,
    }


def regime_from_doc(raw: dict[str, Any]) -> SemanticRegimeRevision:
    row = SemanticRegimeRevision.create(
        regime_kind=str(raw["regime_kind"]),
        logical_id=str(raw["logical_id"]),
        revision_id=str(raw["revision_id"]),
        created_sequence=int(raw["created_sequence"]),
        parent_revision_id=raw.get("parent_revision_id"),
        semantic_digest=str(raw["semantic_digest"]),
        provenance_refs=tuple(str(x) for x in raw.get("provenance_refs", ())),
    )
    if row.canonical_digest != str(raw.get("canonical_digest", "")):
        raise CompactionError("archived semantic-regime digest mismatch")
    return row


@dataclass(frozen=True, slots=True)
class CompactionArchive:
    revisions: tuple[CanonicalLineageRevision, ...]
    regimes: tuple[SemanticRegimeRevision, ...]
    current_object_pointers: tuple[tuple[str, str, str], ...]
    current_regime_pointers: tuple[tuple[str, str], ...]
    canonical_digest: str

    @classmethod
    def create(
        cls,
        *,
        revisions: Iterable[CanonicalLineageRevision],
        regimes: Iterable[SemanticRegimeRevision],
        current_object_pointers: Iterable[tuple[str, str, str]],
        current_regime_pointers: Iterable[tuple[str, str]],
    ) -> "CompactionArchive":
        revision_rows = tuple(sorted(tuple(revisions), key=lambda row: (row.created_sequence, row.revision_id)))
        regime_rows = tuple(sorted(tuple(regimes), key=lambda row: (row.created_sequence, row.revision_id)))
        revision_ids = [row.revision_id for row in revision_rows]
        regime_ids = [row.revision_id for row in regime_rows]
        if len(revision_ids) != len(set(revision_ids)):
            raise CompactionError("duplicate lineage revision in compaction archive")
        if len(regime_ids) != len(set(regime_ids)):
            raise CompactionError("duplicate semantic-regime revision in compaction archive")
        object_pointers = tuple(sorted((str(a), str(b), str(c)) for a, b, c in current_object_pointers))
        regime_pointers = tuple(sorted((str(a), str(b)) for a, b in current_regime_pointers))
        body = {
            "revisions": tuple((row.revision_id, row.lineage_digest) for row in revision_rows),
            "regimes": tuple((row.revision_id, row.canonical_digest) for row in regime_rows),
            "current_object_pointers": object_pointers,
            "current_regime_pointers": regime_pointers,
        }
        return cls(revision_rows, regime_rows, object_pointers, regime_pointers, digest(body))

    def register_revision(self, revision: CanonicalLineageRevision) -> CanonicalLineageRevision:
        for row in self.revisions:
            if row.revision_id == revision.revision_id:
                if row != revision:
                    raise CompactionError("archived revision ID cannot be rebound")
                return row
        raise CompactionError("compaction archive is read-only")

    def register_regime(self, revision: SemanticRegimeRevision) -> SemanticRegimeRevision:
        for row in self.regimes:
            if row.revision_id == revision.revision_id:
                if row != revision:
                    raise CompactionError("archived regime revision ID cannot be rebound")
                return row
        raise CompactionError("compaction archive is read-only")

    def canonical_payload(self) -> dict[str, Any]:
        return {
            "revisions": [lineage_revision_doc(row) for row in self.revisions],
            "regimes": [regime_doc(row) for row in self.regimes],
            "current_object_pointers": [list(row) for row in self.current_object_pointers],
            "current_regime_pointers": [list(row) for row in self.current_regime_pointers],
            "canonical_digest": self.canonical_digest,
        }

    @classmethod
    def from_payload(cls, raw: dict[str, Any]) -> "CompactionArchive":
        value = cls.create(
            revisions=tuple(lineage_revision_from_doc(dict(row)) for row in raw.get("revisions", ())),
            regimes=tuple(regime_from_doc(dict(row)) for row in raw.get("regimes", ())),
            current_object_pointers=tuple(tuple(str(x) for x in row) for row in raw.get("current_object_pointers", ())),
            current_regime_pointers=tuple(tuple(str(x) for x in row) for row in raw.get("current_regime_pointers", ())),
        )
        if value.canonical_digest != str(raw.get("canonical_digest", "")):
            raise CompactionError("compaction archive canonical digest mismatch")
        return value

    def reconstruct(self) -> LineageRegistry:
        registry = LineageRegistry()
        for row in self.regimes:
            registry.register_regime(row)
        for row in self.revisions:
            registry.register(row, make_current=False)

        object_pointers: dict[tuple[str, str], str] = {}
        for family, logical_id, revision_id in self.current_object_pointers:
            row = registry.get(revision_id)
            if (row.object_family, row.logical_id) != (family, logical_id):
                raise CompactionError("archived current pointer crosses logical identity")
            object_pointers[(family, logical_id)] = revision_id
        registry._current = object_pointers

        regime_pointers: dict[SemanticRegimeKind, str] = {}
        regime_by_id = {row.revision_id: row for row in registry.all_regimes()}
        for raw_kind, revision_id in self.current_regime_pointers:
            kind = SemanticRegimeKind.parse(raw_kind)
            row = regime_by_id.get(revision_id)
            if row is None or row.regime_kind != kind:
                raise CompactionError("archived regime pointer crosses semantic-regime identity")
            regime_pointers[kind] = revision_id
        if set(regime_pointers) != set(SemanticRegimeKind):
            raise CompactionError("compaction archive has incomplete semantic-regime pointers")
        registry._current_regimes = regime_pointers
        return registry


@dataclass(frozen=True, slots=True)
class CompactionManifest:
    manifest_id: str
    created_sequence: int
    source_semantic_root_digest: str
    source_canonical_semantic_digest: str
    archive_digest: str
    active_authority_revision_ids: tuple[str, ...]
    dormant_resurrection_refs: tuple[str, ...]
    proof_evidence_debt_refs: tuple[str, ...]
    unique_fallback_refs: tuple[str, ...]
    representation_only: bool
    canonical_digest: str

    @classmethod
    def create(
        cls,
        *,
        manifest_id: str,
        created_sequence: int,
        source_semantic_root_digest: str,
        source_canonical_semantic_digest: str,
        archive_digest: str,
        active_authority_revision_ids: Iterable[str],
        dormant_resurrection_refs: Iterable[str],
        proof_evidence_debt_refs: Iterable[str],
        unique_fallback_refs: Iterable[str],
        representation_only: bool = True,
    ) -> "CompactionManifest":
        sequence = int(created_sequence)
        if sequence < 1:
            raise CompactionError("compaction sequence must be positive")
        body = {
            "manifest_id": _required("manifest_id", manifest_id),
            "created_sequence": sequence,
            "source_semantic_root_digest": _required("source_semantic_root_digest", source_semantic_root_digest),
            "source_canonical_semantic_digest": _required("source_canonical_semantic_digest", source_canonical_semantic_digest),
            "archive_digest": _required("archive_digest", archive_digest),
            "active_authority_revision_ids": _canon(active_authority_revision_ids),
            "dormant_resurrection_refs": _canon(dormant_resurrection_refs),
            "proof_evidence_debt_refs": _canon(proof_evidence_debt_refs),
            "unique_fallback_refs": _canon(unique_fallback_refs),
            "representation_only": bool(representation_only),
        }
        if not body["representation_only"]:
            raise CompactionError("reference runtime only supports representation-only compaction")
        return cls(
            manifest_id=body["manifest_id"],
            created_sequence=sequence,
            source_semantic_root_digest=body["source_semantic_root_digest"],
            source_canonical_semantic_digest=body["source_canonical_semantic_digest"],
            archive_digest=body["archive_digest"],
            active_authority_revision_ids=body["active_authority_revision_ids"],
            dormant_resurrection_refs=body["dormant_resurrection_refs"],
            proof_evidence_debt_refs=body["proof_evidence_debt_refs"],
            unique_fallback_refs=body["unique_fallback_refs"],
            representation_only=True,
            canonical_digest=digest(body),
        )

    def canonical_payload(self) -> dict[str, Any]:
        return {
            "manifest_id": self.manifest_id,
            "created_sequence": self.created_sequence,
            "source_semantic_root_digest": self.source_semantic_root_digest,
            "source_canonical_semantic_digest": self.source_canonical_semantic_digest,
            "archive_digest": self.archive_digest,
            "active_authority_revision_ids": list(self.active_authority_revision_ids),
            "dormant_resurrection_refs": list(self.dormant_resurrection_refs),
            "proof_evidence_debt_refs": list(self.proof_evidence_debt_refs),
            "unique_fallback_refs": list(self.unique_fallback_refs),
            "representation_only": self.representation_only,
            "canonical_digest": self.canonical_digest,
        }

    @classmethod
    def from_payload(cls, raw: dict[str, Any]) -> "CompactionManifest":
        value = cls.create(
            manifest_id=str(raw["manifest_id"]),
            created_sequence=int(raw["created_sequence"]),
            source_semantic_root_digest=str(raw["source_semantic_root_digest"]),
            source_canonical_semantic_digest=str(raw["source_canonical_semantic_digest"]),
            archive_digest=str(raw["archive_digest"]),
            active_authority_revision_ids=tuple(str(x) for x in raw.get("active_authority_revision_ids", ())),
            dormant_resurrection_refs=tuple(str(x) for x in raw.get("dormant_resurrection_refs", ())),
            proof_evidence_debt_refs=tuple(str(x) for x in raw.get("proof_evidence_debt_refs", ())),
            unique_fallback_refs=tuple(str(x) for x in raw.get("unique_fallback_refs", ())),
            representation_only=bool(raw.get("representation_only", False)),
        )
        if value.canonical_digest != str(raw.get("canonical_digest", "")):
            raise CompactionError("compaction manifest canonical digest mismatch")
        return value


@dataclass(frozen=True, slots=True)
class CompactionResult:
    manifest_id: str
    committed_sequence: int
    source_semantic_root_digest: str
    target_semantic_root_digest: str
    source_canonical_semantic_digest: str
    target_canonical_semantic_digest: str
    canonical_digest: str

    @classmethod
    def create(
        cls,
        *,
        manifest_id: str,
        committed_sequence: int,
        source_semantic_root_digest: str,
        target_semantic_root_digest: str,
        source_canonical_semantic_digest: str,
        target_canonical_semantic_digest: str,
    ) -> "CompactionResult":
        sequence = int(committed_sequence)
        body = {
            "manifest_id": _required("manifest_id", manifest_id),
            "committed_sequence": sequence,
            "source_semantic_root_digest": _required("source_semantic_root_digest", source_semantic_root_digest),
            "target_semantic_root_digest": _required("target_semantic_root_digest", target_semantic_root_digest),
            "source_canonical_semantic_digest": _required("source_canonical_semantic_digest", source_canonical_semantic_digest),
            "target_canonical_semantic_digest": _required("target_canonical_semantic_digest", target_canonical_semantic_digest),
        }
        if body["source_semantic_root_digest"] != body["target_semantic_root_digest"]:
            raise CompactionError("representation compaction changed semantic root")
        if body["source_canonical_semantic_digest"] != body["target_canonical_semantic_digest"]:
            raise CompactionError("representation compaction changed canonical semantic digest")
        return cls(
            manifest_id=body["manifest_id"],
            committed_sequence=sequence,
            source_semantic_root_digest=body["source_semantic_root_digest"],
            target_semantic_root_digest=body["target_semantic_root_digest"],
            source_canonical_semantic_digest=body["source_canonical_semantic_digest"],
            target_canonical_semantic_digest=body["target_canonical_semantic_digest"],
            canonical_digest=digest(body),
        )

    def canonical_payload(self) -> dict[str, Any]:
        return {
            "manifest_id": self.manifest_id,
            "committed_sequence": self.committed_sequence,
            "source_semantic_root_digest": self.source_semantic_root_digest,
            "target_semantic_root_digest": self.target_semantic_root_digest,
            "source_canonical_semantic_digest": self.source_canonical_semantic_digest,
            "target_canonical_semantic_digest": self.target_canonical_semantic_digest,
            "canonical_digest": self.canonical_digest,
        }

    @classmethod
    def from_payload(cls, raw: dict[str, Any]) -> "CompactionResult":
        value = cls.create(
            manifest_id=str(raw["manifest_id"]),
            committed_sequence=int(raw["committed_sequence"]),
            source_semantic_root_digest=str(raw["source_semantic_root_digest"]),
            target_semantic_root_digest=str(raw["target_semantic_root_digest"]),
            source_canonical_semantic_digest=str(raw["source_canonical_semantic_digest"]),
            target_canonical_semantic_digest=str(raw["target_canonical_semantic_digest"]),
        )
        if value.canonical_digest != str(raw.get("canonical_digest", "")):
            raise CompactionError("compaction result canonical digest mismatch")
        return value
