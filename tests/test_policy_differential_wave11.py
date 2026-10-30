"""Deterministic differential regression: recovered policy vs registry-aware policy.

This is a public, synthetic corpus. It is NOT a blind model-backed holdout.
"""
from __future__ import annotations

import hashlib
import itertools
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "recovered_v0_2_9"))

from normalized_task import NormalizedTask
from policy_v0_2_7 import compile_semantic_task as compile_legacy

from contracts.pattern_registry import default_pattern_registry
from contracts.registry_policy import RegistryAwarePolicyCompiler, route_signature


# Versioned synthetic factors, not natural-language inference examples.
FACTORS = (
    ((), ("CREATE",), ("MODIFY",), ("DIAGNOSE",), ("OPTIMIZE",)),
    ((), ("BEHAVIOR",)),
    ((), ("CHANGE", "BOUNDARIES"), ("DESIGN_BEFORE_BUILD",)),
    ((), ("EXPLICIT_MULTI_AGENT",), ("PARALLELIZABLE", "INDEPENDENT_REVIEW")),
    ((), ("PRODUCTION", "ACCESSIBILITY"), ("UI", "RESPONSIVE")),
    (0, 2, 3, 4),
)


def synthetic_cases():
    for index, (actions, preservation, architecture, execution, ui, risk) in enumerate(
        itertools.product(*FACTORS)
    ):
        yield NormalizedTask(
            raw_request=f"synthetic-differential-{index:04d}",
            actions=set(actions),
            preservation=set(preservation),
            architecture=set(architecture),
            execution=set(execution),
            ui_requirements=set(ui),
            risks={"SECURITY": risk, "REVERSIBILITY": risk, "DATA_LOSS": risk},
            performance_dimensions={"LATENCY"} if "OPTIMIZE" in actions else set(),
            evidence_policy={"TRACEABLE"} if "DIAGNOSE" in actions else set(),
            external_state=set(),
            capabilities=set(),
            unknowns=[],
            contradictions=[],
        )


def corpus_digest():
    rows = []
    for case in synthetic_cases():
        rows.append({
            "request": case.raw_request,
            "actions": sorted(case.actions),
            "preservation": sorted(case.preservation),
            "architecture": sorted(case.architecture),
            "execution": sorted(case.execution),
            "ui": sorted(case.ui_requirements),
            "risks": dict(sorted(case.risks.items())),
            "performance": sorted(case.performance_dimensions),
            "evidence": sorted(case.evidence_policy),
        })
    payload = json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()
    return len(rows), hashlib.sha256(payload).hexdigest()


class DifferentialPolicyMatrixTests(unittest.TestCase):
    def test_synthetic_matrix_matches_legacy_on_full_route_surface(self):
        migrated = RegistryAwarePolicyCompiler(default_pattern_registry())
        cases = 0
        for task in synthetic_cases():
            with self.subTest(case=task.raw_request):
                self.assertEqual(
                    route_signature(compile_legacy(task)),
                    route_signature(migrated(task)),
                )
            cases += 1
        self.assertEqual(cases, 5 * 2 * 3 * 4 * 3 * 4)

    def test_synthetic_fixture_digest_is_reproducible(self):
        count, sha = corpus_digest()
        self.assertEqual(count, 1440)
        self.assertEqual(len(sha), 64)
        self.assertEqual((count, sha), corpus_digest())

    def test_anti_overengineering_without_value_signals(self):
        migrated = RegistryAwarePolicyCompiler(default_pattern_registry())
        case = NormalizedTask(
            raw_request="explicit-multi-agent-alone",
            actions={"REVIEW"},
            execution={"EXPLICIT_MULTI_AGENT"},
        )
        result = migrated(case)
        self.assertEqual(result.patterns["P07"].score, 0)
        self.assertEqual(result.patterns["P07"].status, "rejected")
        self.assertEqual(route_signature(result), route_signature(compile_legacy(case)))


if __name__ == "__main__":
    unittest.main()
