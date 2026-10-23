"""Fail-closed reconciliation of one-shot release claims.

Only an independently trusted observer can confirm delivery. Never redispatch.
"""
from __future__ import annotations
import sqlite3
from dataclasses import dataclass

@dataclass(frozen=True)
class DestinationObservation:
    release_id: str
    artifact_sha256: str
    destination_id: str
    delivered: bool

def reconcile_delivery(conn: sqlite3.Connection, *, release_id: str,
                       artifact_sha256: str, expected_destination: str,
                       observe) -> tuple[bool, str]:
    if not release_id or not expected_destination or not artifact_sha256:
        return False, "invalid_reconciliation_identity"
    try:
        row = conn.execute(
            "SELECT artifact_sha256 FROM rea_release_claims WHERE release_id = ?",
            (release_id,),
        ).fetchone()
    except sqlite3.Error:
        return False, "release_claim_unavailable"
    if row is None or row[0] != artifact_sha256:
        return False, "release_claim_mismatch"
    # A trusted observer must be provisioned outside the candidate artifact.
    try:
        observation = observe(release_id, expected_destination)
    except Exception:
        return False, "destination_observation_unavailable"
    if (not isinstance(observation, DestinationObservation)
        or observation.release_id != release_id
        or observation.artifact_sha256 != artifact_sha256
        or observation.destination_id != expected_destination
        or observation.delivered is not True):
        return False, "delivery_unverified"
    try:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS rea_release_confirmations "
            "(release_id TEXT PRIMARY KEY, artifact_sha256 TEXT NOT NULL, destination_id TEXT NOT NULL)"
        )
        conn.execute(
            "INSERT OR IGNORE INTO rea_release_confirmations "
            "(release_id, artifact_sha256, destination_id) VALUES (?, ?, ?)",
            (release_id, artifact_sha256, expected_destination),
        )
        conn.commit()
    except sqlite3.Error:
        conn.rollback()
        return False, "confirmation_persistence_failed"
    return True, "DELIVERY_CONFIRMED"
