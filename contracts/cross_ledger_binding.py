"""Domain-separated authenticated binding between replay and REA identities.

The issuer key is provisioned externally. Signing helper is fixture-only.
Never dispatches or modifies a ledger.
"""
from __future__ import annotations
from dataclasses import dataclass
import hashlib
import hmac
import json


@dataclass(frozen=True)
class CrossLedgerBinding:
    issuer: str
    nonce: str
    release_id: str
    artifact_sha256: str
    destination_id: str
    signature: str


def _message(binding: CrossLedgerBinding) -> bytes:
    fields = (binding.issuer, binding.nonce, binding.release_id,
              binding.artifact_sha256, binding.destination_id)
    if any(not isinstance(x, str) or not x.strip() for x in fields):
        raise ValueError("cross_ledger_identity_invalid")
    return b"PAC-REA-CROSS-LEDGER-BINDING-v1\x00" + json.dumps(
        fields, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


class CrossLedgerBindingVerifier:
    def __init__(self, *, trusted_issuer: str, verification_key: bytes):
        if not isinstance(trusted_issuer, str) or not trusted_issuer.strip():
            raise ValueError("binding_issuer_required")
        if not isinstance(verification_key, bytes) or len(verification_key) < 32:
            raise ValueError("binding_key_invalid")
        self._issuer = trusted_issuer
        self._key = verification_key

    def verify(self, *, binding: CrossLedgerBinding, issuer: str, nonce: str,
               release_id: str, artifact_sha256: str, destination_id: str) -> bool:
        if not isinstance(binding, CrossLedgerBinding):
            return False
        if (binding.issuer, binding.nonce, binding.release_id,
            binding.artifact_sha256, binding.destination_id) != (
                issuer, nonce, release_id, artifact_sha256, destination_id):
            return False
        if binding.issuer != self._issuer or not isinstance(binding.signature, str):
            return False
        try:
            actual = hmac.new(self._key, _message(binding), hashlib.sha256).hexdigest()
            return hmac.compare_digest(actual, binding.signature)
        except (ValueError, TypeError):
            return False


def sign_binding_fixture(*, key: bytes, issuer: str, nonce: str, release_id: str,
                         artifact_sha256: str, destination_id: str) -> CrossLedgerBinding:
    unsigned = CrossLedgerBinding(issuer, nonce, release_id, artifact_sha256, destination_id, "")
    return CrossLedgerBinding(issuer, nonce, release_id, artifact_sha256, destination_id,
                              hmac.new(key, _message(unsigned), hashlib.sha256).hexdigest())
