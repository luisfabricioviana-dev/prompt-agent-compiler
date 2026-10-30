"""Wave60 deterministic metamorphic differential matrix.

Mutation corpus is intentionally finite. It tests preservation of diagnostics
between frozen Wave55 and current implementation; it does not grant runtime
dispatch authority or claim comprehensive Python semantics.
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
    ("module_assignment", "contracts/rea_pipeline.py", None,
     "\nreconcile_delivery = None\n"),
    ("module_annotated_assignment", "contracts/rea_pipeline.py", None,
     "\nreconcile_delivery: object = None\n"),
    ("local_assignment", "contracts/rea_pipeline.py",
     "    confirmed, reason = reconcile_delivery(",
     "    reconcile_delivery = None\n"),
    ("local_annotated_assignment", "contracts/rea_pipeline.py",
     "    confirmed, reason = reconcile_delivery(",
     "    reconcile_delivery: object = None\n"),
    ("local_walrus", "compiler.py", "    return run_governed_pipeline(",
     "    assert (run_governed_pipeline := lambda *args: None)\n"),
    ("module_tuple_assignment", "contracts/rea_pipeline.py", None,
     "\nreconcile_delivery, other = None, None\n"),
    ("local_tuple_assignment", "contracts/rea_pipeline.py",
     "    confirmed, reason = reconcile_delivery(",
     "    reconcile_delivery, other = None, None\n"),
)


def frozen():
    spec = importlib.util.spec_from_file_location("frozen_wave55_matrix", FROZEN)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.validate_frozen_release_import_identity


class DeterministicMutationMatrixTests(unittest.TestCase):
    def test_frozen_current_decision_equivalence(self):
        old_gate = frozen()
        for name, relative, marker, payload in MUTATIONS:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                for path in EXPECTED:
                    dest = root / path
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    copyfile(ROOT / path, dest)
                dest = root / relative
                source = dest.read_text(encoding="utf-8")
                if marker is None:
                    source += payload
                else:
                    self.assertIn(marker, source)
                    source = source.replace(marker, payload + marker, 1)
                dest.write_text(source, encoding="utf-8")
                previous = old_gate(root)
                current = validate_critical_import_identity(root)
                self.assertEqual(current, previous)
                self.assertEqual(current["status"], "BLOCK")


if __name__ == "__main__":
    unittest.main()
