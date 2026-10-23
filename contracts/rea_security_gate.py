"""Vendor-neutral REA security gate; no network, secrets, or side effects.

Policy assesses a proposed client-delivered artifact before distribution.
This is a candidate component; production runtime wiring is separate.
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum

class ReconstructionClaim(str, Enum):
    PSEUDOCODE = "pseudocode"
    RECOVERED_SOURCE = "recovered_source"
    BEHAVIORAL_EQUIVALENCE = "behavioral_equivalence"
    BYTE_IDENTICAL = "byte_identical"

@dataclass(frozen=True)
class ArtifactEvidence:
    client_delivered: bool
    embeds_long_lived_secret: bool
    includes_private_key: bool
    provenance_verified: bool
    artifact_sha256: str
    reconstruction_claim: ReconstructionClaim | None = None
    matching_reconstruction_evidence: bool = False

@dataclass(frozen=True)
class Verdict:
    allowed: bool
    reasons: tuple[str, ...]

def evaluate_artifact(evidence: ArtifactEvidence) -> Verdict:
    """Fail closed on missing provenance, secrets, and unsupported claims."""
    import re
    reasons: list[str] = []
    if not isinstance(evidence.client_delivered, bool):
        reasons.append("delivery_class_unverified")
    if not isinstance(evidence.embeds_long_lived_secret, bool):
        reasons.append("secret_scan_unverified")
    if not isinstance(evidence.includes_private_key, bool):
        reasons.append("key_scan_unverified")
    if evidence.embeds_long_lived_secret or evidence.includes_private_key:
        reasons.append("secret_in_distributed_artifact")
    if evidence.provenance_verified is not True:
        reasons.append("provenance_unverified")
    if not isinstance(evidence.artifact_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", evidence.artifact_sha256):
        reasons.append("artifact_digest_invalid")
    if evidence.reconstruction_claim is not None:
        if not isinstance(evidence.reconstruction_claim, ReconstructionClaim):
            reasons.append("reconstruction_claim_invalid")
        elif not evidence.matching_reconstruction_evidence:
            reasons.append("reconstruction_claim_unproven")
    return Verdict(not reasons, tuple(reasons))

def verify_artifact_bytes(payload: bytes, expected_sha256: str) -> Verdict:
    """Independently hash supplied bytes and detect selected high-risk secret markers.

    This is not a general secret scanner and cannot attest that no secrets exist.
    """
    import hashlib
    import hmac
    import re
    reasons = []
    if not isinstance(payload, bytes):
        return Verdict(False, ("artifact_bytes_unavailable",))
    actual = hashlib.sha256(payload).hexdigest()
    if not isinstance(expected_sha256, str) or not hmac.compare_digest(actual, expected_sha256):
        reasons.append("artifact_digest_mismatch")
    markers = (
        rb"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----",
        rb"gh[pousr]_[A-Za-z0-9_]{20,}",
        rb"github_pat_[A-Za-z0-9_]{20,}",
    )
    if any(re.search(marker, payload) for marker in markers):
        reasons.append("high_risk_secret_marker_detected")
    return Verdict(not reasons, tuple(reasons))
