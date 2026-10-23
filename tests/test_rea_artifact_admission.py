import hashlib
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

root = Path(__file__).resolve().parents[1] / "contracts"
for name in ("rea_security_gate", "rea_artifact_admission"):
    spec = importlib.util.spec_from_file_location(name, root / (name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
gate = sys.modules["rea_security_gate"]
admission = sys.modules["rea_artifact_admission"]

class TestAdmission(unittest.TestCase):
    def evidence(self, payload, **overrides):
        fields = dict(client_delivered=True, embeds_long_lived_secret=False,
                      includes_private_key=False, provenance_verified=True,
                      artifact_sha256=hashlib.sha256(payload).hexdigest())
        fields.update(overrides)
        return gate.ArtifactEvidence(**fields)

    def test_valid_real_bytes(self):
        payload = b"documented-safe-fixture"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "candidate.bin"
            path.write_bytes(payload)
            outcome = admission.admit_local_artifact(str(path), self.evidence(payload))
            self.assertTrue(outcome.verdict.allowed)
            self.assertEqual(outcome.checked_digest, hashlib.sha256(payload).hexdigest())

    def test_stale_digest_and_embedded_token_block(self):
        payload = b"ghp_" + b"A" * 40
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "candidate.bin"
            path.write_bytes(payload)
            self.assertFalse(admission.admit_local_artifact(str(path), self.evidence(b"other")).verdict.allowed)
            self.assertFalse(admission.admit_local_artifact(str(path), self.evidence(payload)).verdict.allowed)

    def test_oversized_and_unverified_claim_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "candidate.bin"
            path.write_bytes(b"123456")
            self.assertIn("artifact_exceeds_size_limit", admission.admit_local_artifact(str(path), self.evidence(b"123456"),max_size_bytes=2).verdict.reasons)
            self.assertIn("provenance_unverified", admission.admit_local_artifact(str(path), self.evidence(b"123456", provenance_verified=False)).verdict.reasons)

if __name__ == "__main__":
    unittest.main()
