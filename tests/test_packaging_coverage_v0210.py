from pathlib import Path
import textwrap
import tomllib
import unittest

from contracts.coverage_gate import (
    coverage_percent,
    enforce_minimum_coverage,
    executable_statement_lines,
)


ROOT = Path(__file__).resolve().parents[1]


class PackagingTests(unittest.TestCase):
    def test_pyproject_declares_v0210_contract_package(self):
        data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

        self.assertEqual(data["project"]["name"], "prompt-agent-compiler")
        self.assertEqual(data["project"]["version"], "0.2.10")
        self.assertEqual(data["project"]["requires-python"], ">=3.11")
        find = data["tool"]["setuptools"]["packages"]["find"]
        self.assertIn("contracts*", find["include"])
        self.assertIn("recovered_v0_2_9*", find["exclude"])
        self.assertTrue(find["namespaces"])

    def test_ci_contains_package_install_smoke_test(self):
        workflow = (
            ROOT / ".github" / "workflows" / "full-regression.yml"
        ).read_text(encoding="utf-8")

        self.assertIn("Install v0.2.10 contracts package", workflow)
        self.assertIn("Smoke import installed package", workflow)
        self.assertIn("pip install --no-deps --no-build-isolation", workflow)


class CoverageGateUnitTests(unittest.TestCase):
    def test_executable_statement_lines_exclude_module_docstring(self):
        source = textwrap.dedent(
            '''            """module doc"""
            x = 1
            if x:
                y = 2
            '''
        )

        self.assertEqual(
            executable_statement_lines(source),
            {2, 3, 4},
        )

    def test_coverage_percent_uses_executable_statement_lines(self):
        self.assertAlmostEqual(
            coverage_percent({2, 4}, {2, 3, 4}),
            66.66666666666666,
        )
        self.assertEqual(coverage_percent(set(), set()), 100.0)

    def test_minimum_coverage_fails_closed(self):
        with self.assertRaisesRegex(
            RuntimeError,
            "coverage_below_threshold:69.99<70.00",
        ):
            enforce_minimum_coverage(69.99, 70.0)

        self.assertEqual(enforce_minimum_coverage(70.0, 70.0), 70.0)

    def test_ci_runs_contract_statement_coverage_gate(self):
        workflow = (
            ROOT / ".github" / "workflows" / "full-regression.yml"
        ).read_text(encoding="utf-8")

        self.assertIn("Run contract statement coverage gate", workflow)
        self.assertIn(
            "python tools/run_contract_coverage_gate.py --minimum 70",
            workflow,
        )

    def test_coverage_runner_exists(self):
        self.assertTrue(
            (ROOT / "tools" / "run_contract_coverage_gate.py").is_file()
        )


if __name__ == "__main__":
    unittest.main()
