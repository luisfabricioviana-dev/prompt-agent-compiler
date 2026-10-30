from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
RECOVERED = ROOT / "recovered_v0_2_9"
sys.path.insert(0, str(RECOVERED))

from normalized_task import NormalizedTask
from policy_v0_2_7 import compile_semantic_task as compile_legacy

from contracts.pattern_registry import PatternRegistry, PatternDefinition, default_pattern_registry
from contracts.registry_policy import (
    RegistryAwarePolicyCompiler,
    RegistryPolicyContractError,
    route_signature,
)


def task(
    name,
    *,
    actions=(),
    preservation=(),
    performance=(),
    evidence=(),
    ui=(),
    architecture=(),
    external=(),
    execution=(),
    capabilities=(),
    risks=None,
    unknowns=(),
    contradictions=(),
):
    return NormalizedTask(
        raw_request=name,
        actions=set(actions),
        preservation=set(preservation),
        performance_dimensions=set(performance),
        evidence_policy=set(evidence),
        ui_requirements=set(ui),
        architecture=set(architecture),
        external_state=set(external),
        execution=set(execution),
        capabilities=set(capabilities),
        risks=dict(risks or {}),
        unknowns=list(unknowns),
        contradictions=list(contradictions),
    )


CASES = (
    task("create", actions=("CREATE",)),
    task(
        "refactor",
        actions=("MODIFY",),
        preservation=("BEHAVIOR", "API"),
    ),
    task("debug", actions=("DIAGNOSE",)),
    task(
        "design",
        actions=("DESIGN",),
        architecture=("DESIGN_BEFORE_BUILD",),
        execution=("MULTI_STEP",),
    ),
    task(
        "optimize",
        actions=("OPTIMIZE",),
        preservation=("QUALITY",),
        performance=("MEMORY", "QUALITY_ACCURACY"),
    ),
    task(
        "boundaries",
        actions=("MODIFY",),
        architecture=("CHANGE", "BOUNDARIES"),
        preservation=("BEHAVIOR",),
    ),
    task(
        "multi-agent-value",
        actions=("REVIEW",),
        execution=("PARALLELIZABLE", "INDEPENDENT_REVIEW"),
        risks={"SECURITY": 3},
    ),
    task(
        "multi-agent-overengineering",
        actions=("REVIEW",),
        execution=("EXPLICIT_MULTI_AGENT",),
    ),
    task(
        "production-ui",
        actions=("CREATE",),
        ui=("UI", "PRODUCTION", "ACCESSIBILITY", "RESPONSIVE"),
    ),
    task(
        "evidence",
        actions=("ANALYZE_EVIDENCE",),
        evidence=("TRACEABLE", "SUPPLIED_ONLY"),
    ),
    task(
        "external-state",
        actions=("OPERATE",),
        external=("DATABASE",),
        execution=("STATEFUL", "HUMAN_APPROVAL"),
        capabilities=("AUTHORIZATION", "HUMAN_APPROVAL", "PERSISTENT_STATE_WRITE"),
    ),
    task(
        "destructive",
        actions=("MODIFY",),
        risks={"REVERSIBILITY": 4, "DATA_LOSS": 4},
        contradictions=("destructive_change_requires_approval",),
    ),
)


class RegistryPolicyEquivalenceTests(unittest.TestCase):
    def setUp(self):
        self.compiler = RegistryAwarePolicyCompiler(default_pattern_registry())

    def test_route_surface_matches_recovered_v029_policy_for_matrix(self):
        for case in CASES:
            with self.subTest(case=case.raw_request):
                legacy = compile_legacy(case)
                migrated = self.compiler(case)
                self.assertEqual(
                    route_signature(migrated),
                    route_signature(legacy),
                )

    def test_all_p01_to_p08_decisions_are_emitted(self):
        result = self.compiler(CASES[0])
        self.assertEqual(set(result.patterns), {f"P0{i}" for i in range(1, 9)})

    def test_p07_anti_overengineering_is_preserved(self):
        result = self.compiler(
            task(
                "explicit-only",
                actions=("REVIEW",),
                execution=("EXPLICIT_MULTI_AGENT",),
            )
        )
        decision = result.patterns["P07"]
        self.assertEqual(decision.status, "rejected")
        self.assertEqual(decision.score, 0)
        self.assertIn("anti-overengineering", decision.reasons)

    def test_registry_is_the_authoritative_pattern_identity_set(self):
        incomplete = PatternRegistry(
            (
                PatternDefinition(
                    "P01",
                    "BUILD",
                    activation_features=("actions.CREATE",),
                    complexity_cost=2,
                ),
            )
        )
        compiler = RegistryAwarePolicyCompiler(incomplete)

        with self.assertRaisesRegex(
            RegistryPolicyContractError,
            "registry_pattern_set_mismatch",
        ):
            compiler(CASES[0])

    def test_registry_metadata_drift_is_fail_closed(self):
        base = default_pattern_registry()
        patterns = []
        for pid in base.ids():
            p = base.get(pid)
            if pid == "P05":
                p = PatternDefinition(
                    pattern_id=p.pattern_id,
                    name=p.name,
                    activation_features=p.activation_features,
                    blocking_features=p.blocking_features,
                    prerequisites=p.prerequisites,
                    required_capabilities=p.required_capabilities,
                    produced_artifacts=p.produced_artifacts,
                    default_gates=p.default_gates,
                    failure_routes=p.failure_routes,
                    complexity_cost=99,
                )
            patterns.append(p)
        compiler = RegistryAwarePolicyCompiler(PatternRegistry(patterns))

        with self.assertRaisesRegex(
            RegistryPolicyContractError,
            "registry_pattern_metadata_mismatch:P05",
        ):
            compiler(CASES[4])

    def test_policy_result_records_registry_version(self):
        result = self.compiler(CASES[0])
        self.assertEqual(result.registry_contract, "P01-P08-v0.2.10")


if __name__ == "__main__":
    unittest.main()
