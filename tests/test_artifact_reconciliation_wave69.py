"""Wave69 offline adversarial checks for independently fetched artifact metadata."""
import unittest
from contracts.release_gate_artifact_reconciliation import reconcile_artifact_metadata

SHA = "a" * 40
MANIFEST = {"commit_sha": SHA, "workflow_run_id": "42"}
ARTIFACT = {"id": 1001, "name": "release-gate-differential-evidence",
            "expired": False, "digest": "sha256:" + "b" * 64,
            "workflow_run": {"id": 42, "head_sha": SHA}}


class ArtifactReconciliationTests(unittest.TestCase):
    def check(self, artifact=None, manifest=None):
        return reconcile_artifact_metadata(
            MANIFEST if manifest is None else manifest,
            ARTIFACT if artifact is None else artifact,
            expected_run_id="42", expected_commit_sha=SHA)

    def test_matching_artifact_metadata_passes(self):
        self.assertEqual(self.check()["status"], "PASS_SCOPED")

    def test_artifact_substitution_blocks(self):
        changed = dict(ARTIFACT, name="wrong-evidence", id=1002)
        self.assertIn("artifact_name_mismatch", self.check(artifact=changed)["violations"])

    def test_wrong_commit_and_run_blocks(self):
        changed = dict(ARTIFACT, workflow_run={"id": 99, "head_sha": "c" * 40})
        result = self.check(artifact=changed)
        self.assertIn("artifact_run_id_mismatch", result["violations"])
        self.assertIn("artifact_commit_mismatch", result["violations"])

    def test_malformed_digest_or_expired_blocks(self):
        changed = dict(ARTIFACT, digest="sha256:invalid", expired=True)
        result = self.check(artifact=changed)
        self.assertIn("invalid_archive_digest", result["violations"])
        self.assertIn("artifact_expired_or_unknown", result["violations"])

    def test_wrong_manifest_identity_blocks(self):
        changed = {"commit_sha": "c" * 40, "workflow_run_id": "99"}
        result = self.check(manifest=changed)
        self.assertIn("manifest_run_id_mismatch", result["violations"])
        self.assertIn("manifest_commit_mismatch", result["violations"])


if __name__ == "__main__":
    unittest.main()
