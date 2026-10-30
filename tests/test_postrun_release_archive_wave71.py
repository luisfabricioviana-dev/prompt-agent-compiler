"""Wave71 archive verifier tests: bytes, inventory, and fail closed."""
import hashlib
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from tools.audit_postrun_release_archive import audit_postrun_archive

SHA = "a" * 40


class ArchiveAuditTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.archive = self.root / "evidence.zip"
        self.manifest = {"commit_sha": SHA, "workflow_run_id": "42"}
        self.payload = {"release-gate-differential-report.json": b'{"status":"PASS"}',
                        "release-gate-evidence-manifest.json": json.dumps(self.manifest).encode()}

    def artifact(self, payload=None):
        with zipfile.ZipFile(self.archive, "w") as archive:
            for name, value in (payload or self.payload).items():
                archive.writestr(name, value)
        return {"id": 1, "name": "release-gate-differential-evidence",
                "expired": False,
                "digest": "sha256:" + hashlib.sha256(self.archive.read_bytes()).hexdigest(),
                "workflow_run": {"id": 42, "head_sha": SHA}}

    def check(self, artifact):
        return audit_postrun_archive(self.archive, artifact, run_id="42",
                                     commit_sha=SHA, attempt="1", source_root=self.root)

    def test_valid_archive_reaches_independent_verifier(self):
        artifact = self.artifact()
        with patch("tools.audit_postrun_release_archive.verify_evidence",
                   return_value={"status": "PASS_SCOPED", "violations": []}):
            self.assertEqual(self.check(artifact)["status"], "PASS_SCOPED")

    def test_archive_tampering_blocks(self):
        artifact = self.artifact()
        self.archive.write_bytes(self.archive.read_bytes() + b"x")
        self.assertIn("archive_digest_mismatch", self.check(artifact)["violations"])

    def test_extra_archive_member_blocks(self):
        payload = dict(self.payload, **{"injected.txt": b"malicious"})
        artifact = self.artifact(payload)
        self.assertIn("archive_inventory_mismatch", self.check(artifact)["violations"])

    def test_mismatched_artifact_run_blocks(self):
        artifact = self.artifact()
        artifact["workflow_run"] = {"id": 43, "head_sha": SHA}
        self.assertIn("artifact_run_id_mismatch", self.check(artifact)["violations"])

    def test_malformed_archive_blocks(self):
        self.archive.write_bytes(b"not-a-zip")
        artifact = {"digest": "sha256:" + hashlib.sha256(self.archive.read_bytes()).hexdigest()}
        self.assertEqual(self.check(artifact)["status"], "BLOCK")


if __name__ == "__main__":
    unittest.main()
