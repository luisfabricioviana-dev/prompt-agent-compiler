"""Explicit opt-in REA dry-run orchestrator.

This is a non-publishing integration smoke path. It exercises authorization,
byte integrity, the single-use ledger and signed delivery observation. It does
not claim that ExecutionSpec is wired to a production publisher.
"""
from __future__ import annotations
from dataclasses import dataclass
import hashlib
import sqlite3

from .rea_authorized_handoff import authorized_handoff, read_release_dispatch_state
from .rea_release_authority import ReleaseAuthorization
from .rea_release_reconciliation import reconcile_delivery
from .rea_security_gate import ArtifactEvidence, evaluate_artifact, verify_artifact_bytes

@dataclass(frozen=True)
class PipelineResult:
    state: str
    reason: str
    sha256: str

def run_governed_pipeline(
    conn: sqlite3.Connection, payload: bytes, evidence: ArtifactEvidence,
    authorization: ReleaseAuthorization, *, issuer: str, issuer_key: bytes,
    destination_id: str, observer_id: str, observer_key: bytes,
    dispatch, observe, enable_dispatch: bool = False, trusted_destination_resolver=None,
) -> PipelineResult:
    """Disabled by default; dispatch is only called when explicitly enabled."""
    if not isinstance(payload, bytes):
        return PipelineResult("BLOCKED", "invalid_payload", "")
    digest = hashlib.sha256(payload).hexdigest()
    if not isinstance(evidence, ArtifactEvidence):
        return PipelineResult("BLOCKED", "artifact_evidence_missing", digest)
    policy = evaluate_artifact(evidence)
    bytes_proof = verify_artifact_bytes(payload, evidence.artifact_sha256)
    if not policy.allowed or not bytes_proof.allowed:
        return PipelineResult("BLOCKED", ",".join((*policy.reasons, *bytes_proof.reasons)), digest)
    if enable_dispatch is not True:
        return PipelineResult("DRY_RUN", "artifact_checked_dispatch_disabled", digest)
    if not isinstance(destination_id, str) or not destination_id:
        return PipelineResult("BLOCKED", "destination_missing", digest)
    if not callable(trusted_destination_resolver):
        return PipelineResult("BLOCKED", "trusted_destination_resolver_missing", digest)
    try:
        resolved_destination = trusted_destination_resolver()
    except Exception:
        return PipelineResult("BLOCKED", "trusted_destination_resolution_failed", digest)
    if not isinstance(resolved_destination, str) or resolved_destination != destination_id:
        return PipelineResult("BLOCKED", "destination_identity_mismatch", digest)
    if not isinstance(authorization, ReleaseAuthorization):
        return PipelineResult("BLOCKED", "release_authorization_missing", digest)
    attempt = authorized_handoff(
        conn, payload, evidence, authorization,
        trusted_issuer=issuer, trusted_key=issuer_key, callback=dispatch,
        destination_id=destination_id,
    )
    if not attempt.accepted:
        # Once a release ID is claimed, a failure can represent a remotely
        # completed dispatch whose acknowledgement was lost. Never retry.
        if "release_id_already_consumed" in attempt.reasons:
            return PipelineResult("BLOCKED", "release_id_already_consumed", digest)
        claim_state = read_release_dispatch_state(conn, authorization.release_id)
        if claim_state in ("DISPATCH_RETURNED", "IN_DOUBT"):
            return PipelineResult("IN_DOUBT", ",".join(attempt.reasons), digest)
        return PipelineResult("BLOCKED", ",".join(attempt.reasons), digest)
    dispatched = read_release_dispatch_state(conn, authorization.release_id)
    if dispatched != "DISPATCH_RETURNED":
        return PipelineResult("IN_DOUBT", dispatched, digest)
    confirmed, reason = reconcile_delivery(
        conn, release_id=authorization.release_id,
        artifact_sha256=digest, expected_destination=destination_id,
        observe=observe, trusted_observer_key=observer_key,
        trusted_observer_id=observer_id,
    )
    if not confirmed:
        return PipelineResult("IN_DOUBT", reason, digest)
    return PipelineResult("CONFIRMED_BY_OBSERVER", reason, digest)
