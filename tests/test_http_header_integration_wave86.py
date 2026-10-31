"""Wave86: HTTP header anomalies must block the full read-only archive audit."""
import io
import json
import unittest
from email.message import Message
from unittest.mock import patch
from tools.audit_remote_release_archive import audit_remote_archive

SHA = "a" * 40
ARTIFACT = {"id": 7, "name": "release-gate-differential-evidence",
            "expired": False, "digest": "sha256:" + "b" * 64,
            "workflow_run": {"id": 42, "head_sha": SHA}}


class Response(io.BytesIO):
    status = 200
    url = "https://objects.githubusercontent.com/evidence.zip"
    def __init__(self, payload, headers):
        super().__init__(payload)
        self.headers = headers


class FullAuditHeaderTests(unittest.TestCase):
    def audit(self, headers):
        requests = []
        def opener(request, timeout):
            requests.append(request)
            if len(requests) == 1:
                return io.BytesIO(json.dumps({
                    "total_count": 1, "artifacts": [ARTIFACT]}).encode())
            return Response(b"zip", headers)
        with patch("tools.audit_remote_release_archive.audit_postrun_archive",
                   return_value={"status": "PASS_SCOPED", "violations": []}) as verifier:
            result = audit_remote_archive(run_id="42", commit_sha=SHA, attempt="1",
                                          token="test", opener=opener)
        return result, verifier, len(requests)

    def test_duplicate_header_blocks_before_verifier(self):
        headers = Message()
        headers.add_header("Content-Length", "3")
        headers.add_header("Content-Length", "3")
        result, verifier, count = self.audit(headers)
        self.assertEqual(result["status"], "BLOCK")
        self.assertIn("invalid_archive_content_length", result["violations"])
        self.assertEqual(count, 2)
        verifier.assert_not_called()

    def test_comma_merged_header_blocks_before_verifier(self):
        result, verifier, _ = self.audit({"Content-Length": "3, 3"})
        self.assertIn("invalid_archive_content_length", result["violations"])
        verifier.assert_not_called()

    def test_missing_header_delegates_to_byte_verifier(self):
        result, verifier, _ = self.audit({})
        self.assertEqual(result["status"], "PASS_SCOPED")
        verifier.assert_called_once()

    def test_exact_length_delegates_to_byte_verifier(self):
        result, verifier, _ = self.audit({"Content-Length": "3"})
        self.assertEqual(result["status"], "PASS_SCOPED")
        verifier.assert_called_once()


if __name__ == "__main__":
    unittest.main()
