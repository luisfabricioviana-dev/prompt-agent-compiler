"""Wave44: direct and aliased release callsite detection."""
import tempfile
import unittest
from pathlib import Path
from contracts.release_callsite_scanner import scan_release_calls


class ReleaseCallsiteScannerTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)
        (self.root/"contracts").mkdir()
        (self.root/"compiler.py").write_text("")
        (self.root/"rea_signed_release_bridge.py").write_text("")

    def test_aliased_import_and_call_detected(self):
        (self.root/"compiler.py").write_text(
            "from contracts.rea_pipeline import run_governed_pipeline as run\n"
            "run(None)\n")
        result=scan_release_calls(self.root)
        self.assertEqual(result["status"],"INVENTORIED_SCOPED")
        self.assertIn("compiler.py:2:run_governed_pipeline",result["calls"])

    def test_attribute_call_detected(self):
        (self.root/"contracts"/"consumer.py").write_text(
            "def use(node):\n    return node.inspect_delivery()\n")
        result=scan_release_calls(self.root)
        self.assertIn("contracts/consumer.py:2:inspect_delivery",result["calls"])

    def test_syntax_error_blocks(self):
        (self.root/"contracts"/"invalid.py").write_text("def bad(\n")
        result=scan_release_calls(self.root)
        self.assertEqual(result["status"],"BLOCK")
        self.assertIn("contracts/invalid.py",result["errors"])

    def test_dynamic_invocation_not_claimed_as_covered(self):
        (self.root/"compiler.py").write_text(
            "def call(node):\n    return getattr(node, 'inspect_delivery')()\n")
        result=scan_release_calls(self.root)
        self.assertEqual(result["calls"],())
        self.assertEqual(result["scope"],"compiler_bridge_and_contracts_only")


if __name__=="__main__":
    unittest.main()
