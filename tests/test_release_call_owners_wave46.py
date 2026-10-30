"""Wave46 lexical callsite owner regression."""
import tempfile
import unittest
from pathlib import Path
from shutil import copyfile
from contracts.critical_release_call_baseline import OWNER_BASELINE, validate_release_call_owners

ROOT = Path(__file__).resolve().parents[1]


class ReleaseOwnerTests(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.root = Path(t.name)
        for rel in OWNER_BASELINE:
            target = self.root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            copyfile(ROOT / rel, target)

    def test_baseline_passes(self):
        self.assertEqual(validate_release_call_owners(self.root)["status"], "PASS_SCOPED")

    def test_moved_call_changes_owner(self):
        path = self.root / "compiler.py"
        source = path.read_text()
        source = source.replace("return run_optional_rea_release(", "return other_release(")
        path.write_text(source)
        self.assertEqual(validate_release_call_owners(self.root)["status"], "BLOCK")

    def test_removed_file_blocks(self):
        (self.root / "compiler.py").unlink()
        self.assertEqual(validate_release_call_owners(self.root)["status"], "BLOCK")


if __name__ == "__main__":
    unittest.main()
