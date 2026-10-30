"""Wave51: adversarial aliases to reflection helpers must fail closed."""
import tempfile
import unittest
from pathlib import Path
from shutil import copyfile
from contracts.release_import_identity_gate import EXPECTED, validate_critical_import_identity

ROOT = Path(__file__).resolve().parents[1]


class AdversarialAliasTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        for relative in EXPECTED:
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            copyfile(ROOT / relative, target)

    def inject(self, statement):
        path = self.root / "compiler.py"
        source = path.read_text().replace("    return run_governed_pipeline(",
                                          "    " + statement + "\n    return run_governed_pipeline(", 1)
        path.write_text(source)
        return validate_critical_import_identity(self.root)

    def test_existing_baseline(self):
        self.assertEqual(validate_critical_import_identity(self.root)["status"], "PASS_SCOPED")

    def test_alias_to_exec(self):
        self.assertEqual(self.inject("unsafe = exec; unsafe('pass')")["status"], "BLOCK")

    def test_transitive_alias_to_globals(self):
        self.assertEqual(self.inject("a = globals; b = a; b()")["status"], "BLOCK")

    def test_alias_to_dynamic_import(self):
        self.assertEqual(self.inject("loader = __import__; loader('os')")["status"], "BLOCK")

    def test_alias_to_setattr(self):
        self.assertEqual(self.inject("mutator = setattr; mutator(object(), 'x', 1)")["status"], "BLOCK")


if __name__ == "__main__":
    unittest.main()
