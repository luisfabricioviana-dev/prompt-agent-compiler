"""Wave 19 regression: external observation reconciles, never re-dispatches."""
import tempfile
from pathlib import Path
import unittest
from contracts.bound_provenance import sign_fixture
from contracts.durable_replay_ledger import DurableReplayLedger, ReplayAdmissionError
from contracts.release_reconciliation import (
    ObserverConfirmation, ReleaseReconciliationError, reconcile_confirmed,
)

def signed():
    return sign_fixture(key=b"k"*32,issuer="issuer",spec_id="spec",artifact_id="artifact",
                        run_id="run",payload=b"bytes",nonce="nonce")

def observer(**data):
    return ObserverConfirmation(**data, delivery_id="delivery-123")

class ReconciliationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.ledger=DurableReplayLedger(Path(self.temp.name)/"ledger.sqlite")
        self.statement=signed()
        self.ledger.reserve(self.statement,b"bytes")
        self.ledger.transition(self.statement,b"bytes",expected="RESERVED",target="DISPATCHING")
    def reconcile(self, **changes):
        args=dict(ledger=self.ledger,statement=self.statement,payload=b"bytes",
                  destination_id="destination",observer=observer)
        args.update(changes)
        return reconcile_confirmed(**args)
    def test_uncertain_observation_confirmed(self):
        self.ledger.transition(self.statement,b"bytes",expected="DISPATCHING",target="UNCERTAIN")
        self.assertEqual(self.reconcile(),"CONFIRMED")
        with self.assertRaisesRegex(ReplayAdmissionError,"nonce_already_reserved"):
            DurableReplayLedger(self.ledger.path).reserve(self.statement,b"bytes")
    def test_dispatching_without_observation_remains_blocked(self):
        with self.assertRaisesRegex(ReleaseReconciliationError,"reconciliation_state_not_admissible"):
            self.reconcile()
        self.assertEqual(self.ledger.state(issuer="issuer",nonce="nonce"),"DISPATCHING")
    def test_wrong_destination_observation_denied(self):
        self.ledger.transition(self.statement,b"bytes",expected="DISPATCHING",target="UNCERTAIN")
        def wrong(**data):
            return observer(**{**data,"destination_id":"wrong"})
        with self.assertRaisesRegex(ReleaseReconciliationError,"observer_confirmation_mismatch"):
            self.reconcile(observer=wrong)
        self.assertEqual(self.ledger.state(issuer="issuer",nonce="nonce"),"UNCERTAIN")
    def test_observer_exception_does_not_change_state(self):
        self.ledger.transition(self.statement,b"bytes",expected="DISPATCHING",target="UNCERTAIN")
        def broken(**data): raise RuntimeError("network unavailable")
        with self.assertRaisesRegex(ReleaseReconciliationError,"observer_lookup_failed"):
            self.reconcile(observer=broken)
        self.assertEqual(self.ledger.state(issuer="issuer",nonce="nonce"),"UNCERTAIN")
    def test_unsigned_or_wrong_payload_denied(self):
        self.ledger.transition(self.statement,b"bytes",expected="DISPATCHING",target="UNCERTAIN")
        with self.assertRaisesRegex(ReleaseReconciliationError,"reconciliation_payload_mismatch"):
            self.reconcile(payload=b"tampered")
    def test_repeated_confirmation_is_not_reaccepted(self):
        self.ledger.transition(self.statement,b"bytes",expected="DISPATCHING",target="UNCERTAIN")
        self.reconcile()
        with self.assertRaisesRegex(ReleaseReconciliationError,"reconciliation_state_not_admissible"):
            self.reconcile()

if __name__=="__main__":
    unittest.main()
