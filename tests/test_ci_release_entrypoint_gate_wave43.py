"""Wave43: full regression CI must execute release entrypoint drift gate."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class CIReleaseEntrypointGateTests(unittest.TestCase):
    def test_full_regression_invokes_scanner_as_blocking_step(self):
        workflow = (ROOT / ".github/workflows/full-regression.yml").read_text(encoding="utf-8")
        self.assertIn("Enforce scoped release entrypoint inventory", workflow)
        self.assertIn("scan_release_entrypoints(Path", workflow)
        self.assertIn('if result["status"] != "PASS_SCOPED":', workflow)
        self.assertIn('raise SystemExit("release_entrypoint_inventory_drift")', workflow)

if __name__ == "__main__":
    unittest.main()
