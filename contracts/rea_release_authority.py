"""Authenticated single-use release authorization for an exact artifact digest.

HMAC verification is a local trust boundary only when the key is provisioned
independently of the submitted artifact. No keys are persisted here.
"""
from __future__ import annotations
from dataclasses import dataclass
import hashlib
import hmac
import re

@dataclass(frozen=True)
class ReleaseAuthorization:
    artifact_sha256: str
    release_id: str
    issuer: str
    signature_hex: str

def verify_release_authorization(auth: ReleaseAuthorization, *, trusted_issuer: str,
                                 trusted_key: bytes, artifact_sha256: str) -> bool:
    if not isinstance(trusted_key, bytes) or len(trusted_key) < 32:
        return False
    if not isinstance(auth, ReleaseAuthorization) or auth.issuer != trusted_issuer:
        return False
    if not isinstance(auth.release_id, str) or not re.fullmatch(r"[A-Za-z0-9_.:-]{8,128}", auth.release_id):
        return False
    if not isinstance(artifact_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", artifact_sha256):
        return False
    if auth.artifact_sha256 != artifact_sha256:
        return False
    if not isinstance(auth.signature_hex, str) or not re.fullmatch(r"[a-f0-9]{64}", auth.signature_hex):
        return False
    data = f"REA-RELEASE-v1\n{auth.issuer}\n{auth.release_id}\n{auth.artifact_sha256}".encode()
    expected = hmac.new(trusted_key, data, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, auth.signature_hex)
