"""Wave72 HTTP retrieval is bounded, read-only and delegates byte verification."""
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.audit_remote_release_archive import audit_remote_archive

SHA = "a" * 40


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self
    def __exit__(self, *args):
        self.close()


class RemoteArchiveTests(unittest.TestCase):
    def artifact(self):
        return {"id": 100, "name": "release-gate-differential-evidence",
                "digest": "sha256:" + "b" * 64, "expired": False,
                "workflow_run": {"id": 42, "head_sha": SHA}}

    def run(self, artifacts, archive=b"test", total=None):
        requests = []

        def opener(request, timeout):
            requests.append(request)
            self.assertEqual(request.get_method(), "GET")
            if len(requests) == 1:
                return FakeResponse(json.dumps({
                    "artifacts": artifacts,
                    "total_count": len(artifacts) if total is None else total,
                }).encode())
            return FakeResponse(archive)
        with patch("tools.audit_remote_release_archive.audit_postrun_archive",
                   return_value={"status": "PASS_SCOPED", "violations": []}) as verifier:
            result = audit_remote_archive(run_id="42", commit_sha=SHA, attempt="1",
                                          token="mock-token", opener=opener)
        return result, requests, verifier

    def test_valid_retrieval_delegates_to_zip_verifier(self):
        result, requests, verifier = self.run([self.artifact()])
        self.assertEqual(result["status"], "PASS_SCOPED")
        self.assertEqual(len(requests), 2)
        self.assertIn("/actions/artifacts/100/zip", requests[1].full_url)
        verifier.assert_called_once()

    def test_duplicate_artifacts_block_without_download(self):
        result, requests, verifier = self.run([self.artifact(), self.artifact()])
        self.assertEqual(result["status"], "BLOCK")
        self.assertEqual(len(requests), 1)
        verifier.assert_not_called()

    def test_oversized_download_blocks(self):
        result, requests, verifier = self.run([self.artifact()], archive=b"x" * 10_000_001)
        self.assertIn("remote_archive_too_large", result["violations"])
        verifier.assert_not_called()

    def test_no_token_blocks(self):
        result = audit_remote_archive(run_id="42", commit_sha=SHA, attempt="1", token="")
        self.assertEqual(result["status"], "BLOCK")

    def test_truncated_artifact_listing_blocks(self):
        result, requests, verifier = self.run([self.artifact()], total=101)
        self.assertIn("ambiguous_remote_artifacts", result["violations"])
        verifier.assert_not_called()


if __name__ == "__main__":
    unittest.main()
