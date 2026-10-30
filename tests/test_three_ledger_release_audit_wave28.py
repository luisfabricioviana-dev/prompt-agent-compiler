"""Wave 28: tri-ledger audit must be fail-closed and free of side effects."""
import hashlib
import sqlite3
import tempfile
import unittest
from pathlib import Path

from contracts.bound_provenance import sign_fixture
from contracts.durable_replay_ledger import DurableReplayLedger
from contracts.authenticated_release_reconciliation import ObserverAuthenticator
from contracts.governed_release_recovery import GovernedRecovery
from contracts.cross_ledger_binding import CrossLedgerBindingVerifier, sign_binding_fixture
from contracts.durable_cross_ledger_binding_registry import DurableBindingRegistry
from contracts.three_ledger_release_audit import audit_three_ledgers

KEY=b"k"*32
DIGEST=hashlib.sha256(b"data").hexdigest()


class ThreeLedgerTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root=Path(tmp.name)
        self.ledger=DurableReplayLedger(root/"replay.sqlite")
        self.rea=sqlite3.connect(root/"rea.sqlite")
        self.addCleanup(self.rea.close)
        self.rea.execute("CREATE TABLE rea_release_claims (release_id TEXT PRIMARY KEY, artifact_sha256 TEXT NOT NULL)")
        self.rea.execute("INSERT INTO rea_release_claims VALUES (?,?)",("release-28",DIGEST))
        self.rea.commit()
        self.registry=DurableBindingRegistry(root/"bindings.sqlite")
        self.binding=sign_binding_fixture(key=KEY,issuer="issuer",nonce="nonce",
            release_id="release-28",artifact_sha256=DIGEST,destination_id="destination")
        self.verifier=CrossLedgerBindingVerifier(trusted_issuer="issuer",verification_key=KEY)
        self.registry.reserve(binding=self.binding,verifier=self.verifier)
        self.recovery=GovernedRecovery(ledger=self.ledger,
            authenticator=ObserverAuthenticator(observer_id="observer",verification_key=KEY))
        self.statement=sign_fixture(key=KEY,issuer="issuer",nonce="nonce",spec_id="spec",
            artifact_id="artifact",run_id="run",payload=b"data")
        self.ledger.reserve(self.statement,b"data")
        self.ledger.transition(self.statement,b"data",expected="RESERVED",target="DISPATCHING")
        self.ledger.transition(self.statement,b"data",expected="DISPATCHING",target="UNCERTAIN")

    def check(self,**overrides):
        args=dict(ledger=self.ledger,rea_conn=self.rea,recovery=self.recovery,
            issuer="issuer",nonce="nonce",release_id="release-28",
            artifact_sha256=DIGEST,destination_id="destination",observer_id="observer",
            observer_key=KEY,binding=self.binding,binding_verifier=self.verifier,
            binding_registry=self.registry)
        args.update(overrides)
        return audit_three_ledgers(**args)

    def test_uncertain_never_authorizes_retry(self):
        result=self.check()
        self.assertEqual(result.status,"IN_DOUBT")
        self.assertTrue(result.reason.startswith("no_retry:"))
        self.assertEqual(self.ledger.state(issuer="issuer",nonce="nonce"),"UNCERTAIN")

    def test_missing_registration_blocks(self):
        other=DurableBindingRegistry(Path(self.registry.path).parent/"empty.sqlite")
        self.assertEqual(self.check(binding_registry=other).status,"BLOCK")

    def test_forged_binding_blocks(self):
        from dataclasses import replace
        self.assertEqual(self.check(binding=replace(self.binding,signature="0"*64)).status,"BLOCK")

    def test_wrong_release_blocks(self):
        self.assertEqual(self.check(release_id="different").status,"BLOCK")

    def test_wrong_destination_blocks(self):
        self.assertEqual(self.check(destination_id="wrong").status,"BLOCK")

    def test_wrong_digest_blocks(self):
        self.assertEqual(self.check(artifact_sha256="0"*64).status,"BLOCK")

    def test_audit_does_not_modify_registry_or_ledger(self):
        initial=self.registry.matches(self.binding)
        self.check()
        self.assertEqual(self.registry.matches(self.binding),initial)
        self.assertEqual(self.ledger.state(issuer="issuer",nonce="nonce"),"UNCERTAIN")


if __name__=="__main__":
    unittest.main()
