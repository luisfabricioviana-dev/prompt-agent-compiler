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
    # Retired security-unsafe Wave 19 adapter. All confirmations must pass
    # authenticated_reconcile / GovernedRecovery before a durable state change.
    # Kept as a fail-closed symbol for historical imports only.
    raise ReleaseReconciliationError("authenticated_reconciliation_required")
