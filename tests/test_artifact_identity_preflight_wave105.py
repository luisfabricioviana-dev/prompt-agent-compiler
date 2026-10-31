"""Wave105: reject inconsistent GitHub artifact metadata without downloading ZIP."""
import io
import json
import unittest
from unittest.mock import patch

from tools.audit_remote_release_archive import audit_remote_archive

SHA = "a" * 40


class ArtifactIdentityPreflightTests(unittest.TestCase):
    def audit(self, **changes):
        artifact = {
            "id": 12, "name": "release-gate-differential-evidence",
            "expired": False, "digest": "sha256:" + "b" * 64,
            "workflow_run": {"id": 42, "head_sha": SHA},
        }
        artifact.update(changes)
        requests = []

        def opener(req, timeout):
            requests.append(req.full_url)
            if len(requests) == 1:
                return io.BytesIO(json.dumps({
                    "total_count": 1, "artifacts": [artifact],
                }).encode())
            return io.BytesIO(b"archive")

        with patch("tools.audit_remote_release_archive.audit_postrun_archive",
                   return_value={"status": "PASS_SCOPED", "violations": []}) as downstream:
            result = audit_remote_archive(
                run_id="42", commit_sha=SHA, attempt="1", token="test", opener=opener)
        return result, requests, downstream

    def test_run_id_mismatch_blocks_before_zip_request(self):
        result, calls, verifier = self.audit(workflow_run={"id": 43, "head_sha": SHA})
        self.assertIn("artifact_identity_preflight_failed", result["violations"])
        self.assertEqual(len(calls), 1)
        verifier.assert_not_called()

    def test_commit_mismatch_blocks_before_zip_request(self):
        result, calls, verifier = self.audit(workflow_run={"id": 42, "head_sha": "c" * 40})
        self.assertIn("artifact_identity_preflight_failed", result["violations"])
        self.assertEqual(len(calls), 1)
        verifier.assert_not_called()

    def test_expired_or_invalid_digest_blocks_before_zip_request(self):
        for changes in ({"expired": True}, {"digest": "unknown"}):
            with self.subTest(changes=changes):
                result, calls, verifier = self.audit(**changes)
                self.assertIn("artifact_identity_preflight_failed", result["violations"])
                self.assertEqual(len(calls), 1)
                verifier.assert_not_called()

    def test_matching_identity_reaches_downstream_verifier(self):
        result, calls, verifier = self.audit()
        self.assertEqual(result["status"], "PASS_SCOPED")
        self.assertEqual(len(calls), 2)
        verifier.assert_called_once()


if __name__ == "__main__":
    unittest.main()
