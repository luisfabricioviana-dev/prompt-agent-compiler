"""Wave65: jointly rehashed report/manifest must not alter fixture identities."""
import json
import tempfile
import unittest
from pathlib import Path

from contracts.release_gate_evidence_verifier import verify_evidence
from tools.build_release_gate_evidence_manifest import build_manifest

NAMES = ("baseline", "module_rebind", "local_rebind",
         "shadow_import", "nested_capture", "dynamic_exec")


class PinnedFixturesTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.report = self.root / "release-gate-differential-report.json"
        self.manifest = self.root / "manifest.json"
        self.payload = {
            "schema": "release-gate-differential-report-v1",
            "scope": "six_scoped_deterministic_fixtures_not_exhaustive",
            "status": "PASS", "case_count": 6, "match_count": 6,
            "cases": [
                {"case": name, "matched": True,
                 "old": {"status": "PASS_SCOPED"},
                 "current": {"status": "PASS_SCOPED"}}
                for name in NAMES
            ],
        }

    def check(self):
        self.report.write_text(json.dumps(self.payload), encoding="utf-8")
        self.manifest.write_text(json.dumps(build_manifest(
            self.report, sha="a" * 40, run_id="123", run_attempt="1")), encoding="utf-8")
        return verify_evidence(self.report, self.manifest,
                               commit_sha="a" * 40, run_id="123", run_attempt="1")

    def test_valid_corpus(self):
        self.assertEqual(self.check()["status"], "PASS_SCOPED")

    def test_jointly_rehashed_renamed_fixture(self):
        self.payload["cases"][1]["case"] = "tampered"
        self.assertIn("fixture_identity_mismatch", self.check()["violations"])

    def test_jointly_rehashed_swapped_fixture_order(self):
        self.payload["cases"][1], self.payload["cases"][2] = (
            self.payload["cases"][2], self.payload["cases"][1])
        self.assertIn("fixture_identity_mismatch", self.check()["violations"])

    def test_jointly_rehashed_wrong_scope(self):
        self.payload["scope"] = "unverified_scope"
        self.assertIn("fixture_scope_mismatch", self.check()["violations"])


if __name__ == "__main__":
    unittest.main()
