import unittest

from nolane_plan.compiler import FutureSpaceCompiler
from nolane_plan.future import ConvergenceCertificate, FutureFamily, FutureLattice, NULL_WORLD_ID, StrategicState
from nolane_plan.obligations import ObligationLedger, ObligationStatus, StrategicObligation
from nolane_plan.types import InvariantViolation


class FutureObligationTests(unittest.TestCase):
    def test_condition_centric_obligation_survives_principal_loss(self):
        ledger = ObligationLedger()
        ledger.add(StrategicObligation("o1", "verification complete before deploy", deadline=20, required_capability="verify"))
        ledger.principal_unavailable("agent:a")
        self.assertEqual(ledger.get("o1").status, ObligationStatus.OPEN)

    def test_lattice_always_has_null_world(self):
        lattice = FutureLattice()
        self.assertIn(NULL_WORLD_ID, lattice.families)
        self.assertTrue(lattice.families[NULL_WORLD_ID].residual)

    def test_factorized_compiler_is_budget_bounded(self):
        compiler = FutureSpaceCompiler(max_families=3)
        lattice = compiler.compile({"api": ["v1", "v2"], "network": ["up", "down"], "artifact": ["ok", "bad"]})
        non_residual = [f for f in lattice.families.values() if not f.residual]
        self.assertEqual(len(non_residual), 3)
        self.assertIn(NULL_WORLD_ID, lattice.families)

    def test_unsafe_merge_is_rejected(self):
        lattice = FutureLattice()
        lattice.add_state(StrategicState("s1", mission_version=1, obligations=frozenset({"o1"})))
        lattice.add_state(StrategicState("s2", mission_version=1, obligations=frozenset({"o2"})))
        lattice.add_state(StrategicState("target", mission_version=1))
        cert = ConvergenceCertificate(("s1", "s2"), "target", same_mission_version=True, obligations_compatible=False)
        with self.assertRaises(InvariantViolation):
            lattice.merge(cert)

    def test_valid_merge_records_lineage(self):
        lattice = FutureLattice()
        lattice.add_state(StrategicState("s1", mission_version=1))
        lattice.add_state(StrategicState("s2", mission_version=1))
        lattice.add_state(StrategicState("target", mission_version=1))
        cert = ConvergenceCertificate(("s1", "s2"), "target")
        lattice.merge(cert)
        self.assertEqual(lattice.merge_lineage["target"], ("s1", "s2"))


if __name__ == "__main__": unittest.main()
