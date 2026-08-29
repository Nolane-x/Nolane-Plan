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
        "identity_non_retroactivity",
        "identity.py",
        '        if now < binding.created_at:\n            raise IdentityError("principal binding was not yet established at this decision boundary")',
        '        if False and now < binding.created_at:\n            raise IdentityError("principal binding was not yet established at this decision boundary")',
        "test_wave3_identity_history.py",
    ),
    Mutation(
        "observed_only_knowledge",
        "communication.py",
        '        if receipt.state != CommunicationState.OBSERVED or receipt.observed_at is None:\n            return False',
        '        if receipt.state == CommunicationState.SENT:\n            return False\n        if receipt.observed_at is None:\n            return True',
        "test_wave3_communication.py",
    ),
    Mutation(
        "authorization_binding_continuity",
        "trust_runtime.py",
        '        if binding.binding_id != authorized_binding_id:\n            raise AuthorizationError("principal identity changed after authorization; re-authorization required")',
        '        if False and binding.binding_id != authorized_binding_id:\n            raise AuthorizationError("principal identity changed after authorization; re-authorization required")',
        "test_wave3_kernel_trust.py",
    ),
    Mutation(
        "execution_evidence_snapshot_durability",
        "trust_recovery.py",
        "        kernel.dispatch_attestations[value.authorization_id] = value",
        "        pass  # mutation: drop dispatch attestation during restore",
        "test_wave3_replay.py",
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
    with tempfile.TemporaryDirectory(prefix=f"nolane-plan-{mutation.name}-") as td:
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
            timeout=60,
            check=False,
        )
        killed = proc.returncode != 0
        return killed, proc.stdout


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
    print(f"WAVE3_MUTATIONS_CAUGHT={killed_count}/{len(MUTATIONS)}")
    return 0 if killed_count == len(MUTATIONS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
