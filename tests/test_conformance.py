import unittest

from nolane_plan.conformance import run_principal_scope_oracle, verify_acceptance_surface
from nolane_plan.failure_registry import PRINCIPAL_SCOPE_FAILURES


class ConformanceTests(unittest.TestCase):
    def test_principal_scope_oracle_reproduces_108_to_zero(self):
        result = run_principal_scope_oracle()
        self.assertEqual(result["principal_count"], 4)
        self.assertEqual(result["information_decisions"], 128)
        self.assertEqual(result["authorization_decisions"], 16)
        self.assertEqual(result["v014_information_collision_pairs"], 96)
        self.assertEqual(result["v014_authorization_collision_pairs"], 12)
        self.assertEqual(result["v014_total_collision_pairs"], 108)
        self.assertEqual(result["v015_challenger_collision_pairs"], 0)

    def test_pg_registry_is_complete_and_unique(self):
        self.assertEqual(len(PRINCIPAL_SCOPE_FAILURES), 40)
        self.assertEqual(set(PRINCIPAL_SCOPE_FAILURES), {f"PG{i:02d}" for i in range(1, 41)})

    def test_acceptance_surface_passes(self):
        report = verify_acceptance_surface()
        self.assertTrue(report["ok"])
        self.assertEqual(report["failed"], [])


if __name__ == "__main__": unittest.main()
