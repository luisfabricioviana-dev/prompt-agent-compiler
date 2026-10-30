#!/usr/bin/env python3
"""Run the stdlib statement-line coverage proxy for contracts/."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import trace
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from contracts.coverage_gate import (
    coverage_percent,
    enforce_minimum_coverage,
    executable_statement_lines,
)

CONTRACTS = ROOT / "contracts"
EXCLUDED_FILES = {"coverage_gate.py"}


def _run_tests() -> unittest.result.TestResult:
    suite = unittest.defaultTestLoader.discover(
        str(ROOT / "tests"),
        pattern="test_*.py",
    )
    result = unittest.TextTestRunner(verbosity=0).run(suite)
    if not result.wasSuccessful():
        raise SystemExit("coverage_test_run_failed")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--minimum", type=float, required=True)
    args = parser.parse_args()

    tracer = trace.Trace(
        count=True,
        trace=False,
        ignoredirs=[sys.prefix, sys.exec_prefix],
    )
    tracer.runfunc(_run_tests)
    counts = tracer.results().counts

    executed_by_file: dict[Path, set[int]] = {}
    for (filename, line), count in counts.items():
        if not count:
            continue
        path = Path(filename).resolve()
        executed_by_file.setdefault(path, set()).add(int(line))

    total_lines: set[tuple[str, int]] = set()
    executed_lines: set[tuple[str, int]] = set()
    per_file = {}

    for path in sorted(CONTRACTS.glob("*.py")):
        if path.name in EXCLUDED_FILES:
            continue
        source = path.read_text(encoding="utf-8")
        executable = executable_statement_lines(source)
        executed = executed_by_file.get(path.resolve(), set()) & executable
        relative = path.relative_to(ROOT).as_posix()
        per_file[relative] = {
            "executable_statement_lines": len(executable),
            "executed_statement_lines": len(executed),
            "percent": round(coverage_percent(executed, executable), 2),
        }
        total_lines.update((relative, line) for line in executable)
        executed_lines.update((relative, line) for line in executed)

    overall = coverage_percent(executed_lines, total_lines)
    report = {
        "metric": "stdlib_trace_ast_statement_line_proxy",
        "minimum": args.minimum,
        "percent": round(overall, 2),
        "executed_statement_lines": len(executed_lines),
        "executable_statement_lines": len(total_lines),
        "excluded_files": sorted(EXCLUDED_FILES),
        "files": per_file,
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    enforce_minimum_coverage(overall, args.minimum)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
