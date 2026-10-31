"""Wave87: ZIP inventory identity cannot be bypassed by duplicate names."""
import hashlib
import io
import tempfile
import unittest
import warnings
import zipfile
from pathlib import Path
from unittest.mock import patch

from tools.audit_postrun_release_archive import audit_postrun_archive

SHA = "a" * 40
REPORT = "release-gate-differential-report.json"
MANIFEST = "release-gate-evidence-manifest.json"


def make_archive(duplicate=False):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(REPORT, b"{}")
        archive.writestr(MANIFEST, b"{}")
        if duplicate:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                archive.writestr(REPORT, b'{"alternate": true}')
    return buffer.getvalue()


class ZIPIdentityTests(unittest.TestCase):
    def run_archive(self, payload):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "evidence.zip"
            path.write_bytes(payload)
            artifact = {"digest": "sha256:" + hashlib.sha256(payload).hexdigest()}
            with patch("tools.audit_postrun_release_archive.reconcile_artifact_metadata",
                       return_value={"violations": []}) as metadata, patch(
                       "tools.audit_postrun_release_archive.verify_evidence",
                       return_value={"violations": []}) as evidence:
                result = audit_postrun_archive(
                    path, artifact, run_id="42", commit_sha=SHA,
                    attempt="1", source_root=directory)
            return result, metadata, evidence

    def test_duplicate_entry_rejected_despite_matching_provider_digest(self):
        result, metadata, evidence = self.run_archive(make_archive(duplicate=True))
        self.assertEqual(result["status"], "BLOCK")
        self.assertIn("archive_inventory_mismatch", result["violations"])
        metadata.assert_not_called()
        evidence.assert_not_called()

    def test_unique_expected_members_preserve_verifier_path(self):
        result, metadata, evidence = self.run_archive(make_archive())
        self.assertEqual(result["status"], "PASS_SCOPED")
        metadata.assert_called_once()
        evidence.assert_called_once()


if __name__ == "__main__":
    unittest.main()
