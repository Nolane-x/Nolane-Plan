from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "wave8_mutation_gate.py"
EXPECTED_TARGETS = (
    ("X01", "P02"),
    ("X02", "P03"),
    ("X03", "P05"),
    ("X04", "P06"),
    ("X05", "P07"),
    ("X06", "D02"),
    ("X07", "C03"),
    ("X08", "C07"),
    ("X09", "M10"),
    ("X10", "C10"),
    ("X11", "D10"),
    ("X12", "X12"),
)


def load_gate():
    if not SCRIPT.exists():
        raise AssertionError("scripts/wave8_mutation_gate.py is missing")
    spec = importlib.util.spec_from_file_location("wave8_mutation_gate", SCRIPT)
    if spec is None or spec.loader is None:
        raise AssertionError("cannot load Wave-8 mutation gate")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class Wave8MutationGateTests(unittest.TestCase):
    def test_exact_twelve_mutants_have_unique_target_assertions(self) -> None:
        gate = load_gate()
        self.assertEqual(EXPECTED_TARGETS, tuple((row.mutant_id, row.target_invariant_id) for row in gate.MUTATIONS))
        self.assertEqual(12, len({row.mutant_id for row in gate.MUTATIONS}))
        for row in gate.MUTATIONS:
            self.assertTrue(row.replacements)
            self.assertTrue(row.path)
            self.assertTrue(row.probe_kind)

    def test_only_explicit_target_assertion_failure_counts_as_kill(self) -> None:
        gate = load_gate()
        target = "P02"
        self.assertEqual(
            gate.ProbeOutcome.KILLED,
            gate.classify_probe_result(1, f"TARGET_ASSERTION_REACHED:{target}\nTARGET_ASSERTION_FAILED:{target}\n", target),
        )
        self.assertEqual(
            gate.ProbeOutcome.SURVIVED,
            gate.classify_probe_result(0, f"TARGET_ASSERTION_REACHED:{target}\nTARGET_ASSERTION_PASSED:{target}\n", target),
        )
        for returncode, output in (
            (1, "Traceback: import failed"),
            (1, "SyntaxError"),
            (124, "timeout"),
            (1, "TARGET_ASSERTION_FAILED:P03"),
        ):
            with self.subTest(returncode=returncode, output=output):
                self.assertEqual(gate.ProbeOutcome.INVALID, gate.classify_probe_result(returncode, output, target))

    def test_deadline_and_relocation_oracles_kill_their_target_mutants(self) -> None:
        gate = load_gate()
        for mutant_id in ("X05", "X11"):
            with self.subTest(mutant_id=mutant_id):
                mutation = next(row for row in gate.MUTATIONS if row.mutant_id == mutant_id)
                outcome, detail = gate.run_mutation(mutation)
                self.assertEqual(gate.ProbeOutcome.KILLED, outcome, detail)

    def test_principal_and_unknown_event_guards_kill_their_target_mutants(self) -> None:
        gate = load_gate()
        for mutant_id in ("X01", "X07"):
            with self.subTest(mutant_id=mutant_id):
                mutation = next(row for row in gate.MUTATIONS if row.mutant_id == mutant_id)
                outcome, detail = gate.run_mutation(mutation)
                self.assertEqual(gate.ProbeOutcome.KILLED, outcome, detail)


if __name__ == "__main__":
    unittest.main()
