from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from .hashing import digest
from .lineage_snapshot import LINEAGE_SNAPSHOT_SCHEMA
from .policy_recovery import POLICY_SNAPSHOT_SCHEMA
from .proof_recovery import PROOF_SNAPSHOT_SCHEMA
from .resume import SNAPSHOT_SCHEMA as BASE_SNAPSHOT_SCHEMA
from .schedulability_recovery import SCHEDULABILITY_SNAPSHOT_SCHEMA
from .trust_recovery import TRUST_SNAPSHOT_SCHEMA


_FIXTURE_ROOT = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "wave8_migrations"
_ALLOWED_DISPOSITIONS = frozenset({"PRESERVED_EXACTLY", "RECOMPUTED_FROM_CANONICAL_INPUTS", "INVALIDATED_REQUIRES_RECHECK", "ESCALATED_TO_DEBT", "ARCHIVED_READ_ONLY", "UNSUPPORTED_FAIL_CLOSED"})


@dataclass(frozen=True, slots=True)
class HistoricalMigrationEdge:
    source_schema: str
    target_schema: str
    fixture_ref: str
    expected_dispositions: tuple[str, ...]
    unsupported_cases: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.source_schema.strip() or not self.target_schema.strip():
            raise ValueError("migration edge schemas must be non-empty")
        if self.source_schema == self.target_schema:
            raise ValueError("historical migration edge must change schema")
        if self.target_schema != LINEAGE_SNAPSHOT_SCHEMA:
            raise ValueError("Wave-8 historical matrix targets the frozen v7 lineage schema")
        if not self.fixture_ref.strip():
            raise ValueError("migration edge fixture_ref must be non-empty")
        if not self.expected_dispositions:
            raise ValueError("migration edge must declare conservative dispositions")
        unknown = set(self.expected_dispositions).difference(_ALLOWED_DISPOSITIONS)
        if unknown:
            raise ValueError(f"unknown migration dispositions: {sorted(unknown)!r}")
        if not self.unsupported_cases:
            raise ValueError("migration edge must fail closed for explicit unsupported cases")


_COMMON = ("PRESERVED_EXACTLY", "RECOMPUTED_FROM_CANONICAL_INPUTS", "INVALIDATED_REQUIRES_RECHECK")

SUPPORTED_MIGRATION_EDGES = (
    HistoricalMigrationEdge(BASE_SNAPSHOT_SCHEMA, LINEAGE_SNAPSHOT_SCHEMA, "v2_to_v7.json", _COMMON, ("opaque-v2-extension", "unknown-correctness-event")),
    HistoricalMigrationEdge(TRUST_SNAPSHOT_SCHEMA, LINEAGE_SNAPSHOT_SCHEMA, "v3_to_v7.json", _COMMON, ("opaque-v3-proof-extension", "unknown-correctness-event")),
    HistoricalMigrationEdge(PROOF_SNAPSHOT_SCHEMA, LINEAGE_SNAPSHOT_SCHEMA, "v4_to_v7.json", _COMMON, ("opaque-v4-policy-extension", "unknown-correctness-event")),
    HistoricalMigrationEdge(POLICY_SNAPSHOT_SCHEMA, LINEAGE_SNAPSHOT_SCHEMA, "v5_to_v7.json", _COMMON, ("opaque-v5-schedulability-extension", "unknown-correctness-event")),
    HistoricalMigrationEdge(SCHEDULABILITY_SNAPSHOT_SCHEMA, LINEAGE_SNAPSHOT_SCHEMA, "v6_to_v7.json", (*_COMMON, "ARCHIVED_READ_ONLY"), ("opaque-v6-lineage-extension", "unknown-correctness-event")),
)


def _fixture_path(edge: HistoricalMigrationEdge) -> Path:
    name = Path(edge.fixture_ref)
    if name.name != edge.fixture_ref or name.suffix != ".json":
        raise ValueError("migration fixture_ref must be a plain JSON filename")
    return _FIXTURE_ROOT / name


def load_fixture(edge: HistoricalMigrationEdge) -> dict[str, Any]:
    raw = json.loads(_fixture_path(edge).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("migration fixture must be a JSON object")
    stored_digest = str(raw.get("fixture_digest", ""))
    body = dict(raw)
    body.pop("fixture_digest", None)
    if not stored_digest or stored_digest != digest(body):
        raise ValueError(f"migration fixture digest mismatch: {edge.fixture_ref}")
    if str(raw.get("source_schema")) != edge.source_schema or str(raw.get("target_schema")) != edge.target_schema:
        raise ValueError("migration fixture schema binding does not match matrix edge")
    if tuple(raw.get("expected_dispositions", ())) != edge.expected_dispositions:
        raise ValueError("migration fixture dispositions do not match matrix edge")
    if tuple(raw.get("unsupported_cases", ())) != edge.unsupported_cases:
        raise ValueError("migration fixture unsupported cases do not match matrix edge")
    return raw


def fixture_digest(edge: HistoricalMigrationEdge) -> str:
    raw = load_fixture(edge)
    body = dict(raw)
    body.pop("fixture_digest", None)
    return digest(body)


def materialize_historical_snapshot(kernel, edge: HistoricalMigrationEdge) -> dict[str, Any]:
    fixture = load_fixture(edge)
    state = deepcopy(kernel.snapshot_state())
    state["snapshot_schema"] = edge.source_schema
    for layer_name in fixture.get("drop_layers", ()):
        state.pop(str(layer_name), None)
    kernel.snapshots.save(state)
    return state
