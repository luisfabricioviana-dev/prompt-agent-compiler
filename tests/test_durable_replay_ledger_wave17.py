"""Durable replay admission: restart, replay and invalid transition regression."""
import tempfile
from pathlib import Path
import unittest

from contracts.bound_provenance import sign_fixture
from contracts.durable_replay_ledger import DurableReplayLedger, ReplayAdmissionError

KEY = b"k" * 32
def statement(nonce="n1", run="r1", payload=b"artifact"):
    return sign_fixture(key=KEY, issuer="fixture", spec_id="spec",
                        artifact_id="a", run_id=run, payload=payload, nonce=nonce)

class DurableReplayLedgerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "ledger.sqlite"
        self.ledger = DurableReplayLedger(self.path)

    def test_reservation_survives_new_instance(self):
        signed=statement()
        self.assertEqual(self.ledger.reserve(signed,b"artifact"),"RESERVED")
        other=DurableReplayLedger(self.path)
        self.assertEqual(other.state(issuer="fixture",nonce="n1"),"RESERVED")
        with self.assertRaisesRegex(ReplayAdmissionError,"nonce_already_reserved"):
            other.reserve(signed,b"artifact")

    def test_same_nonce_other_context_denied(self):
        self.ledger.reserve(statement(),b"artifact")
        with self.assertRaisesRegex(ReplayAdmissionError,"nonce_context_conflict"):
            self.ledger.reserve(statement(run="other"),b"artifact")

    def test_different_nonce_is_new_attempt(self):
        self.ledger.reserve(statement(),b"artifact")
        self.assertEqual(self.ledger.reserve(statement(nonce="n2"),b"artifact"),"RESERVED")

    def test_transition_sequence_and_no_automatic_retry(self):
        signed=statement()
        self.ledger.reserve(signed,b"artifact")
        self.assertEqual(self.ledger.transition(signed,b"artifact",expected="RESERVED",target="DISPATCHING"),"DISPATCHING")
        other=DurableReplayLedger(self.path)
        with self.assertRaisesRegex(ReplayAdmissionError,"nonce_already_reserved"):
            other.reserve(signed,b"artifact")
        with self.assertRaisesRegex(ReplayAdmissionError,"replay_transition_not_allowed"):
            other.transition(signed,b"artifact",expected="DISPATCHING",target="RESERVED")
        other.transition(signed,b"artifact",expected="DISPATCHING",target="UNCERTAIN")
        other.transition(signed,b"artifact",expected="UNCERTAIN",target="CONFIRMED")
        self.assertEqual(other.state(issuer="fixture",nonce="n1"),"CONFIRMED")

    def test_invalid_digest_does_not_reserve(self):
        with self.assertRaisesRegex(ReplayAdmissionError,"payload_digest_mismatch"):
            self.ledger.reserve(statement(),b"tampered")
        self.assertIsNone(self.ledger.state(issuer="fixture",nonce="n1"))

    def test_invalid_state_transition_leaves_record(self):
        signed=statement()
        self.ledger.reserve(signed,b"artifact")
        with self.assertRaisesRegex(ReplayAdmissionError,"replay_state_or_context_mismatch"):
            self.ledger.transition(signed,b"artifact",expected="DISPATCHED",target="CONFIRMED")
        self.assertEqual(self.ledger.state(issuer="fixture",nonce="n1"),"RESERVED")

if __name__=="__main__":
    unittest.main()
