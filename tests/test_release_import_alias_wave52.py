"""Wave52 adversarial imported reflection alias tests."""
import tempfile
import unittest
from pathlib import Path
from shutil import copyfile
from contracts.release_import_identity_gate import EXPECTED, validate_critical_import_identity

ROOT = Path(__file__).resolve().parents[1]


class ImportedAliasTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        for rel in EXPECTED:
            target = self.root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            copyfile(ROOT / rel, target)

    def inject(self, code):
        path = self.root / "compiler.py"
        source = path.read_text().replace(
            "    return run_governed_pipeline(",
            "    " + code + "\n    return run_governed_pipeline(", 1)
        path.write_text(source)
        return validate_critical_import_identity(self.root)

    def test_baseline(self):
        self.assertEqual(validate_critical_import_identity(self.root)["status"], "PASS_SCOPED")

    def test_builtins_exec_alias(self):
        result = self.inject("from builtins import exec as x; x('pass')")
        self.assertEqual(result["status"], "BLOCK")

    def test_importlib_alias(self):
        result = self.inject("from importlib import import_module as load; load('os')")
        self.assertEqual(result["status"], "BLOCK")

    def test_module_importlib_loader(self):
        result = self.inject("import importlib as loader; loader.import_module('os')")
        self.assertEqual(result["status"], "BLOCK")


if __name__ == "__main__":
    unittest.main()
