"""Single governed audit entrypoint for deployment adoption.

Read-only; checks mandatory revision lifecycle, version stability, and
authenticated three-ledger consistency. It NEVER authorizes dispatch.
Other direct module imports are not disabled by this module.
"""
from __future__ import annotations
from .monotonic_ledger_audit import versioned_audit
from .stable_three_ledger_audit import audit_stable_three_ledgers


def governed_release_audit(*, ledger, rea_conn, recovery, binding_registry,
                           issuer: str, nonce: str, release_id: str,
                           artifact_sha256: str, destination_id: str,
                           observer_id: str, observer_key: bytes, binding,
                           binding_verifier) -> tuple[str, str]:
    args = dict(
        ledger=ledger, rea_conn=rea_conn, recovery=recovery,
        binding_registry=binding_registry, issuer=issuer, nonce=nonce,
        release_id=release_id, artifact_sha256=artifact_sha256,
        destination_id=destination_id, observer_id=observer_id,
        observer_key=observer_key, binding=binding,
        binding_verifier=binding_verifier,
    )
    return versioned_audit(
        ledger=ledger, rea_conn=rea_conn,
        binding_registry=binding_registry,
        audit=lambda: audit_stable_three_ledgers(**args),
    )
