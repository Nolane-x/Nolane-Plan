from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .hashing import digest
from .wave9_registry import WAVE9_CORE_INVARIANT_IDS


WAVE9_COVERAGE_HEADER = "| Wave 9 invariant | State | Implementation evidence | Unit/integration evidence | Chaos/differential/replay evidence | Mutation evidence |"


@dataclass(frozen=True, slots=True)
class Wave9CoverageRow:
    invariant_id: str
    state: str
    implementation_evidence: str
    test_evidence: str
    falsification_evidence: str
    mutation_evidence: str

    def canonical_payload(self) -> dict[str, str]:
        return {
            "invariant_id": self.invariant_id,
            "state": self.state,
            "implementation_evidence": self.implementation_evidence,
            "test_evidence": self.test_evidence,
            "falsification_evidence": self.falsification_evidence,
            "mutation_evidence": self.mutation_evidence,
        }


@dataclass(frozen=True, slots=True)
class Wave9CoverageAudit:
    passed: bool
    failures: tuple[str, ...]
    invariant_states: dict[str, str]
    row_count: int
    green_count: int
    partial_count: int
    orphan_count: int
    evidence_free_green_count: int
    canonical_digest: str


def coverage_ledger_path() -> Path:
    return Path(__file__).resolve().parents[2] / "docs" / "SPEC-COVERAGE.md"


def parse_wave9_coverage_table(text: str) -> tuple[Wave9CoverageRow, ...]:
    lines = text.splitlines()
    header_index = None
    for index, line in enumerate(lines):
        if line.strip() == WAVE9_COVERAGE_HEADER:
            header_index = index
            break
    if header_index is None:
        return ()
    rows: list[Wave9CoverageRow] = []
    for line in lines[header_index + 2 :]:
        stripped = line.strip()
        if not stripped.startswith("|"):
            break
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(cells) != 6:
            raise ValueError(f"malformed Wave-9 coverage row: {line}")
        rows.append(Wave9CoverageRow(*cells))
    return tuple(rows)


def _has_evidence(value: str) -> bool:
    text = str(value).strip()
    return bool(text and text not in {"-", "—", "N/A", "n/a"})


def audit_coverage_text(
    text: str,
    *,
    expected_ids: tuple[str, ...] = WAVE9_CORE_INVARIANT_IDS,
) -> Wave9CoverageAudit:
    failures: list[str] = []
    try:
        rows = parse_wave9_coverage_table(text)
    except ValueError as exc:
        rows = ()
        failures.append(str(exc))
    if not rows:
        failures.append("S01: Wave-9 coverage table is missing or empty")

    by_id: dict[str, Wave9CoverageRow] = {}
    for row in rows:
        key = row.invariant_id.strip().upper()
        if not key:
            failures.append("S01: coverage row has empty invariant id")
            continue
        if key in by_id:
            failures.append(f"S01: duplicate Wave-9 coverage row: {key}")
            continue
        by_id[key] = row

    expected = tuple(str(item).strip().upper() for item in expected_ids)
    expected_set = set(expected)
    missing = [item for item in expected if item not in by_id]
    extras = sorted(key for key in by_id if key not in expected_set)
    for item in missing:
        failures.append(f"S02: missing Wave-9 invariant coverage row: {item}")
    for item in extras:
        failures.append(f"S02: orphan Wave-9 coverage row: {item}")

    green = 0
    partial = 0
    evidence_free_green = 0
    states: dict[str, str] = {}
    for invariant_id in expected:
        row = by_id.get(invariant_id)
        if row is None:
            continue
        state = row.state.strip()
        upper = state.upper()
        states[invariant_id] = state
        if upper.startswith("GREEN"):
            green += 1
            evidence_fields = (
                row.implementation_evidence,
                row.test_evidence,
                row.falsification_evidence,
                row.mutation_evidence,
            )
            if not all(_has_evidence(value) for value in evidence_fields):
                evidence_free_green += 1
                failures.append(f"S03: evidence-free GREEN row: {invariant_id}")
        elif upper.startswith("PARTIAL"):
            partial += 1
            if "—" not in state:
                failures.append(f"S04: PARTIAL row lacks explicit rationale: {invariant_id}")
            failures.append(f"S04: Wave-9 closure row remains PARTIAL: {invariant_id}")
        else:
            failures.append(f"S04: Wave-9 closure row is not GREEN: {invariant_id}={state or '<empty>'}")

    normalized = tuple(sorted(set(failures)))
    canonical = digest({
        "expected_ids": expected,
        "rows": [row.canonical_payload() for row in rows],
        "failures": normalized,
    })
    return Wave9CoverageAudit(
        passed=not normalized,
        failures=normalized,
        invariant_states={key: states[key] for key in expected if key in states},
        row_count=len(rows),
        green_count=green,
        partial_count=partial,
        orphan_count=len(extras) + len(missing),
        evidence_free_green_count=evidence_free_green,
        canonical_digest=canonical,
    )


def audit_repository_coverage() -> Wave9CoverageAudit:
    path = coverage_ledger_path()
    if not path.is_file():
        return Wave9CoverageAudit(
            passed=False,
            failures=(f"S01: coverage ledger not found: {path}",),
            invariant_states={},
            row_count=0,
            green_count=0,
            partial_count=0,
            orphan_count=len(WAVE9_CORE_INVARIANT_IDS),
            evidence_free_green_count=0,
            canonical_digest=digest({"missing": str(path)}),
        )
    return audit_coverage_text(path.read_text(encoding="utf-8"))


def main() -> int:
    audit = audit_repository_coverage()
    print(f"WAVE9_COVERAGE_ROWS={audit.row_count}")
    print(f"WAVE9_COVERAGE_GREEN={audit.green_count}")
    print(f"WAVE9_COVERAGE_PARTIAL={audit.partial_count}")
    print(f"WAVE9_COVERAGE_ORPHANS={audit.orphan_count}")
    print(f"WAVE9_COVERAGE_EVIDENCE_FREE_GREEN={audit.evidence_free_green_count}")
    print(f"WAVE9_COVERAGE_DIGEST={audit.canonical_digest}")
    for failure in audit.failures:
        print(f"WAVE9_COVERAGE_FAILURE={failure}")
    print(f"WAVE9_COVERAGE={'GREEN' if audit.passed else 'RED'}")
    return 0 if audit.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
