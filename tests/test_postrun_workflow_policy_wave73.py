"""Wave73 policy regression for the opt-in post-run audit workflow."""
import unittest
from pathlib import Path

WORKFLOW = (Path(__file__).resolve().parents[1] /
            ".github/workflows/release-gate-postrun-audit.yml")


class PostrunWorkflowPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow = WORKFLOW.read_text(encoding="utf-8")

    def test_manual_only_and_read_permissions(self):
        self.assertIn("workflow_dispatch:", self.workflow)
        self.assertNotIn("workflow_run:", self.workflow)
        self.assertIn("  contents: read", self.workflow)
        self.assertIn("  actions: read", self.workflow)
        self.assertNotIn("  contents: write", self.workflow)
        self.assertNotIn("  actions: write", self.workflow)

    def test_commit_bound_checkout(self):
        self.assertIn("ref: ${{ inputs.evidence_commit_sha }}", self.workflow)
        self.assertIn("persist-credentials: false", self.workflow)

    def test_only_postrun_audit_invoked(self):
        self.assertIn("python -m tools.audit_remote_release_archive", self.workflow)
        self.assertNotIn("run_optional_rea_release", self.workflow)
        self.assertNotIn("run_governed_pipeline", self.workflow)


if __name__ == "__main__":
    unittest.main()
