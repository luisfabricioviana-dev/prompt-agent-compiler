"""Wave94: local ZIP CRC and sizes must match central directory absent descriptor."""
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
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED) as zf:
        zf.writestr(REPORT, b"{}")
        zf.writestr(MANIFEST, b"{}")
    return output.getvalue()

class IntegrityMetadataTests(unittest.TestCase):
    def audit(self, raw):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "evidence.zip"
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

    def test_valid_metadata_reaches_verifiers(self):
        result, metadata, verifier = self.audit(fixture())
        self.assertEqual(result["status"], "PASS_SCOPED")
        metadata.assert_called_once()
        verifier.assert_called_once()

    def test_crc_mismatch_blocks_even_with_recomputed_archive_digest(self):
        raw = bytearray(fixture())
        raw[14:18] = (0).to_bytes(4, "little")
        result, metadata, verifier = self.audit(bytes(raw))
        self.assertIn("zip_local_integrity_metadata_mismatch", result["violations"])
        metadata.assert_not_called()
        verifier.assert_not_called()

    def test_compressed_size_mismatch_blocks(self):
        raw = bytearray(fixture())
        raw[18:22] = (999).to_bytes(4, "little")
        result, metadata, verifier = self.audit(bytes(raw))
        self.assertIn("zip_local_integrity_metadata_mismatch", result["violations"])
        metadata.assert_not_called()
        verifier.assert_not_called()

    def test_uncompressed_size_mismatch_blocks(self):
        raw = bytearray(fixture())
        raw[22:26] = (999).to_bytes(4, "little")
        result, metadata, verifier = self.audit(bytes(raw))
        self.assertIn("zip_local_integrity_metadata_mismatch", result["violations"])
        metadata.assert_not_called()
        verifier.assert_not_called()

if __name__ == "__main__":
    unittest.main()
