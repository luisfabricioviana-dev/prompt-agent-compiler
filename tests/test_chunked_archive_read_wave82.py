"""Wave82: multi-read archive transport must assemble full bounded bytes."""
import io
import json
import unittest
from unittest.mock import patch
from tools.audit_remote_release_archive import audit_remote_archive

SHA = "a" * 40
ARTIFACT = {"id": 7, "name": "release-gate-differential-evidence",
            "expired": False, "digest": "sha256:" + "b" * 64,
            "workflow_run": {"id": 42, "head_sha": SHA}}


class PartialReader(io.BytesIO):
    status = 200
    url = "https://objects.githubusercontent.com/evidence.zip"
    def __init__(self, data, length=None):
        super().__init__(data)
        self.headers = {} if length is None else {"Content-Length": length}
    def read(self, size=-1):
        return super().read(min(size, 2))


class ChunkedReadTests(unittest.TestCase):
    def check(self, response):
        calls = []
        def opener(request, timeout):
            calls.append(request.full_url)
            if len(calls) == 1:
                return io.BytesIO(json.dumps({"artifacts": [ARTIFACT],
                                              "total_count": 1}).encode())
            return response
        with patch("tools.audit_remote_release_archive.audit_postrun_archive",
                   return_value={"status": "PASS_SCOPED", "violations": []}) as audit:
            result = audit_remote_archive(run_id="42", commit_sha=SHA,
                                          attempt="1", token="test", opener=opener)
            return result, audit

    def test_multiple_partial_reads_reassemble(self):
        result, verifier = self.check(PartialReader(b"complete", length="8"))
        self.assertEqual(result["status"], "PASS_SCOPED")
        self.assertEqual(verifier.call_count, 1)
        verified_path = verifier.call_args.args[0]
        # Archive file is temporary and removed after the call; successful
        # delegation with matching Content-Length is the observable contract.
        self.assertEqual(verified_path.name, "evidence.zip")

    def test_early_eof_declared_length_blocks(self):
        result, verifier = self.check(PartialReader(b"short", length="10"))
        self.assertIn("truncated_archive_response", result["violations"])
        verifier.assert_not_called()

    def test_no_content_length_reaches_byte_verifier(self):
        result, verifier = self.check(PartialReader(b"complete"))
        self.assertEqual(result["status"], "PASS_SCOPED")
        verifier.assert_called_once()

if __name__ == "__main__":
    unittest.main()
