import unittest
from dataclasses import dataclass

from contracts.capability_registry import (
    CapabilityGateState,
    CapabilityRegistry,
    CapabilitySpec,
    CapabilityStatus,
)
from contracts.execution_spec_v2 import (
    ArtifactContract,
    ExecutionNode,
    ExecutionSpecV2,
    FailureRoute,
)


class CapabilityRegistryTests(unittest.TestCase):
    def test_unknown_capability_is_not_silently_available(self):
        registry = CapabilityRegistry()
        result = registry.resolve(required=["email.send"])

        self.assertEqual(result.state, CapabilityGateState.UNKNOWN)
        self.assertEqual(result.required[0].status, CapabilityStatus.UNKNOWN)
        self.assertIn("mandatory_capability_unknown:email.send", result.reasons)

    def test_unavailable_required_capability_blocks(self):
        registry = CapabilityRegistry([
            CapabilitySpec("github.write", CapabilityStatus.UNAVAILABLE)
        ])

        result = registry.resolve(required=["github.write"])

        self.assertEqual(result.state, CapabilityGateState.BLOCKED)
        self.assertIn("mandatory_capability_unavailable:github.write", result.reasons)

    def test_constrained_required_capability_requires_adaptation(self):
        registry = CapabilityRegistry([
            CapabilitySpec(
                "video.generate",
                CapabilityStatus.CONSTRAINED,
                limitation="dry_run_only",
                fallback="generate_spec_only",
            )
        ])

        result = registry.resolve(required=["video.generate"])

        self.assertEqual(result.state, CapabilityGateState.ADAPT_REQUIRED)
        self.assertFalse(result.blocked)
        self.assertEqual(result.required[0].fallback, "generate_spec_only")

    def test_optional_unavailable_capability_does_not_block(self):
        registry = CapabilityRegistry([
            CapabilitySpec("telemetry.export", CapabilityStatus.UNAVAILABLE)
        ])

        result = registry.resolve(required=[], optional=["telemetry.export"])

        self.assertEqual(result.state, CapabilityGateState.READY)
        self.assertFalse(result.blocked)


class ExecutionSpecV2Tests(unittest.TestCase):
    def _ready_registry(self):
        return CapabilityRegistry([
            CapabilitySpec("files.read", CapabilityStatus.AVAILABLE),
            CapabilitySpec("tests.run", CapabilityStatus.AVAILABLE),
        ])

    def test_ready_spec_requires_executable_graph_and_capabilities(self):
        capabilities = self._ready_registry().resolve(
            required=["files.read", "tests.run"]
        )
        node = ExecutionNode(
            node_id="analyze",
            purpose="Analyze the supplied files",
            role="analyst",
            required_capabilities=("files.read",),
            output_artifacts=("analysis",),
            on_fail=("repair:analyze",),
        )
        artifact = ArtifactContract(
            artifact_id="analysis",
            artifact_type="AnalysisReport",
            producer_node="analyze",
            required_fields=("findings",),
        )

        spec = ExecutionSpecV2(
            spec_id="spec-1",
            compiler_version="0.2.10",
            raw_request="analyze os arquivos",
            objective="Produce a traceable analysis.",
            success_definition=("analysis artifact is valid",),
            complexity_level="N2",
            complexity_score=6,
            capabilities=capabilities,
            execution_nodes=(node,),
            artifacts=(artifact,),
            verification_plan=("validate:analysis",),
            stop_conditions=("blocking_gate_failed",),
        )

        self.assertEqual(spec.readiness, "READY")
        self.assertEqual(spec.validation_errors(), ())

    def test_missing_graph_is_not_executable(self):
        capabilities = self._ready_registry().resolve(required=[])

        spec = ExecutionSpecV2(
            spec_id="spec-2",
            compiler_version="0.2.10",
            raw_request="do something",
            objective="Do the task.",
            success_definition=("done",),
            complexity_level="N1",
            complexity_score=2,
            capabilities=capabilities,
        )

        self.assertEqual(spec.readiness, "INVALID")
        self.assertIn("execution_graph_empty", spec.validation_errors())

    def test_unknown_required_capability_makes_spec_conditional(self):
        capabilities = CapabilityRegistry().resolve(required=["calendar.write"])
        node = ExecutionNode(
            node_id="update",
            purpose="Update external state",
            role="operator",
            required_capabilities=("calendar.write",),
        )
        spec = ExecutionSpecV2(
            spec_id="spec-3",
            compiler_version="0.2.10",
            raw_request="update calendar",
            objective="Update the calendar event.",
            success_definition=("event updated",),
            complexity_level="N2",
            complexity_score=7,
            capabilities=capabilities,
            execution_nodes=(node,),
        )

        self.assertEqual(spec.readiness, "UNKNOWN_CAPABILITY")

    def test_graph_validation_detects_missing_dependency_and_cycle(self):
        capabilities = self._ready_registry().resolve(required=[])
        a = ExecutionNode(
            node_id="a", purpose="A", role="worker", prerequisites=("b",)
        )
        b = ExecutionNode(
            node_id="b", purpose="B", role="worker", prerequisites=("a",)
        )
        c = ExecutionNode(
            node_id="c", purpose="C", role="worker", prerequisites=("missing",)
        )
        spec = ExecutionSpecV2(
            spec_id="spec-4",
            compiler_version="0.2.10",
            raw_request="graph",
            objective="Execute graph.",
            success_definition=("graph complete",),
            complexity_level="N2",
            complexity_score=6,
            capabilities=capabilities,
            execution_nodes=(a, b, c),
        )

        errors = spec.validation_errors()
        self.assertIn("missing_prerequisite:c->missing", errors)
        self.assertIn("execution_graph_cycle", errors)
        self.assertEqual(spec.readiness, "INVALID")

    def test_artifact_contract_requires_existing_producer(self):
        capabilities = self._ready_registry().resolve(required=[])
        node = ExecutionNode(node_id="a", purpose="A", role="worker")
        artifact = ArtifactContract(
            artifact_id="x",
            artifact_type="X",
            producer_node="missing",
        )
        spec = ExecutionSpecV2(
            spec_id="spec-5",
            compiler_version="0.2.10",
            raw_request="artifact",
            objective="Produce artifact.",
            success_definition=("artifact valid",),
            complexity_level="N1",
            complexity_score=3,
            capabilities=capabilities,
            execution_nodes=(node,),
            artifacts=(artifact,),
        )

        self.assertIn(
            "artifact_producer_missing:x->missing",
            spec.validation_errors(),
        )

    def test_from_legacy_preserves_routing_contract(self):
        @dataclass
        class Legacy:
            raw_request: str = "legacy request"
            complexity_level: str = "N2"
            complexity_score: int = 7
            constraints: tuple = ("preserve_behavior",)
            contradictions: tuple = ("c1",)
            patterns: dict = None
            quality_gates: tuple = ("REGRESSION_GATE",)
            capabilities: tuple = ("files.read",)

        legacy = Legacy(patterns={"P02": "mandatory"})
        registry = self._ready_registry()
        node = ExecutionNode(node_id="execute", purpose="Execute", role="worker")

        spec = ExecutionSpecV2.from_legacy(
            legacy,
            registry=registry,
            mandatory_capabilities=("files.read",),
            objective="Preserve behavior while executing the change.",
            success_definition=("regression gate passes",),
            execution_nodes=(node,),
        )

        self.assertEqual(spec.raw_request, "legacy request")
        self.assertEqual(spec.complexity_level, "N2")
        self.assertEqual(spec.constraints, ("preserve_behavior",))
        self.assertEqual(spec.contradictions, ("c1",))
        self.assertEqual(spec.legacy_patterns, {"P02": "mandatory"})
        self.assertEqual(spec.quality_gates, ("REGRESSION_GATE",))
        self.assertEqual(spec.readiness, "READY")


class FailureRouteTests(unittest.TestCase):
    def test_failure_route_defaults_to_local_repair(self):
        route = FailureRoute(
            failure_class="quality_failure",
            source_node="analyze",
            target="repair:analyze",
        )
        self.assertEqual(route.repair_scope, "local")


if __name__ == "__main__":
    unittest.main()
