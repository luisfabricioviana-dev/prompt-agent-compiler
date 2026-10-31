"""Wave97: data descriptors cannot cross next ZIP member boundary."""
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

class NonSeekable(io.BytesIO):
    def seekable(self):
        return False
    def seek(self, *args):
        raise io.UnsupportedOperation("nonseekable")

def archive_bytes():
    buffer = NonSeekable()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(REPORT, b'{"value":1}')
        zf.writestr(MANIFEST, b"{}")
    return buffer.getvalue()

class DescriptorBoundariesTests(unittest.TestCase):
    def audit(self, raw):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "evidence.zip"
            path.write_bytes(raw)
            artifact = {"digest": "sha256:" + hashlib.sha256(raw).hexdigest()}
            with patch("tools.audit_postrun_release_archive.reconcile_artifact_metadata",
                       return_value={"violations": []}) as metadata, patch(
                       "tools.audit_postrun_release_archive.verify_evidence",
                       return_value={"violations": []}) as verifier:
                result = audit_postrun_archive(
                    path, artifact, run_id="42", commit_sha="a"*40,
                    attempt="1", source_root=root)
            return result, metadata, verifier

    def test_valid_descriptors_reach_verifiers(self):
        result, metadata, verifier = self.audit(archive_bytes())
        self.assertEqual(result["status"], "PASS_SCOPED")
        metadata.assert_called_once()
        verifier.assert_called_once()

    def test_fraudulent_compressed_length_crossing_next_entry_blocks(self):
        raw = bytearray(archive_bytes())
        first_central = raw.find(bytes((80, 75, 1, 2)))
        self.assertGreaterEqual(first_central, 0)
        raw[first_central + 20:first_central + 24] = (9999).to_bytes(4, "little")
        result, metadata, verifier = self.audit(bytes(raw))
        self.assertEqual(result["status"], "BLOCK")
        self.assertTrue({"zip_descriptor_boundary_violation", "zip_member_region_overlap"} & set(result["violations"]))
        metadata.assert_not_called()
        verifier.assert_not_called()

if __name__ == "__main__":
    unittest.main()
