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


@dataclass(frozen=True)
class Mutation:
    name: str
    path: str
    old: str
    new: str
    test_pattern: str


MUTATIONS = (
    Mutation(
        "capture_assurance_firewall",
        "proof_inputs.py",
        "        if self.capture_assurance == DependencyCaptureAssurance.TRUSTED_DYNAMIC_CAPTURE:\n            return bool(self.capture_mechanism_ref) and self.external_read_policy == ExternalReadPolicy.CAPTURE_REQUIRED\n        return False",
        "        if self.capture_assurance == DependencyCaptureAssurance.TRUSTED_DYNAMIC_CAPTURE:\n            return bool(self.capture_mechanism_ref) and self.external_read_policy == ExternalReadPolicy.CAPTURE_REQUIRED\n        return True  # mutation: self-report/opaque capture becomes strong",
        "test_wave4_proof_inputs.py",
    ),
    Mutation(
        "query_revision_freshness",
        "query_domain.py",
        "        return latest.canonical_digest == bound_revision.canonical_digest",
        "        return True  # mutation: historical query revision never stales",
        "test_wave4_query_domain.py",
    ),
    Mutation(
        "independent_grounding_floor",
        "support.py",
        "            if len(clause_roots) < clause.minimum_independent_roots:\n                continue",
        "            if False and len(clause_roots) < clause.minimum_independent_roots:\n                continue",
        "test_wave4_support.py",
    ),
    Mutation(
        "blocking_invalidity_authority",
        "support.py",
        "            and not any(cause.active and cause.blocking for cause in self.invalidity_causes)",
        "            and True  # mutation: blocking invalidity ignored",
        "test_wave4_support.py",
    ),
    Mutation(
        "semantic_freshness_barrier",
        "semantic_barrier.py",
        "            return vector.current(self.freshness)",
        "            return True  # mutation: cached/stale artifact always current",
        "test_wave4_semantic_barrier.py",
    ),
    Mutation(
        "kernel_manifest_reuse_gate",
        "proof_runtime.py",
        "        if not manifest.strong_reuse_eligible(\n            freshness=self.freshness,\n            exact_current_revisions=self.proof_exact_revisions,\n            query_domains=self.query_domains,\n            current_trust_profile_refs=self.proof_profile_refs,\n            minimum_query_assurance=minimum_query_assurance,\n        ):\n            raise AuthorizationError(\"proof dependency/capture authority is stale or incomplete\")",
        "        if False and not manifest.strong_reuse_eligible(\n            freshness=self.freshness,\n            exact_current_revisions=self.proof_exact_revisions,\n            query_domains=self.query_domains,\n            current_trust_profile_refs=self.proof_profile_refs,\n            minimum_query_assurance=minimum_query_assurance,\n        ):\n            raise AuthorizationError(\"proof dependency/capture authority is stale or incomplete\")",
        "test_wave4_kernel_proof_authority.py",
    ),
    Mutation(
        "replay_manifest_integrity",
        "proof_recovery.py",
        "    if digest(body) != recorded:\n        raise ReplayError(\"proof dependency manifest canonical digest mismatch\")",
        "    if False and digest(body) != recorded:\n        raise ReplayError(\"proof dependency manifest canonical digest mismatch\")",
        "test_wave4_replay.py",
    ),
)


def _mutate(source_root: Path, mutation: Mutation) -> None:
    path = source_root / mutation.path
    text = path.read_text(encoding="utf-8")
    count = text.count(mutation.old)
    if count != 1:
        raise RuntimeError(f"{mutation.name}: expected exactly one mutation site, found {count}")
    path.write_text(text.replace(mutation.old, mutation.new, 1), encoding="utf-8")


def _run_mutant(mutation: Mutation) -> tuple[bool, str]:
    with tempfile.TemporaryDirectory(prefix=f"nolane-plan-wave4-{mutation.name}-") as td:
        mutant_root = Path(td)
        package_root = mutant_root / "nolane_plan"
        shutil.copytree(SOURCE, package_root)
        _mutate(package_root, mutation)
        env = dict(os.environ)
        env["PYTHONPATH"] = str(mutant_root)
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "unittest",
                "discover",
                "-s",
                "tests",
                "-p",
                mutation.test_pattern,
                "-v",
            ],
            cwd=ROOT,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=90,
            check=False,
        )
        return proc.returncode != 0, proc.stdout


def main() -> int:
    killed_count = 0
    for mutation in MUTATIONS:
        killed, output = _run_mutant(mutation)
        if killed:
            killed_count += 1
            print(f"KILLED {mutation.name}")
            continue
        print(f"SURVIVED {mutation.name}")
        print(output)
    print(f"WAVE4_MUTATIONS_CAUGHT={killed_count}/{len(MUTATIONS)}")
    return 0 if killed_count == len(MUTATIONS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
