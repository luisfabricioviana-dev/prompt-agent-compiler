"""Wave98: compressed ZIP member regions cannot overlap later headers."""
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
    with zipfile.ZipFile(out,"w",compression=zipfile.ZIP_STORED) as zf:
        zf.writestr(REPORT,b"{}")
        zf.writestr(MANIFEST,b"{}")
    return out.getvalue()

class RegionTests(unittest.TestCase):
    def audit(self,raw):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"archive.zip"
            path.write_bytes(raw)
            artifact={"digest":"sha256:"+hashlib.sha256(raw).hexdigest()}
            with patch("tools.audit_postrun_release_archive.reconcile_artifact_metadata",
                       return_value={"violations":[]}) as metadata, patch(
                       "tools.audit_postrun_release_archive.verify_evidence",
                       return_value={"violations":[]}) as verifier:
                result=audit_postrun_archive(path,artifact,run_id="42",
                                              commit_sha="a"*40,attempt="1",source_root=folder)
            return result,metadata,verifier

    def test_valid_regions_pass(self):
        result,metadata,verifier=self.audit(make_zip())
        self.assertEqual(result["status"],"PASS_SCOPED")
        metadata.assert_called_once()
        verifier.assert_called_once()

    def test_forged_central_compressed_size_crosses_next_header(self):
        raw=bytearray(make_zip())
        central=raw.find(bytes((80,75,1,2)))
        self.assertGreaterEqual(central,0)
        raw[central+20:central+24]=(9999).to_bytes(4,"little")
        result,metadata,verifier=self.audit(bytes(raw))
        self.assertIn("zip_member_region_overlap",result["violations"])
        metadata.assert_not_called()
        verifier.assert_not_called()

if __name__=="__main__":
    unittest.main()
