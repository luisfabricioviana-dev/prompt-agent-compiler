"""Best-effort stable tri-ledger read with fail-closed before/after snapshots.

Not a distributed transaction, lock, or proof against ABA transitions.
Only signed and persisted identity-bound evidence is considered.
"""
from __future__ import annotations
from dataclasses import dataclass
import sqlite3
from .three_ledger_release_audit import audit_three_ledgers, ThreeLedgerVerdict


def _snapshot(*, ledger, rea_conn, binding_registry, issuer, nonce, release_id):
    with ledger._connection() as db:
        replay = db.execute(
            "SELECT spec_id,artifact_id,run_id,artifact_sha256,state FROM release_attempts "
            "WHERE issuer=? AND nonce=?", (issuer, nonce)).fetchone()
        try:
            replay_evidence = db.execute(
                "SELECT observer_id,delivery_id,destination_id,evidence_sha256,signature "
                "FROM release_observer_evidence WHERE issuer=? AND nonce=?", (issuer, nonce)).fetchone()
        except sqlite3.OperationalError as exc:
            if "no such table" not in str(exc):
                raise
            replay_evidence = None
    with binding_registry._connection() as db:
        binding = db.execute(
            "SELECT release_id,artifact_sha256,destination_id,signature FROM cross_ledger_bindings "
            "WHERE issuer=? AND nonce=?", (issuer, nonce)).fetchone()
        reverse = db.execute(
            "SELECT issuer,nonce FROM cross_ledger_bindings WHERE release_id=?",
            (release_id,)).fetchone()
    claim = rea_conn.execute(
        "SELECT artifact_sha256 FROM rea_release_claims WHERE release_id=?", (release_id,)).fetchone()
    try:
        confirmation = rea_conn.execute(
            "SELECT artifact_sha256,destination_id FROM rea_release_confirmations "
            "WHERE release_id=?", (release_id,)).fetchone()
        observation = rea_conn.execute(
            "SELECT observer_id,artifact_sha256,destination_id,signature_hex "
            "FROM rea_release_observer_evidence WHERE release_id=?", (release_id,)).fetchone()
    except sqlite3.OperationalError as exc:
        if "no such table" not in str(exc):
            raise
        confirmation = observation = None
    return (replay, replay_evidence, binding, reverse, claim, confirmation, observation)


def audit_stable_three_ledgers(*, ledger, rea_conn, recovery, issuer: str, nonce: str,
                               release_id: str, artifact_sha256: str, destination_id: str,
                               observer_id: str, observer_key: bytes, binding,
                               binding_verifier, binding_registry) -> ThreeLedgerVerdict:
    args = dict(ledger=ledger, rea_conn=rea_conn, recovery=recovery,
                issuer=issuer, nonce=nonce, release_id=release_id,
                artifact_sha256=artifact_sha256, destination_id=destination_id,
                observer_id=observer_id, observer_key=observer_key,
                binding=binding, binding_verifier=binding_verifier,
                binding_registry=binding_registry)
    try:
        before = _snapshot(ledger=ledger, rea_conn=rea_conn,
                           binding_registry=binding_registry, issuer=issuer,
                           nonce=nonce, release_id=release_id)
    except (sqlite3.Error, AttributeError, TypeError, ValueError):
        return ThreeLedgerVerdict("BLOCK", "stable_read_before_unavailable")
    try:
        result = audit_three_ledgers(**args)
    except (sqlite3.Error, AttributeError, TypeError, ValueError):
        return ThreeLedgerVerdict("BLOCK", "stable_read_audit_unavailable")
    try:
        after = _snapshot(ledger=ledger, rea_conn=rea_conn,
                          binding_registry=binding_registry, issuer=issuer,
                          nonce=nonce, release_id=release_id)
    except (sqlite3.Error, AttributeError, TypeError, ValueError):
        return ThreeLedgerVerdict("BLOCK", "stable_read_after_unavailable")
    if before != after:
        return ThreeLedgerVerdict("BLOCK", "concurrent_ledger_change_detected")
    return result
