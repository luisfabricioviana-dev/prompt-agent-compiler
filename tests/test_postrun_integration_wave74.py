"""Wave74: end-to-end read-only audit with actual ZIP bytes and mocked GitHub HTTP."""
import hashlib
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from shutil import copyfile

from contracts.release_gate_source_binding import SOURCE_PATHS, source_digests
from tools.audit_remote_release_archive import audit_remote_archive
from tools.build_release_gate_evidence_manifest import build_manifest

ROOT = Path(__file__).resolve().parents[1]
SHA = "a" * 40
NAMES = ("baseline", "module_rebind", "local_rebind",
         "shadow_import", "nested_capture", "dynamic_exec")


class Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class PostrunIntegrationTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        for name in SOURCE_PATHS:
            dest = self.root / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            copyfile(ROOT / name, dest)
        self.report = self.root / "release-gate-differential-report.json"
        self.manifest = self.root / "release-gate-evidence-manifest.json"
        records = [{"case": name, "matched": True,
                    "old": {"status": "PASS_SCOPED", "violations": []},
                    "current": {"status": "PASS_SCOPED", "violations": []}}
                   for name in NAMES]
        payload = {"schema": "release-gate-differential-report-v1",
                   "scope": "six_scoped_deterministic_fixtures_not_exhaustive",
                   "status": "PASS", "case_count": 6, "match_count": 6,
                   "cases": records}
        self.report.write_text(json.dumps(payload), encoding="utf-8")
        metadata = build_manifest(self.report, sha=SHA, run_id="42", run_attempt="1")
        metadata["source_sha256"] = source_digests(self.root)
        self.manifest.write_text(json.dumps(metadata), encoding="utf-8")

    def verify(self, *, tamper_manifest=False, tamper_archive=False):
        manifest = json.loads(self.manifest.read_text())
        if tamper_manifest:
            manifest["commit_sha"] = "b" * 40
        with io.BytesIO() as sink:
            with zipfile.ZipFile(sink, "w") as archive:
                archive.writestr(self.report.name, self.report.read_bytes())
                archive.writestr(self.manifest.name, json.dumps(manifest).encode())
            raw = sink.getvalue()
        artifact = {"id": 100, "name": "release-gate-differential-evidence",
                    "expired": False, "digest": "sha256:" + hashlib.sha256(raw).hexdigest(),
                    "workflow_run": {"id": 42, "head_sha": SHA}}
        if tamper_archive:
            raw += b"x"
        calls = []

        def opener(request, timeout):
            calls.append(request.full_url)
            if len(calls) == 1:
                return Response(json.dumps({"artifacts": [artifact], "total_count": 1}).encode())
            return Response(raw)

        result = audit_remote_archive(
            run_id="42", commit_sha=SHA, attempt="1",
            token="mock-token", source_root=self.root, opener=opener)
        self.assertEqual(len(calls), 2)
        return result

    def test_complete_valid_archive_passes(self):
        self.assertEqual(self.verify()["status"], "PASS_SCOPED")

    def test_changed_manifest_identity_blocks(self):
        self.assertIn("manifest_commit_mismatch",
                      self.verify(tamper_manifest=True)["violations"])

    def test_mutated_download_bytes_block(self):
        self.assertIn("archive_digest_mismatch",
                      self.verify(tamper_archive=True)["violations"])

    def test_missing_source_blocks(self):
        (self.root / SOURCE_PATHS[0]).unlink()
        self.assertIn("source_inventory_unreadable", self.verify()["violations"])


if __name__ == "__main__":
    unittest.main()
