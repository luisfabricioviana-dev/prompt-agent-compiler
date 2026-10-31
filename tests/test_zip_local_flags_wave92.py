"""Wave92: local ZIP flags must agree with central metadata."""
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

def fixture():
    output=io.BytesIO()
    with zipfile.ZipFile(output,"w",compression=zipfile.ZIP_STORED) as zf:
        zf.writestr(REPORT,b"{}")
        zf.writestr(MANIFEST,b"{}")
    return output.getvalue()

class LocalFlagsTests(unittest.TestCase):
    def run_archive(self,data):
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/"test.zip"
            path.write_bytes(data)
            artifact={"digest":"sha256:"+hashlib.sha256(data).hexdigest()}
            with patch("tools.audit_postrun_release_archive.reconcile_artifact_metadata",
                       return_value={"violations":[]}) as metadata,patch(
                       "tools.audit_postrun_release_archive.verify_evidence",
                       return_value={"violations":[]}) as integrity:
                result=audit_postrun_archive(path,artifact,run_id="42",
                      commit_sha="a"*40,attempt="1",source_root=root)
            return result,metadata,integrity

    def test_valid_flags_pass(self):
        result,metadata,integrity=self.run_archive(fixture())
        self.assertEqual(result["status"],"PASS_SCOPED")
        metadata.assert_called_once()
        integrity.assert_called_once()

    def test_local_only_flag_mutation_blocks(self):
        data=bytearray(fixture())
        data[6:8]=(0x0008).to_bytes(2,"little")
        result,metadata,integrity=self.run_archive(bytes(data))
        self.assertIn("zip_local_flags_mismatch",result["violations"])
        metadata.assert_not_called()
        integrity.assert_not_called()

    def test_unsupported_flag_in_both_headers_blocks(self):
        data=bytearray(fixture())
        data[6:8]=(0x0040).to_bytes(2,"little")
        index=data.find(b"PK\\x01\\x02".decode("unicode_escape").encode("latin1"))
        self.assertGreaterEqual(index,0)
        data[index+8:index+10]=(0x0040).to_bytes(2,"little")
        result,metadata,integrity=self.run_archive(bytes(data))
        self.assertIn("zip_local_flags_mismatch",result["violations"])
        metadata.assert_not_called()
        integrity.assert_not_called()

if __name__=="__main__":
    unittest.main()
