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
    message = f"REA-DESTINATION-v2
{trusted_observer_id}
{release_id}
{artifact_sha256}
{expected_destination}
delivered".encode()
    expected = hmac.new(trusted_observer_key, message, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, observation.signature_hex):
        return False, "destination_signature_invalid"
    try:
        conn.execute("CREATE TABLE IF NOT EXISTS rea_release_confirmations "
                     "(release_id TEXT PRIMARY KEY, artifact_sha256 TEXT NOT NULL, destination_id TEXT NOT NULL)")
        existing = conn.execute("SELECT artifact_sha256, destination_id FROM rea_release_confirmations "
                                "WHERE release_id = ?", (release_id,)).fetchone()
        if existing is not None:
            if existing != (artifact_sha256, expected_destination):
                return False, "confirmation_conflict"
            return True, "DELIVERY_CONFIRMED"
        conn.execute("INSERT INTO rea_release_confirmations "
                     "(release_id, artifact_sha256, destination_id) VALUES (?, ?, ?)",
                     (release_id, artifact_sha256, expected_destination))
        conn.commit()
    except sqlite3.Error:
        conn.rollback()
        return False, "confirmation_persistence_failed"
    return True, "DELIVERY_CONFIRMED"
