from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src" / "nolane_plan"
TESTS = ROOT / "tests"


@dataclass(frozen=True)
class Mutation:
    name: str
    path: str
    old: str
    new: str
    test_pattern: str


MUTATIONS = (
    Mutation(
        "nonanticipativity_bypass",
        "policy_information.py",
        "if len(action_semantics) <= 1:\n                continue",
        "if len(action_semantics) >= 1:\n                continue",
        "test_wave5_policy_information.py",
    ),
    Mutation(
        "hard_veto_bypass",
        "selection.py",
        "admitted = {ref for ref, allowed, _ in hard_rows if allowed}",
        "admitted = {ref for ref, allowed, _ in hard_rows}",
        "test_wave5_selection.py",
    ),
    Mutation(
        "selection_freshness_bypass",
        "selection.py",
        "if int(current_generations.get(domain, -1)) != bound:\n                return SelectionStatus.STALE",
        "if False and int(current_generations.get(domain, -1)) != bound:\n                return SelectionStatus.STALE",
        "test_wave5_selection.py",
    ),
    Mutation(
        "recursive_recall_mismatch_bypass",
        "policy_certificates.py",
        "if getattr(row, field) != getattr(baseline, field):\n                        differing.add(field)",
        "if False and getattr(row, field) != getattr(baseline, field):\n                        differing.add(field)",
        "test_wave5_policy_certificates.py",
    ),
    Mutation(
        "totality_missing_successor_bypass",
        "policy_certificates.py",
        "candidates = exact_handlers.get(outcome.outcome_ref, ())\n                valid = False",
        "candidates = exact_handlers.get(outcome.outcome_ref, ())\n                valid = True",
        "test_wave5_policy_certificates.py",
    ),
    Mutation(
        "global_composition_unsat_bypass",
        "seals.py",
        "if not survivors:\n                status = CompositionStatus.NONCOMPOSABLE_CONFLICT",
        "if False and not survivors:\n                status = CompositionStatus.NONCOMPOSABLE_CONFLICT",
        "test_wave5_seals.py",
    ),
    Mutation(
        "reaction_worst_case_bypass",
        "policy_readiness.py",
        "elif worst_timely:\n            controllability = ReactionControllabilityClass.IA2_BOUNDED_GUARANTEED_TIMELY",
        "elif best_timely:\n            controllability = ReactionControllabilityClass.IA2_BOUNDED_GUARANTEED_TIMELY",
        "test_wave5_policy_readiness.py",
    ),
    Mutation(
        "information_capability_loss_bypass",
        "policy_readiness.py",
        "return not destructive or bool(robust_information_independent_continuation)",
        "return True",
        "test_wave5_policy_readiness.py",
    ),
    Mutation(
        "continuation_horizon_bypass",
        "policy_readiness.py",
        "return self.terminal_semantics == TerminalSemantics.MISSION_COMPLETE",
        "return True",
        "test_wave5_policy_readiness.py",
    ),
    Mutation(
        "kernel_executability_gate_bypass",
        "policy_runtime.py",
        "if executability.status not in _BOUNDED_EXECUTABILITY:\n        raise AuthorizationError(\"policy executability is not bounded\")",
        "if False and executability.status not in _BOUNDED_EXECUTABILITY:\n        raise AuthorizationError(\"policy executability is not bounded\")",
        "test_wave5_kernel_policy_authority.py",
    ),
    Mutation(
        "kernel_selection_freshness_bypass",
        "policy_runtime.py",
        "if self._current_selection_status(selection) != SelectionStatus.ADVISORY:\n        raise AuthorizationError(\"selection record is stale or superseded\")",
        "if False and self._current_selection_status(selection) != SelectionStatus.ADVISORY:\n        raise AuthorizationError(\"selection record is stale or superseded\")",
        "test_wave5_kernel_policy_authority.py",
    ),
    Mutation(
        "policy_internal_digest_bypass",
        "policy_codec.py",
        "if actual != recorded:\n        raise ReplayError(f\"{label} canonical digest mismatch\")",
        "if False and actual != recorded:\n        raise ReplayError(f\"{label} canonical digest mismatch\")",
        "test_wave5_replay.py",
    ),
    Mutation(
        "seal_revival_bypass",
        "seal_lifecycle.py",
        "if target not in _ALLOWED_INVALIDATIONS[self.status]:\n        raise ValueError(f\"illegal PlanSeal status transition: {self.status.value} -> {target.value}\")",
        "if False and target not in _ALLOWED_INVALIDATIONS[self.status]:\n        raise ValueError(f\"illegal PlanSeal status transition: {self.status.value} -> {target.value}\")",
        "test_wave5_seals.py",
    ),
)


def _run_one(mutation: Mutation) -> tuple[bool, str]:
    with tempfile.TemporaryDirectory(prefix=f"nolane-wave5-mut-{mutation.name}-") as temp_dir:
        temp = Path(temp_dir)
        package_root = temp / "src" / "nolane_plan"
        shutil.copytree(SOURCE, package_root)
        target = package_root / mutation.path
        original = target.read_text(encoding="utf-8")
        count = original.count(mutation.old)
        if count != 1:
            return False, f"mutation target count={count}, expected 1"
        target.write_text(original.replace(mutation.old, mutation.new, 1), encoding="utf-8")

        env = os.environ.copy()
        env["PYTHONPATH"] = str(temp / "src")
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "unittest",
                "discover",
                "-s",
                str(TESTS),
                "-p",
                mutation.test_pattern,
                "-v",
            ],
            cwd=ROOT,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=120,
        )
        if proc.returncode != 0:
            tail = "\n".join(proc.stdout.splitlines()[-16:])
            return True, tail
        return False, "focused test suite survived mutation"


def main() -> int:
    killed = 0
    for mutation in MUTATIONS:
        caught, detail = _run_one(mutation)
        if caught:
            killed += 1
            print(f"KILLED {mutation.name}")
        else:
            print(f"SURVIVED {mutation.name}: {detail}")
    print(f"WAVE5_MUTATIONS_CAUGHT={killed}/{len(MUTATIONS)}")
    return 0 if killed == len(MUTATIONS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
