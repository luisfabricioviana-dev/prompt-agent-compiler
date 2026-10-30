"""Fail-closed tri-ledger consistency audit, read-only and non-publishing.

No three-database atomic snapshot is claimed. Any mismatch requires manual
investigation; this function never authorizes retry, replay or dispatch.
"""
from __future__ import annotations
from dataclasses import dataclass
import sqlite3

from .cross_ledger_release_audit import audit_cross_ledger, CrossLedgerAudit
from .durable_cross_ledger_binding_registry import DurableBindingRegistry
from .cross_ledger_binding import CrossLedgerBinding, CrossLedgerBindingVerifier


@dataclass(frozen=True)
class ThreeLedgerVerdict:
    status: str
    reason: str


def audit_three_ledgers(*, ledger, rea_conn, recovery,
                        issuer: str, nonce: str, release_id: str,
                        artifact_sha256: str, destination_id: str,
                        observer_id: str, observer_key: bytes,
                        binding: CrossLedgerBinding,
                        binding_verifier: CrossLedgerBindingVerifier,
                        binding_registry: DurableBindingRegistry) -> ThreeLedgerVerdict:
    if not isinstance(binding_registry, DurableBindingRegistry):
        return ThreeLedgerVerdict("BLOCK", "registry_required")
    if not isinstance(binding, CrossLedgerBinding):
        return ThreeLedgerVerdict("BLOCK", "binding_required")
    try:
        with binding_registry._connection() as db:
            row = db.execute(
                "SELECT release_id,artifact_sha256,destination_id,signature "
                "FROM cross_ledger_bindings WHERE issuer=? AND nonce=?",
                (issuer, nonce)
            ).fetchone()
            reverse = db.execute(
                "SELECT issuer,nonce FROM cross_ledger_bindings WHERE release_id=?",
                (release_id,)
            ).fetchone()
    except (sqlite3.Error, ValueError, TypeError):
        return ThreeLedgerVerdict("BLOCK", "registry_unavailable")
    if row is None or reverse is None:
        return ThreeLedgerVerdict("BLOCK", "registry_binding_missing")
    if reverse != (issuer, nonce):
        return ThreeLedgerVerdict("BLOCK", "registry_reverse_identity_conflict")
    if row != (release_id, artifact_sha256, destination_id, binding.signature):
        return ThreeLedgerVerdict("BLOCK", "registry_binding_conflict")
    result = audit_cross_ledger(
        ledger=ledger, rea_conn=rea_conn, recovery=recovery,
        issuer=issuer, nonce=nonce, release_id=release_id,
        artifact_sha256=artifact_sha256, destination_id=destination_id,
        observer_id=observer_id, observer_key=observer_key,
        binding=binding, binding_verifier=binding_verifier,
        binding_registry=binding_registry,
    )
    if result.state == "CONSISTENT":
        return ThreeLedgerVerdict("CONSISTENT", "three_ledger_evidence_verified_read_only")
    if result.state == "IN_DOUBT":
        return ThreeLedgerVerdict("IN_DOUBT", "no_retry:" + result.reason)
    return ThreeLedgerVerdict("BLOCK", result.reason)
