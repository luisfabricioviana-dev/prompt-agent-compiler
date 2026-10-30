"""Wave48: prohibit lexical shadowing of critical imported release targets."""
import tempfile
import unittest
from pathlib import Path
from shutil import copyfile
from contracts.release_import_identity_gate import EXPECTED, validate_critical_import_identity

ROOT = Path(__file__).resolve().parents[1]


class RebindingGateTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        for relative in EXPECTED:
            destination = self.root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            copyfile(ROOT / relative, destination)

    def test_clean_baseline(self):
        self.assertEqual(validate_critical_import_identity(self.root)["status"], "PASS_SCOPED")

    def test_module_level_import_rebinding_is_blocked(self):
        path = self.root / "contracts/rea_pipeline.py"
        source = path.read_text()
        source += "\nreconcile_delivery = lambda *args, **kwargs: (True, 'bypass')\n"
        path.write_text(source)
        result = validate_critical_import_identity(self.root)
        self.assertEqual(result["status"], "BLOCK")
        self.assertTrue(any("module_rebound_target:" in x for x in result["violations"]))

    def test_imported_name_shadowed_by_parameter_is_blocked(self):
        path = self.root / "compiler.py"
        source = path.read_text()
        source = source.replace("trusted_destination_resolver=None):",
                                "trusted_destination_resolver=None, run_governed_pipeline=None):", 1)
        path.write_text(source)
        result = validate_critical_import_identity(self.root)
        self.assertEqual(result["status"], "BLOCK")
        self.assertTrue(any("shadowed_parameter:" in x for x in result["violations"]))

    def test_aliased_import_to_different_module_is_blocked(self):
        path = self.root / "compiler.py"
        source = path.read_text().replace(
            "from contracts.rea_pipeline import run_governed_pipeline",
            "from attacker.module import run_governed_pipeline")
        path.write_text(source)
        self.assertEqual(validate_critical_import_identity(self.root)["status"], "BLOCK")


if __name__ == "__main__":
    unittest.main()
