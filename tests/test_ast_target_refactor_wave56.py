"""Wave 56: assignment-target extraction and previous gate diagnostics."""
import ast
import tempfile
import unittest
from pathlib import Path
from shutil import copyfile
from contracts.release_import_identity_gate import (
    EXPECTED, _assignment_targets, _bound_names, validate_critical_import_identity,
)

ROOT = Path(__file__).resolve().parents[1]


class ASTTargetRefactorTests(unittest.TestCase):
    def test_unpacking_assignment_targets_not_rhs(self):
        tree = ast.parse("alpha, (beta, gamma) = innocent, dangerous()")
        stmt = tree.body[0]
        self.assertEqual(_bound_names(_assignment_targets(stmt)),
                         {"alpha", "beta", "gamma"})

    def test_annotated_walrus_augmented_targets(self):
        for source, expected in (
            ("critical: int = harmless", {"critical"}),
            ("if (critical := harmless): pass", {"critical"}),
            ("critical += harmless", {"critical"}),
        ):
            with self.subTest(source=source):
                statement = next(n for n in ast.walk(ast.parse(source))
                                 if isinstance(n, (ast.AnnAssign, ast.NamedExpr, ast.AugAssign)))
                self.assertEqual(_bound_names(_assignment_targets(statement)), expected)

    def test_non_assignment_has_no_targets(self):
        self.assertEqual(_assignment_targets(ast.parse("f()").body[0]), ())

    def test_existing_gate_baseline_and_rebinding(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for relative in EXPECTED:
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                copyfile(ROOT / relative, target)
            self.assertEqual(validate_critical_import_identity(root)["status"], "PASS_SCOPED")
            path = root / "contracts/rea_pipeline.py"
            path.write_text(path.read_text() +
                            "\nreconcile_delivery = lambda *args: None\n")
            result = validate_critical_import_identity(root)
            self.assertEqual(result["status"], "BLOCK")
            self.assertTrue(any(v.startswith("module_rebound_target:")
                                for v in result["violations"]))


if __name__ == "__main__":
    unittest.main()
