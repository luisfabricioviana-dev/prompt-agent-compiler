"""Wave53: shadowed critical import names must fail closed."""
import tempfile
import unittest
from pathlib import Path
from shutil import copyfile
from contracts.release_import_identity_gate import EXPECTED, validate_critical_import_identity

ROOT = Path(__file__).resolve().parents[1]


class ImportShadowTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        for relative in EXPECTED:
            dest = self.root / relative
            dest.parent.mkdir(parents=True, exist_ok=True)
            copyfile(ROOT / relative, dest)

    def inject(self, statement):
        path = self.root / "compiler.py"
        content = path.read_text().replace(
            "    return run_governed_pipeline(",
            "    " + statement + "\n    return run_governed_pipeline(", 1)
        path.write_text(content)
        return validate_critical_import_identity(self.root)

    def test_clean_baseline(self):
        self.assertEqual(validate_critical_import_identity(self.root)["status"], "PASS_SCOPED")

    def test_nested_function_redefines_pinned_target(self):
        result = self.inject("def run_governed_pipeline(*a, **kw): return None")
        self.assertEqual(result["status"], "BLOCK")
        self.assertTrue(any("nested_definition_shadow:" in v for v in result["violations"]))

    def test_conflicting_import_replaces_pinned_target(self):
        result = self.inject("from attacker.module import run_governed_pipeline")
        self.assertEqual(result["status"], "BLOCK")
        self.assertTrue(any("shadow_import:" in v for v in result["violations"]))

    def test_walrus_rebinds_pinned_name(self):
        result = self.inject("assert (run_governed_pipeline := lambda *a: None)")
        self.assertEqual(result["status"], "BLOCK")


if __name__ == "__main__":
    unittest.main()
