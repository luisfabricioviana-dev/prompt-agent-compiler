"""Wave91: real ZIP local-header vs central-directory reconciliation."""
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

def make_zip():
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_STORED) as zf:
        zf.writestr(REPORT, b"{}")
        zf.writestr(MANIFEST, b"{}")
    return stream.getvalue()

class LocalHeaderTests(unittest.TestCase):
    def audit(self, raw):
        with tempfile.TemporaryDirectory() as root:
            archive = Path(root) / "evidence.zip"
            archive.write_bytes(raw)
            artifact = {"digest": "sha256:" + hashlib.sha256(raw).hexdigest()}
            with patch("tools.audit_postrun_release_archive.reconcile_artifact_metadata",
                       return_value={"violations": []}) as metadata, patch(
                       "tools.audit_postrun_release_archive.verify_evidence",
                       return_value={"violations": []}) as verifier:
                result = audit_postrun_archive(archive, artifact, run_id="42",
                                               commit_sha="a"*40, attempt="1", source_root=root)
            return result, metadata, verifier

    def test_valid_zip_retains_verification(self):
        result, metadata, verifier = self.audit(make_zip())
        self.assertEqual(result["status"], "PASS_SCOPED")
        metadata.assert_called_once()
        verifier.assert_called_once()

    def test_local_compression_mismatch_blocks(self):
        raw = bytearray(make_zip())
        raw[8:10] = (8).to_bytes(2, "little")
        result, metadata, verifier = self.audit(bytes(raw))
        self.assertIn("zip_local_header_mismatch", result["violations"])
        metadata.assert_not_called()
        verifier.assert_not_called()

    def test_local_name_mismatch_blocks(self):
        raw = bytearray(make_zip())
        raw[30] = ord("X")
        result, metadata, verifier = self.audit(bytes(raw))
        self.assertIn("zip_local_header_mismatch", result["violations"])
        metadata.assert_not_called()
        verifier.assert_not_called()

    def test_corrupt_local_signature_blocks(self):
        raw = bytearray(make_zip())
        raw[0:4] = b"NOPE"
        result, metadata, verifier = self.audit(bytes(raw))
        self.assertIn("invalid_zip_local_header", result["violations"])
        metadata.assert_not_called()
        verifier.assert_not_called()

if __name__ == "__main__":
    unittest.main()
