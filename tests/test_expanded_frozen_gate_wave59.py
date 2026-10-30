"""Wave59: expanded deterministic differential corpus against frozen Wave55 gate.

Both implementations evaluate the same parsed files. This corpus only tests
known syntactic mutation classes, not arbitrary Python runtime behaviors.
"""
import importlib.util
import tempfile
import unittest
from pathlib import Path
from shutil import copyfile
from contracts.release_import_identity_gate import EXPECTED, validate_critical_import_identity

ROOT = Path(__file__).resolve().parents[1]
FROZEN = ROOT / "tests/fixtures/frozen_release_import_identity_wave55.py"

MUTATIONS = (
    ("compiler.py", "    return run_governed_pipeline(",
     "    unsafe = exec; unsafe('pass')\n", "aliased_exec"),
    ("compiler.py", "    return run_governed_pipeline(",
     "    from builtins import exec as unsafe; unsafe('pass')\n", "builtins_import"),
    ("compiler.py", "    return run_governed_pipeline(",
     "    from importlib import import_module as load; load('os')\n", "importlib_alias"),
    ("compiler.py", "    return run_governed_pipeline(",
     "    for run_governed_pipeline in (): pass\n", "for_rebind"),
    ("compiler.py", "    return run_governed_pipeline(",
     "    with open(__file__) as run_governed_pipeline: pass\n", "with_rebind"),
    ("compiler.py", "    return run_governed_pipeline(",
     "    if True:\n        from contracts.rea_pipeline import run_governed_pipeline\n", "conditional_import"),
    ("compiler.py", "    return run_governed_pipeline(",
     "    def nested(): return run_governed_pipeline\n", "nested_capture"),
    ("compiler.py", "    return run_governed_pipeline(",
     "    capture = lambda: run_governed_pipeline\n", "lambda_capture"),
    ("contracts/rea_pipeline.py", "    confirmed, reason = reconcile_delivery(",
     "    reconcile_delivery = None\n", "local_rebind"),
)


def frozen_gate():
    spec = importlib.util.spec_from_file_location("wave55_frozen_expanded", FROZEN)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.validate_frozen_release_import_identity


class ExpandedDifferentialTests(unittest.TestCase):
    def test_frozen_verdict_and_diagnostics_match_current(self):
        frozen = frozen_gate()
        for relative, marker, prefix, case in MUTATIONS:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                for filename in EXPECTED:
                    dest = root / filename
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    copyfile(ROOT / filename, dest)
                target = root / relative
                source = target.read_text(encoding="utf-8")
                self.assertIn(marker, source)
                target.write_text(source.replace(marker, prefix + marker, 1), encoding="utf-8")
                old = frozen(root)
                new = validate_critical_import_identity(root)
                self.assertEqual(new, old)
                self.assertEqual(new["status"], "BLOCK")


if __name__ == "__main__":
    unittest.main()
