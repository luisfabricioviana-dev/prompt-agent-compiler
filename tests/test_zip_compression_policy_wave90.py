"""Wave90: real archive methods and declared size limits."""
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

class ZipCompressionPolicyTests(unittest.TestCase):
    def run_archive(self, compression, payload=b"{}"):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", compression=compression) as zf:
            zf.writestr(REPORT, payload)
            zf.writestr(MANIFEST, b"{}")
        raw = buffer.getvalue()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "archive.zip"
            path.write_bytes(raw)
            artifact = {"digest": "sha256:" + hashlib.sha256(raw).hexdigest()}
            with patch("tools.audit_postrun_release_archive.reconcile_artifact_metadata",
                       return_value={"violations": []}) as metadata, patch(
                       "tools.audit_postrun_release_archive.verify_evidence",
                       return_value={"violations": []}) as verifier:
                result = audit_postrun_archive(
                    path, artifact, run_id="42", commit_sha="a"*40,
                    attempt="1", source_root=directory)
            return result, metadata, verifier

    def test_deflated_valid_evidence_reaches_verifiers(self):
        result, metadata, verifier = self.run_archive(zipfile.ZIP_DEFLATED)
        self.assertEqual(result["status"], "PASS_SCOPED")
        metadata.assert_called_once()
        verifier.assert_called_once()

    def test_stored_valid_evidence_reaches_verifiers(self):
        result, metadata, verifier = self.run_archive(zipfile.ZIP_STORED)
        self.assertEqual(result["status"], "PASS_SCOPED")
        metadata.assert_called_once()
        verifier.assert_called_once()

    def test_bzip2_archive_blocks_even_with_matching_digest(self):
        result, metadata, verifier = self.run_archive(zipfile.ZIP_BZIP2)
        self.assertIn("unsupported_archive_compression", result["violations"])
        metadata.assert_not_called()
        verifier.assert_not_called()

    def test_oversized_declared_member_blocks_before_extraction(self):
        result, metadata, verifier = self.run_archive(zipfile.ZIP_DEFLATED, b"z"*1_000_001)
        self.assertIn("archive_entry_too_large", result["violations"])
        metadata.assert_not_called()
        verifier.assert_not_called()

if __name__ == "__main__":
    unittest.main()
