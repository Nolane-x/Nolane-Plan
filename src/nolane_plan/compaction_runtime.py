from __future__ import annotations

from .compaction import CompactionError


def _compact_lineage(self, *args, **kwargs):
    raise CompactionError("Wave 7 compaction semantics are not implemented yet")


def _reconstruct_compacted_lineage(self, *args, **kwargs):
    raise CompactionError("Wave 7 compaction reconstruction is not implemented yet")


def install_compaction_runtime(kernel_cls) -> None:
    """Install the Task-6 API surface before semantic implementation."""
    if getattr(kernel_cls, "_wave7_compaction_runtime_installed", False):
        return
    kernel_cls.compact_lineage = _compact_lineage
    kernel_cls.reconstruct_compacted_lineage = _reconstruct_compacted_lineage
    kernel_cls._wave7_compaction_runtime_installed = True
