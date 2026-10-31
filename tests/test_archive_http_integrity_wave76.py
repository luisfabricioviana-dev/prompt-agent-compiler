"""Wave76: reject incomplete, oversized or inconsistent artifact HTTP responses."""
import io
import json
import unittest
from unittest.mock import patch
from tools.audit_remote_release_archive import audit_remote_archive

SHA = "a" * 40


class Response(io.BytesIO):
    def __init__(self, body, *, status=200, length=None, url="https://objects.githubusercontent.com/evidence.zip"):
        super().__init__(body)
        self.status = status
        self.url = url
        self.headers = {} if length is None else {"Content-Length": length}


class DownloadIntegrityTests(unittest.TestCase):
    def check(self, *, status=200, length=None, url="https://objects.githubusercontent.com/evidence.zip"):
        artifact = {"id": 7, "name": "release-gate-differential-evidence",
                    "expired": False, "digest": "sha256:" + "b" * 64,
                    "workflow_run": {"id": 42, "head_sha": SHA}}
        calls = []

        def opener(request, timeout):
            calls.append(request.full_url)
            if len(calls) == 1:
                return Response(json.dumps({"total_count": 1, "artifacts": [artifact]}).encode())
            return Response(b"zip", status=status, length=length, url=url)

        with patch("tools.audit_remote_release_archive.audit_postrun_archive",
                   return_value={"status": "PASS_SCOPED", "violations": []}) as audit:
            result = audit_remote_archive(
                run_id="42", commit_sha=SHA, attempt="1", token="mock",
                opener=opener)
            return result, audit

    def test_consistent_response_passes_to_byte_verifier(self):
        result, audit = self.check(length="3")
        self.assertEqual(result["status"], "PASS_SCOPED")
        audit.assert_called_once()

    def test_truncated_response_blocks_before_verifier(self):
        result, audit = self.check(length="4")
        self.assertIn("truncated_archive_response", result["violations"])
        audit.assert_not_called()

    def test_bad_http_status_blocks(self):
        result, audit = self.check(status=206)
        self.assertIn("unexpected_archive_http_status", result["violations"])
        audit.assert_not_called()

    def test_invalid_declared_length_blocks(self):
        for length in ("invalid", "10000001"):
            with self.subTest(length=length):
                result, audit = self.check(length=length)
                self.assertIn("invalid_archive_content_length", result["violations"])
                audit.assert_not_called()

    def test_insecure_final_download_url_blocks(self):
        result, audit = self.check(url="http://objects.example/evidence.zip")
        self.assertIn("unexpected_archive_url_scheme", result["violations"])
        audit.assert_not_called()


if __name__ == "__main__":
    unittest.main()
