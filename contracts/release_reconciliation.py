"""Offline observer reconciliation of ambiguous release attempts.

No dispatch occurs here. A deployment-supplied trusted observer must provide
correlated confirmation; caller booleans alone never authorize state changes.
"""
from __future__ import annotations
from dataclasses import dataclass
import hashlib
from typing import Callable

from .bound_provenance import BoundProvenanceStatement
from .durable_replay_ledger import DurableReplayLedger, ReplayAdmissionError


@dataclass(frozen=True)
class ObserverConfirmation:
    issuer: str
    nonce: str
    spec_id: str
    artifact_id: str
    run_id: str
    artifact_sha256: str
    destination_id: str
    delivery_id: str


class ReleaseReconciliationError(RuntimeError):
    pass


def reconcile_confirmed(
    *,
    ledger: DurableReplayLedger,
    statement: BoundProvenanceStatement,
    payload: bytes,
    destination_id: str,
    observer: Callable[..., ObserverConfirmation],
) -> str:
    if not isinstance(ledger, DurableReplayLedger):
        raise ReleaseReconciliationError("durable_ledger_required")
    if not isinstance(statement, BoundProvenanceStatement) or not isinstance(payload, bytes):
        raise ReleaseReconciliationError("reconciliation_statement_invalid")
    if not isinstance(destination_id, str) or not destination_id.strip():
        raise ReleaseReconciliationError("destination_required")
    if not callable(observer):
        raise ReleaseReconciliationError("trusted_observer_required")

    digest = hashlib.sha256(payload).hexdigest()
    if digest != statement.artifact_sha256:
        raise ReleaseReconciliationError("reconciliation_payload_mismatch")
    state = ledger.state(issuer=statement.issuer, nonce=statement.nonce)
    if state not in ("UNCERTAIN", "DISPATCHED"):
        raise ReleaseReconciliationError("reconciliation_state_not_admissible")
    try:
        confirmation = observer(
            issuer=statement.issuer,
            nonce=statement.nonce,
            spec_id=statement.spec_id,
            artifact_id=statement.artifact_id,
            run_id=statement.run_id,
            artifact_sha256=digest,
            destination_id=destination_id,
        )
    except Exception as exc:
        raise ReleaseReconciliationError("observer_lookup_failed") from exc

    expected = (statement.issuer, statement.nonce, statement.spec_id,
                statement.artifact_id, statement.run_id, digest, destination_id)
    if (not isinstance(confirmation, ObserverConfirmation)
            or (confirmation.issuer, confirmation.nonce, confirmation.spec_id,
                confirmation.artifact_id, confirmation.run_id,
                confirmation.artifact_sha256, confirmation.destination_id) != expected
            or not isinstance(confirmation.delivery_id, str)
            or not confirmation.delivery_id.strip()):
        raise ReleaseReconciliationError("observer_confirmation_mismatch")
    try:
        return ledger.transition(statement, payload, expected=state, target="CONFIRMED")
    except ReplayAdmissionError as exc:
        raise ReleaseReconciliationError("reconciliation_atomic_transition_failed") from exc
