"""Wave95: verify ZIP data descriptors from nonseekable ZIP writers."""
import hashlib
import io
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch
from tools.audit_postrun_release_archive import audit_postrun_archive

REPORT="release-gate-differential-report.json"
MANIFEST="release-gate-evidence-manifest.json"

class NonSeekable(io.BytesIO):
    def seekable(self):
        return False
    def seek(self,*args):
        raise io.UnsupportedOperation("nonseekable")

def archive_bytes():
    out=NonSeekable()
    with zipfile.ZipFile(out,"w",compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(REPORT,b"{}")
        zf.writestr(MANIFEST,b"{}")
    return out.getvalue()

class DescriptorIntegrityTests(unittest.TestCase):
    def audit(self,raw):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"evidence.zip"
            path.write_bytes(raw)
            artifact={"digest":"sha256:"+hashlib.sha256(raw).hexdigest()}
            with patch("tools.audit_postrun_release_archive.reconcile_artifact_metadata",
                       return_value={"violations":[]}) as metadata,patch(
                       "tools.audit_postrun_release_archive.verify_evidence",
                       return_value={"violations":[]}) as verifier:
                result=audit_postrun_archive(path,artifact,run_id="42",
                                commit_sha="a"*40,attempt="1",source_root=directory)
            return result,metadata,verifier

    def test_valid_descriptor_preserves_verifiers(self):
        raw=archive_bytes()
        with zipfile.ZipFile(io.BytesIO(raw)) as zf:
            self.assertTrue(zf.infolist()[0].flag_bits & 0x8)
        result,metadata,verifier=self.audit(raw)
        self.assertEqual(result["status"],"PASS_SCOPED")
        metadata.assert_called_once()
        verifier.assert_called_once()

    def test_modified_descriptor_crc_blocks(self):
        raw=bytearray(archive_bytes())
        with zipfile.ZipFile(io.BytesIO(raw)) as zf:
            entry=zf.infolist()[0]
            off=entry.header_offset
            name_len=int.from_bytes(raw[off+26:off+28],"little")
            extra_len=int.from_bytes(raw[off+28:off+30],"little")
            descriptor=off+30+name_len+extra_len+entry.compress_size
        self.assertEqual(raw[descriptor:descriptor+4],bytes((80,75,7,8)))
        raw[descriptor+4:descriptor+8]=(0).to_bytes(4,"little")
        result,metadata,verifier=self.audit(bytes(raw))
        self.assertIn("zip_data_descriptor_mismatch",result["violations"])
        metadata.assert_not_called()
        verifier.assert_not_called()

if __name__=="__main__":
    unittest.main()
