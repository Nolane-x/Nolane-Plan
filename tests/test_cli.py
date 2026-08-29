import json
import subprocess
import sys
import tempfile
import unittest


class CliTests(unittest.TestCase):
    def test_conformance_command(self):
        proc = subprocess.run([sys.executable, "-m", "nolane_plan", "conformance"], text=True, capture_output=True, env={**__import__('os').environ, "PYTHONPATH": "src"})
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["oracle"]["v014_total_collision_pairs"], 108)

    def test_demo_command_runs_end_to_end(self):
        with tempfile.TemporaryDirectory() as td:
            proc = subprocess.run([sys.executable, "-m", "nolane_plan", "demo", "--root", td], text=True, capture_output=True, env={**__import__('os').environ, "PYTHONPATH": "src"})
            self.assertEqual(proc.returncode, 0, proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertTrue(payload["canonical_state"]["deployed"])
            self.assertTrue(payload["journal_valid"])


if __name__ == "__main__": unittest.main()
