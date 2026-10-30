"""Wave 27 immutable binding registry regression."""
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path

from contracts.cross_ledger_binding import CrossLedgerBindingVerifier, sign_binding_fixture
from contracts.durable_cross_ledger_binding_registry import DurableBindingRegistry, BindingRegistryError

KEY = b"binding-fixture-key-for-wave27-32bytes"


class RegistryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "bindings.sqlite"
        self.registry = DurableBindingRegistry(self.path)
        self.verifier = CrossLedgerBindingVerifier(trusted_issuer="issuer", verification_key=KEY)
        self.args = dict(issuer="issuer", nonce="nonce", release_id="release-27",
                         artifact_sha256="a"*64, destination_id="dest")
        self.binding = sign_binding_fixture(key=KEY, **self.args)

    def test_restart_and_idempotent_reservation(self):
        self.assertEqual(self.registry.reserve(binding=self.binding, verifier=self.verifier), "RESERVED")
        reopened = DurableBindingRegistry(self.path)
        self.assertTrue(reopened.matches(self.binding))
        self.assertEqual(reopened.reserve(binding=self.binding, verifier=self.verifier), "ALREADY_RESERVED")

    def test_same_nonce_different_release_denied(self):
        self.registry.reserve(binding=self.binding, verifier=self.verifier)
        other = sign_binding_fixture(key=KEY, **{**self.args, "release_id": "other-release"})
        with self.assertRaisesRegex(BindingRegistryError, "binding_identity_conflict"):
            self.registry.reserve(binding=other, verifier=self.verifier)

    def test_same_release_different_nonce_denied(self):
        self.registry.reserve(binding=self.binding, verifier=self.verifier)
        other = sign_binding_fixture(key=KEY, **{**self.args, "nonce": "other-nonce"})
        with self.assertRaisesRegex(BindingRegistryError, "binding_release_id_conflict"):
            self.registry.reserve(binding=other, verifier=self.verifier)

    def test_forged_binding_denied_without_row(self):
        with self.assertRaisesRegex(BindingRegistryError, "binding_signature_invalid"):
            self.registry.reserve(binding=replace(self.binding, signature="0"*64),
                                  verifier=self.verifier)
        self.assertFalse(self.registry.matches(self.binding))

    def test_concurrent_same_binding_single_reservation(self):
        def attempt(_):
            return DurableBindingRegistry(self.path).reserve(
                binding=self.binding, verifier=self.verifier)
        with ThreadPoolExecutor(max_workers=6) as pool:
            results = list(pool.map(attempt, range(12)))
        self.assertEqual(results.count("RESERVED"), 1)
        self.assertEqual(results.count("ALREADY_RESERVED"), 11)

    def test_concurrent_conflicting_bindings_fail_closed(self):
        other = sign_binding_fixture(key=KEY, **{**self.args, "release_id": "release-28"})
        def attempt(binding):
            try:
                return DurableBindingRegistry(self.path).reserve(
                    binding=binding, verifier=self.verifier)
            except BindingRegistryError:
                return "BLOCK"
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(attempt, [self.binding, other]))
        self.assertEqual(sorted(results), ["BLOCK", "RESERVED"])


if __name__ == "__main__":
    unittest.main()
