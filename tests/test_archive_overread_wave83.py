"""Wave83: adversarial HTTP reader over-delivery is rejected."""
import io
import json
import unittest
from unittest.mock import patch
from tools.audit_remote_release_archive import audit_remote_archive

SHA = "a" * 40
ARTIFACT = {"id": 7, "name": "release-gate-differential-evidence",
            "expired": False, "digest": "sha256:" + "b" * 64,
            "workflow_run": {"id": 42, "head_sha": SHA}}


class AdversarialReader(io.BytesIO):
    status = 200
    url = "https://objects.githubusercontent.com/evidence.zip"
    headers = {}
    def read(self, size=-1):
        return b"x" * (size + 1)


class NormalReader(io.BytesIO):
    status = 200
    url = "https://objects.githubusercontent.com/evidence.zip"
    headers = {"Content-Length": "3"}


class OverreadTests(unittest.TestCase):
    def run_audit(self, reader):
        calls = []
        def opener(request, timeout):
            calls.append(request)
            if len(calls) == 1:
                return io.BytesIO(json.dumps({"artifacts": [ARTIFACT],
                                              "total_count": 1}).encode())
            return reader
        with patch("tools.audit_remote_release_archive.audit_postrun_archive",
                   return_value={"status": "PASS_SCOPED", "violations": []}) as verifier:
            outcome = audit_remote_archive(run_id="42", commit_sha=SHA,
                                           attempt="1", token="mock", opener=opener)
        return outcome, verifier

    def test_over_delivery_blocks_before_verifier(self):
        result, verifier = self.run_audit(AdversarialReader(b""))
        self.assertIn("archive_overread", result["violations"])
        verifier.assert_not_called()

    def test_normal_exact_delivery_reaches_verifier(self):
        result, verifier = self.run_audit(NormalReader(b"zip"))
        self.assertEqual(result["status"], "PASS_SCOPED")
        verifier.assert_called_once()


if __name__ == "__main__":
    unittest.main()
