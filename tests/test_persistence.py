import json
import tempfile
import unittest
from pathlib import Path

from nolane_plan.persistence import HashJournal, SnapshotStore
from nolane_plan.types import ReplayError


class PersistenceTests(unittest.TestCase):
    def test_hash_chain_round_trip(self):
        with tempfile.TemporaryDirectory() as td:
            j = HashJournal(Path(td) / "journal.jsonl")
            j.append("mission.created", {"version": 1})
            j.append("state.commit", {"canonical_version": 2})
            self.assertTrue(j.verify())
            self.assertEqual(len(j.entries()), 2)

    def test_tamper_is_detected(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "journal.jsonl"
            j = HashJournal(p)
            j.append("x", {"v": 1})
            row = json.loads(p.read_text().strip())
            row["payload"]["v"] = 999
            p.write_text(json.dumps(row) + "\n")
            with self.assertRaises(ReplayError):
                j.verify(raise_on_error=True)

    def test_snapshot_digest_is_verified(self):
        with tempfile.TemporaryDirectory() as td:
            s = SnapshotStore(Path(td) / "snapshot.json")
            s.save({"mission_version": 1, "canonical": {"x": 1}})
            self.assertEqual(s.load()["canonical"]["x"], 1)
            doc = json.loads((Path(td) / "snapshot.json").read_text())
            doc["state"]["canonical"]["x"] = 2
            (Path(td) / "snapshot.json").write_text(json.dumps(doc))
            with self.assertRaises(ReplayError): s.load()


if __name__ == "__main__": unittest.main()
