import hashlib
import hmac
import sqlite3
import unittest
from contracts.rea_pipeline import run_governed_pipeline
from contracts.rea_release_authority import ReleaseAuthorization
from contracts.rea_release_reconciliation import DestinationObservation
from contracts.rea_security_gate import ArtifactEvidence

class PipelineTests(unittest.TestCase):
    payload = b"safe pipeline fixture"
    sha = hashlib.sha256(payload).hexdigest()
    key = b"release-key-for-unit-tests-only-123456"
    observer_key = b"independent-observer-test-key-123456"
    release = "release-001"
    destination = "target-repository"
    observer = "trusted-observer-A"

    def evidence(self):
        return ArtifactEvidence(True, False, False, True, self.sha)

    def authorization(self):
        msg = ("REA-RELEASE-DEST-v2\nrelease-owner\n" + self.release + "\n" + self.sha + "\n" + self.destination).encode()
        return ReleaseAuthorization(self.sha, self.release, "release-owner",
                                    hmac.new(self.key, msg, hashlib.sha256).hexdigest())

    def observation(self, release, destination):
        msg = ("REA-DESTINATION-v2\n" + self.observer + "\n" + release +
               "\n" + self.sha + "\n" + destination + "\ndelivered").encode()
        return DestinationObservation(release, self.sha, destination, True,
            hmac.new(self.observer_key, msg, hashlib.sha256).hexdigest())

    def execute_pipeline(self, db, dispatch, *, enabled=False, observe=None, payload=None):
        return run_governed_pipeline(
            db, self.payload if payload is None else payload, self.evidence(),
            self.authorization(), issuer="release-owner", issuer_key=self.key,
            destination_id=self.destination, observer_id=self.observer,
            observer_key=self.observer_key, dispatch=dispatch,
            observe=self.observation if observe is None else observe,
            enable_dispatch=enabled,
            trusted_destination_resolver=lambda: self.destination,
        )

    def test_dry_run_rejects_tampered_artifacts_without_dispatch(self):
        sent = []
        with sqlite3.connect(":memory:") as db:
            result = self.execute_pipeline(db, lambda *_: sent.append(True), payload=b"tampered")
            self.assertEqual(result.state, "BLOCKED")
            self.assertIn("artifact_digest_mismatch", result.reason)
            self.assertEqual(sent, [])

    def test_destination_retargeting_is_blocked(self):
        with sqlite3.connect(":memory:") as db:
            sent = []
            result = run_governed_pipeline(db, self.payload, self.evidence(), self.authorization(),
                issuer="release-owner", issuer_key=self.key, destination_id="attacker-repository",
                observer_id=self.observer, observer_key=self.observer_key,
                dispatch=lambda *_: sent.append(True), observe=self.observation,
                enable_dispatch=True, trusted_destination_resolver=lambda: self.destination)
            self.assertEqual(result.state, "BLOCKED")
            self.assertEqual(sent, [])

    def test_enabled_missing_authorization_does_not_dispatch(self):
        calls = []
        with sqlite3.connect(":memory:") as db:
            result = run_governed_pipeline(
                db, self.payload, self.evidence(), None,
                issuer="release-owner", issuer_key=self.key,
                destination_id=self.destination, observer_id=self.observer,
                observer_key=self.observer_key,
                dispatch=lambda *_: calls.append(True), observe=self.observation,
                enable_dispatch=True, trusted_destination_resolver=lambda: self.destination)
            self.assertEqual(result.state, "BLOCKED")
            self.assertEqual(result.reason, "release_authorization_missing")
            self.assertEqual(calls, [])

    def test_missing_or_mismatched_trusted_destination_blocks_dispatch(self):
        for resolver, reason in ((None, "trusted_destination_resolver_missing"),
                                 (lambda: "other-repo", "destination_identity_mismatch")):
            calls = []
            with sqlite3.connect(":memory:") as db:
                result = run_governed_pipeline(
                    db, self.payload, self.evidence(), self.authorization(),
                    issuer="release-owner", issuer_key=self.key,
                    destination_id=self.destination, observer_id=self.observer,
                    observer_key=self.observer_key, dispatch=lambda *_: calls.append(True),
                    observe=self.observation, enable_dispatch=True,
                    trusted_destination_resolver=resolver)
                self.assertEqual(result.state, "BLOCKED")
                self.assertEqual(result.reason, reason)
                self.assertEqual(calls, [])

    def test_default_never_dispatches(self):
        sent = []
        with sqlite3.connect(":memory:") as db:
            result = self.execute_pipeline(db, lambda *_: sent.append(True))
            self.assertEqual(result.state, "DRY_RUN")
            self.assertEqual(sent, [])

    def test_explicit_simulated_dispatch_and_signed_observation(self):
        sent = []
        with sqlite3.connect(":memory:") as db:
            result = self.execute_pipeline(db, lambda data, digest: sent.append((data, digest)), enabled=True)
            self.assertEqual(result.state, "CONFIRMED_BY_OBSERVER")
            self.assertEqual(sent, [(self.payload, self.sha)])
            duplicate = self.execute_pipeline(db, lambda *_: sent.append("duplicate"), enabled=True)
            self.assertEqual(duplicate.state, "BLOCKED")
            self.assertEqual(len(sent), 1)

    def test_false_observer_or_tampered_bytes_fail_closed(self):
        with sqlite3.connect(":memory:") as db:
            wrong = lambda *_: DestinationObservation(
                self.release, self.sha, self.destination, True, "0"*64)
            result = self.execute_pipeline(db, lambda *_: None, enabled=True, observe=wrong)
            self.assertEqual(result.state, "IN_DOUBT")
        with sqlite3.connect(":memory:") as db:
            calls = []
            result = self.execute_pipeline(db, lambda *_: calls.append(True),
                              enabled=True, payload=b"tampered")
            self.assertEqual(result.state, "BLOCKED")
            self.assertEqual(calls, [])

    def test_dispatch_timeout_is_in_doubt_and_never_retried(self):
        deliveries = []
        with sqlite3.connect(":memory:") as db:
            def lost_ack(data, digest):
                deliveries.append(digest)
                raise TimeoutError("acknowledgment lost")
            first = self.execute_pipeline(db, lost_ack, enabled=True)
            self.assertEqual(first.state, "IN_DOUBT")
            self.assertEqual(deliveries, [self.sha])
            second = self.execute_pipeline(db, lambda *_: deliveries.append("retry"), enabled=True)
            self.assertEqual(second.state, "BLOCKED")
            self.assertEqual(deliveries, [self.sha])

if __name__ == "__main__":
    unittest.main()
