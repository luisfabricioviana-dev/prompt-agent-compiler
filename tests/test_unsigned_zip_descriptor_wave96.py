"""Wave96: unsigned ZIP descriptor and mismatched declared sizes."""
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
    def seekable(self): return False
    def seek(self,*args): raise io.UnsupportedOperation("nonseekable")

def make_archive():
    output=NonSeekable()
    with zipfile.ZipFile(output,"w",compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(REPORT,b"{}")
        zf.writestr(MANIFEST,b"{}")
    return output.getvalue()

def first_descriptor(raw):
    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        entry=zf.infolist()[0]
    offset=entry.header_offset
    name_len=int.from_bytes(raw[offset+26:offset+28],"little")
    extra_len=int.from_bytes(raw[offset+28:offset+30],"little")
    return offset+30+name_len+extra_len+entry.compress_size

def remove_descriptor_signature(raw, index):
    """Remove four bytes and repair later central offsets and EOCD start."""
    data = bytearray(raw[:index] + raw[index+4:])
    cursor = 0
    while True:
        cursor = data.find(bytes((80, 75, 1, 2)), cursor)
        if cursor < 0:
            break
        old_offset = int.from_bytes(data[cursor+42:cursor+46], "little")
        if old_offset > index:
            data[cursor+42:cursor+46] = (old_offset-4).to_bytes(4, "little")
        cursor += 46
    eocd = data.rfind(bytes((80, 75, 5, 6)))
    if eocd < 0:
        raise AssertionError("missing eocd")
    central_offset = int.from_bytes(data[eocd+16:eocd+20], "little")
    data[eocd+16:eocd+20] = (central_offset-4).to_bytes(4, "little")
    return data


class UnsignedDescriptorTests(unittest.TestCase):
    def audit(self,raw):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"artifact.zip"
            path.write_bytes(raw)
            artifact={"digest":"sha256:"+hashlib.sha256(raw).hexdigest()}
            with patch("tools.audit_postrun_release_archive.reconcile_artifact_metadata",
                       return_value={"violations":[]}) as metadata,patch(
                       "tools.audit_postrun_release_archive.verify_evidence",
                       return_value={"violations":[]}) as verifier:
                result=audit_postrun_archive(path,artifact,run_id="42",
                                commit_sha="a"*40,attempt="1",source_root=folder)
            return result,metadata,verifier

    def test_unsigned_data_descriptor_is_valid(self):
        raw=make_archive()
        index=first_descriptor(raw)
        self.assertEqual(raw[index:index+4],bytes((80,75,7,8)))
        unsigned=remove_descriptor_signature(raw,index)
        result,metadata,verifier=self.audit(unsigned)
        self.assertEqual(result["status"],"PASS_SCOPED")
        metadata.assert_called_once()
        verifier.assert_called_once()

    def test_unsigned_descriptor_wrong_compressed_size_blocks(self):
        raw=make_archive()
        index=first_descriptor(raw)
        unsigned=remove_descriptor_signature(raw,index)
        unsigned[index+4:index+8]=(999).to_bytes(4,"little")
        result,metadata,verifier=self.audit(bytes(unsigned))
        self.assertIn("zip_data_descriptor_mismatch",result["violations"])
        metadata.assert_not_called()
        verifier.assert_not_called()

    def test_signed_descriptor_wrong_uncompressed_size_blocks(self):
        raw=bytearray(make_archive())
        index=first_descriptor(raw)
        raw[index+12:index+16]=(999).to_bytes(4,"little")
        result,metadata,verifier=self.audit(bytes(raw))
        self.assertIn("zip_data_descriptor_mismatch",result["violations"])
        metadata.assert_not_called()
        verifier.assert_not_called()

if __name__=="__main__":
    unittest.main()
