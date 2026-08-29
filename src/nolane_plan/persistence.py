from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .hashing import digest
from .types import ReplayError


@dataclass(frozen=True, slots=True)
class JournalEntry:
    sequence: int
    event_type: str
    payload: dict[str, Any]
    previous_hash: str
    entry_hash: str


class HashJournal:
    GENESIS = "0" * 64

    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("", encoding="utf-8")

    def entries(self) -> list[JournalEntry]:
        out: list[JournalEntry] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            raw = json.loads(line)
            out.append(JournalEntry(**raw))
        return out

    @property
    def head(self) -> str:
        rows = self.entries()
        return rows[-1].entry_hash if rows else self.GENESIS

    def append(self, event_type: str, payload: dict[str, Any]) -> JournalEntry:
        rows = self.entries()
        sequence = len(rows) + 1
        previous_hash = rows[-1].entry_hash if rows else self.GENESIS
        body = {"sequence": sequence, "event_type": event_type, "payload": payload, "previous_hash": previous_hash}
        entry = JournalEntry(sequence, event_type, payload, previous_hash, digest(body))
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(entry), sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n")
            f.flush()
            os.fsync(f.fileno())
        return entry

    def verify(self, raise_on_error: bool = False) -> bool:
        try:
            prev = self.GENESIS
            for expected_seq, row in enumerate(self.entries(), start=1):
                if row.sequence != expected_seq or row.previous_hash != prev:
                    raise ReplayError("journal sequence/hash-link mismatch")
                body = {"sequence": row.sequence, "event_type": row.event_type, "payload": row.payload, "previous_hash": row.previous_hash}
                if digest(body) != row.entry_hash:
                    raise ReplayError("journal entry hash mismatch")
                prev = row.entry_hash
            return True
        except Exception as exc:
            if raise_on_error:
                if isinstance(exc, ReplayError):
                    raise
                raise ReplayError(str(exc)) from exc
            return False


class SnapshotStore:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def save(self, state: dict[str, Any]) -> None:
        doc = {"state": state, "digest": digest(state)}
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(doc, sort_keys=True, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, self.path)

    def load(self) -> dict[str, Any]:
        doc = json.loads(self.path.read_text(encoding="utf-8"))
        if digest(doc["state"]) != doc.get("digest"):
            raise ReplayError("snapshot digest mismatch")
        return doc["state"]
