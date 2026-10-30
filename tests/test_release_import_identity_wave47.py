"""Wave 47: critical release calls must resolve to pinned import identities."""
import tempfile
import unittest
from pathlib import Path
from shutil import copyfile
from contracts.release_import_identity_gate import EXPECTED, validate_critical_import_identity

ROOT = Path(__file__).resolve().parents[1]


class ImportIdentityTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        for relative in EXPECTED:
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            copyfile(ROOT / relative, target)

    def test_current_edge_baseline(self):
        self.assertEqual(validate_critical_import_identity(self.root)["status"], "PASS_SCOPED")

    def test_substituted_import_module_is_blocked(self):
        path = self.root / "compiler.py"
        original = path.read_text()
        self.assertIn("from contracts.rea_pipeline import run_governed_pipeline", original)
        path.write_text(original.replace(
            "from contracts.rea_pipeline import run_governed_pipeline",
            "from other.rea_pipeline import run_governed_pipeline"))
        self.assertEqual(validate_critical_import_identity(self.root)["status"], "BLOCK")

    def test_missing_call_is_blocked(self):
        path = self.root / "compiler.py"
        path.write_text(path.read_text().replace(
            "return run_optional_rea_release(", "return unknown_release("))
        self.assertEqual(validate_critical_import_identity(self.root)["status"], "BLOCK")

    def test_missing_file_is_blocked(self):
        (self.root / "compiler.py").unlink()
        self.assertEqual(validate_critical_import_identity(self.root)["status"], "BLOCK")


if __name__ == "__main__":
    unittest.main()
