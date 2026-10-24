"""Offline REA provenance verification with caller-provisioned trusted signing key.

The signing authority is external to this module. Fixture tests do not prove
that production key custody or source verification has been deployed.
No publishing or network operations are performed.
"""
from __future__ import annotations
import hashlib
import hmac
from dataclasses import dataclass

from contracts.rea_security_gate import ArtifactEvidence, evaluate_artifact, verify_artifact_bytes

DOMAIN = b"REA-ARTIFACT-PROVENANCE-v1"

@dataclass(frozen=True)
class SignedProvenance:
    issuer: str
    source_ref: str
    artifact_sha256: str
    signature: str

def signature_message(issuer: str, source_ref: str, digest: str) -> bytes:
    return b"\n".join((DOMAIN, issuer.encode(), source_ref.encode(), digest.encode()))

def inspect_signed_candidate(payload: bytes, statement: SignedProvenance,
                             *, trusted_issuer: str, verification_key: bytes) -> dict:
    """Require a signed, payload-bound provenance statement before candidate admission.

    The external verifier/key provisioning must be audited separately.
    """
    digest = hashlib.sha256(payload).hexdigest()
    reasons = []
    valid_statement = (
        isinstance(statement, SignedProvenance)
        and isinstance(statement.issuer, str)
        and isinstance(statement.source_ref, str)
        and isinstance(statement.artifact_sha256, str)
        and isinstance(statement.signature, str)
        and bool(statement.source_ref.strip())
        and bool(statement.issuer.strip())
    )
    valid_key = isinstance(verification_key, bytes) and len(verification_key) >= 32
    if not valid_statement or not valid_key or not trusted_issuer:
        reasons.append("trusted_provenance_material_missing")
    elif statement.issuer != trusted_issuer or not hmac.compare_digest(
            statement.artifact_sha256, digest):
        reasons.append("provenance_identity_or_digest_mismatch")
    else:
        expected = hmac.new(verification_key,
                            signature_message(statement.issuer, statement.source_ref, digest),
                            hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, statement.signature):
            reasons.append("provenance_signature_invalid")
    evidence = ArtifactEvidence(True, False, False, not reasons, digest)
    policy = evaluate_artifact(evidence)
    checked = verify_artifact_bytes(payload, digest)
    reasons = sorted(set((*reasons, *policy.reasons, *checked.reasons)))
    return {"sha256": digest,
            "state": "BLOCKED" if reasons else "ADMISSIBLE_CANDIDATE",
            "reasons": reasons, "dispatch_performed": False,
            "publication_performed": False,
            "production_issuer_custody_certified": False}
