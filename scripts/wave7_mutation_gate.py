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
    replacements: tuple[tuple[str, str], ...]
    test_pattern: str


def _one(name: str, path: str, old: str, new: str, test_pattern: str) -> Mutation:
    return Mutation(name, path, ((old, new),), test_pattern)


MUTATIONS = (
    _one(
        "revision_rebind_bypass",
        "lineage.py",
        'if existing != revision:\n                raise LineageError("revision_id cannot be rebound to different lineage content")',
        'if False and existing != revision:\n                raise LineageError("revision_id cannot be rebound to different lineage content")',
        "test_wave7_lineage.py",
    ),
    Mutation(
        "parent_cycle_bypass",
        "lineage.py",
        (
            (
                'if revision in parents:\n            raise LineageError("revision cannot be its own parent")',
                'if False and revision in parents:\n            raise LineageError("revision cannot be its own parent")',
            ),
            (
                'if parent not in self._revisions:\n                    raise LineageError(f"unknown parent lineage revision: {parent}")',
                'if parent not in self._revisions and parent != revision.revision_id:\n                    raise LineageError(f"unknown parent lineage revision: {parent}")',
            ),
            (
                'for parent in revision.parent_revision_ids:\n            if parent == revision.revision_id:\n                raise LineageError("lineage parent cycle detected")',
                'for parent in revision.parent_revision_ids:\n            if False and parent == revision.revision_id:\n                raise LineageError("lineage parent cycle detected")',
            ),
        ),
        "test_wave7_lineage.py",
    ),
    _one(
        "semantic_regime_freshness_bypass",
        "lineage_runtime.py",
        'if dict(binding.regime_revisions) != current_regimes:\n        raise AuthorizationError("authorization semantic-regime lineage is stale")',
        'if False and dict(binding.regime_revisions) != current_regimes:\n        raise AuthorizationError("authorization semantic-regime lineage is stale")',
        "test_wave7_kernel_lineage.py",
    ),
    _one(
        "logical_only_authority_binding",
        "lineage_runtime.py",
        "action_revision_id=action_lineage.revision_id,",
        "action_revision_id=authorization.action_id,",
        "test_wave7_conformance.py",
    ),
    _one(
        "migration_silent_default_bypass",
        "migration.py",
        "if set(disposition_by_key) != set(changed_fields):",
        "if False and set(disposition_by_key) != set(changed_fields):",
        "test_wave7_migration.py",
    ),
    _one(
        "migration_debt_drop_bypass",
        "migration.py",
        "if row.debt_ref not in debts:\n                    raise MigrationError(f\"migration debt {row.debt_ref!r} is not declared in new_debt_refs\")",
        "if False and row.debt_ref not in debts:\n                    raise MigrationError(f\"migration debt {row.debt_ref!r} is not declared in new_debt_refs\")",
        "test_wave7_migration.py",
    ),
    _one(
        "ambiguous_action_migration_bypass",
        "migration_runtime.py",
        "if not ambiguous_transaction_ids:\n        return",
        "if not ambiguous_transaction_ids or bridge is None:\n        return",
        "test_wave7_migration.py",
    ),
    _one(
        "migration_authority_recheck_bypass",
        "migration_runtime.py",
        "self.migration_recheck_required_authorizations.update(invalidated)",
        "self.migration_recheck_required_authorizations.difference_update(invalidated)",
        "test_wave7_migration.py",
    ),
    _one(
        "replay_unknown_event_bypass",
        "replay_registry.py",
        "if correctness_significant:\n                raise ReplayError(f\"unregistered correctness-significant replay event: {event_type}\")",
        "if False and correctness_significant:\n                raise ReplayError(f\"unregistered correctness-significant replay event: {event_type}\")",
        "test_wave7_replay_registry.py",
    ),
    _one(
        "replay_semantic_freshness_drop",
        "lineage_recovery.py",
        'kernel.freshness.generations = {\n        str(key): int(value) for key, value in dict(meta["freshness_generations"]).items()\n    }',
        "kernel.freshness.generations = {}",
        "test_wave7_base_replay.py",
    ),
    _one(
        "compaction_active_lineage_drop",
        "compaction_runtime.py",
        "active_authority_revision_ids=_authority_lineage_refs(self),",
        "active_authority_revision_ids=(),",
        "test_wave7_compaction.py",
    ),
    Mutation(
        "compaction_authority_equivalence_break",
        "compaction.py",
        (
            (
                'if body["source_canonical_semantic_digest"] != body["target_canonical_semantic_digest"]:\n            raise CompactionError("representation compaction changed canonical semantic digest")',
                'if False and body["source_canonical_semantic_digest"] != body["target_canonical_semantic_digest"]:\n            raise CompactionError("representation compaction changed canonical semantic digest")',
            ),
        ),
        "test_wave7_compaction.py",
    ),
)


def _run_one(mutation: Mutation) -> tuple[bool, str]:
    with tempfile.TemporaryDirectory(prefix=f"nolane-wave7-mut-{mutation.name}-") as temp_dir:
        temp = Path(temp_dir)
        package_root = temp / "src" / "nolane_plan"
        shutil.copytree(SOURCE, package_root)
        target = package_root / mutation.path
        mutated = target.read_text(encoding="utf-8")
        for old, new in mutation.replacements:
            count = mutated.count(old)
            if count != 1:
                return False, f"mutation target count={count}, expected 1 in {mutation.path}"
            mutated = mutated.replace(old, new, 1)

        if mutation.name == "compaction_authority_equivalence_break":
            runtime = package_root / "compaction_runtime.py"
            runtime_text = runtime.read_text(encoding="utf-8")
            old = "target_canonical = canonical_semantic_digest(self)"
            new = 'target_canonical = digest({"mutant": "changed-canonical-authority"})'
            if runtime_text.count(old) != 1:
                return False, "compaction authority-equivalence runtime target is not unique"
            runtime.write_text(runtime_text.replace(old, new, 1), encoding="utf-8")

        target.write_text(mutated, encoding="utf-8")

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
    print(f"WAVE7_MUTATIONS_CAUGHT={killed}/{len(MUTATIONS)}")
    return 0 if killed == len(MUTATIONS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
