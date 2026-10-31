"""Wave89: actual ZIP bytes with corrupt content must fail closed."""
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


def archive_data():
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED) as archive:
        archive.writestr(REPORT, b'{"valid": true}')
        archive.writestr(MANIFEST, b"{}")
    return output.getvalue()


class ZipDecompressionIntegrityTests(unittest.TestCase):
    def run_audit(self, raw):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "evidence.zip"
            path.write_bytes(raw)
            artifact = {"digest": "sha256:" + hashlib.sha256(raw).hexdigest()}
            with patch("tools.audit_postrun_release_archive.reconcile_artifact_metadata",
                       return_value={"violations": []}) as metadata, patch(
                       "tools.audit_postrun_release_archive.verify_evidence",
                       return_value={"violations": []}) as verifier:
                result = audit_postrun_archive(
                    path, artifact, run_id="42", commit_sha="a" * 40,
                    attempt="1", source_root=folder)
            return result, metadata, verifier

    def test_corrupted_member_crc_blocks_even_if_archive_digest_matches(self):
        original = archive_data()
        damaged = original.replace(b'{"valid": true}', b'{"valid": fals}')
        self.assertNotEqual(original, damaged)
        result, metadata, verifier = self.run_audit(damaged)
        self.assertEqual(result["status"], "BLOCK")
        self.assertIn("archive_entry_integrity_failure", result["violations"])
        metadata.assert_not_called()
        verifier.assert_not_called()

    def test_valid_zip_reaches_downstream_verifiers(self):
        result, metadata, verifier = self.run_audit(archive_data())
        self.assertEqual(result["status"], "PASS_SCOPED")
        metadata.assert_called_once()
        verifier.assert_called_once()


if __name__ == "__main__":
    unittest.main()
