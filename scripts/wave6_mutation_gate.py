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
        "rs1_joint_guarantee_bypass",
        "schedulability.py",
        "return self.level in {\n            ReactionSchedulabilityLevel.RS2_DECLARED_COHORT_FEASIBLE,",
        "return self.level in {\n            ReactionSchedulabilityLevel.RS1_EACH_JOB_INDIVIDUALLY_FEASIBLE,\n            ReactionSchedulabilityLevel.RS2_DECLARED_COHORT_FEASIBLE,",
        "test_wave6_schedulability.py",
    ),
    Mutation(
        "coexistence_bypass",
        "schedulability.py",
        "if not coexistence_known:\n            exclusions = set()\n            debts.add(\"coexistence-unknown\")",
        "if False and not coexistence_known:\n            exclusions = set()\n            debts.add(\"coexistence-unknown\")",
        "test_wave6_schedulability.py",
    ),
    Mutation(
        "resource_regime_freshness_bypass",
        "schedulability.py",
        "return job_rows == self.reaction_job_digests and resource_rows == self.control_resource_digests",
        "return job_rows == self.reaction_job_digests",
        "test_wave6_schedulability.py",
    ),
    Mutation(
        "protected_capacity_bypass",
        "budget.py",
        "planning_capacity = self.total_budget - protected",
        "planning_capacity = self.total_budget",
        "test_wave6_resource_governor.py",
    ),
    Mutation(
        "stutter_budget_bypass",
        "handoff_liveness.py",
        "elif ordinary_stutters < progress_policy.bounded_stutter_allowance:",
        "elif ordinary_stutters <= progress_policy.bounded_stutter_allowance:",
        "test_wave6_handoff_liveness.py",
    ),
    Mutation(
        "deadline_self_extension_bypass",
        "handoff_liveness.py",
        "and authority == new_policy.temporal_authority_ref\n            and authority != old_policy.temporal_authority_ref",
        "and authority == new_policy.temporal_authority_ref\n            and True",
        "test_wave6_handoff_liveness.py",
    ),
    Mutation(
        "equivalent_debt_progress_bypass",
        "handoff_liveness.py",
        "if debt_lineage_equivalent and debt_reduction >= policy.minimum_debt_reduction_rate and debt_reduction > 0:",
        "if debt_reduction >= policy.minimum_debt_reduction_rate and debt_reduction > 0:",
        "test_wave6_conformance.py",
    ),
    Mutation(
        "edge_activation_refresh_bypass",
        "handoff_stability.py",
        "if still_required:\n                status = EdgeActivationStatus.REFRESH_REQUIRED",
        "if False and still_required:\n                status = EdgeActivationStatus.REFRESH_REQUIRED",
        "test_wave6_handoff_stability.py",
    ),
    Mutation(
        "totality_open_world_laundering",
        "policy_coverage.py",
        "def open_world_complete(self) -> bool:\n        return (\n            self.modeled_total",
        "def open_world_complete(self) -> bool:\n        return self.modeled_total or (\n            self.modeled_total",
        "test_wave6_policy_adequacy.py",
    ),
    Mutation(
        "common_mode_independence_bypass",
        "option_independence.py",
        "elif blockers:\n            status = OptionIndependenceStatus.NOMINAL_ONLY",
        "elif False and blockers:\n            status = OptionIndependenceStatus.NOMINAL_ONLY",
        "test_wave6_option_independence.py",
    ),
    Mutation(
        "replay_internal_digest_bypass",
        "schedulability_codec.py",
        "if str(expected) != str(actual):\n        raise ReplayError(f\"{what} canonical digest mismatch\")",
        "if False and str(expected) != str(actual):\n        raise ReplayError(f\"{what} canonical digest mismatch\")",
        "test_wave6_replay.py",
    ),
    Mutation(
        "stale_wave6_restart_resurrection",
        "schedulability_recovery.py",
        "value = kernel.control_plane_resource_revisions.get(str(revision_id))",
        "value = next(iter(kernel.control_plane_resource_revisions.values()), None)",
        "test_wave6_replay.py",
    ),
)


def _run_one(mutation: Mutation) -> tuple[bool, str]:
    with tempfile.TemporaryDirectory(prefix=f"nolane-wave6-mut-{mutation.name}-") as temp_dir:
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
            tail = "\n".join(proc.stdout.splitlines()[-18:])
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
    print(f"WAVE6_MUTATIONS_CAUGHT={killed}/{len(MUTATIONS)}")
    return 0 if killed == len(MUTATIONS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
