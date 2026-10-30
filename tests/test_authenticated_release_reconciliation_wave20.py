"""Wave 20: authentication, durable evidence, crash-safe rollback, no dispatch."""
import hashlib
import hmac
import json
import sqlite3
import tempfile
from pathlib import Path
import unittest
from contracts.bound_provenance import sign_fixture
from contracts.durable_replay_ledger import DurableReplayLedger, ReplayAdmissionError
from contracts.release_reconciliation import ObserverConfirmation, ReleaseReconciliationError
from contracts.authenticated_release_reconciliation import (
    AuthenticatedConfirmation, ObserverAuthenticator, _canonical,
    reconcile_authenticated,
)

KEY = b"observer-secret-for-fixtures-only-32bytes"
OBS = "observer-A"


def envelope(data, *, key=KEY, observer_id=OBS):
    confirmation = ObserverConfirmation(**data, delivery_id="delivery-123")
    message = observer_id.encode("utf-8") + b"\x00" + _canonical(confirmation)
    return AuthenticatedConfirmation(confirmation, observer_id, hmac.new(key, message, hashlib.sha256).hexdigest())


class AuthenticatedReconciliationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.ledger = DurableReplayLedger(Path(self.temp.name) / "ledger.sqlite")
        self.statement = sign_fixture(key=b"k" * 32, issuer="issuer", spec_id="spec",
                                      artifact_id="artifact", run_id="run", payload=b"bytes", nonce="nonce")
        self.ledger.reserve(self.statement, b"bytes")
        self.ledger.transition(self.statement, b"bytes", expected="RESERVED", target="DISPATCHING")
        self.ledger.transition(self.statement, b"bytes", expected="DISPATCHING", target="UNCERTAIN")
        self.authenticator = ObserverAuthenticator(observer_id=OBS, verification_key=KEY)

    def reconcile(self, observer=None, **kwargs):
        if observer is None:
            observer = lambda **data: envelope(data)
        args = dict(ledger=self.ledger, statement=self.statement, payload=b"bytes",
                    destination_id="destination", observer=observer,
                    authenticator=self.authenticator)
        args.update(kwargs)
        return reconcile_authenticated(**args)

    def evidence(self):
        with self.ledger._connection() as db:
            return db.execute("SELECT observer_id, delivery_id, destination_id, evidence_sha256 "
                              "FROM release_observer_evidence WHERE issuer='issuer' AND nonce='nonce'").fetchone()

    def test_authenticated_confirmation_persisted_across_restart_and_no_replay(self):
        self.assertEqual(self.reconcile(), "CONFIRMED")
        self.assertEqual(self.evidence()[:3], (OBS, "delivery-123", "destination"))
        self.assertEqual(DurableReplayLedger(self.ledger.path).state(issuer="issuer", nonce="nonce"), "CONFIRMED")
        with self.assertRaises(ReplayAdmissionError):
            DurableReplayLedger(self.ledger.path).reserve(self.statement, b"bytes")

    def test_forged_observer_signature_rejected(self):
        with self.assertRaisesRegex(ReleaseReconciliationError, "observer_authentication_failed"):
            self.reconcile(observer=lambda **data: envelope(data, key=b"wrong" * 8))
        self.assertEqual(self.ledger.state(issuer="issuer", nonce="nonce"), "UNCERTAIN")

    def test_correlated_but_wrong_destination_rejected(self):
        def wrong(**data):
            data["destination_id"] = "other"
            return envelope(data)
        with self.assertRaisesRegex(ReleaseReconciliationError, "observer_confirmation_mismatch"):
            self.reconcile(observer=wrong)
        self.assertEqual(self.ledger.state(issuer="issuer", nonce="nonce"), "UNCERTAIN")

    def test_observer_failure_leaves_uncertain(self):
        def offline(**_):
            raise TimeoutError("unavailable")
        with self.assertRaisesRegex(ReleaseReconciliationError, "observer_lookup_failed"):
            self.reconcile(observer=offline)
        self.assertEqual(self.ledger.state(issuer="issuer", nonce="nonce"), "UNCERTAIN")

    def test_repeated_confirmation_rejected(self):
        self.reconcile()
        with self.assertRaisesRegex(ReleaseReconciliationError, "reconciliation_state_not_admissible"):
            self.reconcile()

    def test_evidence_insert_failure_rolls_back_state(self):
        with self.ledger._connection() as db:
            db.execute("CREATE TABLE release_observer_evidence (issuer TEXT PRIMARY KEY)")
        with self.assertRaisesRegex(ReleaseReconciliationError, "observer_evidence_persistence_failed"):
            self.reconcile()
        self.assertEqual(self.ledger.state(issuer="issuer", nonce="nonce"), "UNCERTAIN")

    def test_missing_or_wrong_authenticator_rejected(self):
        with self.assertRaisesRegex(ReleaseReconciliationError, "reconciliation_dependencies_invalid"):
            self.reconcile(authenticator=None)
        with self.assertRaisesRegex(ReleaseReconciliationError, "observer_authentication_failed"):
            self.reconcile(authenticator=ObserverAuthenticator(observer_id="other", verification_key=KEY))

    def test_wrong_payload_rejected(self):
        with self.assertRaisesRegex(ReleaseReconciliationError, "reconciliation_payload_invalid"):
            self.reconcile(payload=b"altered")


if __name__ == "__main__":
    unittest.main()
