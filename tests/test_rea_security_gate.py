"""Candidate REA security gate regression tests."""
import importlib.util
import unittest
from pathlib import Path

source = Path(__file__).resolve().parents[1] / "contracts" / "rea_security_gate.py"
spec = importlib.util.spec_from_file_location("rea_security_gate", source)
import sys
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)

class TestReaGate(unittest.TestCase):
    def good(self, **changes):
        args = dict(client_delivered=True, embeds_long_lived_secret=False,
                    includes_private_key=False, provenance_verified=True,
                    artifact_sha256="a"*64)
        args.update(changes)
        return module.ArtifactEvidence(**args)

    def test_verified_clean_artifact(self):
        self.assertTrue(module.evaluate_artifact(self.good()).allowed)

    def test_secrets_block_even_compiled(self):
        for changes in (dict(embeds_long_lived_secret=True), dict(includes_private_key=True)):
            result = module.evaluate_artifact(self.good(**changes))
            self.assertFalse(result.allowed)
            self.assertIn("secret_in_distributed_artifact", result.reasons)

    def test_missing_provenance_or_hash_blocks(self):
        for changes in (dict(provenance_verified=False), dict(artifact_sha256="claimed"),
                        dict(embeds_long_lived_secret=None)):
            self.assertFalse(module.evaluate_artifact(self.good(**changes)).allowed)

    def test_unproven_reconstruction_claim_blocks(self):
        result = module.evaluate_artifact(self.good(
            reconstruction_claim=module.ReconstructionClaim.BYTE_IDENTICAL))
        self.assertFalse(result.allowed)
        self.assertIn("reconstruction_claim_unproven", result.reasons)

    def test_claim_evidence_required_and_distinguished(self):
        evidence = self.good(reconstruction_claim=module.ReconstructionClaim.PSEUDOCODE,
                             matching_reconstruction_evidence=True)
        self.assertTrue(module.evaluate_artifact(evidence).allowed)


    def test_real_artifact_byte_digest(self):
        import hashlib
        payload = b"safe test artifact"
        sha = hashlib.sha256(payload).hexdigest()
        self.assertTrue(module.verify_artifact_bytes(payload, sha).allowed)
        self.assertIn("artifact_digest_mismatch",
                      module.verify_artifact_bytes(payload + b"x", sha).reasons)

    def test_private_key_and_github_token_markers(self):
        import hashlib
        for payload in (
            b"-----BEGIN PRIVATE KEY-----\\nsecret",
            b"ghp_" + b"A"*40,
            b"github_pat_" + b"B"*35,
        ):
            result = module.verify_artifact_bytes(payload, hashlib.sha256(payload).hexdigest())
            self.assertIn("high_risk_secret_marker_detected", result.reasons)

if __name__ == "__main__":
    unittest.main()
