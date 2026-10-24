import hashlib
import hmac
import unittest

from rea_trusted_provenance_canary import (
    SignedProvenance, inspect_signed_candidate, signature_message,
)

KEY = b"test-only-signer-key-not-for-production-123456"
ISSUER = "offline-test-issuer"
SOURCE = "fixture:source-commit"

def signed(payload):
    digest = hashlib.sha256(payload).hexdigest()
    tag = hmac.new(KEY, signature_message(ISSUER, SOURCE, digest), hashlib.sha256).hexdigest()
    return SignedProvenance(ISSUER, SOURCE, digest, tag)

class TrustedProvenanceCanaryTests(unittest.TestCase):
    def test_signed_fixture_eligible_but_not_published(self):
        result = inspect_signed_candidate(
            b"harmless artifact", signed(b"harmless artifact"),
            trusted_issuer=ISSUER, verification_key=KEY)
        self.assertEqual(result["state"], "ADMISSIBLE_CANDIDATE")
        self.assertFalse(result["publication_performed"])
        self.assertFalse(result["production_issuer_custody_certified"])

    def test_modified_bytes_block(self):
        result = inspect_signed_candidate(
            b"tampered artifact", signed(b"harmless artifact"),
            trusted_issuer=ISSUER, verification_key=KEY)
        self.assertEqual(result["state"], "BLOCKED")

    def test_wrong_issuer_block(self):
        result = inspect_signed_candidate(
            b"harmless artifact", signed(b"harmless artifact"),
            trusted_issuer="other", verification_key=KEY)
        self.assertEqual(result["state"], "BLOCKED")

    def test_wrong_key_block(self):
        result = inspect_signed_candidate(
            b"harmless artifact", signed(b"harmless artifact"),
            trusted_issuer=ISSUER, verification_key=b"different-signing-key-for-fixture-only")
        self.assertEqual(result["state"], "BLOCKED")

    def test_missing_trusted_key_block(self):
        result = inspect_signed_candidate(
            b"harmless artifact", signed(b"harmless artifact"),
            trusted_issuer=ISSUER, verification_key=b"")
        self.assertEqual(result["state"], "BLOCKED")

    def test_secret_marker_block_even_with_signature(self):
        payload = b"-----BEGIN RSA PRIVATE KEY-----\nfixture"
        result = inspect_signed_candidate(
            payload, signed(payload), trusted_issuer=ISSUER, verification_key=KEY)
        self.assertEqual(result["state"], "BLOCKED")
        self.assertIn("high_risk_secret_marker_detected", result["reasons"])

if __name__ == "__main__":
    unittest.main()
