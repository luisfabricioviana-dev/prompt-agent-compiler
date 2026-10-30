import tempfile
import unittest
from pathlib import Path
from shutil import copyfile
from contracts.critical_release_call_baseline import BASELINE, validate_critical_release_calls

ROOT = Path(__file__).resolve().parents[1]


class CriticalCallBaselineTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        for rel in BASELINE:
            target = self.root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            copyfile(ROOT / rel, target)

    def test_baseline(self):
        self.assertEqual(validate_critical_release_calls(self.root)["status"], "PASS_SCOPED")

    def test_added_release_call_blocks(self):
        path = self.root / "compiler.py"
        path.write_text(path.read_text() + "\nrun_optional_rea_release(None)\n")
        self.assertEqual(validate_critical_release_calls(self.root)["status"], "BLOCK")

    def test_removed_release_call_blocks(self):
        path = self.root / "contracts/rea_pipeline.py"
        path.write_text(path.read_text().replace("reconcile_delivery(", "renamed_reconcile(", 1))
        self.assertEqual(validate_critical_release_calls(self.root)["status"], "BLOCK")

    def test_missing_file_blocks(self):
        (self.root / "compiler.py").unlink()
        self.assertEqual(validate_critical_release_calls(self.root)["status"], "BLOCK")


if __name__ == "__main__":
    unittest.main()
