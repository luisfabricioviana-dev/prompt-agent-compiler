"""Wave70 authenticated API collector regression with stubbed HTTP response."""
import io
import json
import tempfile
import unittest
from pathlib import Path
from tools.audit_published_release_artifact import audit_published_artifact

REPO = "luisfabricioviana-dev/prompt-agent-compiler"
SHA = "a" * 40


class Response(io.BytesIO):
    def __enter__(self):
        return self
    def __exit__(self, *args):
        self.close()


class PublishedArtifactAuditTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.manifest = Path(tmp.name) / "manifest.json"
        self.manifest.write_text(json.dumps({
            "workflow_run_id": "42", "commit_sha": SHA,
        }))

    def audit(self, artifacts, total=1):
        def open_stub(request, timeout):
            self.assertEqual(request.get_method(), "GET")
            self.assertIn("/actions/runs/42/artifacts", request.full_url)
            self.assertEqual(timeout, 20)
            return Response(json.dumps({"artifacts": artifacts, "total_count": total}).encode())
        return audit_published_artifact(
            repository=REPO, run_id="42", commit_sha=SHA,
            manifest_path=self.manifest, token="test-only-secret", opener=open_stub)

    def item(self, **override):
        value = {"id": 123, "name": "release-gate-differential-evidence",
                 "expired": False, "digest": "sha256:" + "b" * 64,
                 "workflow_run": {"id": 42, "head_sha": SHA}}
        value.update(override)
        return value

    def test_matching_api_artifact(self):
        self.assertEqual(self.audit([self.item()])["status"], "PASS_SCOPED")

    def test_duplicate_artifacts_block(self):
        self.assertIn("artifact_inventory_ambiguous",
                      self.audit([self.item(), self.item(id=124)], total=2)["violations"])

    def test_mismatched_api_commit_blocks(self):
        result = self.audit([self.item(workflow_run={"id": 42, "head_sha": "c"*40})])
        self.assertIn("artifact_commit_mismatch", result["violations"])

    def test_missing_credential_blocks(self):
        result = audit_published_artifact(repository=REPO, run_id="42",
                                          commit_sha=SHA, manifest_path=self.manifest,
                                          token="")
        self.assertIn("missing_api_credential", result["violations"])

    def test_truncated_inventory_blocks(self):
        self.assertIn("artifact_inventory_ambiguous",
                      self.audit([self.item()], total=101)["violations"])


if __name__ == "__main__":
    unittest.main()
