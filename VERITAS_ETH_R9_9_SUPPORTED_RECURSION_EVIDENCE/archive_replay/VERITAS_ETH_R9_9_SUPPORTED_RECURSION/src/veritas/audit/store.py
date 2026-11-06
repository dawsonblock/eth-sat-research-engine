"""Locally hash-chained SQLite audit journal. Hashes detect accidental edits,
not malicious database rewrites by someone controlling the host; use external
signatures and immutable storage when a stronger integrity guarantee is needed.
"""
from __future__ import annotations
from hashlib import sha256
from pathlib import Path
from threading import Lock
import json
import os
import sqlite3
import time


def canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def digest(value) -> str:
    return sha256(canonical(value)).hexdigest()


class AuditStore:
    def __init__(self, path: str | Path | None = None):
        self.path = str(path or os.environ.get("VERITAS_AUDIT_DB", ".veritas/audit.sqlite3"))
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self.lock = Lock()
        with sqlite3.connect(self.path) as db:
            db.execute("CREATE TABLE IF NOT EXISTS entries (seq INTEGER PRIMARY KEY AUTOINCREMENT, hash TEXT UNIQUE NOT NULL, previous TEXT NOT NULL, payload TEXT NOT NULL, created_unix REAL NOT NULL)")

    def add(self, payload: dict) -> str:
        with self.lock, sqlite3.connect(self.path) as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT hash FROM entries ORDER BY seq DESC LIMIT 1").fetchone()
            prev = row[0] if row else "GENESIS"
            h = digest({"previous": prev, "payload": payload})
            db.execute("INSERT INTO entries(hash,previous,payload,created_unix) VALUES(?,?,?,?)", (h, prev, canonical(payload).decode(), time.time()))
            return h

    def get(self, h: str) -> dict | None:
        with sqlite3.connect(self.path) as db:
            row = db.execute("SELECT seq,hash,previous,payload,created_unix FROM entries WHERE hash=?", (h,)).fetchone()
        if row is None: return None
        seq, got, previous, payload, created = row
        obj = json.loads(payload)
        return {"sequence": seq, "audit_sha256": got, "previous": previous,
                "payload": obj, "created_unix": created,
                "entry_valid": got == digest({"previous": previous, "payload": obj})}

    def verify_chain(self) -> tuple[bool, int]:
        with sqlite3.connect(self.path) as db:
            rows = db.execute("SELECT hash,previous,payload FROM entries ORDER BY seq").fetchall()
        prev = "GENESIS"
        for h, earlier, raw in rows:
            if earlier != prev or h != digest({"previous": earlier, "payload": json.loads(raw)}):
                return False, len(rows)
            prev = h
        return True, len(rows)
