"""Wave 54: decorators and closure scope escapes on critical release owners."""
import tempfile
import unittest
from pathlib import Path
from shutil import copyfile
from contracts.release_import_identity_gate import EXPECTED, validate_critical_import_identity

ROOT = Path(__file__).resolve().parents[1]


class DecoratorClosureGateTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        for relative in EXPECTED:
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            copyfile(ROOT / relative, target)

    def test_original_baseline(self):
        self.assertEqual(validate_critical_import_identity(self.root)["status"], "PASS_SCOPED")

    def test_decorated_release_owner_blocks(self):
        path = self.root / "compiler.py"
        source = path.read_text().replace(
            "def run_optional_rea_release(", "@unknown_decorator\ndef run_optional_rea_release(", 1)
        path.write_text(source)
        result = validate_critical_import_identity(self.root)
        self.assertEqual(result["status"], "BLOCK")
        self.assertTrue(any("decorated_owner:" in x for x in result["violations"]))

    def test_nested_global_scope_escape_blocks(self):
        path = self.root / "compiler.py"
        source = path.read_text().replace(
            "    return run_governed_pipeline(",
            "    def bypass():\n        global run_governed_pipeline\n"
            "        run_governed_pipeline = lambda *args, **kwargs: None\n"
            "    return run_governed_pipeline(", 1)
        path.write_text(source)
        result = validate_critical_import_identity(self.root)
        self.assertEqual(result["status"], "BLOCK")
        self.assertTrue(any("scope_escape:" in x for x in result["violations"]))

    def test_module_function_decorator_blocks(self):
        path = self.root / "contracts/rea_pipeline.py"
        source = path.read_text().replace(
            "def run_governed_pipeline(", "@unknown_decorator\ndef run_governed_pipeline(", 1)
        path.write_text(source)
        self.assertEqual(validate_critical_import_identity(self.root)["status"], "BLOCK")


if __name__ == "__main__":
    unittest.main()
