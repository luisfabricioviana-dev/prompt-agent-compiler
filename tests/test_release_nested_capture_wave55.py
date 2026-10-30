"""Wave55: nested closure capture of release call targets is rejected."""
import tempfile
import unittest
from pathlib import Path
from shutil import copyfile
from contracts.release_import_identity_gate import EXPECTED, validate_critical_import_identity

ROOT = Path(__file__).resolve().parents[1]


class NestedCaptureTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        for relative in EXPECTED:
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            copyfile(ROOT / relative, target)

    def inject(self, statement):
        path = self.root / "compiler.py"
        source = path.read_text().replace(
            "    return run_governed_pipeline(",
            "    " + statement + "\n    return run_governed_pipeline(", 1)
        path.write_text(source)
        return validate_critical_import_identity(self.root)

    def test_current_baseline(self):
        self.assertEqual(validate_critical_import_identity(self.root)["status"], "PASS_SCOPED")

    def test_nested_function_capture_blocks(self):
        result = self.inject("def nested(): return run_governed_pipeline")
        self.assertEqual(result["status"], "BLOCK")
        self.assertTrue(any("nested_target_capture:" in v for v in result["violations"]))

    def test_nested_lambda_capture_blocks(self):
        result = self.inject("capture = lambda: run_governed_pipeline")
        self.assertEqual(result["status"], "BLOCK")
        self.assertTrue(any("nested_target_capture:" in v for v in result["violations"]))


if __name__ == "__main__":
    unittest.main()
