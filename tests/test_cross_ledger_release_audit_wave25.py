"""Wave 25: cross-ledger audit is read-only and never authorizes replay."""
import hashlib
import hmac
import sqlite3
import tempfile
from pathlib import Path
import unittest

from contracts.bound_provenance import sign_fixture
from contracts.durable_replay_ledger import DurableReplayLedger
from contracts.authenticated_release_reconciliation import (
    ObserverAuthenticator, AuthenticatedConfirmation, _canonical)
from contracts.release_reconciliation import ObserverConfirmation
from contracts.governed_release_recovery import GovernedRecovery
from contracts.rea_release_reconciliation import DestinationObservation, reconcile_delivery
from contracts.cross_ledger_release_audit import audit_cross_ledger

KEY = b"observer-key-for-wave25-fixtures-1234"
OBS = "trusted-observer"
DEST = "destination"
RELEASE = "release-25"
PAYLOAD = b"payload-wave25"
DIGEST = hashlib.sha256(PAYLOAD).hexdigest()


class CrossLedgerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.ledger = DurableReplayLedger(Path(self.tmp.name) / "replay.db")
        self.db = sqlite3.connect(Path(self.tmp.name) / "rea.db")
        self.addCleanup(self.db.close)
        self.db.execute("CREATE TABLE rea_release_claims "
                        "(release_id TEXT PRIMARY KEY, artifact_sha256 TEXT NOT NULL)")
        self.db.execute("INSERT INTO rea_release_claims VALUES (?,?)", (RELEASE, DIGEST))
        self.db.commit()
        self.statement = sign_fixture(
            key=b"p" * 32, issuer="issuer", spec_id="spec", artifact_id="artifact",
            run_id="run", payload=PAYLOAD, nonce="nonce")
        self.ledger.reserve(self.statement, PAYLOAD)
        self.ledger.transition(self.statement, PAYLOAD, expected="RESERVED", target="DISPATCHING")
        self.ledger.transition(self.statement, PAYLOAD, expected="DISPATCHING", target="UNCERTAIN")
        self.auth = ObserverAuthenticator(observer_id=OBS, verification_key=KEY)
        self.recovery = GovernedRecovery(ledger=self.ledger, authenticator=self.auth)

    def args(self):
        return dict(ledger=self.ledger, rea_conn=self.db, recovery=self.recovery,
                    issuer="issuer", nonce="nonce", release_id=RELEASE,
                    artifact_sha256=DIGEST, destination_id=DEST,
                    observer_id=OBS, observer_key=KEY)

    def observe_replay(self, **data):
        obs = ObserverConfirmation(**data, delivery_id="delivery-25")
        sig = hmac.new(KEY, OBS.encode() + b"\x00" + _canonical(obs), hashlib.sha256).hexdigest()
        return AuthenticatedConfirmation(obs, OBS, sig)

    def observe_rea(self, release_id, destination_id):
        msg = f"REA-DESTINATION-v2\n{OBS}\n{release_id}\n{DIGEST}\n{destination_id}\ndelivered".encode()
        sig = hmac.new(KEY, msg, hashlib.sha256).hexdigest()
        return DestinationObservation(release_id, DIGEST, destination_id, True, sig)

    def confirm_both(self):
        self.recovery.reconcile(statement=self.statement, payload=PAYLOAD,
                                destination_id=DEST, observer=self.observe_replay)
        self.assertEqual(reconcile_delivery(
            self.db, release_id=RELEASE, artifact_sha256=DIGEST,
            expected_destination=DEST, observe=self.observe_rea,
            trusted_observer_key=KEY, trusted_observer_id=OBS),
            (True, "DELIVERY_CONFIRMED"))

    def test_confirmed_both_restarts_consistent(self):
        self.confirm_both()
        self.assertEqual(audit_cross_ledger(**self.args()).state, "CONSISTENT")
        self.assertEqual(DurableReplayLedger(self.ledger.path).state(
            issuer="issuer", nonce="nonce"), "CONFIRMED")

    def test_uncertain_replay_never_authorizes_retry(self):
        result = audit_cross_ledger(**self.args())
        self.assertEqual(result.state, "IN_DOUBT")
        self.assertEqual(self.ledger.state(issuer="issuer", nonce="nonce"), "UNCERTAIN")

    def test_rea_evidence_missing_blocks(self):
        self.confirm_both()
        self.db.execute("DELETE FROM rea_release_observer_evidence")
        self.db.commit()
        self.assertEqual(audit_cross_ledger(**self.args()).state, "BLOCK")

    def test_cross_ledger_digest_mismatch_blocks(self):
        self.confirm_both()
        args = self.args()
        args["artifact_sha256"] = "0" * 64
        self.assertEqual(audit_cross_ledger(**args).reason, "audit_artifact_digest_mismatch")

    def test_cross_ledger_destination_mismatch_blocks(self):
        self.confirm_both()
        args = self.args()
        args["destination_id"] = "other"
        self.assertEqual(audit_cross_ledger(**args).state, "BLOCK")

    def test_recovery_for_another_database_is_rejected(self):
        args = self.args()
        args["recovery"] = GovernedRecovery(
            ledger=DurableReplayLedger(Path(self.tmp.name) / "other.db"),
            authenticator=self.auth)
        self.assertEqual(audit_cross_ledger(**args).state, "BLOCK")


if __name__ == "__main__":
    unittest.main()
