"""Wave57: differential oracle for the two Wave56 AST target replacements.

The oracle recreates the previous inline expressions independently and compares
both extracted names and security verdicts on representative mutations.
"""
import ast
import tempfile
import unittest
from pathlib import Path
from shutil import copyfile
from contracts.release_import_identity_gate import (
    EXPECTED, _assignment_targets, _bound_names, validate_critical_import_identity,
)

ROOT = Path(__file__).resolve().parents[1]


def old_inline_bound_names(node):
    if isinstance(node, ast.Assign):
        targets = node.targets
    elif isinstance(node, (ast.AnnAssign, ast.NamedExpr)):
        targets = [node.target]
    else:
        return set()
    return {n.id for target in targets for n in ast.walk(target)
            if isinstance(n, ast.Name)}


class DifferentialReleaseGateTests(unittest.TestCase):
    def test_old_and_new_assignment_semantics(self):
        cases = (
            "a = b", "a, (b, c) = source", "a: str = value",
            "if (token := value): pass", "(a, b) = (1, 2)",
        )
        for source in cases:
            with self.subTest(source=source):
                tree = ast.parse(source)
                for node in ast.walk(tree):
                    if isinstance(node, (ast.Assign, ast.AnnAssign, ast.NamedExpr)):
                        self.assertEqual(
                            old_inline_bound_names(node),
                            _bound_names(_assignment_targets(node)),
                        )

    def test_gate_outcomes_on_mutated_replay_fixtures(self):
        mutations = (
            (None, "PASS_SCOPED", ()),
            ("module", "BLOCK", ("module_rebound_target:",)),
            ("local", "BLOCK", ("rebound_target:",)),
        )
        for mutation, status, reasons in mutations:
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                for relative in EXPECTED:
                    target = root / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    copyfile(ROOT / relative, target)
                if mutation == "module":
                    path = root / "contracts/rea_pipeline.py"
                    path.write_text(path.read_text() + "\nreconcile_delivery = None\n")
                elif mutation == "local":
                    path = root / "contracts/rea_pipeline.py"
                    path.write_text(path.read_text().replace(
                        "    confirmed, reason = reconcile_delivery(",
                        "    reconcile_delivery = None\n"
                        "    confirmed, reason = reconcile_delivery(", 1))
                result = validate_critical_import_identity(root)
                self.assertEqual(result["status"], status)
                for reason in reasons:
                    self.assertTrue(any(v.startswith(reason) for v in result["violations"]))


if __name__ == "__main__":
    unittest.main()
