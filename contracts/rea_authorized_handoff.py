"""Trusted authorization + atomically consumed release ID around REA handoff.

SQLite guarantees one dispatch attempt per release ID on this database.
A failed/uncertain callback intentionally stays consumed: reconcile externally.
"""
from __future__ import annotations
import sqlite3
from .rea_release_authority import ReleaseAuthorization, verify_destination_bound_authorization
from .rea_release_handoff import governed_artifact_handoff, HandoffResult
from .rea_security_gate import ArtifactEvidence, evaluate_artifact, verify_artifact_bytes

def authorized_handoff(conn: sqlite3.Connection, payload: bytes,
                       evidence: ArtifactEvidence, auth: ReleaseAuthorization, *,
                       trusted_issuer: str, trusted_key: bytes, callback, destination_id: str | None = None) -> HandoffResult:
    if not isinstance(payload, bytes):
        return HandoffResult(False, ("payload_unavailable",))
    if not isinstance(evidence, ArtifactEvidence):
        return HandoffResult(False, ("artifact_evidence_missing",))
    if destination_id is None:
        return HandoffResult(False, ("destination_required",))
    if not verify_destination_bound_authorization(
        auth, trusted_issuer=trusted_issuer, trusted_key=trusted_key,
        artifact_sha256=evidence.artifact_sha256, destination_id=destination_id,
    ):
        return HandoffResult(False, ("release_authority_unverified",))
    policy = evaluate_artifact(evidence)
    if not policy.allowed:
        return HandoffResult(False, policy.reasons)
    byte_proof = verify_artifact_bytes(payload, evidence.artifact_sha256)
    if not byte_proof.allowed:
        return HandoffResult(False, byte_proof.reasons)
    try:
        conn.execute("CREATE TABLE IF NOT EXISTS rea_release_claims (release_id TEXT PRIMARY KEY, artifact_sha256 TEXT NOT NULL)")
        conn.execute("INSERT INTO rea_release_claims (release_id, artifact_sha256) VALUES (?, ?)",
                     (auth.release_id, auth.artifact_sha256))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.rollback()
        return HandoffResult(False, ("release_id_already_consumed",))
    except sqlite3.Error:
        try:
            conn.rollback()
        except sqlite3.Error:
            pass
        return HandoffResult(False, ("release_claim_persistence_failed",))
    # A persisted claim without an outcome is IN_DOUBT after a crash.
    # Callback return never proves delivery to the final destination.
    outcome = governed_artifact_handoff(
        payload, evidence, authorized_for_release=True, callback=callback
    )
    try:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS rea_release_outcomes "
            "(release_id TEXT PRIMARY KEY, dispatch_state TEXT NOT NULL)"
        )
        conn.execute(
            "INSERT INTO rea_release_outcomes (release_id, dispatch_state) VALUES (?, ?)",
            (auth.release_id, "DISPATCH_RETURNED" if outcome.accepted else "IN_DOUBT"),
        )
        conn.commit()
    except sqlite3.Error:
        conn.rollback()
        return HandoffResult(False, ("dispatch_outcome_persistence_failed",))
    return outcome

def read_release_dispatch_state(conn: sqlite3.Connection, release_id: str) -> str:
    """Read local dispatch state, never final delivery confirmation."""
    try:
        claimed = conn.execute(
            "SELECT 1 FROM rea_release_claims WHERE release_id = ?", (release_id,)
        ).fetchone()
        if claimed is None:
            return "NOT_CLAIMED"
        try:
            state = conn.execute(
                "SELECT dispatch_state FROM rea_release_outcomes WHERE release_id = ?",
                (release_id,),
            ).fetchone()
        except sqlite3.OperationalError as error:
            # A crash after the durable claim but before the outcomes table
            # was initialized has an unknown delivery result, not a clean state.
            if "no such table: rea_release_outcomes" in str(error):
                return "IN_DOUBT"
            return "STATE_UNAVAILABLE"
        return state[0] if state else "IN_DOUBT"
    except sqlite3.Error:
        return "STATE_UNAVAILABLE"
