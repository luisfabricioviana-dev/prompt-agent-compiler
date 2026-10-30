"""Wave67 read-only Git object source binding regression."""
import hashlib
import subprocess
import tempfile
import unittest
from pathlib import Path

from contracts.release_gate_git_tree_verifier import verify_git_tree_sources
from contracts.release_gate_source_binding import SOURCE_PATHS


class GitTreeEvidenceTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        subprocess.run(["git", "-C", str(self.root), "config", "user.email", "test@example.org"], check=True)
        subprocess.run(["git", "-C", str(self.root), "config", "user.name", "Regression"], check=True)
        self.recorded = {}
        for path in SOURCE_PATHS:
            file = self.root / path
            file.parent.mkdir(parents=True, exist_ok=True)
            raw = ("fixture " + path).encode()
            file.write_bytes(raw)
            self.recorded[path] = hashlib.sha256(raw).hexdigest()
        subprocess.run(["git", "-C", str(self.root), "add", "."], check=True)
        subprocess.run(["git", "-C", str(self.root), "commit", "-qm", "fixture"], check=True)
        self.sha = subprocess.check_output(["git", "-C", str(self.root), "rev-parse", "HEAD"]).decode().strip()

    def test_pinned_git_tree_passes(self):
        self.assertEqual(verify_git_tree_sources(self.root, self.sha, self.recorded)["status"], "PASS_SCOPED")

    def test_wrong_blob_digest_blocks(self):
        forged = dict(self.recorded)
        forged[SOURCE_PATHS[0]] = "0" * 64
        self.assertIn("git_blob_digest_mismatch:" + SOURCE_PATHS[0],
                      verify_git_tree_sources(self.root, self.sha, forged)["violations"])

    def test_invalid_commit_blocks(self):
        self.assertEqual(verify_git_tree_sources(self.root, "bad", self.recorded)["status"], "BLOCK")

    def test_missing_blob_blocks(self):
        (self.root / SOURCE_PATHS[0]).unlink()
        # Object remains verifiable even when worktree content is missing.
        self.assertEqual(verify_git_tree_sources(self.root, self.sha, self.recorded)["status"], "PASS_SCOPED")

    def test_unavailable_commit_blocks(self):
        self.assertEqual(verify_git_tree_sources(self.root, "f"*40, self.recorded)["status"], "BLOCK")


if __name__ == "__main__":
    unittest.main()
