"""Authenticated fail-closed reconciliation of destination delivery.

The observer key MUST be provisioned outside agent-controlled inputs. This
verifies a signed observation, not the observer's real-world reliability.
"""
from __future__ import annotations
import hashlib
import hmac
import re
import sqlite3
from dataclasses import dataclass

@dataclass(frozen=True)
class DestinationObservation:
    release_id: str
    artifact_sha256: str
    destination_id: str
    delivered: bool
    signature_hex: str

def reconcile_delivery(conn: sqlite3.Connection, *, release_id: str,
                       artifact_sha256: str, expected_destination: str,
                       observe, trusted_observer_key: bytes,
                       trusted_observer_id: str) -> tuple[bool, str]:
    if (not isinstance(release_id, str) or not re.fullmatch(r"[A-Za-z0-9_.:-]{8,128}", release_id)
        or not isinstance(expected_destination, str) or not expected_destination
        or not isinstance(artifact_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", artifact_sha256)):
        return False, "invalid_reconciliation_identity"
    if not isinstance(trusted_observer_id, str) or not re.fullmatch(r"[A-Za-z0-9_.:-]{8,128}", trusted_observer_id):
        return False, "trusted_observer_identity_unavailable"
    if not isinstance(trusted_observer_key, bytes) or len(trusted_observer_key) < 32:
        return False, "trusted_observer_key_unavailable"
    try:
        row = conn.execute("SELECT artifact_sha256 FROM rea_release_claims WHERE release_id = ?",
                           (release_id,)).fetchone()
    except sqlite3.Error:
        return False, "release_claim_unavailable"
    if row is None or row[0] != artifact_sha256:
        return False, "release_claim_mismatch"
    try:
        observation = observe(release_id, expected_destination)
    except Exception:
        return False, "destination_observation_unavailable"
    if (not isinstance(observation, DestinationObservation)
        or observation.release_id != release_id
        or observation.artifact_sha256 != artifact_sha256
        or observation.destination_id != expected_destination
        or observation.delivered is not True
        or not isinstance(observation.signature_hex, str)
        or not re.fullmatch(r"[0-9a-f]{64}", observation.signature_hex)):
        return False, "delivery_unverified"
    message = f"REA-DESTINATION-v2\n{trusted_observer_id}\n{release_id}\n{artifact_sha256}\n{expected_destination}\ndelivered".encode()
    expected = hmac.new(trusted_observer_key, message, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, observation.signature_hex):
        return False, "destination_signature_invalid"
    # Persist the signed observation and the terminal confirmation atomically.
    # Legacy rows without evidence do not establish a verified confirmation.
    try:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("CREATE TABLE IF NOT EXISTS rea_release_confirmations "
                     "(release_id TEXT PRIMARY KEY, artifact_sha256 TEXT NOT NULL, destination_id TEXT NOT NULL)")
        conn.execute("CREATE TABLE IF NOT EXISTS rea_release_observer_evidence "
                     "(release_id TEXT PRIMARY KEY, observer_id TEXT NOT NULL, "
                     "artifact_sha256 TEXT NOT NULL, destination_id TEXT NOT NULL, "
                     "signature_hex TEXT NOT NULL)")
        existing = conn.execute(
            "SELECT c.artifact_sha256,c.destination_id,e.observer_id,"
            "e.artifact_sha256,e.destination_id,e.signature_hex "
            "FROM rea_release_confirmations c LEFT JOIN rea_release_observer_evidence e "
            "ON c.release_id=e.release_id WHERE c.release_id=?", (release_id,)
        ).fetchone()
        expected_row = (artifact_sha256, expected_destination, trusted_observer_id,
                        artifact_sha256, expected_destination, observation.signature_hex)
        if existing is not None:
            if existing != expected_row:
                conn.rollback()
                return False, "confirmation_evidence_conflict"
            conn.commit()
            return True, "DELIVERY_CONFIRMED"
        orphan = conn.execute(
            "SELECT 1 FROM rea_release_observer_evidence WHERE release_id=?", (release_id,)
        ).fetchone()
        if orphan is not None:
            conn.rollback()
            return False, "orphan_observer_evidence"
        conn.execute("INSERT INTO rea_release_confirmations "
                     "(release_id, artifact_sha256, destination_id) VALUES (?, ?, ?)",
                     (release_id, artifact_sha256, expected_destination))
        conn.execute("INSERT INTO rea_release_observer_evidence "
                     "(release_id, observer_id, artifact_sha256, destination_id, signature_hex) "
                     "VALUES (?, ?, ?, ?, ?)",
                     (release_id, trusted_observer_id, artifact_sha256,
                      expected_destination, observation.signature_hex))
        conn.commit()
    except sqlite3.Error:
        conn.rollback()
        return False, "confirmation_persistence_failed"
    return True, "DELIVERY_CONFIRMED"


def verify_persisted_delivery(conn: sqlite3.Connection, *, release_id: str,
                              observer_id: str, trusted_observer_key: bytes) -> tuple[bool, str]:
    """Verify retained observation after restart without contacting or dispatching."""
    if not isinstance(trusted_observer_key, bytes) or len(trusted_observer_key) < 32:
        return False, "trusted_observer_key_unavailable"
    try:
        row = conn.execute(
            "SELECT c.artifact_sha256,c.destination_id,e.observer_id,"
            "e.artifact_sha256,e.destination_id,e.signature_hex "
            "FROM rea_release_confirmations c LEFT JOIN rea_release_observer_evidence e "
            "ON c.release_id=e.release_id WHERE c.release_id=?", (release_id,)
        ).fetchone()
        claim = conn.execute("SELECT artifact_sha256 FROM rea_release_claims WHERE release_id=?",
                             (release_id,)).fetchone()
    except sqlite3.Error:
        return False, "confirmation_evidence_unavailable"
    if row is None or claim is None or None in row:
        return False, "confirmation_evidence_missing"
    digest, destination, recorded_observer, observed_digest, observed_destination, signature = row
    if (claim[0] != digest or observed_digest != digest or observed_destination != destination
            or recorded_observer != observer_id or not isinstance(signature, str)):
        return False, "confirmation_evidence_mismatch"
    msg = f"REA-DESTINATION-v2\\n{observer_id}\\n{release_id}\\n{digest}\\n{destination}\\ndelivered".encode()
    expected = hmac.new(trusted_observer_key, msg, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        return False, "confirmation_signature_invalid"
    return True, "DELIVERY_CONFIRMED"
