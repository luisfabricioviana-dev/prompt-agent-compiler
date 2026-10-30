"""Authenticated, atomic offline reconciliation. Never dispatches a delivery.

Deployment must provision an independent observer verification key and establish
the observer's operational trust. SQLite guarantees atomic evidence/state only
for one ledger database on a supported local filesystem.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import hmac
import json
import sqlite3
from typing import Callable

from .bound_provenance import BoundProvenanceStatement
from .durable_replay_ledger import DurableReplayLedger, ReplayAdmissionError
from .release_reconciliation import ObserverConfirmation, ReleaseReconciliationError

_DOMAIN = b"PAC-OBSERVER-CONFIRMATION-v1\x00"


def _canonical(confirmation: ObserverConfirmation) -> bytes:
    fields = (
        confirmation.issuer, confirmation.nonce, confirmation.spec_id,
        confirmation.artifact_id, confirmation.run_id,
        confirmation.artifact_sha256, confirmation.destination_id,
        confirmation.delivery_id,
    )
    if any(not isinstance(v, str) or not v.strip() for v in fields):
        raise ReleaseReconciliationError("observer_confirmation_invalid")
    return _DOMAIN + json.dumps(fields, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


@dataclass(frozen=True)
class AuthenticatedConfirmation:
    observation: ObserverConfirmation
    observer_id: str
    signature: str


class ObserverAuthenticator:
    """A trusted, deployment-provisioned HMAC verification boundary."""
    def __init__(self, *, observer_id: str, verification_key: bytes):
        if not isinstance(observer_id, str) or not observer_id.strip():
            raise ValueError("observer_id_required")
        if not isinstance(verification_key, bytes) or len(verification_key) < 32:
            raise ValueError("observer_verification_key_invalid")
        self.observer_id = observer_id
        self._key = verification_key

    def verify(self, envelope: AuthenticatedConfirmation) -> bool:
        if not isinstance(envelope, AuthenticatedConfirmation):
            return False
        if envelope.observer_id != self.observer_id or not isinstance(envelope.signature, str):
            return False
        try:
            message = self.observer_id.encode("utf-8") + b"\x00" + _canonical(envelope.observation)
            expected = hmac.new(self._key, message, hashlib.sha256).hexdigest()
            return hmac.compare_digest(expected, envelope.signature)
        except (TypeError, ValueError, ReleaseReconciliationError):
            return False


def reconcile_authenticated(
    *, ledger: DurableReplayLedger, statement: BoundProvenanceStatement,
    payload: bytes, destination_id: str,
    observer: Callable[..., AuthenticatedConfirmation],
    authenticator: ObserverAuthenticator,
) -> str:
    if not isinstance(ledger, DurableReplayLedger) or not isinstance(authenticator, ObserverAuthenticator):
        raise ReleaseReconciliationError("reconciliation_dependencies_invalid")
    if not isinstance(destination_id, str) or not destination_id.strip() or not callable(observer):
        raise ReleaseReconciliationError("reconciliation_observer_or_destination_invalid")
    try:
        identity = ledger._identity(statement, payload)
    except ReplayAdmissionError as exc:
        raise ReleaseReconciliationError("reconciliation_payload_invalid") from exc
    if ledger.state(issuer=statement.issuer, nonce=statement.nonce) not in ("UNCERTAIN", "DISPATCHED"):
        raise ReleaseReconciliationError("reconciliation_state_not_admissible")
    try:
        envelope = observer(
            issuer=statement.issuer, nonce=statement.nonce,
            spec_id=statement.spec_id, artifact_id=statement.artifact_id,
            run_id=statement.run_id, artifact_sha256=identity[-1],
            destination_id=destination_id,
        )
    except Exception as exc:
        raise ReleaseReconciliationError("observer_lookup_failed") from exc
    if not authenticator.verify(envelope):
        raise ReleaseReconciliationError("observer_authentication_failed")
    confirmation = envelope.observation
    if (
        confirmation.issuer, confirmation.nonce, confirmation.spec_id,
        confirmation.artifact_id, confirmation.run_id,
        confirmation.artifact_sha256, confirmation.destination_id,
    ) != (*identity, destination_id):
        raise ReleaseReconciliationError("observer_confirmation_mismatch")
    evidence_hash = hashlib.sha256(_canonical(confirmation)).hexdigest()
    # The evidence and status update share one SQLite transaction. A crash
    # before commit leaves both absent; after commit leaves both present.
    with ledger._connection() as db:
        try:
            db.execute("BEGIN IMMEDIATE")
            db.execute("""CREATE TABLE IF NOT EXISTS release_observer_evidence (
                issuer TEXT NOT NULL, nonce TEXT NOT NULL,
                observer_id TEXT NOT NULL, delivery_id TEXT NOT NULL,
                destination_id TEXT NOT NULL, evidence_sha256 TEXT NOT NULL,
                signature TEXT NOT NULL,
                PRIMARY KEY (issuer, nonce),
                UNIQUE (observer_id, delivery_id)
            )""")
            changed = db.execute(
                "UPDATE release_attempts SET state='CONFIRMED' "
                "WHERE issuer=? AND nonce=? AND spec_id=? AND artifact_id=? "
                "AND run_id=? AND artifact_sha256=? "
                "AND state IN ('UNCERTAIN','DISPATCHED')",
                identity,
            ).rowcount
            if changed != 1:
                raise ReleaseReconciliationError("reconciliation_atomic_transition_failed")
            db.execute(
                "INSERT INTO release_observer_evidence VALUES (?,?,?,?,?,?,?)",
                (statement.issuer, statement.nonce, envelope.observer_id,
                 confirmation.delivery_id, destination_id, evidence_hash, envelope.signature),
            )
            db.commit()
        except BaseException as exc:
            db.rollback()
            if isinstance(exc, ReleaseReconciliationError):
                raise
            if isinstance(exc, sqlite3.Error):
                raise ReleaseReconciliationError("observer_evidence_persistence_failed") from exc
            raise
    return "CONFIRMED"
