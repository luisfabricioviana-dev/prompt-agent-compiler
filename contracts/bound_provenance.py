"""Offline context-bound HMAC admission. No production custody assertion.

Signer provisioning, authorization, and durable anti-replay remain external.
"""
from __future__ import annotations
from dataclasses import dataclass
import hashlib
import hmac

DOMAIN = b"PAC-REA-CONTEXT-PROVENANCE-v1"

def _message(issuer: str, spec_id: str, artifact_id: str, run_id: str,
             digest: str, nonce: str) -> bytes:
    fields = (issuer, spec_id, artifact_id, run_id, digest, nonce)
    if any(not isinstance(x, str) or not x.strip() or "\n" in x for x in fields):
        raise ValueError("context_provenance_field_invalid")
    return b"\n".join((DOMAIN, *(x.encode("utf-8") for x in fields)))

@dataclass(frozen=True)
class BoundProvenanceStatement:
    issuer: str
    spec_id: str
    artifact_id: str
    run_id: str
    artifact_sha256: str
    nonce: str
    signature: str

def sign_fixture(*, key: bytes, issuer: str, spec_id: str, artifact_id: str,
                 run_id: str, payload: bytes, nonce: str) -> BoundProvenanceStatement:
    """Test-only helper; never a production issuer or custody system."""
    digest = hashlib.sha256(payload).hexdigest()
    message = _message(issuer, spec_id, artifact_id, run_id, digest, nonce)
    return BoundProvenanceStatement(
        issuer, spec_id, artifact_id, run_id, digest, nonce,
        hmac.new(key, message, hashlib.sha256).hexdigest(),
    )

class BoundProvenanceVerifier:
    """Trusted key supplied externally; verifier cannot authorize release alone."""
    def __init__(self, *, trusted_issuer: str, verification_key: bytes):
        if not isinstance(trusted_issuer, str) or not trusted_issuer.strip():
            raise ValueError("trusted_issuer_required")
        if not isinstance(verification_key, bytes) or len(verification_key) < 32:
            raise ValueError("trusted_verification_key_invalid")
        self._issuer = trusted_issuer
        self._key = verification_key

    def verify(self, *, statement: BoundProvenanceStatement, spec_id: str,
               artifact_id: str, run_id: str, payload: bytes) -> bool:
        if not isinstance(statement, BoundProvenanceStatement) or not isinstance(payload, bytes):
            return False
        if (statement.issuer != self._issuer or statement.spec_id != spec_id
                or statement.artifact_id != artifact_id or statement.run_id != run_id):
            return False
        digest = hashlib.sha256(payload).hexdigest()
        if not hmac.compare_digest(statement.artifact_sha256, digest):
            return False
        try:
            message = _message(statement.issuer, statement.spec_id, statement.artifact_id,
                               statement.run_id, digest, statement.nonce)
            expected = hmac.new(self._key, message, hashlib.sha256).hexdigest()
            return hmac.compare_digest(expected, statement.signature)
        except (TypeError, ValueError):
            return False
