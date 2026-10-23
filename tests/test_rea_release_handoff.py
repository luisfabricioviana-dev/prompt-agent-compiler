import hashlib
import unittest
from contracts.rea_release_handoff import governed_artifact_handoff, verify_handoff_candidate
from contracts.rea_security_gate import ArtifactEvidence

class HandoffTests(unittest.TestCase):
    def evidence(self, payload, **kwargs):
        fields = dict(client_delivered=True, embeds_long_lived_secret=False,
            includes_private_key=False, provenance_verified=True,
            artifact_sha256=hashlib.sha256(payload).hexdigest())
        fields.update(kwargs)
        return ArtifactEvidence(**fields)

    def test_low_level_boolean_never_dispatches_even_when_true(self):
        payload = b"fixture"
        calls = []
        for flag in (True, False):
            verdict = governed_artifact_handoff(payload, self.evidence(payload),
                authorized_for_release=flag,
                callback=lambda *_: calls.append(True))
            self.assertFalse(verdict.accepted)
            self.assertEqual(verdict.reasons, ("authenticated_release_authority_required",))
        self.assertEqual(calls, [])

    def test_pure_validator_does_not_dispatch(self):
        payload = b"fixture"
        result = verify_handoff_candidate(payload, self.evidence(payload))
        self.assertTrue(result.accepted)
        self.assertEqual(result.digest, hashlib.sha256(payload).hexdigest())

    def test_invalid_candidate_rejected(self):
        payload = b"fixture"
        for data, evidence, limit, reason in (
            (b"", self.evidence(payload), 100, "payload_unavailable_or_oversized"),
            (payload, None, 100, "artifact_evidence_missing"),
            (payload, self.evidence(payload), True, "payload_unavailable_or_oversized"),
            (payload, self.evidence(payload), 1, "payload_unavailable_or_oversized"),
            (b"tampered", self.evidence(payload), 100, "artifact_digest_mismatch"),
            (payload, self.evidence(payload, provenance_verified=False), 100, "provenance_unverified"),
        ):
            verdict = verify_handoff_candidate(data, evidence, max_size_bytes=limit)
            self.assertFalse(verdict.accepted)
            self.assertIn(reason, verdict.reasons)

if __name__ == "__main__":
    unittest.main()
