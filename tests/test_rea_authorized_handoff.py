import hashlib
import hmac
import sqlite3
import tempfile
import unittest
from contracts.rea_release_authority import ReleaseAuthorization, verify_destination_bound_authorization
from contracts.rea_authorized_handoff import authorized_handoff, read_release_dispatch_state
from contracts.rea_security_gate import ArtifactEvidence

class AuthorizedHandoffTests(unittest.TestCase):
    KEY = b"fixture-not-for-production-very-long-secret-key"
    PAYLOAD = b"artifact without secrets"
    SHA = hashlib.sha256(PAYLOAD).hexdigest()
    DESTINATION = "repo-target"

    def evidence(self):
        return ArtifactEvidence(True, False, False, True, self.SHA)

    def auth(self, release_id="release-001", sha=None):
        sha = sha or self.SHA
        data = f"REA-RELEASE-DEST-v2\nrelease-owner\n{release_id}\n{sha}\n{self.DESTINATION}".encode()
        signature = hmac.new(self.KEY, data, hashlib.sha256).hexdigest()
        return ReleaseAuthorization(sha, release_id, "release-owner", signature)

    def test_missing_evidence_never_dispatches(self):
        calls = []
        with sqlite3.connect(":memory:") as db:
            result = authorized_handoff(
                db, self.PAYLOAD, None, self.auth(),
                trusted_issuer="release-owner", trusted_key=self.KEY, destination_id=self.DESTINATION,
                callback=lambda *_: calls.append(True))
            self.assertFalse(result.accepted)
            self.assertEqual(result.reasons, ("artifact_evidence_missing",))
            self.assertEqual(calls, [])

    def test_legacy_missing_destination_blocked(self):
        calls = []
        with sqlite3.connect(":memory:") as db:
            result = authorized_handoff(
                db, self.PAYLOAD, self.evidence(), self.auth(),
                trusted_issuer="release-owner", trusted_key=self.KEY,
                callback=lambda *_: calls.append(True))
            self.assertEqual(result.reasons, ("destination_required",))
            self.assertEqual(calls, [])

    def test_single_use_verified_handoff(self):
        sent = []
        with tempfile.TemporaryDirectory() as td:
            path = td + "/claims.db"
            with sqlite3.connect(path) as db:
                args = dict(trusted_issuer="release-owner", trusted_key=self.KEY, destination_id=self.DESTINATION,
                            callback=lambda data, sha: sent.append((data, sha)))
                first = authorized_handoff(db, self.PAYLOAD, self.evidence(), self.auth(), **args)
                second = authorized_handoff(db, self.PAYLOAD, self.evidence(), self.auth(), **args)
        self.assertTrue(first.accepted)
        self.assertFalse(second.accepted)
        self.assertEqual(len(sent), 1)
        self.assertEqual(second.reasons, ("release_id_already_consumed",))

    def test_forged_signature_never_dispatches(self):
        sent = []
        with sqlite3.connect(":memory:") as db:
            auth = self.auth()
            forged = ReleaseAuthorization(auth.artifact_sha256, auth.release_id, auth.issuer, "0"*64)
            result = authorized_handoff(db, self.PAYLOAD, self.evidence(), forged,
                trusted_issuer="release-owner", trusted_key=self.KEY, destination_id=self.DESTINATION,
                callback=lambda *_: sent.append(True))
        self.assertFalse(result.accepted)
        self.assertEqual(sent, [])

    def test_digest_binding_and_short_key(self):
        auth = self.auth()
        self.assertFalse(verify_destination_bound_authorization(auth, trusted_issuer="release-owner",
                         trusted_key=b"weak", destination_id=self.DESTINATION, artifact_sha256=self.SHA))
        self.assertFalse(verify_destination_bound_authorization(auth, trusted_issuer="release-owner",
                         trusted_key=self.KEY, destination_id=self.DESTINATION, artifact_sha256="b"*64))

    def test_invalid_bytes_do_not_consume_authorization(self):
        sent = []
        with sqlite3.connect(":memory:") as db:
            args = dict(trusted_issuer="release-owner", trusted_key=self.KEY, destination_id=self.DESTINATION,
                        callback=lambda data, digest: sent.append(data))
            rejected = authorized_handoff(db, b"tampered", self.evidence(), self.auth(), **args)
            self.assertFalse(rejected.accepted)
            accepted = authorized_handoff(db, self.PAYLOAD, self.evidence(), self.auth(), **args)
            self.assertTrue(accepted.accepted)
            self.assertEqual(sent, [self.PAYLOAD])

    def test_dispatch_state_is_not_delivery_confirmation(self):
        with sqlite3.connect(":memory:") as db:
            result = authorized_handoff(
                db, self.PAYLOAD, self.evidence(), self.auth(),
                trusted_issuer="release-owner", trusted_key=self.KEY, destination_id=self.DESTINATION,
                callback=lambda *_: None,
            )
            self.assertTrue(result.accepted)
            self.assertEqual(read_release_dispatch_state(db, "release-001"), "DISPATCH_RETURNED")
            self.assertEqual(read_release_dispatch_state(db, "missing-claim"), "NOT_CLAIMED")

    def test_failed_callback_requires_reconciliation(self):
        with sqlite3.connect(":memory:") as db:
            def fail(*_):
                raise RuntimeError("provider timeout")
            result = authorized_handoff(
                db, self.PAYLOAD, self.evidence(), self.auth(),
                trusted_issuer="release-owner", trusted_key=self.KEY, destination_id=self.DESTINATION, callback=fail,
            )
            self.assertFalse(result.accepted)
            self.assertEqual(read_release_dispatch_state(db, "release-001"), "IN_DOUBT")
            retry = authorized_handoff(
                db, self.PAYLOAD, self.evidence(), self.auth(),
                trusted_issuer="release-owner", trusted_key=self.KEY, destination_id=self.DESTINATION,
                callback=lambda *_: None,
            )
            self.assertFalse(retry.accepted)
            self.assertEqual(retry.reasons, ("release_id_already_consumed",))

    def test_unavailable_ledger_never_dispatches(self):
        sent = []
        db = sqlite3.connect(":memory:")
        db.close()
        result = authorized_handoff(
            db, self.PAYLOAD, self.evidence(), self.auth(),
            trusted_issuer="release-owner", trusted_key=self.KEY, destination_id=self.DESTINATION,
            callback=lambda *_: sent.append(True),
        )
        self.assertFalse(result.accepted)
        self.assertEqual(result.reasons, ("release_claim_persistence_failed",))
        self.assertEqual(sent, [])

    def test_crash_after_durable_claim_without_outcome_table(self):
        with sqlite3.connect(":memory:") as db:
            db.execute("CREATE TABLE rea_release_claims (release_id TEXT PRIMARY KEY, artifact_sha256 TEXT NOT NULL)")
            db.execute("INSERT INTO rea_release_claims VALUES (?, ?)",
                       ("release-001", self.SHA))
            db.commit()
            self.assertEqual(read_release_dispatch_state(db, "release-001"), "IN_DOUBT")
            sent = []
            retry = authorized_handoff(
                db, self.PAYLOAD, self.evidence(), self.auth(),
                trusted_issuer="release-owner", trusted_key=self.KEY, destination_id=self.DESTINATION,
                callback=lambda *_: sent.append(True),
            )
            self.assertEqual(retry.reasons, ("release_id_already_consumed",))
            self.assertEqual(sent, [])

if __name__ == "__main__":
    unittest.main()
