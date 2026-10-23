"""Trusted authorization + atomically consumed release ID around REA handoff.

SQLite guarantees one dispatch attempt per release ID on this database.
A failed/uncertain callback intentionally stays consumed: reconcile externally.
"""
from __future__ import annotations
import sqlite3
from .rea_release_authority import ReleaseAuthorization, verify_release_authorization
from .rea_release_handoff import governed_artifact_handoff, HandoffResult
from .rea_security_gate import ArtifactEvidence

def authorized_handoff(conn: sqlite3.Connection, payload: bytes,
                       evidence: ArtifactEvidence, auth: ReleaseAuthorization, *,
                       trusted_issuer: str, trusted_key: bytes, callback) -> HandoffResult:
    if not isinstance(payload, bytes):
        return HandoffResult(False, ("payload_unavailable",))
    if not verify_release_authorization(
        auth, trusted_issuer=trusted_issuer, trusted_key=trusted_key,
        artifact_sha256=evidence.artifact_sha256
    ):
        return HandoffResult(False, ("release_authority_unverified",))
    conn.execute("CREATE TABLE IF NOT EXISTS rea_release_claims (release_id TEXT PRIMARY KEY, artifact_sha256 TEXT NOT NULL)")
    try:
        conn.execute("INSERT INTO rea_release_claims (release_id, artifact_sha256) VALUES (?, ?)",
                     (auth.release_id, auth.artifact_sha256))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.rollback()
        return HandoffResult(False, ("release_id_already_consumed",))
    # At-most-once invocation, not a claim of exactly-once delivery.
    return governed_artifact_handoff(
        payload, evidence, authorized_for_release=True, callback=callback
    )
