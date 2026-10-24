import hashlib
import hmac
import sqlite3
import unittest

from rea_signed_release_bridge import run_signed_optional_release
from rea_trusted_provenance_canary import SignedProvenance, signature_message

KEY = b"test-fixture-signing-key-1234567890-long"
ISSUER = "fixture-issuer"

def signed(payload):
    digest = hashlib.sha256(payload).hexdigest()
    signature = hmac.new(KEY, signature_message(ISSUER, "fixture:source", digest), hashlib.sha256).hexdigest()
    return SignedProvenance(ISSUER, "fixture:source", digest, signature)

def execute(payload, statement, *, enable=False):
    effects = []
    with sqlite3.connect(":memory:") as db:
        result = run_signed_optional_release(
            db, payload, statement, None, trusted_provenance_issuer=ISSUER,
            verification_key=KEY, issuer="release-issuer", issuer_key=b"",
            destination_id="example/repo", observer_id="observer", observer_key=b"",
            dispatch=lambda *_: effects.append("DISPATCH"),
            observe=lambda *_: effects.append("OBSERVE"),
            enable_dispatch=enable,
            trusted_destination_resolver=lambda: effects.append("RESOLVE"))
    return result, effects

class SignedReleaseBridgeTests(unittest.TestCase):
    def test_tampered_bytes_block_before_any_callback(self):
        result, effects = execute(b"tampered", signed(b"original"), enable=True)
        self.assertEqual(result.state, "BLOCKED")
        self.assertEqual(effects, [])

    def test_unsigned_statement_block_before_any_callback(self):
        result, effects = execute(b"fixture", None, enable=True)
        self.assertEqual(result.state, "BLOCKED")
        self.assertEqual(effects, [])

    def test_valid_signature_default_is_dry_run(self):
        payload = b"fixture"
        result, effects = execute(payload, signed(payload))
        self.assertEqual(result.state, "DRY_RUN")
        self.assertEqual(effects, [])

    def test_signed_secret_marker_blocks_before_callback(self):
        payload = b"-----BEGIN RSA PRIVATE KEY-----\\nfixture"
        result, effects = execute(payload, signed(payload), enable=True)
        self.assertEqual(result.state, "BLOCKED")
        self.assertEqual(effects, [])

if __name__ == "__main__":
    unittest.main()
