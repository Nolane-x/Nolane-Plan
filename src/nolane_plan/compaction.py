from __future__ import annotations


class CompactionError(ValueError):
    """Raised when representation compaction would change or lose semantics."""
