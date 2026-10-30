"""Wave49 indirect assignment and conditional import regression."""
import tempfile
import unittest
from pathlib import Path
from shutil import copyfile
from contracts.release_import_identity_gate import EXPECTED, validate_critical_import_identity

ROOT = Path(__file__).resolve().parents[1]


class IndirectBindingTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        for rel in EXPECTED:
            path = self.root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            copyfile(ROOT / rel, path)

    def test_baseline(self):
        self.assertEqual(validate_critical_import_identity(self.root)["status"], "PASS_SCOPED")

    def test_for_target_rebinding_blocks(self):
        path = self.root / "compiler.py"
        source = path.read_text().replace(
            "    return run_governed_pipeline(",
            "    for run_governed_pipeline in (): pass\n    return run_governed_pipeline(", 1)
        path.write_text(source)
        self.assertEqual(validate_critical_import_identity(self.root)["status"], "BLOCK")

    def test_with_target_rebinding_blocks(self):
        path = self.root / "contracts/rea_pipeline.py"
        source = path.read_text().replace(
            "    confirmed, reason = reconcile_delivery(",
            "    with open(__file__) as reconcile_delivery: pass\n    confirmed, reason = reconcile_delivery(", 1)
        path.write_text(source)
        self.assertEqual(validate_critical_import_identity(self.root)["status"], "BLOCK")

    def test_nested_conditional_import_blocks(self):
        path = self.root / "compiler.py"
        source = path.read_text().replace(
            "    from contracts.rea_pipeline import run_governed_pipeline",
            "    if True:\n        from contracts.rea_pipeline import run_governed_pipeline", 1)
        path.write_text(source)
        self.assertEqual(validate_critical_import_identity(self.root)["status"], "BLOCK")


if __name__ == "__main__":
    unittest.main()
