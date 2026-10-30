import unittest
from dataclasses import dataclass

from contracts.capability_registry import (
    CapabilityRegistry,
    CapabilitySpec,
    CapabilityStatus,
)
from contracts.canonical_runtime import (
    CanonicalCompilerRuntime,
    ExecutionPlan,
    RuntimeCompilationError,
    reviewer_spec_from_execution,
)
from contracts.execution_spec_v2 import ArtifactContract, ExecutionNode
from contracts.pattern_registry import default_pattern_registry


class FakeProvider:
    def __init__(self, task):
        self.task = task
        self.requests = []

    def interpret(self, request):
        self.requests.append(request)
        return self.task


@dataclass
class LegacyPolicyResult:
    raw_request: str
    complexity_level: str = "N2"
    complexity_score: int = 6
    constraints: tuple = ()
    contradictions: tuple = ()
    patterns: dict = None
    quality_gates: tuple = ()
    capabilities: tuple = ()


class FakePolicy:
    def __init__(self, result):
        self.result = result
        self.tasks = []

    def __call__(self, task):
        self.tasks.append(task)
        return self.result


class Gate:
    def __init__(self, gate_id):
        self.gate_id = gate_id


class CanonicalRuntimeTests(unittest.TestCase):
    def plan(self):
        return ExecutionPlan(
            objective="Produce the requested verified result.",
            success_definition=("output contract passes",),
            required_capabilities=("files.read",),
            execution_nodes=(
                ExecutionNode(
                    node_id="execute",
                    purpose="Execute the compiled task",
                    role="executor",
                    required_capabilities=("files.read",),
                    output_artifacts=("result",),
                ),
            ),
            artifacts=(
                ArtifactContract(
                    artifact_id="result",
                    artifact_type="Result",
                    producer_node="execute",
                ),
            ),
            verification_plan=("validate:result",),
            stop_conditions=("blocking_gate_failed",),
        )

    def registry(self):
        return CapabilityRegistry(
            (CapabilitySpec("files.read", CapabilityStatus.AVAILABLE),)
        )

    def test_runtime_composes_provider_policy_capabilities_and_execution_spec(self):
        task = object()
        provider = FakeProvider(task)
        legacy = LegacyPolicyResult(
            raw_request="analyze",
            patterns={"P01": "mandatory"},
            quality_gates=(Gate("REQUIREMENT_GATE"),),
        )
        policy = FakePolicy(legacy)
        runtime = CanonicalCompilerRuntime(
            semantic_provider=provider,
            policy_compiler=policy,
            capability_registry=self.registry(),
            pattern_registry=default_pattern_registry(),
        )

        result = runtime.compile("analyze", plan=self.plan())

        self.assertEqual(provider.requests, ["analyze"])
        self.assertEqual(policy.tasks, [task])
        self.assertEqual(result.readiness, "READY")
        self.assertEqual(result.objective, self.plan().objective)
        self.assertIn("P01", result.legacy_patterns)
        self.assertEqual(result.execution_nodes[0].node_id, "execute")

    def test_unknown_required_capability_is_preserved_as_unknown(self):
        runtime = CanonicalCompilerRuntime(
            semantic_provider=FakeProvider(object()),
            policy_compiler=FakePolicy(
                LegacyPolicyResult(
                    raw_request="send",
                    patterns={"P01": "mandatory"},
                )
            ),
            capability_registry=CapabilityRegistry(),
            pattern_registry=default_pattern_registry(),
        )
        plan = ExecutionPlan(
            objective="Send the result.",
            success_definition=("delivery requested",),
            required_capabilities=("email.send",),
            execution_nodes=(
                ExecutionNode(
                    node_id="send",
                    purpose="Send",
                    role="operator",
                    required_capabilities=("email.send",),
                ),
            ),
        )

        result = runtime.compile("send", plan=plan)

        self.assertEqual(result.readiness, "UNKNOWN_CAPABILITY")

    def test_runtime_rejects_unknown_policy_pattern(self):
        runtime = CanonicalCompilerRuntime(
            semantic_provider=FakeProvider(object()),
            policy_compiler=FakePolicy(
                LegacyPolicyResult(
                    raw_request="x",
                    patterns={"P99": "mandatory"},
                )
            ),
            capability_registry=self.registry(),
            pattern_registry=default_pattern_registry(),
        )

        with self.assertRaisesRegex(
            RuntimeCompilationError, "unknown_policy_pattern:P99"
        ):
            runtime.compile("x", plan=self.plan())

    def test_runtime_rejects_request_identity_drift_from_policy(self):
        runtime = CanonicalCompilerRuntime(
            semantic_provider=FakeProvider(object()),
            policy_compiler=FakePolicy(
                LegacyPolicyResult(
                    raw_request="different request",
                    patterns={"P01": "mandatory"},
                )
            ),
            capability_registry=self.registry(),
            pattern_registry=default_pattern_registry(),
        )

        with self.assertRaisesRegex(
            RuntimeCompilationError, "policy_request_identity_mismatch"
        ):
            runtime.compile("original request", plan=self.plan())

    def test_plan_node_capabilities_must_be_declared_required_or_optional(self):
        runtime = CanonicalCompilerRuntime(
            semantic_provider=FakeProvider(object()),
            policy_compiler=FakePolicy(
                LegacyPolicyResult(
                    raw_request="x",
                    patterns={"P01": "mandatory"},
                )
            ),
            capability_registry=self.registry(),
            pattern_registry=default_pattern_registry(),
        )
        plan = ExecutionPlan(
            objective="Do x.",
            success_definition=("x done",),
            execution_nodes=(
                ExecutionNode(
                    node_id="x",
                    purpose="X",
                    role="worker",
                    required_capabilities=("undeclared.capability",),
                ),
            ),
        )

        with self.assertRaisesRegex(
            RuntimeCompilationError, "plan_node_capability_not_declared"
        ):
            runtime.compile("x", plan=plan)


class ReviewerCompilerTests(unittest.TestCase):
    def spec(self):
        runtime = CanonicalCompilerRuntime(
            semantic_provider=FakeProvider(object()),
            policy_compiler=FakePolicy(
                LegacyPolicyResult(
                    raw_request="review me",
                    patterns={"P02": "mandatory"},
                    quality_gates=(
                        Gate("REGRESSION_GATE"),
                        "EVIDENCE_GATE",
                    ),
                )
            ),
            capability_registry=self.registry(),
            pattern_registry=default_pattern_registry(),
        )
        plan = ExecutionPlan(
            objective="Preserve behavior.",
            success_definition=("all required gates pass",),
            required_capabilities=("files.read",),
            execution_nodes=(
                ExecutionNode(
                    node_id="execute",
                    purpose="Execute",
                    role="executor",
                    required_capabilities=("files.read",),
                    output_artifacts=("result",),
                ),
            ),
            artifacts=(
                ArtifactContract(
                    artifact_id="result",
                    artifact_type="Result",
                    producer_node="execute",
                ),
            ),
        )
        return runtime.compile("review me", plan=plan)

    def registry(self):
        return CapabilityRegistry(
            (CapabilitySpec("files.read", CapabilityStatus.AVAILABLE),)
        )

    def test_reviewer_spec_is_compiled_from_execution_spec_gates(self):
        spec = self.spec()

        review = reviewer_spec_from_execution(
            spec,
            review_id="review-1",
            independent_required=True,
            adversarial_checks=("unsupported_assumption",),
        )

        self.assertEqual(
            review.required_gates,
            ("REGRESSION_GATE", "EVIDENCE_GATE"),
        )
        self.assertEqual(review.target_artifacts, ("result",))
        self.assertEqual(review.original_objective, "Preserve behavior.")
        self.assertTrue(review.independent_required)

    def test_reviewer_compiler_rejects_gate_without_identity(self):
        spec = self.spec()
        object.__setattr__(spec, "quality_gates", (object(),))

        with self.assertRaisesRegex(
            RuntimeCompilationError, "quality_gate_identity_missing"
        ):
            reviewer_spec_from_execution(spec, review_id="review-2")


if __name__ == "__main__":
    unittest.main()
