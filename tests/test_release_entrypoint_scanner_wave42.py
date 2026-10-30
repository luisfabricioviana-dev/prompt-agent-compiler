"""Wave 42: AST scan identifies drift in monitored release surfaces."""
import tempfile
import unittest
from pathlib import Path
from shutil import copyfile
from contracts.release_entrypoint_scanner import MONITORED_FILES, scan_release_entrypoints

ROOT = Path(__file__).resolve().parents[1]


class ReleaseEntrypointScannerTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        for relative in MONITORED_FILES:
            destination = self.root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            copyfile(ROOT / relative, destination)

    def test_known_surface_baseline(self):
        self.assertEqual(scan_release_entrypoints(self.root)["status"], "PASS_SCOPED")

    def test_new_compiler_entrypoint_blocks(self):
        path = self.root / "compiler.py"
        path.write_text(path.read_text() + "\ndef run_optional_rea_new(payload):\n    return payload\n")
        result = scan_release_entrypoints(self.root)
        self.assertEqual(result["status"], "BLOCK")
        self.assertIn("compiler.run_optional_rea_new", result["unknown"])

    def test_new_release_node_method_blocks(self):
        path = self.root / "contracts/rea_release_node.py"
        path.write_text(path.read_text() + "\nReleaseNode.extra = None\n" +
                        "\nclass ReleaseNodeExtra:\n    def execute(self): pass\n")
        # New unrelated class is not within scanner scope.
        self.assertEqual(scan_release_entrypoints(self.root)["status"], "PASS_SCOPED")
        source = path.read_text()
        source = source.replace("    def inspect_delivery(", "    def inspect_legacy_new(self):\n        pass\n\n    def inspect_delivery(")
        path.write_text(source)
        self.assertIn("contracts.rea_release_node.ReleaseNode.inspect_legacy_new",
                      scan_release_entrypoints(self.root)["unknown"])

    def test_missing_or_invalid_file_blocks(self):
        (self.root / "compiler.py").unlink()
        self.assertEqual(scan_release_entrypoints(self.root)["status"], "BLOCK")
        path = self.root / "compiler.py"
        path.write_text("def invalid(\n")
        self.assertEqual(scan_release_entrypoints(self.root)["status"], "BLOCK")

    def test_removed_known_entrypoint_blocks(self):
        path = self.root / "compiler.py"
        path.write_text(path.read_text().replace(
            "def run_optional_rea_release(", "def renamed_release("))
        result = scan_release_entrypoints(self.root)
        self.assertIn("compiler.run_optional_rea_release", result["missing"])


if __name__ == "__main__":
    unittest.main()
