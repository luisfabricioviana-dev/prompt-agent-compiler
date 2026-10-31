"""Wave100 consolidated regressions for independent ZIP structural gates."""
import hashlib
import io
import tempfile
import unittest
import warnings
import zipfile
from pathlib import Path
from unittest.mock import patch
from tools.audit_postrun_release_archive import audit_postrun_archive

REPORT = "release-gate-differential-report.json"
MANIFEST = "release-gate-evidence-manifest.json"

def archive_bytes(extra=False, duplicate=False):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_STORED) as zf:
        zf.writestr(REPORT, b"{}")
        zf.writestr(MANIFEST, b"{}")
        if extra:
            zf.writestr("unapproved.json", b"{}")
        if duplicate:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                zf.writestr(REPORT, b"{}")
    return stream.getvalue()

class ConsolidatedZipAuditTests(unittest.TestCase):
    def audit(self, raw, digest=None):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "evidence.zip"
            path.write_bytes(raw)
            artifact = {"digest": digest if digest is not None else
                        "sha256:" + hashlib.sha256(raw).hexdigest()}
            with patch("tools.audit_postrun_release_archive.reconcile_artifact_metadata",
                       return_value={"violations": []}) as metadata, patch(
                       "tools.audit_postrun_release_archive.verify_evidence",
                       return_value={"violations": []}) as verifier:
                result = audit_postrun_archive(path, artifact, run_id="42",
                                               commit_sha="a" * 40,
                                               attempt="1", source_root=root)
            return result, metadata, verifier

    def test_canonical_archive_delegates_to_both_verifiers(self):
        result, metadata, verifier = self.audit(archive_bytes())
        self.assertEqual(result["status"], "PASS_SCOPED")
        metadata.assert_called_once()
        verifier.assert_called_once()

    def test_extra_entry_fails_before_downstream_verification(self):
        result, metadata, verifier = self.audit(archive_bytes(extra=True))
        self.assertEqual(result["status"], "BLOCK")
        self.assertIn("archive_inventory_mismatch", result["violations"])
        metadata.assert_not_called()
        verifier.assert_not_called()

    def test_duplicate_entry_fails_before_downstream_verification(self):
        result, metadata, verifier = self.audit(archive_bytes(duplicate=True))
        self.assertIn("archive_inventory_mismatch", result["violations"])
        metadata.assert_not_called()
        verifier.assert_not_called()

    def test_outer_digest_mismatch_fails_before_zip_inspection(self):
        result, metadata, verifier = self.audit(archive_bytes(), "sha256:" + "0"*64)
        self.assertIn("archive_digest_mismatch", result["violations"])
        metadata.assert_not_called()
        verifier.assert_not_called()

    def test_broken_zip_with_matching_outer_digest_blocks(self):
        result, metadata, verifier = self.audit(b"this is not a zip")
        self.assertEqual(result["status"], "BLOCK")
        self.assertIn("archive_unverifiable", result["violations"])
        metadata.assert_not_called()
        verifier.assert_not_called()

if __name__ == "__main__":
    unittest.main()
