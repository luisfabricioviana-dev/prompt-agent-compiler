"""Wave66: source hashes bind report/manifest to the checked-out inputs."""
import json
import tempfile
import unittest
from pathlib import Path
from shutil import copyfile
from contracts.release_gate_source_binding import SOURCE_PATHS, source_digests
from contracts.release_gate_evidence_verifier import verify_evidence
from tools.build_release_gate_evidence_manifest import build_manifest

ROOT = Path(__file__).resolve().parents[1]
NAMES = ("baseline", "module_rebind", "local_rebind",
         "shadow_import", "nested_capture", "dynamic_exec")


class SourceEvidenceBindingTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        for name in SOURCE_PATHS:
            dest = self.root / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            copyfile(ROOT / name, dest)
        self.report = self.root / "release-gate-differential-report.json"
        self.manifest = self.root / "manifest.json"
        payload = {"schema": "release-gate-differential-report-v1", "status": "PASS",
                   "case_count": 6, "match_count": 6,
                   "scope": "six_scoped_deterministic_fixtures_not_exhaustive",
                   "cases": [{"case": name, "matched": True,
                              "old": {"status": "PASS_SCOPED"},
                              "current": {"status": "PASS_SCOPED"}}
                             for name in NAMES]}
        self.report.write_text(json.dumps(payload))
        result = build_manifest(self.report, sha="a"*40, run_id="12", run_attempt="1")
        result["source_sha256"] = source_digests(self.root)
        self.manifest.write_text(json.dumps(result))

    def check(self):
        return verify_evidence(self.report, self.manifest,
                               commit_sha="a"*40, run_id="12", run_attempt="1",
                               source_root=self.root)

    def test_matching_sources_pass(self):
        self.assertEqual(self.check()["status"], "PASS_SCOPED")

    def test_source_changed_after_manifest_blocks(self):
        path = self.root / SOURCE_PATHS[0]
        path.write_bytes(path.read_bytes() + b"\n# altered\n")
        self.assertIn("source_digest_mismatch", self.check()["violations"])

    def test_removed_source_blocks(self):
        (self.root / SOURCE_PATHS[1]).unlink()
        self.assertIn("source_inventory_unreadable", self.check()["violations"])

    def test_manifest_source_digest_tampering_blocks(self):
        manifest = json.loads(self.manifest.read_text())
        manifest["source_sha256"][SOURCE_PATHS[0]] = "0"*64
        self.manifest.write_text(json.dumps(manifest))
        self.assertIn("source_digest_mismatch", self.check()["violations"])


if __name__ == "__main__":
    unittest.main()
