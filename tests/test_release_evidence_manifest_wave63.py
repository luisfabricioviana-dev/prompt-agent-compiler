"""Wave63 provenance-manifest unit tests."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from tools.build_release_gate_evidence_manifest import build_manifest


class EvidenceManifestTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.file = Path(tmp.name) / "report.json"
        self.payload = {"status": "PASS", "case_count": 6, "match_count": 6,
                        "scope": "six_scoped_deterministic_fixtures_not_exhaustive"}
        self.file.write_text(json.dumps(self.payload), encoding="utf-8")

    def test_digest_and_run_binding(self):
        result = build_manifest(self.file, sha="a" * 40, run_id="123", run_attempt="2")
        self.assertEqual(result["report_sha256"], hashlib.sha256(self.file.read_bytes()).hexdigest())
        self.assertEqual((result["commit_sha"], result["workflow_run_id"], result["workflow_run_attempt"]),
                         ("a" * 40, "123", "2"))

    def test_reject_report_failure(self):
        self.payload["match_count"] = 5
        self.file.write_text(json.dumps(self.payload), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "differential_report_not_pass"):
            build_manifest(self.file, sha="a" * 40, run_id="123", run_attempt="1")

    def test_reject_unbound_identity(self):
        for sha, run_id, attempt in (("bad", "123", "1"), ("a" * 40, "bad", "1"),
                                     ("a" * 40, "123", "bad")):
            with self.subTest(sha=sha, run_id=run_id, attempt=attempt):
                with self.assertRaises(ValueError):
                    build_manifest(self.file, sha=sha, run_id=run_id, run_attempt=attempt)


if __name__ == "__main__":
    unittest.main()
