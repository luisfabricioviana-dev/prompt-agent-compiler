"""Wave 21 governed recovery regression: restart evidence and fail-closed tampering."""
import hashlib
import hmac
import tempfile
import unittest
from pathlib import Path
from contracts.bound_provenance import sign_fixture
from contracts.durable_replay_ledger import DurableReplayLedger
from contracts.release_reconciliation import ObserverConfirmation, ReleaseReconciliationError
from contracts.authenticated_release_reconciliation import (
    _canonical, AuthenticatedConfirmation, ObserverAuthenticator,
)
from contracts.governed_release_recovery import GovernedRecovery, legacy_reconciliation_forbidden

KEY = b"fixture-key-for-observer-authentication-32"
OBSERVER = "trusted-observer"


class GovernedRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "replay.db"
        self.ledger = DurableReplayLedger(self.path)
        self.auth = ObserverAuthenticator(observer_id=OBSERVER, verification_key=KEY)
        self.statement = sign_fixture(
            key=b"b" * 32, issuer="issuer", spec_id="spec",
            artifact_id="artifact", run_id="run", payload=b"data", nonce="nonce",
        )
        self.ledger.reserve(self.statement, b"data")
        self.ledger.transition(self.statement, b"data", expected="RESERVED", target="DISPATCHING")
        self.ledger.transition(self.statement, b"data", expected="DISPATCHING", target="UNCERTAIN")

    def observer(self, **fields):
        obs = ObserverConfirmation(**fields, delivery_id="delivery-001")
        signature = hmac.new(KEY, OBSERVER.encode() + b"\x00" + _canonical(obs), hashlib.sha256).hexdigest()
        return AuthenticatedConfirmation(obs, OBSERVER, signature)

    def governed(self):
        return GovernedRecovery(ledger=DurableReplayLedger(self.path), authenticator=self.auth)

    def confirm(self):
        return self.governed().reconcile(
            statement=self.statement, payload=b"data",
            destination_id="destination", observer=self.observer,
        )

    def test_restart_audit_of_authenticated_confirmation(self):
        self.assertEqual(self.confirm(), "CONFIRMED")
        self.assertEqual(self.governed().verify_after_restart(issuer="issuer", nonce="nonce"),
                         (True, "CONFIRMED_EVIDENCE_VERIFIED"))

    def test_uncertain_remains_blocked_without_evidence(self):
        self.assertEqual(self.governed().verify_after_restart(issuer="issuer", nonce="nonce"),
                         (False, "recovery_not_confirmed"))
        self.assertEqual(self.ledger.state(issuer="issuer", nonce="nonce"), "UNCERTAIN")

    def test_missing_evidence_fails_closed_after_restart(self):
        self.confirm()
        with self.ledger._connection() as db:
            db.execute("DELETE FROM release_observer_evidence")
        self.assertEqual(self.governed().verify_after_restart(issuer="issuer", nonce="nonce"),
                         (False, "recovery_evidence_missing"))

    def test_modified_evidence_fails_closed(self):
        self.confirm()
        with self.ledger._connection() as db:
            db.execute("UPDATE release_observer_evidence SET destination_id='wrong'")
        self.assertEqual(self.governed().verify_after_restart(issuer="issuer", nonce="nonce"),
                         (False, "recovery_evidence_digest_mismatch"))

    def test_modified_signature_fails_closed(self):
        self.confirm()
        with self.ledger._connection() as db:
            db.execute("UPDATE release_observer_evidence SET signature='forged'")
        self.assertEqual(self.governed().verify_after_restart(issuer="issuer", nonce="nonce"),
                         (False, "recovery_observer_authentication_failed"))

    def test_legacy_entrypoint_blocks(self):
        with self.assertRaisesRegex(ReleaseReconciliationError, "authenticated_reconciliation_required"):
            legacy_reconciliation_forbidden()
