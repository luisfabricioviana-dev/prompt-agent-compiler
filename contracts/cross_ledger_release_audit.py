"""Read-only cross-ledger REA release consistency audit.

Never mutates ledgers or dispatches. Correlation of release_id to issuer/nonce
must be supplied by a separately trusted deployment binding; matching digests
alone do not prove that two attempts refer to the same delivery.
"""
from __future__ import annotations
from dataclasses import dataclass
import hmac
import sqlite3

from .durable_replay_ledger import DurableReplayLedger
from .governed_release_recovery import GovernedRecovery
from .rea_release_reconciliation import verify_persisted_delivery


@dataclass(frozen=True)
class CrossLedgerAudit:
    state: str
    reason: str


def audit_cross_ledger(
    *, ledger: DurableReplayLedger, rea_conn: sqlite3.Connection,
    recovery: GovernedRecovery, issuer: str, nonce: str,
    release_id: str, artifact_sha256: str, destination_id: str,
    observer_id: str, observer_key: bytes,
) -> CrossLedgerAudit:
    if (not isinstance(ledger, DurableReplayLedger)
            or not isinstance(recovery, GovernedRecovery)
            or not isinstance(rea_conn, sqlite3.Connection)
            or recovery._ledger.path != ledger.path
            or any(not isinstance(x, str) or not x.strip() for x in
                   (issuer, nonce, release_id, artifact_sha256, destination_id,
                    observer_id))):
        return CrossLedgerAudit("BLOCK", "audit_dependencies_or_identity_invalid")
    # Avoid confusing different backing databases and accidental cross-tenant
    # correlations. Caller must bind release_id to (issuer, nonce) independently.
    try:
        with ledger._connection() as db:
            attempt = db.execute(
                "SELECT artifact_sha256,state FROM release_attempts "
                "WHERE issuer=? AND nonce=?", (issuer, nonce)
            ).fetchone()
        claim = rea_conn.execute(
            "SELECT artifact_sha256 FROM rea_release_claims WHERE release_id=?",
            (release_id,)
        ).fetchone()
    except sqlite3.Error:
        return CrossLedgerAudit("BLOCK", "audit_storage_unavailable")
    if attempt is None or claim is None:
        return CrossLedgerAudit("BLOCK", "audit_attempt_or_claim_missing")
    replay_digest, replay_state = attempt
    if not (hmac.compare_digest(replay_digest, artifact_sha256)
            and hmac.compare_digest(claim[0], artifact_sha256)):
        return CrossLedgerAudit("BLOCK", "audit_artifact_digest_mismatch")
    # Uncertain attempts can never be treated as permission to retry, even if
    # another database holds a signed confirmation.
    if replay_state != "CONFIRMED":
        return CrossLedgerAudit("IN_DOUBT", "audit_replay_not_confirmed_no_retry")
    ok, reason = recovery.verify_after_restart(issuer=issuer, nonce=nonce)
    if not ok:
        return CrossLedgerAudit("BLOCK", "audit_replay_evidence_invalid:" + reason)
    try:
        with ledger._connection() as db:
            row = db.execute(
                "SELECT destination_id FROM release_observer_evidence "
                "WHERE issuer=? AND nonce=?", (issuer, nonce)
            ).fetchone()
    except sqlite3.Error:
        return CrossLedgerAudit("BLOCK", "audit_replay_evidence_unavailable")
    if row is None or row[0] != destination_id:
        return CrossLedgerAudit("BLOCK", "audit_replay_destination_mismatch")
    ok, reason = verify_persisted_delivery(
        rea_conn, release_id=release_id, observer_id=observer_id,
        trusted_observer_key=observer_key,
    )
    if not ok:
        return CrossLedgerAudit("BLOCK", "audit_rea_evidence_invalid:" + reason)
    try:
        rea_dest = rea_conn.execute(
            "SELECT destination_id FROM rea_release_confirmations "
            "WHERE release_id=?", (release_id,)
        ).fetchone()
    except sqlite3.Error:
        return CrossLedgerAudit("BLOCK", "audit_rea_destination_unavailable")
    if rea_dest is None or rea_dest[0] != destination_id:
        return CrossLedgerAudit("BLOCK", "audit_rea_destination_mismatch")
    return CrossLedgerAudit("CONSISTENT", "signed_evidence_verified_no_dispatch")
