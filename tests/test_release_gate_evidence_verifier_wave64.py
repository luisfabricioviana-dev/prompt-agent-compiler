"""Wave64 independent integrity verification and tampering fixtures."""
import json
import tempfile
import unittest
from pathlib import Path
from tools.build_release_gate_evidence_manifest import build_manifest
from contracts.release_gate_evidence_verifier import verify_evidence


class EvidenceVerifierTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.report = self.root / "release-gate-differential-report.json"
        self.manifest = self.root / "manifest.json"
        self.data = {"schema": "release-gate-differential-report-v1", "status": "PASS",
                     "case_count": 1, "match_count": 1, "scope": "test_scoped",
                     "cases": [{"case": "baseline", "matched": True,
                                "old": {"status": "PASS_SCOPED"},
                                "current": {"status": "PASS_SCOPED"}}]}
        self.write()

    def write(self):
        self.report.write_text(json.dumps(self.data), encoding="utf-8")
        self.manifest.write_text(json.dumps(build_manifest(
            self.report, sha="a"*40, run_id="42", run_attempt="1")), encoding="utf-8")

    def check(self):
        return verify_evidence(self.report, self.manifest,
                               commit_sha="a"*40, run_id="42", run_attempt="1")

    def test_verified_evidence(self):
        self.assertEqual(self.check()["status"], "PASS_SCOPED")

    def test_report_modified_after_manifest_blocks(self):
        self.report.write_bytes(self.report.read_bytes() + b" ")
        self.assertIn("report_digest_mismatch", self.check()["violations"])

    def test_wrong_workflow_identity_blocks(self):
        result = verify_evidence(self.report, self.manifest,
                                 commit_sha="b"*40, run_id="43", run_attempt="2")
        self.assertEqual(result["status"], "BLOCK")
        self.assertIn("commit_sha_mismatch", result["violations"])

    def test_consistently_rehashed_forged_diagnostics_block(self):
        self.data["cases"][0]["current"] = {"status": "BLOCK"}
        self.write()
        self.assertIn("case_diagnostic_mismatch", self.check()["violations"])

    def test_missing_files_block(self):
        self.manifest.unlink()
        self.assertEqual(self.check()["status"], "BLOCK")


if __name__ == "__main__":
    unittest.main()
