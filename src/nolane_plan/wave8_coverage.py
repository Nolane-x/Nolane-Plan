from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from .hashing import digest
from .wave8_registry import WAVE8_INVARIANTS, Wave8Layer


FINAL_WAVE7_RELEASE_SHA = "78e44da066bd362a2ee935c06ad5902bb0872238"
FINAL_WAVE7_CI_RUN = "33350465557"

RESEARCH_SURFACES = frozenset({
    "Real benchmark worlds / empirical superiority",
})
BOUNDARY_SURFACES = frozenset({
    "Distributed correctness writers / consensus",
    "Generic identity provider",
    "Generic scheduler/orchestrator product",
    "Generic messaging/task marketplace/orchestration platform",
    "Production physical history deletion/general storage-engine compaction",
})


@dataclass(frozen=True, slots=True)
class CoverageRow:
    surface: str
    state: str
    closure_wave: str

    def canonical_payload(self) -> dict[str, str]:
        return {
            "surface": self.surface,
            "state": self.state,
            "closure_wave": self.closure_wave,
        }


@dataclass(frozen=True, slots=True)
class CoverageAudit:
    passed: bool
    failures: tuple[str, ...]
    row_count: int
    in_scope_row_count: int
    research_row_count: int
    boundary_row_count: int
    invariant_surface_states: dict[str, str]
    canonical_digest: str


def coverage_ledger_path() -> Path:
    return Path(__file__).resolve().parents[2] / "docs" / "SPEC-COVERAGE.md"


def parse_coverage_table(text: str) -> tuple[CoverageRow, ...]:
    lines = text.splitlines()
    header_index = None
    for index, line in enumerate(lines):
        if line.strip() == "| Spec surface | Current state | Closure wave |":
            header_index = index
            break
    if header_index is None:
        return ()

    rows: list[CoverageRow] = []
    for line in lines[header_index + 2 :]:
        stripped = line.strip()
        if not stripped.startswith("|"):
            break
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(cells) != 3:
            raise ValueError(f"malformed coverage row: {line}")
        surface, state, closure_wave = cells
        if not surface or not state or not closure_wave:
            raise ValueError(f"coverage row has empty field: {line}")
        rows.append(CoverageRow(surface, state, closure_wave))
    return tuple(rows)


def _is_research(row: CoverageRow) -> bool:
    return row.surface in RESEARCH_SURFACES or "RESEARCH" in row.state.upper()


def _is_boundary(row: CoverageRow) -> bool:
    return row.surface in BOUNDARY_SURFACES or "BOUNDARY" in row.state.upper()


def _has_named_engineering_evidence(row: CoverageRow) -> bool:
    return bool(re.search(r"\b(?:existing|W[2-8])\b", row.closure_wave, re.IGNORECASE))


def audit_coverage_text(text: str) -> CoverageAudit:
    failures: list[str] = []
    try:
        rows = parse_coverage_table(text)
    except ValueError as exc:
        rows = ()
        failures.append(str(exc))

    if not rows:
        failures.append("S01: coverage ledger table is missing or empty")

    by_surface: dict[str, CoverageRow] = {}
    for row in rows:
        if row.surface in by_surface:
            failures.append(f"S01: duplicate coverage surface: {row.surface}")
        else:
            by_surface[row.surface] = row

    invariant_surface_states: dict[str, str] = {}
    for invariant in WAVE8_INVARIANTS:
        for surface in invariant.spec_surface_refs:
            row = by_surface.get(surface)
            if row is None:
                failures.append(f"S02: {invariant.invariant_id} has orphan ledger surface: {surface}")
                continue
            invariant_surface_states[surface] = row.state
            if invariant.layer is not Wave8Layer.COVERAGE and (_is_research(row) or _is_boundary(row)):
                failures.append(
                    f"S02: correctness invariant {invariant.invariant_id} maps to non-correctness state {row.state}: {surface}"
                )

    in_scope = 0
    research = 0
    boundary = 0
    for row in rows:
        upper = row.state.upper()
        if _is_research(row):
            research += 1
        elif _is_boundary(row):
            boundary += 1
        else:
            in_scope += 1
            if "MISSING" in upper:
                failures.append(f"S01: in-scope row is MISSING: {row.surface}")
            if not _has_named_engineering_evidence(row):
                failures.append(f"S01/S03: in-scope row lacks named existing/Wave evidence: {row.surface}")

        if "PARTIAL" in upper and "—" not in row.state:
            failures.append(f"S04: PARTIAL row lacks explicit bounded rationale: {row.surface}")

        if row.surface in RESEARCH_SURFACES:
            if "RESEARCH" not in upper or "GREEN" in upper:
                failures.append(f"S05: research measurement promoted to correctness: {row.surface}")

        if row.surface in BOUNDARY_SURFACES:
            if "BOUNDARY" not in upper or "GREEN" in upper:
                failures.append(f"S06: product boundary promoted into bounded correctness claim: {row.surface}")

    if FINAL_WAVE7_RELEASE_SHA not in text:
        failures.append("S07: final Wave-7 release SHA missing from ledger")
    if FINAL_WAVE7_CI_RUN not in text:
        failures.append("S07: final Wave-7 main CI run missing from ledger")
    if "release verification in progress" in text.lower():
        failures.append("S07: stale release-verification-in-progress claim remains")

    ordered_states = {
        surface: row.state
        for surface, row in sorted(by_surface.items(), key=lambda item: item[0])
    }
    normalized_failures = tuple(sorted(set(failures)))
    canonical = digest(
        {
            "rows": [row.canonical_payload() for row in rows],
            "invariant_surface_states": ordered_states,
            "failures": normalized_failures,
            "wave7_release_sha": FINAL_WAVE7_RELEASE_SHA,
            "wave7_final_main_ci": FINAL_WAVE7_CI_RUN,
        }
    )
    return CoverageAudit(
        passed=not normalized_failures,
        failures=normalized_failures,
        row_count=len(rows),
        in_scope_row_count=in_scope,
        research_row_count=research,
        boundary_row_count=boundary,
        invariant_surface_states=ordered_states,
        canonical_digest=canonical,
    )


def audit_repository_coverage() -> CoverageAudit:
    path = coverage_ledger_path()
    if not path.is_file():
        return CoverageAudit(
            passed=False,
            failures=(f"S01: coverage ledger not found: {path}",),
            row_count=0,
            in_scope_row_count=0,
            research_row_count=0,
            boundary_row_count=0,
            invariant_surface_states={},
            canonical_digest=digest({"missing": str(path)}),
        )
    return audit_coverage_text(path.read_text(encoding="utf-8"))


def main() -> int:
    audit = audit_repository_coverage()
    print(f"WAVE8_COVERAGE_ROWS={audit.row_count}")
    print(f"WAVE8_COVERAGE_IN_SCOPE={audit.in_scope_row_count}")
    print(f"WAVE8_COVERAGE_RESEARCH={audit.research_row_count}")
    print(f"WAVE8_COVERAGE_BOUNDARY={audit.boundary_row_count}")
    print(f"WAVE8_COVERAGE_DIGEST={audit.canonical_digest}")
    for failure in audit.failures:
        print(f"WAVE8_COVERAGE_FAILURE={failure}")
    print(f"WAVE8_COVERAGE={'GREEN' if audit.passed else 'RED'}")
    return 0 if audit.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
