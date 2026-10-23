import hashlib
import importlib.util
import sys
import unittest
from pathlib import Path

root = Path(__file__).resolve().parents[1] / "contracts"
for name in ("rea_security_gate", "rea_release_handoff"):
    spec = importlib.util.spec_from_file_location(name, root / (name + ".py"))
    obj = importlib.util.module_from_spec(spec)
    sys.modules[name] = obj
    spec.loader.exec_module(obj)
gate = sys.modules["rea_security_gate"]
handoff = sys.modules["rea_release_handoff"]

class HandoffTests(unittest.TestCase):
    def evidence(self, payload, **kwargs):
        items = dict(client_delivered=True, embeds_long_lived_secret=False,
                     includes_private_key=False, provenance_verified=True,
                     artifact_sha256=hashlib.sha256(payload).hexdigest())
        items.update(kwargs)
        return gate.ArtifactEvidence(**items)

    def test_valid_artifact_calls_callback_with_verified_bytes(self):
        payload = b"nonsecret-payload"
        seen = []
        result = handoff.governed_artifact_handoff(payload, self.evidence(payload),
                     authorized_for_release=True,
                     callback=lambda contents, digest: seen.append((contents, digest)))
        self.assertTrue(result.accepted)
        self.assertEqual(seen, [(payload, hashlib.sha256(payload).hexdigest())])

    def test_no_dispatch_without_authorization_or_proof(self):
        payload = b"nonsecret-payload"
        seen = []
        def call(contents, digest):
            seen.append(contents)
        for authorized, data, contents in (
            (False, self.evidence(payload), payload),
            (True, self.evidence(b"another"), payload),
            (True, self.evidence(payload, provenance_verified=False), payload),
            (True, self.evidence(payload), b"ghp_" + b"A"*40),
        ):
            result = handoff.governed_artifact_handoff(contents, data,
                      authorized_for_release=authorized, callback=call)
            self.assertFalse(result.accepted)
        self.assertEqual(seen, [])

    def test_malformed_inputs_fail_closed_without_callback(self):
        payload = b"fixture"
        calls = []
        for kwargs, expected in (
            (dict(evidence=None), "artifact_evidence_missing"),
            (dict(callback=None), "callback_unavailable"),
            (dict(max_size_bytes="unbounded"), "payload_unavailable_or_oversized"),
            (dict(max_size_bytes=True), "payload_unavailable_or_oversized"),
            (dict(payload=b""), "payload_unavailable_or_oversized"),
        ):
            options = dict(payload=payload, evidence=self.evidence(payload),
                           authorized_for_release=True,
                           callback=lambda *_: calls.append(True))
            options.update(kwargs)
            result = handoff.governed_artifact_handoff(**options)
            self.assertFalse(result.accepted)
            self.assertIn(expected, result.reasons)
        self.assertEqual(calls, [])

    def test_callback_failure_never_claims_success(self):
        payload = b"fixture"
        def broken(contents, digest):
            raise RuntimeError("delivery failed")
        result = handoff.governed_artifact_handoff(payload, self.evidence(payload),
                      authorized_for_release=True, callback=broken)
        self.assertFalse(result.accepted)
        self.assertIn("downstream_dispatch_failed", result.reasons)

if __name__ == "__main__":
    unittest.main()
