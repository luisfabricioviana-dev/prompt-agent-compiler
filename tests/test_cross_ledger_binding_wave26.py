"""Wave 26 authenticated correlation prevents misbinding and replay substitution."""
import unittest
from dataclasses import replace
from contracts.cross_ledger_binding import (
    CrossLedgerBindingVerifier, sign_binding_fixture,
)

KEY = b"independent-fixture-binding-secret-32bytes"


class SignedBindingTests(unittest.TestCase):
    def setUp(self):
        self.verifier = CrossLedgerBindingVerifier(
            trusted_issuer="issuer", verification_key=KEY)
        self.identity = dict(
            issuer="issuer", nonce="nonce", release_id="release-26",
            artifact_sha256="a"*64, destination_id="destination")
        self.binding = sign_binding_fixture(key=KEY, **self.identity)

    def verify(self, binding=None, **override):
        return self.verifier.verify(binding=binding if binding is not None else self.binding,
                                    **{**self.identity, **override})

    def test_valid_binding(self):
        self.assertTrue(self.verify())

    def test_missing_binding_rejected(self):
        self.assertFalse(self.verifier.verify(binding=None, **self.identity))

    def test_signature_forgery_rejected(self):
        self.assertFalse(self.verify(binding=replace(self.binding, signature="0"*64)))

    def test_nonce_reuse_with_distinct_release_rejected(self):
        self.assertFalse(self.verify(release_id="different-release"))

    def test_destination_substitution_rejected(self):
        self.assertFalse(self.verify(destination_id="different-destination"))

    def test_digest_substitution_rejected(self):
        self.assertFalse(self.verify(artifact_sha256="b"*64))

    def test_untrusted_issuer_rejected(self):
        self.assertFalse(self.verify(issuer="another-issuer"))

    def test_wrong_key_rejected(self):
        wrong = CrossLedgerBindingVerifier(
            trusted_issuer="issuer", verification_key=b"z"*32)
        self.assertFalse(wrong.verify(binding=self.binding, **self.identity))


if __name__ == "__main__":
    unittest.main()
