"""Governed recovery entrypoint: authenticated-only, read-only restart audit.

This API never calls a dispatch runner. It cannot disable other legacy APIs;
deployment must expose only this governed interface for recovery operations.
"""
from __future__ import annotations

import hashlib
import sqlite3
from .authenticated_release_reconciliation import (
    ObserverAuthenticator, AuthenticatedConfirmation, _canonical,
    reconcile_authenticated,
)
from .release_reconciliation import ObserverConfirmation, ReleaseReconciliationError
from .durable_replay_ledger import DurableReplayLedger


class GovernedRecovery:
    def __init__(self, *, ledger: DurableReplayLedger, authenticator: ObserverAuthenticator):
        if not isinstance(ledger, DurableReplayLedger) or not isinstance(authenticator, ObserverAuthenticator):
            raise ValueError("governed_recovery_dependencies_required")
        self._ledger = ledger
        self._authenticator = authenticator

    def reconcile(self, *, statement, payload: bytes, destination_id: str, observer):
        return reconcile_authenticated(
            ledger=self._ledger, statement=statement, payload=payload,
            destination_id=destination_id, observer=observer,
            authenticator=self._authenticator,
        )

    def verify_after_restart(self, *, issuer: str, nonce: str) -> tuple[bool, str]:
        """Reconstruct signed evidence and reject incomplete/corrupted confirmation.

        A failed audit is a release BLOCK, not a reset of the replay barrier.
        """
        try:
            with self._ledger._connection() as db:
                db.execute("BEGIN")
                attempt = db.execute(
                    "SELECT spec_id,artifact_id,run_id,artifact_sha256,state "
                    "FROM release_attempts WHERE issuer=? AND nonce=?", (issuer, nonce)
                ).fetchone()
                try:
                    evidence = db.execute(
                        "SELECT observer_id,delivery_id,destination_id,evidence_sha256,signature "
                        "FROM release_observer_evidence WHERE issuer=? AND nonce=?",
                        (issuer, nonce)
                    ).fetchone()
                except sqlite3.OperationalError as exc:
                    if "no such table" not in str(exc):
                        raise
                    evidence = None
                db.commit()
        except (sqlite3.Error, TypeError, ValueError):
            return False, "recovery_storage_unavailable"
        if attempt is None:
            return False, "recovery_attempt_missing"
        if attempt[4] != "CONFIRMED":
            return False, "recovery_not_confirmed"
        if evidence is None:
            return False, "recovery_evidence_missing"
        observer_id, delivery_id, destination, digest, signature = evidence
        confirmation = ObserverConfirmation(issuer, nonce, *attempt[:4], destination, delivery_id)
        try:
            if hashlib.sha256(_canonical(confirmation)).hexdigest() != digest:
                return False, "recovery_evidence_digest_mismatch"
        except (ReleaseReconciliationError, TypeError):
            return False, "recovery_evidence_invalid"
        if not self._authenticator.verify(AuthenticatedConfirmation(confirmation, observer_id, signature)):
            return False, "recovery_observer_authentication_failed"
        return True, "CONFIRMED_EVIDENCE_VERIFIED"


def legacy_reconciliation_forbidden(*args, **kwargs):
    """For use as a deployment-level adapter when legacy imports must remain."""
    raise ReleaseReconciliationError("authenticated_reconciliation_required")
