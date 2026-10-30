"""Wave58: frozen Wave55 gate versus refactored Wave56+ gate."""
import importlib.util
import tempfile
import unittest
from pathlib import Path
from shutil import copyfile

from contracts.release_import_identity_gate import EXPECTED, validate_critical_import_identity

ROOT = Path(__file__).resolve().parents[1]
FROZEN = ROOT / "tests/fixtures/frozen_release_import_identity_wave55.py"


def old_gate():
    spec = importlib.util.spec_from_file_location("frozen_release_gate_wave55", FROZEN)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.validate_frozen_release_import_identity


class FrozenGateDifferentialTests(unittest.TestCase):
    def test_frozen_gate_is_independent_of_refactored_helper(self):
        source = FROZEN.read_text()
        self.assertNotIn("_assignment_targets(", source)
        self.assertNotIn("_bound_names(", source)

    def test_status_and_diagnostic_equivalence(self):
        fixtures = {
            "baseline": None,
            "module_rebind": ("contracts/rea_pipeline.py",
                              "\nreconcile_delivery = None\n"),
            "local_rebind": ("compiler.py",
                              "    run_governed_pipeline = None\n"),
            "shadow_import": ("compiler.py",
                               "    from attacker.api import run_governed_pipeline\n"),
            "nested_capture": ("compiler.py",
                               "    capture = lambda: run_governed_pipeline\n"),
            "dynamic_exec": ("compiler.py",
                             "    exec('pass')\n"),
        }
        frozen = old_gate()
        for name, mutation in fixtures.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                for relative in EXPECTED:
                    path = root / relative
                    path.parent.mkdir(parents=True, exist_ok=True)
                    copyfile(ROOT / relative, path)
                if mutation:
                    relative, insertion = mutation
                    path = root / relative
                    source = path.read_text()
                    if relative == "compiler.py":
                        marker = "    return run_governed_pipeline("
                    else:
                        marker = "    confirmed, reason = reconcile_delivery("
                    if name == "module_rebind":
                        path.write_text(source + insertion)
                    else:
                        self.assertIn(marker, source)
                        path.write_text(source.replace(marker, insertion + marker, 1))
                expected = frozen(root)
                actual = validate_critical_import_identity(root)
                self.assertEqual(actual, expected)


if __name__ == "__main__":
    unittest.main()
