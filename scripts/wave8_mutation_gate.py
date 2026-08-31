from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src" / "nolane_plan"


class ProbeOutcome(str, Enum):
    KILLED = "KILLED"
    SURVIVED = "SURVIVED"
    INVALID = "INVALID"


@dataclass(frozen=True, slots=True)
class Mutation:
    mutant_id: str
    name: str
    path: str
    replacements: tuple[tuple[str, str], ...]
    target_invariant_id: str
    probe_kind: str


def _one(mutant_id: str, name: str, path: str, old: str, new: str, target: str, probe_kind: str) -> Mutation:
    return Mutation(mutant_id, name, path, ((old, new),), target, probe_kind)


MUTATIONS = (
    _one(
        "X01", "principal_anti_escalation_bypass", "principals.py",
        '        if not item.tags.issubset(profile.allowed_tags):\n            return False',
        '        if False and not item.tags.issubset(profile.allowed_tags):\n            return False',
        "P02", "property",
    ),
    _one(
        "X02", "blocker_monotonicity_bypass", "support.py",
        '            and not any(cause.active and cause.blocking for cause in self.invalidity_causes)',
        '            and True',
        "P03", "property",
    ),
    _one(
        "X03", "hard_veto_resurrection", "selector.py",
        '    eligible = [s for s in scores if not s.hard_veto]',
        '    eligible = list(scores)',
        "P05", "property",
    ),
    _one(
        "X04", "resource_capacity_monotonicity_inversion", "schedulability.py",
        '            if required_service > available_service + 1e-12:\n                reasons.append("service_demand_exceeds_bound")',
        '            if required_service < available_service + 1e-12:\n                reasons.append("service_demand_exceeds_bound")',
        "P06", "property",
    ),
    _one(
        "X05", "temporal_information_deadline_optimism", "handoff_liveness.py",
        '        elif not information_available_by_deadline:\n            status = HandoffProgressStatus.UNKNOWN\n            blockers.append("information_not_available_by_deadline")',
        '        elif False and not information_available_by_deadline:\n            status = HandoffProgressStatus.UNKNOWN\n            blockers.append("information_not_available_by_deadline")',
        "P07", "property",
    ),
    _one(
        "X06", "replay_equivalence_suffix_drop", "lineage_recovery.py",
        '            objective=str(doc["objective"]),',
        '            objective=kernel.mission.current.objective,',
        "D02", "differential",
    ),
    _one(
        "X07", "unknown_event_fail_open", "replay_registry.py",
        '            if correctness_significant:\n                raise ReplayError(f"unregistered correctness-significant replay event: {event_type}")',
        '            if False and correctness_significant:\n                raise ReplayError(f"unregistered correctness-significant replay event: {event_type}")',
        "C03", "chaos",
    ),
    _one(
        "X08", "migration_authority_resurrection", "migration_runtime.py",
        '        self.migration_recheck_required_authorizations.update(invalidated)',
        '        self.migration_recheck_required_authorizations.difference_update(invalidated)',
        "C07", "chaos",
    ),
    _one(
        "X09", "compaction_semantic_equivalence_break", "compaction_runtime.py",
        '        target_canonical = canonical_semantic_digest(self)',
        '        target_canonical = digest({"wave8-mutant": "changed-canonical-semantics"})',
        "M10", "metamorphic",
    ),
    _one(
        "X10", "post_dispatch_cancellation_falsely_clean", "cancellation_runtime.py",
        '        elif source_state == TransactionState.DISPATCH_RECORDED:\n            result = self.transactions.request_cancellation_after_dispatch(tx.id, detail)',
        '        elif source_state == TransactionState.DISPATCH_RECORDED:\n            result = self.transactions._set(tx.id, state=TransactionState.CANCELLED_PRE_DISPATCH, detail=str(detail).strip())',
        "C10", "chaos",
    ),
    _one(
        "X11", "relocation_ambiguity_collapsed", "relocation.py",
        '        status = LocationStatus.LOCATED if len(signatures) == 1 else LocationStatus.AMBIGUOUS',
        '        status = LocationStatus.LOCATED',
        "D10", "differential",
    ),
    _one(
        "X12", "pairwise_only_global_composition", "seals.py",
        '            intersection = set.intersection(*world_sets)',
        '            intersection = (world_sets[0].intersection(world_sets[1]) if len(world_sets) > 1 else set(world_sets[0]))',
        "X12", "composition",
    ),
)


def classify_probe_result(returncode: int, output: str, target_invariant_id: str) -> ProbeOutcome:
    target = str(target_invariant_id).strip().upper()
    reached = f"TARGET_ASSERTION_REACHED:{target}" in output
    failed = f"TARGET_ASSERTION_FAILED:{target}" in output
    passed = f"TARGET_ASSERTION_PASSED:{target}" in output
    if reached and failed and not passed and returncode != 0:
        return ProbeOutcome.KILLED
    if reached and passed and not failed and returncode == 0:
        return ProbeOutcome.SURVIVED
    return ProbeOutcome.INVALID


def _probe_target(target: str, probe_kind: str) -> int:
    target = str(target).strip().upper()
    print(f"TARGET_ASSERTION_REACHED:{target}")
    try:
        if probe_kind == "property":
            from nolane_plan.wave8_properties import run_wave8_property
            failures = run_wave8_property(target, range(4))
        elif probe_kind == "metamorphic":
            from nolane_plan.wave8_metamorphic import run_wave8_metamorphic_relation
            failures = run_wave8_metamorphic_relation(target, range(4))
        elif probe_kind == "chaos":
            from nolane_plan.wave8_chaos import run_wave8_chaos_invariant
            failures = run_wave8_chaos_invariant(target, range(4))
        elif probe_kind == "differential":
            from nolane_plan.wave8_differential import run_wave8_differential_invariant
            failures = run_wave8_differential_invariant(target, range(4))
        elif probe_kind == "composition":
            from nolane_plan.seals import ArtifactAssurance, CompositionStatus, ProofContextComponent, SealCompiler

            def context(ref: str, worlds: tuple[str, ...]) -> ProofContextComponent:
                return ProofContextComponent.create(
                    component_ref=ref,
                    assurance=ArtifactAssurance.CHECKED,
                    assumptions=(),
                    scope="mission",
                    guarantee="G2",
                    debt_refs=(),
                    risk_refs=(),
                    authority_refs=(),
                    resource_refs=(),
                    external_regime_refs=(),
                    validity_horizon=(0, 100),
                    constraint_theory="finite-world-set",
                    allowed_worlds=worlds,
                )

            rows = (
                context("ctx:a", ("w1", "w2")),
                context("ctx:b", ("w2", "w3")),
                context("ctx:c", ("w1", "w3")),
            )
            result = SealCompiler.compose_contexts(rows, accepted_debt_refs=())
            failures = () if (
                result.status is CompositionStatus.NONCOMPOSABLE_CONFLICT
                and result.surviving_worlds == ()
            ) else (f"status={result.status.value} survivors={result.surviving_worlds!r}",)
        else:
            print(f"TARGET_ASSERTION_ERROR:{target}:unknown_probe_kind:{probe_kind}")
            return 2
    except Exception as exc:
        print(f"TARGET_ASSERTION_ERROR:{target}:{type(exc).__name__}:{exc}")
        return 2

    if failures:
        print(f"TARGET_ASSERTION_FAILED:{target}")
        print(f"TARGET_COUNTEREXAMPLE:{failures[0]}")
        return 1
    print(f"TARGET_ASSERTION_PASSED:{target}")
    return 0


def run_mutation(mutation: Mutation) -> tuple[ProbeOutcome, str]:
    with tempfile.TemporaryDirectory(prefix=f"nolane-wave8-mut-{mutation.mutant_id.lower()}-") as temp_dir:
        temp = Path(temp_dir)
        package_root = temp / "src" / "nolane_plan"
        shutil.copytree(SOURCE, package_root)
        target = package_root / mutation.path
        mutated = target.read_text(encoding="utf-8")
        for old, new in mutation.replacements:
            count = mutated.count(old)
            if count != 1:
                return ProbeOutcome.INVALID, f"mutation target count={count}, expected 1 in {mutation.path}"
            mutated = mutated.replace(old, new, 1)
        target.write_text(mutated, encoding="utf-8")

        env = os.environ.copy()
        env["PYTHONPATH"] = str(temp / "src")
        try:
            proc = subprocess.run(
                [sys.executable, str(Path(__file__).resolve()), "--probe", mutation.target_invariant_id, mutation.probe_kind],
                cwd=ROOT,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=120,
            )
        except subprocess.TimeoutExpired as exc:
            return ProbeOutcome.INVALID, f"timeout: {exc}"
        outcome = classify_probe_result(proc.returncode, proc.stdout, mutation.target_invariant_id)
        return outcome, proc.stdout


def _find_mutation(mutant_id: str) -> Mutation:
    key = str(mutant_id).strip().upper()
    for mutation in MUTATIONS:
        if mutation.mutant_id == key:
            return mutation
    raise ValueError(f"unknown Wave-8 mutant: {mutant_id}")


def main() -> int:
    if len(sys.argv) >= 2 and sys.argv[1] == "--probe":
        if len(sys.argv) != 4:
            print("probe usage: --probe TARGET PROBE_KIND")
            return 2
        return _probe_target(sys.argv[2], sys.argv[3])

    killed = 0
    invalid = 0
    for mutation in MUTATIONS:
        outcome, detail = run_mutation(mutation)
        if outcome is ProbeOutcome.KILLED:
            killed += 1
            print(f"KILLED {mutation.mutant_id} {mutation.name} target={mutation.target_invariant_id}")
        elif outcome is ProbeOutcome.SURVIVED:
            print(f"SURVIVED {mutation.mutant_id} {mutation.name} target={mutation.target_invariant_id}")
        else:
            invalid += 1
            tail = "\n".join(detail.splitlines()[-8:])
            print(f"INVALID {mutation.mutant_id} {mutation.name} target={mutation.target_invariant_id}: {tail}")
    print(f"WAVE8_MUTATIONS_CAUGHT={killed}/{len(MUTATIONS)}")
    print(f"WAVE8_MUTATIONS_INVALID={invalid}")
    return 0 if killed == len(MUTATIONS) and invalid == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
