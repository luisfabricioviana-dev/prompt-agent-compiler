"""Wave29: stable audit observes changes without mutating delivery records."""
import hashlib
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from contracts.bound_provenance import sign_fixture
from contracts.durable_replay_ledger import DurableReplayLedger
from contracts.authenticated_release_reconciliation import ObserverAuthenticator
from contracts.governed_release_recovery import GovernedRecovery
from contracts.cross_ledger_binding import CrossLedgerBindingVerifier, sign_binding_fixture
from contracts.durable_cross_ledger_binding_registry import DurableBindingRegistry
from contracts.stable_three_ledger_audit import audit_stable_three_ledgers
from contracts.three_ledger_release_audit import ThreeLedgerVerdict


class StableReadTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.ledger = DurableReplayLedger(root / "replay.db")
        self.rea = sqlite3.connect(root / "rea.db")
        self.addCleanup(self.rea.close)
        digest = hashlib.sha256(b"payload").hexdigest()
        self.rea.execute("CREATE TABLE rea_release_claims "
                         "(release_id TEXT PRIMARY KEY, artifact_sha256 TEXT NOT NULL)")
        self.rea.execute("INSERT INTO rea_release_claims VALUES (?,?)", ("release-29", digest))
        self.rea.commit()
        self.registry = DurableBindingRegistry(root / "binding.db")
        self.binding = sign_binding_fixture(key=b"k"*32, issuer="issuer", nonce="nonce",
            release_id="release-29", artifact_sha256=digest, destination_id="destination")
        self.verifier = CrossLedgerBindingVerifier(trusted_issuer="issuer", verification_key=b"k"*32)
        self.registry.reserve(binding=self.binding, verifier=self.verifier)
        self.recovery = GovernedRecovery(ledger=self.ledger,
            authenticator=ObserverAuthenticator(observer_id="observer", verification_key=b"k"*32))
        self.statement = sign_fixture(key=b"k"*32, issuer="issuer", nonce="nonce",
            spec_id="spec", artifact_id="artifact", run_id="run", payload=b"payload")
        self.ledger.reserve(self.statement, b"payload")
        self.ledger.transition(self.statement, b"payload", expected="RESERVED", target="DISPATCHING")
        self.args = dict(ledger=self.ledger, rea_conn=self.rea, recovery=self.recovery,
            issuer="issuer", nonce="nonce", release_id="release-29",
            artifact_sha256=digest, destination_id="destination",
            observer_id="observer", observer_key=b"k"*32, binding=self.binding,
            binding_verifier=self.verifier, binding_registry=self.registry)

    def test_no_mutation_and_in_doubt(self):
        verdict = audit_stable_three_ledgers(**self.args)
        self.assertEqual(verdict.status, "IN_DOUBT")
        self.assertEqual(self.ledger.state(issuer="issuer", nonce="nonce"), "DISPATCHING")

    def test_concurrent_state_change_blocks(self):
        def change(**kwargs):
            self.ledger.transition(self.statement, b"payload",
                                   expected="DISPATCHING", target="UNCERTAIN")
            return ThreeLedgerVerdict("CONSISTENT", "simulated")
        with patch("contracts.stable_three_ledger_audit.audit_three_ledgers", side_effect=change):
            verdict = audit_stable_three_ledgers(**self.args)
        self.assertEqual(verdict, ThreeLedgerVerdict("BLOCK", "concurrent_ledger_change_detected"))

    def test_concurrent_rea_claim_change_blocks(self):
        def change(**kwargs):
            self.rea.execute("UPDATE rea_release_claims SET artifact_sha256=?", ("f"*64,))
            self.rea.commit()
            return ThreeLedgerVerdict("CONSISTENT", "simulated")
        with patch("contracts.stable_three_ledger_audit.audit_three_ledgers", side_effect=change):
            verdict = audit_stable_three_ledgers(**self.args)
        self.assertEqual(verdict.status, "BLOCK")

    def test_missing_registry_and_invalid_dependencies_fail_closed(self):
        args = {**self.args, "binding_registry": None}
        self.assertEqual(audit_stable_three_ledgers(**args).status, "BLOCK")

if __name__ == "__main__":
    unittest.main()
