"""Wave81: fail-closed transport behavior of post-run artifact retrieval."""
import io
import json
import unittest
from urllib.error import URLError
from unittest.mock import patch
from tools.audit_remote_release_archive import audit_remote_archive

SHA = "a" * 40
ARTIFACT = {"id": 21, "name": "release-gate-differential-evidence",
            "expired": False, "digest": "sha256:" + "b" * 64,
            "workflow_run": {"id": 42, "head_sha": SHA}}


class Response(io.BytesIO):
    status = 200
    url = "https://objects.githubusercontent.com/evidence.zip"
    headers = {"Content-Length": "3"}


class InterruptedResponse(Response):
    def read(self, *args):
        raise OSError("simulated connection reset")


class TransportFailureTests(unittest.TestCase):
    def audit(self, second_response):
        calls = []

        def opener(request, timeout):
            calls.append(request.full_url)
            if len(calls) == 1:
                return Response(json.dumps({
                    "total_count": 1, "artifacts": [ARTIFACT],
                }).encode())
            if isinstance(second_response, BaseException):
                raise second_response
            return second_response

        with patch("tools.audit_remote_release_archive.audit_postrun_archive",
                   return_value={"status": "PASS_SCOPED", "violations": []}) as verifier:
            result = audit_remote_archive(run_id="42", commit_sha=SHA,
                                          attempt="1", token="test-token", opener=opener)
        return result, verifier

    def test_connection_reset_during_read_blocks(self):
        result, verifier = self.audit(InterruptedResponse(b"zip"))
        self.assertEqual(result["status"], "BLOCK")
        self.assertIn("remote_archive_unverifiable", result["violations"])
        verifier.assert_not_called()

    def test_connection_failure_after_redirect_blocks(self):
        result, verifier = self.audit(URLError("redirect target unavailable"))
        self.assertEqual(result["status"], "BLOCK")
        verifier.assert_not_called()

    def test_partial_body_with_declared_full_length_blocks(self):
        response = Response(b"zi")
        result, verifier = self.audit(response)
        self.assertIn("truncated_archive_response", result["violations"])
        verifier.assert_not_called()

    def test_valid_complete_response_reaches_verifier(self):
        result, verifier = self.audit(Response(b"zip"))
        self.assertEqual(result["status"], "PASS_SCOPED")
        verifier.assert_called_once()


if __name__ == "__main__":
    unittest.main()
