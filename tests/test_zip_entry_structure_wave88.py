"""Wave88: fail closed on ZIP entries with unsafe Unix file type metadata."""
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

def archive_bytes(mode):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        info = zipfile.ZipInfo(REPORT)
        info.create_system = 3
        info.external_attr = (mode | 0o644) << 16
        archive.writestr(info, b"{}")
        archive.writestr(MANIFEST, b"{}")
    return stream.getvalue()

class EntryStructureTests(unittest.TestCase):
    def audit(self, mode):
        data = archive_bytes(mode)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "evidence.zip"
            path.write_bytes(data)
            artifact = {"digest": "sha256:" + hashlib.sha256(data).hexdigest()}
            with patch("tools.audit_postrun_release_archive.reconcile_artifact_metadata",
                       return_value={"violations": []}) as metadata, patch(
                       "tools.audit_postrun_release_archive.verify_evidence",
                       return_value={"violations": []}) as verifier:
                result = audit_postrun_archive(path, artifact, run_id="42",
                                               commit_sha="a" * 40,
                                               attempt="1", source_root=folder)
            return result, metadata, verifier

    def test_symlink_entry_blocks_before_verification(self):
        result, metadata, verifier = self.audit(0o120000)
        self.assertIn("unsafe_archive_entry", result["violations"])
        metadata.assert_not_called()
        verifier.assert_not_called()

    def test_directory_type_entry_blocks_before_verification(self):
        result, metadata, verifier = self.audit(0o040000)
        self.assertIn("unsafe_archive_entry", result["violations"])
        metadata.assert_not_called()
        verifier.assert_not_called()

    def test_regular_file_metadata_preserves_verification(self):
        result, metadata, verifier = self.audit(0o100000)
        self.assertEqual(result["status"], "PASS_SCOPED")
        metadata.assert_called_once()
        verifier.assert_called_once()

if __name__ == "__main__":
    unittest.main()
