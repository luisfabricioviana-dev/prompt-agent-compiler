"""Wave84 declared HTTP archive length is enforced before accumulation."""
import io
import json
import unittest
from unittest.mock import patch
from tools.audit_remote_release_archive import audit_remote_archive

SHA = "a"*40
ARTIFACT = {"id":7,"name":"release-gate-differential-evidence","expired":False,
            "digest":"sha256:"+"b"*64,"workflow_run":{"id":42,"head_sha":SHA}}

class Body(io.BytesIO):
    status = 200
    url = "https://objects.githubusercontent.com/evidence.zip"
    def __init__(self, raw, length):
        super().__init__(raw)
        self.headers = {"Content-Length":str(length)}

class DeclaredLengthTests(unittest.TestCase):
    def call_audit(self, body):
        count = [0]
        def opener(request,timeout):
            count[0] += 1
            if count[0] == 1:
                return io.BytesIO(json.dumps({"artifacts":[ARTIFACT],"total_count":1}).encode())
            return body
        with patch("tools.audit_remote_release_archive.audit_postrun_archive",
                   return_value={"status":"PASS_SCOPED","violations":[]}) as verifier:
            result = audit_remote_archive(run_id="42",commit_sha=SHA,attempt="1",
                                          token="mock",opener=opener)
        return result,verifier

    def test_excess_bytes_block_early(self):
        result,verifier=self.call_audit(Body(b"too many bytes",3))
        self.assertIn("archive_exceeds_declared_length",result["violations"])
        verifier.assert_not_called()

    def test_exact_declared_length_accepted(self):
        result,verifier=self.call_audit(Body(b"exact",5))
        self.assertEqual(result["status"],"PASS_SCOPED")
        verifier.assert_called_once()

    def test_shorter_than_declared_still_blocks(self):
        result,verifier=self.call_audit(Body(b"less",8))
        self.assertIn("truncated_archive_response",result["violations"])
        verifier.assert_not_called()

if __name__ == "__main__":
    unittest.main()
