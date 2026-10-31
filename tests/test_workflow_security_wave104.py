"""Wave104: regress immutable, read-only workflow boundary controls."""
import re
import unittest
from pathlib import Path

WORKFLOWS = Path(__file__).resolve().parents[1] / ".github" / "workflows"


class WorkflowSecurityTests(unittest.TestCase):
    def test_all_checkout_steps_disable_persistent_credentials(self):
        for name in ("full-regression.yml", "release-gate-postrun-audit.yml"):
            contents = (WORKFLOWS / name).read_text(encoding="utf-8")
            checkouts = re.findall(
                r"(?m)^\s+- uses: actions/checkout@[a-f0-9]{40}[^\n]*"
                r"(?:(?!\n\s+- (?:uses|name):)[\s\S])*?",
                contents,
            )
            # Each checkout invocation must have its own setting, not merely
            # a matching setting elsewhere in the workflow.
            lines = contents.splitlines()
            offsets = [i for i, line in enumerate(lines)
                       if re.search(r"- uses: actions/checkout@[a-f0-9]{40}", line)]
            self.assertTrue(offsets, name)
            for index in offsets:
                section = "\n".join(lines[index:index + 4])
                self.assertIn("persist-credentials: false", section, (name, index))

    def test_workflow_permissions_are_read_only(self):
        regression = (WORKFLOWS / "full-regression.yml").read_text(encoding="utf-8")
        postrun = (WORKFLOWS / "release-gate-postrun-audit.yml").read_text(encoding="utf-8")
        self.assertIn("permissions:\n  contents: read\n", regression)
        self.assertIn("permissions:\n  contents: read\n  actions: read\n", postrun)
        self.assertNotRegex(regression + postrun, r"(?m)^\s+(?:contents|actions): write\s*$")

    def test_postrun_audit_has_manual_trigger_only(self):
        postrun = (WORKFLOWS / "release-gate-postrun-audit.yml").read_text(encoding="utf-8")
        preamble = postrun.split("\npermissions:", 1)[0]
        self.assertIn("  workflow_dispatch:", preamble)
        self.assertNotIn("\n  push:", preamble)
        self.assertNotIn("\n  pull_request:", preamble)
        self.assertNotIn("\n  schedule:", preamble)


if __name__ == "__main__":
    unittest.main()
