"""Wave 19 legacy entrypoint is retired in Wave 23: no unverified confirmation."""
import tempfile
from pathlib import Path
import unittest
from contracts.bound_provenance import sign_fixture
from contracts.durable_replay_ledger import DurableReplayLedger, ReplayAdmissionError
from contracts.release_reconciliation import ObserverConfirmation, ReleaseReconciliationError, reconcile_confirmed


class LegacyReconciliationBlockedTests(unittest.TestCase):
    def test_legacy_confirmation_cannot_change_uncertain(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = DurableReplayLedger(Path(tmp) / "ledger.sqlite")
            statement = sign_fixture(key=b"k" * 32, issuer="issuer",
                spec_id="spec", artifact_id="artifact", run_id="run",
                payload=b"bytes", nonce="nonce")
            ledger.reserve(statement, b"bytes")
            ledger.transition(statement, b"bytes", expected="RESERVED", target="DISPATCHING")
            ledger.transition(statement, b"bytes", expected="DISPATCHING", target="UNCERTAIN")
            calls = []
            def observer(**identity):
                calls.append(identity)
                return ObserverConfirmation(**identity, delivery_id="delivery-123")
            with self.assertRaisesRegex(ReleaseReconciliationError, "authenticated_reconciliation_required"):
                reconcile_confirmed(ledger=ledger, statement=statement,
                    payload=b"bytes", destination_id="destination", observer=observer)
            self.assertEqual(calls, [])
            self.assertEqual(ledger.state(issuer="issuer", nonce="nonce"), "UNCERTAIN")
            with self.assertRaisesRegex(ReplayAdmissionError, "nonce_already_reserved"):
                DurableReplayLedger(ledger.path).reserve(statement, b"bytes")

    def test_legacy_confirmation_rejected_even_with_missing_dependencies(self):
        with self.assertRaisesRegex(ReleaseReconciliationError, "authenticated_reconciliation_required"):
            reconcile_confirmed(ledger=None, statement=None, payload=b"",
                destination_id="destination", observer=lambda **k: None)


if __name__ == "__main__":
    unittest.main()
