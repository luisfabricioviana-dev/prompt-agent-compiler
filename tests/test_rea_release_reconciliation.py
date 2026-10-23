import hashlib
import hmac
import sqlite3
import unittest
from contracts.rea_release_reconciliation import DestinationObservation, reconcile_delivery

class ReconciliationTests(unittest.TestCase):
    RELEASE = "release-001"
    SHA = hashlib.sha256(b"artifact").hexdigest()
    DEST = "destination-A"
    KEY = b"separate-observer-key-for-tests-only-123456"

    def setup_claim(self, db):
        db.execute("CREATE TABLE rea_release_claims (release_id TEXT PRIMARY KEY, artifact_sha256 TEXT NOT NULL)")
        db.execute("INSERT INTO rea_release_claims VALUES (?, ?)", (self.RELEASE, self.SHA))
        db.commit()

    def observe(self, release_id, destination_id):
        data = f"REA-DESTINATION-v1\n{release_id}\n{self.SHA}\n{destination_id}\ndelivered".encode()
        sig = hmac.new(self.KEY, data, hashlib.sha256).hexdigest()
        return DestinationObservation(release_id, self.SHA, destination_id, True, sig)

    def check(self, db, release_id=None, observe=None, key=None):
        return reconcile_delivery(
            db, release_id=release_id or self.RELEASE,
            artifact_sha256=self.SHA, expected_destination=self.DEST,
            observe=observe or self.observe, trusted_observer_key=self.KEY if key is None else key)

    def test_signed_delivery_and_idempotent_confirmation(self):
        with sqlite3.connect(":memory:") as db:
            self.setup_claim(db)
            self.assertEqual(self.check(db), (True, "DELIVERY_CONFIRMED"))
            self.assertEqual(self.check(db), (True, "DELIVERY_CONFIRMED"))
            self.assertEqual(db.execute("SELECT COUNT(*) FROM rea_release_confirmations").fetchone()[0], 1)

    def test_forged_observation_rejected(self):
        with sqlite3.connect(":memory:") as db:
            self.setup_claim(db)
            original = self.observe(self.RELEASE, self.DEST)
            for forged in (
                DestinationObservation(self.RELEASE, "b"*64, self.DEST, True, original.signature_hex),
                DestinationObservation(self.RELEASE, self.SHA, "other", True, original.signature_hex),
                DestinationObservation(self.RELEASE, self.SHA, self.DEST, False, original.signature_hex),
                DestinationObservation(self.RELEASE, self.SHA, self.DEST, True, "0"*64),
            ):
                accepted, _ = self.check(db, observe=lambda *_: forged)
                self.assertFalse(accepted)
            self.assertEqual(self.check(db, key=b"weak"), (False, "trusted_observer_key_unavailable"))

    def test_missing_claim_and_observer_timeout(self):
        with sqlite3.connect(":memory:") as db:
            self.setup_claim(db)
            self.assertEqual(self.check(db, release_id="missing-release")[1], "release_claim_mismatch")
            def offline(*_): raise TimeoutError("offline")
            self.assertEqual(self.check(db, observe=offline)[1], "destination_observation_unavailable")

if __name__ == "__main__":
    unittest.main()
