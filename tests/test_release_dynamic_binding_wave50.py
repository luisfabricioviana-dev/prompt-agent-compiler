"""Wave 50: reflective namespace operations fail closed in critical owners."""
import tempfile
import unittest
from pathlib import Path
from shutil import copyfile
from contracts.release_import_identity_gate import EXPECTED, validate_critical_import_identity

ROOT = Path(__file__).resolve().parents[1]


class DynamicBindingTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        for rel in EXPECTED:
            destination = self.root / rel
            destination.parent.mkdir(parents=True, exist_ok=True)
            copyfile(ROOT / rel, destination)

    def inject(self, statement):
        path = self.root / "compiler.py"
        contents = path.read_text()
        contents = contents.replace("    return run_governed_pipeline(",
                                    "    " + statement + "\n    return run_governed_pipeline(", 1)
        path.write_text(contents)
        return validate_critical_import_identity(self.root)

    def test_clean_baseline(self):
        self.assertEqual(validate_critical_import_identity(self.root)["status"], "PASS_SCOPED")

    def test_reflective_assignment_rejected(self):
        self.assertEqual(self.inject("globals()['run_governed_pipeline'] = lambda *a: None")["status"], "BLOCK")

    def test_exec_rejected(self):
        self.assertEqual(self.inject("exec('run_governed_pipeline = None')")["status"], "BLOCK")

    def test_dynamic_import_rejected(self):
        self.assertEqual(self.inject("__import__('attacker')")["status"], "BLOCK")

    def test_setattr_rejected(self):
        self.assertEqual(self.inject("setattr(object(), 'run_governed_pipeline', None)")["status"], "BLOCK")


if __name__ == "__main__":
    unittest.main()
