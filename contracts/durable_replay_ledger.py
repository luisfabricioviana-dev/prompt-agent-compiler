"""SQLite-backed fail-closed replay ledger (single shared filesystem scope).

Reservation is atomic and durable. DISPATCHING is an uncertainty barrier:
after a crash, never issue the same dispatch again automatically.
No external publisher or distributed deployment guarantee is implied.
"""
from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path


class ReplayAdmissionError(RuntimeError):
    pass


class DurableReplayLedger:
    def __init__(self, database_path: str | Path):
        path = str(database_path)
        if not path or path == ":memory:":
            raise ValueError("durable_database_path_required")
        self.path = path
        with self._connection() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS release_attempts (
                issuer TEXT NOT NULL, nonce TEXT NOT NULL,
                spec_id TEXT NOT NULL, artifact_id TEXT NOT NULL,
                run_id TEXT NOT NULL, artifact_sha256 TEXT NOT NULL,
                state TEXT NOT NULL,
                PRIMARY KEY (issuer, nonce)
            )""")

    def _connection(self):
        db = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        db.execute("PRAGMA busy_timeout=10000")
        db.execute("PRAGMA synchronous=FULL")
        return db

    @staticmethod
    def _identity(statement, payload: bytes):
        from .bound_provenance import BoundProvenanceStatement
        if not isinstance(statement, BoundProvenanceStatement) or not isinstance(payload, bytes):
            raise ReplayAdmissionError("signed_statement_or_payload_invalid")
        digest = hashlib.sha256(payload).hexdigest()
        if digest != statement.artifact_sha256:
            raise ReplayAdmissionError("payload_digest_mismatch")
        values = (statement.issuer, statement.nonce, statement.spec_id,
                  statement.artifact_id, statement.run_id, digest)
        if any(not isinstance(value, str) or not value.strip() for value in values):
            raise ReplayAdmissionError("replay_identity_invalid")
        return values

    def reserve(self, statement, payload: bytes):
        values = self._identity(statement, payload)
        with self._connection() as db:
            try:
                db.execute("BEGIN IMMEDIATE")
                prior = db.execute(
                    "SELECT spec_id, artifact_id, run_id, artifact_sha256, state "
                    "FROM release_attempts WHERE issuer=? AND nonce=?", values[:2]
                ).fetchone()
                if prior is not None:
                    if prior[:4] != values[2:]:
                        raise ReplayAdmissionError("nonce_context_conflict")
                    raise ReplayAdmissionError("nonce_already_reserved:" + prior[4])
                db.execute(
                    "INSERT INTO release_attempts VALUES (?,?,?,?,?,?,?)",
                    (*values, "RESERVED")
                )
                db.commit()
            except BaseException:
                db.rollback()
                raise
        return "RESERVED"

    def transition(self, statement, payload: bytes, *, expected: str, target: str):
        valid = {
            ("RESERVED", "DISPATCHING"),
            ("DISPATCHING", "DISPATCHED"),
            ("DISPATCHING", "UNCERTAIN"),
            ("DISPATCHED", "CONFIRMED"),
            ("DISPATCHED", "UNCERTAIN"),
            ("UNCERTAIN", "CONFIRMED"),
        }
        if (expected, target) not in valid:
            raise ReplayAdmissionError("replay_transition_not_allowed")
        values = self._identity(statement, payload)
        with self._connection() as db:
            try:
                db.execute("BEGIN IMMEDIATE")
                changed = db.execute(
                    "UPDATE release_attempts SET state=? "
                    "WHERE issuer=? AND nonce=? AND spec_id=? AND artifact_id=? "
                    "AND run_id=? AND artifact_sha256=? AND state=?",
                    (target, *values, expected)
                ).rowcount
                if changed != 1:
                    raise ReplayAdmissionError("replay_state_or_context_mismatch")
                db.commit()
            except BaseException:
                db.rollback()
                raise
        return target

    def state(self, *, issuer: str, nonce: str) -> str | None:
        with self._connection() as db:
            row = db.execute(
                "SELECT state FROM release_attempts WHERE issuer=? AND nonce=?",
                (issuer, nonce)
            ).fetchone()
        return row[0] if row else None
