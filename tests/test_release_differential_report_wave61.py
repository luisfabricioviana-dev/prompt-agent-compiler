"""Wave61 report format and deterministic differential verification."""
import json
import unittest
from tools.build_release_gate_differential_report import build_differential_report


class DifferentialReportTests(unittest.TestCase):
    def test_report_contains_inspectable_case_evidence(self):
        report = build_differential_report()
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["case_count"], 6)
        self.assertEqual(report["match_count"], 6)
        self.assertTrue(all(item["matched"] for item in report["cases"]))
        self.assertEqual(len({item["case"] for item in report["cases"]}), 6)
        json.dumps(report, sort_keys=True)

    def test_diagnostic_results_are_retained(self):
        for case in build_differential_report()["cases"]:
            self.assertEqual(case["old"], case["current"])
            self.assertIn("violations", case["old"])
            self.assertIn("status", case["current"])


if __name__ == "__main__":
    unittest.main()
