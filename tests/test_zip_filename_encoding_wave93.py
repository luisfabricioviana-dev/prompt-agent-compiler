"""Wave93: reject noncanonical ZIP filename encoding flags."""
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

def make_zip():
    out=io.BytesIO()
    with zipfile.ZipFile(out,"w") as zf:
        zf.writestr(REPORT,b"{}")
        zf.writestr(MANIFEST,b"{}")
    return out.getvalue()

class EncodingTests(unittest.TestCase):
    def audit(self,raw):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"evidence.zip"
            path.write_bytes(raw)
            artifact={"digest":"sha256:"+hashlib.sha256(raw).hexdigest()}
            with patch("tools.audit_postrun_release_archive.reconcile_artifact_metadata",
                       return_value={"violations":[]}) as metadata,patch(
                       "tools.audit_postrun_release_archive.verify_evidence",
                       return_value={"violations":[]}) as integrity:
                result=audit_postrun_archive(path,artifact,run_id="42",
                            commit_sha="a"*40,attempt="1",source_root=folder)
            return result,metadata,integrity

    def test_plain_ascii_names_pass(self):
        result,metadata,integrity=self.audit(make_zip())
        self.assertEqual(result["status"],"PASS_SCOPED")
        metadata.assert_called_once()
        integrity.assert_called_once()

    def test_utf8_flag_on_ascii_name_blocks(self):
        raw=bytearray(make_zip())
        raw[6:8]=(0x800).to_bytes(2,"little")
        index=raw.find(bytes((80,75,1,2)))
        self.assertGreaterEqual(index,0)
        raw[index+8:index+10]=(0x800).to_bytes(2,"little")
        result,metadata,integrity=self.audit(bytes(raw))
        self.assertIn("unsupported_zip_filename_encoding",result["violations"])
        metadata.assert_not_called()
        integrity.assert_not_called()

    def test_local_name_mutation_blocks(self):
        raw=bytearray(make_zip())
        raw[30]=ord("X")
        result,metadata,integrity=self.audit(bytes(raw))
        self.assertIn("zip_local_header_mismatch",result["violations"])
        metadata.assert_not_called()
        integrity.assert_not_called()

if __name__=="__main__":
    unittest.main()
