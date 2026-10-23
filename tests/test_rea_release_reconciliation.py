import hashlib
import sqlite3
import unittest
from contracts.rea_release_reconciliation import DestinationObservation, reconcile_delivery

class ReconciliationTests(unittest.TestCase):
    RELEASE = "release-001"
    SHA = hashlib.sha256(b"artifact").hexdigest()
    DEST = "destination-A"

    def setup_claim(self, db):
        db.execute("CREATE TABLE rea_release_claims (release_id TEXT PRIMARY KEY, artifact_sha256 TEXT NOT NULL)")
        db.execute("INSERT INTO rea_release_claims VALUES (?, ?)", (self.RELEASE, self.SHA))
        db.commit()

    def observe(self, release_id, destination_id):
        return DestinationObservation(release_id, self.SHA, destination_id, True)

    def test_destination_bound_confirmation(self):
        with sqlite3.connect(":memory:") as db:
            self.setup_claim(db)
            allowed, state = reconcile_delivery(
                db, release_id=self.RELEASE, artifact_sha256=self.SHA,
                expected_destination=self.DEST, observe=self.observe)
            self.assertTrue(allowed)
            self.assertEqual(state, "DELIVERY_CONFIRMED")
            self.assertEqual(db.execute("SELECT COUNT(*) FROM rea_release_confirmations").fetchone()[0], 1)

    def test_forged_or_stale_observation_blocks(self):
        with sqlite3.connect(":memory:") as db:
            self.setup_claim(db)
            for observation in (
                DestinationObservation(self.RELEASE, "b"*64, self.DEST, True),
                DestinationObservation(self.RELEASE, self.SHA, "other", True),
                DestinationObservation(self.RELEASE, self.SHA, self.DEST, False),
            ):
                ok, reason = reconcile_delivery(
                    db, release_id=self.RELEASE, artifact_sha256=self.SHA,
                    expected_destination=self.DEST, observe=lambda *_: observation)
                self.assertFalse(ok)
                self.assertEqual(reason, "delivery_unverified")

    def test_missing_claim_and_unavailable_destination_block(self):
        with sqlite3.connect(":memory:") as db:
            self.setup_claim(db)
            ok, reason = reconcile_delivery(db, release_id="missing-release",
                artifact_sha256=self.SHA, expected_destination=self.DEST, observe=self.observe)
            self.assertFalse(ok)
            self.assertEqual(reason, "release_claim_mismatch")
            def offline(*_): raise TimeoutError("destination not reachable")
            ok, reason = reconcile_delivery(db, release_id=self.RELEASE,
                artifact_sha256=self.SHA, expected_destination=self.DEST, observe=offline)
            self.assertFalse(ok)
            self.assertEqual(reason, "destination_observation_unavailable")

if __name__ == "__main__":
    unittest.main()
