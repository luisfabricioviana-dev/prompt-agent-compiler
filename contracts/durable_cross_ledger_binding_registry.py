"""Single-host durable binding registry: immutable identities, no dispatch.

An authenticated binding is reserved atomically before cross-ledger audit.
A repeated identical binding is idempotent; conflicting reuse of issuer/nonce
or release_id is always rejected. Separate deployment DB coordination is not
a distributed atomicity guarantee.
"""
from __future__ import annotations
import sqlite3
from pathlib import Path
from .cross_ledger_binding import CrossLedgerBinding, CrossLedgerBindingVerifier


class BindingRegistryError(RuntimeError):
    pass


class DurableBindingRegistry:
    def __init__(self, database_path: str | Path):
        if not isinstance(database_path, (str, Path)) or not str(database_path) or str(database_path) == ":memory:":
            raise ValueError("binding_registry_path_required")
        self.path = str(database_path)
        with self._connection() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS cross_ledger_bindings (
                issuer TEXT NOT NULL, nonce TEXT NOT NULL,
                release_id TEXT NOT NULL UNIQUE,
                artifact_sha256 TEXT NOT NULL, destination_id TEXT NOT NULL,
                signature TEXT NOT NULL, PRIMARY KEY(issuer,nonce)
            )""")

    def _connection(self):
        db = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        db.execute("PRAGMA busy_timeout=10000")
        db.execute("PRAGMA synchronous=FULL")
        return db

    def reserve(self, *, binding: CrossLedgerBinding, verifier: CrossLedgerBindingVerifier) -> str:
        if not isinstance(verifier, CrossLedgerBindingVerifier) or not isinstance(binding, CrossLedgerBinding):
            raise BindingRegistryError("authenticated_binding_required")
        if not verifier.verify(
            binding=binding, issuer=binding.issuer, nonce=binding.nonce,
            release_id=binding.release_id, artifact_sha256=binding.artifact_sha256,
            destination_id=binding.destination_id,
        ):
            raise BindingRegistryError("binding_signature_invalid")
        expected = (binding.release_id, binding.artifact_sha256,
                    binding.destination_id, binding.signature)
        with self._connection() as db:
            try:
                db.execute("BEGIN IMMEDIATE")
                existing = db.execute(
                    "SELECT release_id,artifact_sha256,destination_id,signature "
                    "FROM cross_ledger_bindings WHERE issuer=? AND nonce=?",
                    (binding.issuer, binding.nonce),
                ).fetchone()
                if existing is not None:
                    if existing != expected:
                        raise BindingRegistryError("binding_identity_conflict")
                    db.commit()
                    return "ALREADY_RESERVED"
                db.execute(
                    "INSERT INTO cross_ledger_bindings VALUES (?,?,?,?,?,?)",
                    (binding.issuer, binding.nonce, *expected),
                )
                db.commit()
            except sqlite3.IntegrityError as exc:
                db.rollback()
                raise BindingRegistryError("binding_release_id_conflict") from exc
            except BaseException:
                db.rollback()
                raise
        return "RESERVED"

    def matches(self, binding: CrossLedgerBinding) -> bool:
        if not isinstance(binding, CrossLedgerBinding):
            return False
        with self._connection() as db:
            row = db.execute(
                "SELECT release_id,artifact_sha256,destination_id,signature "
                "FROM cross_ledger_bindings WHERE issuer=? AND nonce=?",
                (binding.issuer, binding.nonce)
            ).fetchone()
        return row == (binding.release_id, binding.artifact_sha256,
                       binding.destination_id, binding.signature)
