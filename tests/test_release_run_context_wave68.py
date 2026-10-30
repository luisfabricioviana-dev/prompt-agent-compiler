"""Wave68 pinned CI run context tests."""
import unittest
from contracts.release_gate_run_context import verify_run_context

REPO = "luisfabricioviana-dev/prompt-agent-compiler"
SHA = "a" * 40
MANIFEST = {"commit_sha": SHA, "workflow_run_id": "123", "workflow_run_attempt": "1"}


def check(**overrides):
    args = dict(repository=REPO, workflow="Full project regression",
                event="pull_request", sha=SHA, run_id="123", attempt="1",
                expected_repository=REPO)
    args.update(overrides)
    return verify_run_context(MANIFEST, **args)


class RunContextTests(unittest.TestCase):
    def test_expected_context_passes(self):
        self.assertEqual(check()["status"], "PASS_SCOPED")

    def test_wrong_repository_blocks(self):
        self.assertIn("repository_identity_mismatch",
                      check(repository="attacker/repository")["violations"])

    def test_wrong_workflow_blocks(self):
        self.assertIn("workflow_identity_mismatch",
                      check(workflow="Release unreviewed")["violations"])

    def test_wrong_run_or_sha_blocks(self):
        for params, reason in (({"sha": "b" * 40}, "commit_sha_mismatch"),
                               ({"run_id": "124"}, "workflow_run_id_mismatch"),
                               ({"attempt": "2"}, "workflow_run_attempt_mismatch")):
            with self.subTest(params=params):
                self.assertIn(reason, check(**params)["violations"])

    def test_unapproved_event_blocks(self):
        self.assertIn("unapproved_workflow_event",
                      check(event="repository_dispatch")["violations"])


if __name__ == "__main__":
    unittest.main()
