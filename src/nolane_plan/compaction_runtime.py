from __future__ import annotations

from typing import Iterable

from .compaction import (
    CompactionArchive,
    CompactionError,
    CompactionManifest,
    CompactionResult,
)
from .lineage import SemanticRegimeKind
from .types import ReplayError


def _current_object_pointers(kernel) -> tuple[tuple[str, str, str], ...]:
    keys = sorted({(row.object_family, row.logical_id) for row in kernel.lineage.all_revisions()})
    return tuple(
        (family, logical_id, kernel.lineage.current(family, logical_id).revision_id)
        for family, logical_id in keys
    )


def _current_regime_pointers(kernel) -> tuple[tuple[str, str], ...]:
    return tuple(
        sorted(
            (kind.value, kernel.lineage.current_regime(kind).revision_id)
            for kind in SemanticRegimeKind
        )
    )


def _authority_lineage_refs(kernel) -> tuple[str, ...]:
    refs: set[str] = set()
    for binding in kernel.authorization_lineage_bindings.values():
        refs.update(
            {
                binding.mission_revision_id,
                binding.canonical_state_revision_id,
                binding.action_revision_id,
            }
        )
        refs.update(binding.grant_revision_ids)
        refs.update(revision_id for _, revision_id in binding.regime_revisions)
    return tuple(sorted(refs))


def _dormant_refs(branches: Iterable[object]) -> tuple[str, ...]:
    refs: set[str] = set()
    for branch in branches:
        for name in ("revision_id", "transition_model_revision", "temporal_feasibility_revision"):
            value = getattr(branch, name, None)
            if value:
                refs.add(str(value))
        for name in (
            "assumption_revision_refs",
            "evidence_revision_refs",
            "resource_revision_refs",
            "capability_revision_refs",
            "authority_revision_refs",
            "resurrection_dependency_refs",
        ):
            refs.update(str(value) for value in getattr(branch, name, ()) if str(value))
    return tuple(sorted(refs))


def _proof_evidence_debt_refs(kernel) -> tuple[str, ...]:
    refs: set[str] = set()
    for row in kernel.lineage.all_revisions():
        refs.update(row.provenance_refs)
        refs.update(row.debt_refs)
    refs.update(str(key) for key in getattr(kernel.evidence, "records", {}))
    for manifest in getattr(kernel, "proof_manifests", {}).values():
        for name in (
            "positive_revision_dependencies",
            "semantic_profile_dependencies",
            "trust_checker_normalizer_dependencies",
            "execution_semantic_profile_dependencies",
        ):
            value = getattr(manifest, name, ())
            if isinstance(value, dict):
                refs.update(str(item) for item in value.values())
            else:
                refs.update(str(item) for item in value)
    return tuple(sorted(refs))


def _unique_fallback_refs(kernel) -> tuple[str, ...]:
    refs = {
        str(row.fallback_on_instability)
        for row in getattr(kernel, "handoff_stability_contracts", {}).values()
        if getattr(row, "fallback_on_instability", None)
    }
    return tuple(sorted(refs))


def _make_archive(kernel) -> CompactionArchive:
    return CompactionArchive.create(
        revisions=kernel.lineage.all_revisions(),
        regimes=kernel.lineage.all_regimes(),
        current_object_pointers=_current_object_pointers(kernel),
        current_regime_pointers=_current_regime_pointers(kernel),
    )


def _compact_lineage(self, manifest_id: str, *, dormant_branches: Iterable[object] = ()) -> CompactionResult:
    from .lineage_recovery import canonical_semantic_digest

    with self._writer_lock:
        manifest_key = str(manifest_id).strip()
        if not manifest_key:
            raise CompactionError("manifest_id must be non-empty")
        existing = self.compaction_manifests.get(manifest_key)
        if existing is not None:
            return self.compaction_results[manifest_key]

        source_root = self.lineage.semantic_root_digest()
        source_canonical = canonical_semantic_digest(self)
        archive = _make_archive(self)
        target_sequence = self.writer_sequence + 1
        manifest = CompactionManifest.create(
            manifest_id=manifest_key,
            created_sequence=target_sequence,
            source_semantic_root_digest=source_root,
            source_canonical_semantic_digest=source_canonical,
            archive_digest=archive.canonical_digest,
            active_authority_revision_ids=_authority_lineage_refs(self),
            dormant_resurrection_refs=_dormant_refs(tuple(dormant_branches)),
            proof_evidence_debt_refs=_proof_evidence_debt_refs(self),
            unique_fallback_refs=_unique_fallback_refs(self),
            representation_only=True,
        )
        reconstructed = archive.reconstruct()
        if reconstructed.semantic_root_digest() != source_root:
            raise CompactionError("archive reconstruction does not reproduce source semantic root")

        # Reference-runtime compaction is intentionally representation-only: the
        # canonical lineage registry, current pointers, regimes and authority
        # bindings remain untouched. The single journal record is the atomic
        # visibility point for archive+manifest+result.
        target_root = self.lineage.semantic_root_digest()
        target_canonical = canonical_semantic_digest(self)
        result = CompactionResult.create(
            manifest_id=manifest.manifest_id,
            committed_sequence=target_sequence,
            source_semantic_root_digest=source_root,
            target_semantic_root_digest=target_root,
            source_canonical_semantic_digest=source_canonical,
            target_canonical_semantic_digest=target_canonical,
        )
        self._record(
            "compaction.representation_committed",
            {
                "manifest": manifest.canonical_payload(),
                "archive": archive.canonical_payload(),
                "result": result.canonical_payload(),
            },
        )
        if self.writer_sequence != target_sequence:
            raise CompactionError("compaction journal sequence did not commit atomically")
        self.compaction_archives[manifest.manifest_id] = archive
        self.compaction_manifests[manifest.manifest_id] = manifest
        self.compaction_results[manifest.manifest_id] = result
        return result


def _reconstruct_compacted_lineage(self, manifest_id: str):
    key = str(manifest_id)
    manifest = self.compaction_manifests.get(key)
    archive = self.compaction_archives.get(key)
    if manifest is None or archive is None:
        raise CompactionError(f"unknown compaction manifest: {key}")
    if archive.canonical_digest != manifest.archive_digest:
        raise CompactionError("compaction archive no longer matches manifest")
    reconstructed = archive.reconstruct()
    if reconstructed.semantic_root_digest() != manifest.source_semantic_root_digest:
        raise CompactionError("compaction reconstruction changed semantic root")
    return reconstructed


def compaction_snapshot_state(kernel) -> dict[str, object]:
    return {
        "manifests": {
            key: value.canonical_payload()
            for key, value in sorted(kernel.compaction_manifests.items())
        },
        "archives": {
            key: value.canonical_payload()
            for key, value in sorted(kernel.compaction_archives.items())
        },
        "results": {
            key: value.canonical_payload()
            for key, value in sorted(kernel.compaction_results.items())
        },
    }


def _validate_restored_compaction(kernel, manifest: CompactionManifest, archive: CompactionArchive, result: CompactionResult) -> None:
    from .lineage_recovery import canonical_semantic_digest

    if archive.canonical_digest != manifest.archive_digest:
        raise ReplayError("compaction archive digest does not match manifest")
    if result.manifest_id != manifest.manifest_id:
        raise ReplayError("compaction result references wrong manifest")
    reconstructed = archive.reconstruct()
    if reconstructed.semantic_root_digest() != manifest.source_semantic_root_digest:
        raise ReplayError("compaction archive reconstruction changed semantic root")
    if kernel.lineage.semantic_root_digest() != result.target_semantic_root_digest:
        raise ReplayError("restored compaction target semantic root is stale")
    if canonical_semantic_digest(kernel) != result.target_canonical_semantic_digest:
        raise ReplayError("restored compaction target canonical digest is stale")


def restore_compaction_snapshot(kernel, raw: dict[str, object]) -> None:
    manifests_raw = raw.get("manifests", {})
    archives_raw = raw.get("archives", {})
    results_raw = raw.get("results", {})
    if not isinstance(manifests_raw, dict) or not isinstance(archives_raw, dict) or not isinstance(results_raw, dict):
        raise ReplayError("invalid compaction snapshot envelope")
    if set(manifests_raw) != set(archives_raw) or set(manifests_raw) != set(results_raw):
        raise ReplayError("compaction snapshot manifest/archive/result sets differ")

    manifests: dict[str, CompactionManifest] = {}
    archives: dict[str, CompactionArchive] = {}
    results: dict[str, CompactionResult] = {}
    try:
        for key in sorted(manifests_raw):
            manifest = CompactionManifest.from_payload(dict(manifests_raw[key]))
            archive = CompactionArchive.from_payload(dict(archives_raw[key]))
            result = CompactionResult.from_payload(dict(results_raw[key]))
            if manifest.manifest_id != str(key) or result.manifest_id != str(key):
                raise ReplayError("compaction snapshot key/id mismatch")
            _validate_restored_compaction(kernel, manifest, archive, result)
            manifests[str(key)] = manifest
            archives[str(key)] = archive
            results[str(key)] = result
    except ReplayError:
        raise
    except Exception as exc:
        raise ReplayError(f"invalid compaction snapshot: {exc}") from exc
    kernel.compaction_manifests = manifests
    kernel.compaction_archives = archives
    kernel.compaction_results = results


def replay_compaction_commit(kernel, entry) -> None:
    from .lineage_recovery import canonical_semantic_digest

    payload = dict(entry.payload)
    try:
        manifest = CompactionManifest.from_payload(dict(payload["manifest"]))
        archive = CompactionArchive.from_payload(dict(payload["archive"]))
        result = CompactionResult.from_payload(dict(payload["result"]))
    except Exception as exc:
        raise ReplayError(f"invalid compaction replay payload: {exc}") from exc
    if manifest.created_sequence != entry.sequence or result.committed_sequence != entry.sequence:
        raise ReplayError("compaction replay sequence does not match journal sequence")
    if manifest.manifest_id != result.manifest_id:
        raise ReplayError("compaction replay manifest/result ID mismatch")
    if archive.canonical_digest != manifest.archive_digest:
        raise ReplayError("compaction replay archive digest mismatch")
    if kernel.lineage.semantic_root_digest() != manifest.source_semantic_root_digest:
        raise ReplayError("compaction replay source semantic root is stale")
    if canonical_semantic_digest(kernel) != manifest.source_canonical_semantic_digest:
        raise ReplayError("compaction replay source canonical digest is stale")
    reconstructed = archive.reconstruct()
    if reconstructed.semantic_root_digest() != manifest.source_semantic_root_digest:
        raise ReplayError("compaction replay archive cannot reconstruct source root")
    if result.target_semantic_root_digest != manifest.source_semantic_root_digest:
        raise ReplayError("compaction replay attempted a semantic root switch")
    if result.target_canonical_semantic_digest != manifest.source_canonical_semantic_digest:
        raise ReplayError("compaction replay attempted a canonical semantic switch")

    existing = kernel.compaction_manifests.get(manifest.manifest_id)
    if existing is not None and existing.canonical_digest != manifest.canonical_digest:
        raise ReplayError("compaction manifest ID rebound during replay")
    kernel.compaction_manifests[manifest.manifest_id] = manifest
    kernel.compaction_archives[manifest.manifest_id] = archive
    kernel.compaction_results[manifest.manifest_id] = result


def install_compaction_runtime(kernel_cls) -> None:
    """Install reversible representation-only compaction on the Wave-7 writer spine."""
    if getattr(kernel_cls, "_wave7_compaction_runtime_installed", False):
        return
    original_init = kernel_cls.__init__

    def __init__(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        self.compaction_manifests: dict[str, CompactionManifest] = {}
        self.compaction_archives: dict[str, CompactionArchive] = {}
        self.compaction_results: dict[str, CompactionResult] = {}

    kernel_cls.__init__ = __init__
    kernel_cls.compact_lineage = _compact_lineage
    kernel_cls.reconstruct_compacted_lineage = _reconstruct_compacted_lineage
    kernel_cls._wave7_compaction_runtime_installed = True
