import unittest

from contracts.capability_registry import (
    CapabilityRegistry,
    CapabilitySpec,
    CapabilityStatus,
)
from contracts.canonical_runtime import CanonicalCompilerRuntime
from contracts.execution_graph_compiler import ExecutionGraphCompiler
from contracts.pattern_registry import default_pattern_registry
from contracts.registry_policy import (
    RegistryAwarePolicyCompiler,
    RegistryPatternDecision,
    RegistryPolicyResult,
    RegistryQualityGate,
)


def decision(pid, status, score=90):
    names = {
        "P01": "BUILD",
        "P02": "REFACTOR",
        "P03": "DEBUG",
        "P04": "SYSTEM_DESIGN",
        "P05": "OPTIMIZE",
        "P06": "CLEAN_ARCHITECTURE",
        "P07": "MULTI_AGENT",
        "P08": "PRODUCTION_UI",
    }
    return RegistryPatternDecision(
        pattern_id=pid,
        pattern_name=names[pid],
        score=score,
        status=status,
        reasons=("fixture",),
    )


def policy_result(*, active=(), gates=()):
    patterns = {
        f"P0{i}": decision(
            f"P0{i}",
            "mandatory" if f"P0{i}" in active else "rejected",
            90 if f"P0{i}" in active else 0,
        )
        for i in range(1, 9)
    }
    return RegistryPolicyResult(
        raw_request="fixture",
        complexity_level="N2",
        complexity_score=6,
        patterns=patterns,
        quality_gates=tuple(gates),
        constraints=(),
        capabilities=(),
        contradictions=(),
        why_this_route=(),
    )


class ExecutionGraphCompilerTests(unittest.TestCase):
    def setUp(self):
        self.registry = default_pattern_registry()
        self.compiler = ExecutionGraphCompiler(self.registry)

    def test_rejected_patterns_are_not_in_active_pattern_contract(self):
        result = policy_result(active=("P01", "P05"))
        plan = self.compiler.compile(
            result,
            objective="Build and optimize.",
            success_definition=("verified result",),
        )

        self.assertEqual(
            plan.output_contract["active_patterns"],
            ("P01", "P05"),
        )
        self.assertNotIn("P07", plan.output_contract["active_patterns"])

    def test_pattern_prerequisites_create_prepare_phase(self):
        result = policy_result(active=("P05",))
        plan = self.compiler.compile(
            result,
            objective="Optimize.",
            success_definition=("optimization verified",),
        )

        self.assertEqual(
            [node.node_id for node in plan.execution_nodes],
            ["prepare", "execute"],
        )
        prepare = plan.execution_nodes[0]
        execute = plan.execution_nodes[1]
        self.assertEqual(
            prepare.output_artifacts,
            ("prerequisites",),
        )
        self.assertIn(
            "measurable_baseline_or_proxy",
            prepare.purpose,
        )
        self.assertEqual(execute.prerequisites, ("prepare",))

    def test_active_patterns_compile_declared_artifact_contracts(self):
        result = policy_result(active=("P01", "P05"))
        plan = self.compiler.compile(
            result,
            objective="Build and optimize.",
            success_definition=("verified result",),
        )

        ids = tuple(a.artifact_id for a in plan.artifacts)
        self.assertEqual(
            ids,
            ("prerequisites", "implementation", "optimization_result"),
        )
        producers = {a.artifact_id: a.producer_node for a in plan.artifacts}
        self.assertEqual(producers["prerequisites"], "prepare")
        self.assertEqual(producers["implementation"], "execute")
        self.assertEqual(producers["optimization_result"], "execute")

    def test_verify_phase_uses_policy_emitted_gates_only(self):
        result = policy_result(
            active=("P01",),
            gates=(
                RegistryQualityGate(
                    "EVIDENCE_GATE",
                    "evidence",
                    "Evidence required.",
                ),
            ),
        )
        plan = self.compiler.compile(
            result,
            objective="Build.",
            success_definition=("verified",),
        )

        self.assertEqual(
            [node.node_id for node in plan.execution_nodes],
            ["execute", "verify"],
        )
        verify = plan.execution_nodes[1]
        self.assertEqual(verify.quality_gates, ("EVIDENCE_GATE",))
        self.assertNotIn("REQUIREMENT_GATE", verify.quality_gates)
        self.assertEqual(
            plan.verification_plan,
            ("verify_gate:EVIDENCE_GATE",),
        )

    def test_no_verify_phase_when_policy_emits_no_gates(self):
        result = policy_result(active=("P01",))
        plan = self.compiler.compile(
            result,
            objective="Build.",
            success_definition=("built",),
        )

        self.assertEqual(
            [node.node_id for node in plan.execution_nodes],
            ["execute"],
        )

    def test_independent_review_phase_requires_actual_policy_gate(self):
        without_gate = self.compiler.compile(
            policy_result(active=("P07",)),
            objective="Coordinate.",
            success_definition=("done",),
        )
        self.assertNotIn(
            "independent-review",
            [node.node_id for node in without_gate.execution_nodes],
        )

        with_gate = self.compiler.compile(
            policy_result(
                active=("P07",),
                gates=(
                    RegistryQualityGate(
                        "INDEPENDENT_REVIEW_GATE",
                        "consistency",
                        "Independent review must pass.",
                        True,
                        "critical",
                    ),
                ),
            ),
            objective="Coordinate.",
            success_definition=("reviewed",),
        )
        self.assertEqual(
            [node.node_id for node in with_gate.execution_nodes],
            ["execute", "verify", "independent-review"],
        )
        self.assertEqual(
            with_gate.execution_nodes[-1].prerequisites,
            ("verify",),
        )

    def test_required_runtime_capabilities_are_declared_on_execute_node(self):
        result = policy_result(active=("P01",))
        plan = self.compiler.compile(
            result,
            objective="Build.",
            success_definition=("built",),
            required_capabilities=("files.read", "github.write"),
            optional_capabilities=("telemetry.export",),
        )

        execute = next(n for n in plan.execution_nodes if n.node_id == "execute")
        self.assertEqual(
            execute.required_capabilities,
            ("files.read", "github.write"),
        )
        self.assertEqual(
            plan.required_capabilities,
            ("files.read", "github.write"),
        )
        self.assertEqual(
            plan.optional_capabilities,
            ("telemetry.export",),
        )


class CanonicalRuntimeAutoGraphTests(unittest.TestCase):
    class Task:
        raw_request = "create"
        actions = {"CREATE"}
        preservation = set()
        performance_dimensions = set()
        evidence_policy = set()
        ui_requirements = set()
        architecture = set()
        external_state = set()
        execution = set()
        capabilities = set()
        risks = {}
        unknowns = []
        contradictions = []

    class Provider:
        def __init__(self):
            self.calls = 0

        def interpret(self, request):
            self.calls += 1
            return CanonicalRuntimeAutoGraphTests.Task()

    def test_compile_auto_builds_graph_without_manual_execution_plan(self):
        provider = self.Provider()
        registry = default_pattern_registry()
        runtime = CanonicalCompilerRuntime(
            semantic_provider=provider,
            policy_compiler=RegistryAwarePolicyCompiler(registry),
            capability_registry=CapabilityRegistry(
                (
                    CapabilitySpec(
                        "files.read",
                        CapabilityStatus.AVAILABLE,
                    ),
                )
            ),
            pattern_registry=registry,
        )

        spec = runtime.compile_auto(
            "create",
            graph_compiler=ExecutionGraphCompiler(registry),
            objective="Create a verified result.",
            success_definition=("result exists",),
            required_capabilities=("files.read",),
        )

        self.assertEqual(provider.calls, 1)
        self.assertEqual(spec.readiness, "READY")
        self.assertEqual(
            [node.node_id for node in spec.execution_nodes],
            ["execute"],
        )
        self.assertEqual(
            tuple(a.artifact_id for a in spec.artifacts),
            ("implementation",),
        )

    def test_compile_auto_preserves_unknown_runtime_capability(self):
        registry = default_pattern_registry()
        runtime = CanonicalCompilerRuntime(
            semantic_provider=self.Provider(),
            policy_compiler=RegistryAwarePolicyCompiler(registry),
            capability_registry=CapabilityRegistry(),
            pattern_registry=registry,
        )

        spec = runtime.compile_auto(
            "create",
            graph_compiler=ExecutionGraphCompiler(registry),
            objective="Create.",
            success_definition=("result exists",),
            required_capabilities=("files.read",),
        )

        self.assertEqual(spec.readiness, "UNKNOWN_CAPABILITY")


if __name__ == "__main__":
    unittest.main()
