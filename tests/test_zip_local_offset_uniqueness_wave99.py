"""Wave99: unique local offsets and strict central region membership."""
import hashlib
import io
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch
from tools.audit_postrun_release_archive import audit_postrun_archive

REPORT = "release-gate-differential-report.json"
MANIFEST = "release-gate-evidence-manifest.json"

def fixture():
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as zf:
        zf.writestr(REPORT, b"{}")
        zf.writestr(MANIFEST, b"{}")
    return out.getvalue()

class LocalOffsetTests(unittest.TestCase):
    def audit(self, raw):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "archive.zip"
            path.write_bytes(raw)
            artifact = {"digest": "sha256:" + hashlib.sha256(raw).hexdigest()}
            with patch("tools.audit_postrun_release_archive.reconcile_artifact_metadata",
                       return_value={"violations": []}) as metadata, patch(
                       "tools.audit_postrun_release_archive.verify_evidence",
                       return_value={"violations": []}) as verifier:
                result = audit_postrun_archive(path, artifact, run_id="42",
                                               commit_sha="a"*40, attempt="1",
                                               source_root=folder)
            return result, metadata, verifier

    def test_valid_unique_offsets_pass(self):
        result, metadata, verifier = self.audit(fixture())
        self.assertEqual(result["status"], "PASS_SCOPED")
        metadata.assert_called_once()
        verifier.assert_called_once()

    def test_repeated_local_offset_blocks(self):
        raw = bytearray(fixture())
        first = raw.find(bytes((80, 75, 1, 2)))
        second = raw.find(bytes((80, 75, 1, 2)), first + 4)
        self.assertGreaterEqual(second, 0)
        raw[second+42:second+46] = (0).to_bytes(4, "little")
        result, metadata, verifier = self.audit(bytes(raw))
        self.assertIn("zip_local_offsets_invalid", result["violations"])
        metadata.assert_not_called()
        verifier.assert_not_called()

if __name__ == "__main__":
    unittest.main()
