"""Canonical composition runtime for PROMPT & AGENT COMPILER v0.2.10.

This module composes already-separated boundaries:
semantic provider -> deterministic policy -> capability resolution ->
ExecutionSpecV2. It does not choose a model, mutate policy, or enable REA.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Mapping

from .capability_registry import CapabilityRegistry
from .execution_spec_v2 import (
    ArtifactContract,
    ExecutionNode,
    ExecutionSpecV2,
    FailureRoute,
)
from .pattern_registry import PatternRegistry
from .reviewer_spec import ReviewerSpec


class RuntimeCompilationError(RuntimeError):
    pass


@dataclass(frozen=True)
class ExecutionPlan:
    objective: str
    success_definition: tuple[str, ...]
    required_capabilities: tuple[str, ...] = ()
    optional_capabilities: tuple[str, ...] = ()
    execution_nodes: tuple[ExecutionNode, ...] = ()
    artifacts: tuple[ArtifactContract, ...] = ()
    dependencies: tuple[str, ...] = ()
    roles: tuple[str, ...] = ()
    verification_plan: tuple[str, ...] = ()
    failure_routes: tuple[FailureRoute, ...] = ()
    stop_conditions: tuple[str, ...] = ()
    output_contract: Mapping[str, Any] = field(default_factory=dict)
    learning_trace: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.objective, str) or not self.objective.strip():
            raise ValueError("plan_objective_required")
        if not self.success_definition:
            raise ValueError("plan_success_definition_required")


class CanonicalCompilerRuntime:
    def __init__(
        self,
        *,
        semantic_provider: Any,
        policy_compiler: Callable[[Any], Any],
        capability_registry: CapabilityRegistry,
        pattern_registry: PatternRegistry,
        compiler_version: str = "0.2.10",
    ) -> None:
        if not hasattr(semantic_provider, "interpret"):
            raise TypeError("semantic_provider_interpret_required")
        if not callable(policy_compiler):
            raise TypeError("policy_compiler_callable_required")
        if not isinstance(capability_registry, CapabilityRegistry):
            raise TypeError("capability_registry_invalid")
        if not isinstance(pattern_registry, PatternRegistry):
            raise TypeError("pattern_registry_invalid")
        if not isinstance(compiler_version, str) or not compiler_version.strip():
            raise ValueError("compiler_version_required")
        self.semantic_provider = semantic_provider
        self.policy_compiler = policy_compiler
        self.capability_registry = capability_registry
        self.pattern_registry = pattern_registry
        self.compiler_version = compiler_version.strip()

    def _validate_policy_patterns(self, legacy: Any) -> None:
        patterns = getattr(legacy, "patterns", {}) or {}
        if not isinstance(patterns, Mapping):
            raise RuntimeCompilationError("policy_patterns_invalid")
        for pattern_id in patterns:
            try:
                self.pattern_registry.get(pattern_id)
            except KeyError as exc:
                raise RuntimeCompilationError(
                    f"unknown_policy_pattern:{pattern_id}"
                ) from exc

    @staticmethod
    def _validate_request_identity(request: str, legacy: Any) -> None:
        policy_request = getattr(legacy, "raw_request", None)
        if policy_request != request:
            raise RuntimeCompilationError("policy_request_identity_mismatch")

    @staticmethod
    def _declared_capabilities(
        plan: ExecutionPlan, legacy: Any
    ) -> tuple[str, ...]:
        names = list(plan.required_capabilities)
        names.extend(plan.optional_capabilities)
        names.extend(tuple(getattr(legacy, "capabilities", ()) or ()))
        return tuple(dict.fromkeys(names))

    @classmethod
    def _validate_node_capabilities(
        cls, plan: ExecutionPlan, legacy: Any
    ) -> None:
        declared = set(cls._declared_capabilities(plan, legacy))
        for node in plan.execution_nodes:
            for capability in node.required_capabilities:
                if capability not in declared:
                    raise RuntimeCompilationError(
                        "plan_node_capability_not_declared:"
                        f"{node.node_id}->{capability}"
                    )

    def _interpret_and_route(self, request: str):
        if not isinstance(request, str) or not request.strip():
            raise RuntimeCompilationError("request_required")
        task = self.semantic_provider.interpret(request)
        legacy = self.policy_compiler(task)
        self._validate_request_identity(request, legacy)
        self._validate_policy_patterns(legacy)
        return legacy

    def _compile_from_policy(
        self,
        request: str,
        *,
        legacy: Any,
        plan: ExecutionPlan,
    ) -> ExecutionSpecV2:
        if not isinstance(plan, ExecutionPlan):
            raise TypeError("execution_plan_invalid")
        self._validate_node_capabilities(plan, legacy)

        legacy_caps = tuple(getattr(legacy, "capabilities", ()) or ())
        required_set = set(plan.required_capabilities)
        optional = tuple(
            dict.fromkeys(
                (
                    *plan.optional_capabilities,
                    *(cap for cap in legacy_caps if cap not in required_set),
                )
            )
        )
        resolution = self.capability_registry.resolve(
            required=plan.required_capabilities,
            optional=optional,
        )

        return ExecutionSpecV2(
            spec_id=f"runtime:{self.compiler_version}",
            compiler_version=self.compiler_version,
            raw_request=request,
            objective=plan.objective,
            success_definition=tuple(plan.success_definition),
            complexity_level=getattr(legacy, "complexity_level", "N0"),
            complexity_score=getattr(legacy, "complexity_score", 0),
            capabilities=resolution,
            contradictions=tuple(
                getattr(legacy, "contradictions", ()) or ()
            ),
            constraints=tuple(getattr(legacy, "constraints", ()) or ()),
            dependencies=tuple(plan.dependencies),
            roles=tuple(plan.roles),
            legacy_patterns=dict(getattr(legacy, "patterns", {}) or {}),
            execution_nodes=tuple(plan.execution_nodes),
            artifacts=tuple(plan.artifacts),
            quality_gates=tuple(
                getattr(legacy, "quality_gates", ()) or ()
            ),
            verification_plan=tuple(plan.verification_plan),
            failure_routes=tuple(plan.failure_routes),
            stop_conditions=tuple(plan.stop_conditions),
            output_contract=dict(plan.output_contract),
            learning_trace=dict(plan.learning_trace),
        )

    def compile(self, request: str, *, plan: ExecutionPlan) -> ExecutionSpecV2:
        legacy = self._interpret_and_route(request)
        return self._compile_from_policy(request, legacy=legacy, plan=plan)

    def compile_auto(
        self,
        request: str,
        *,
        graph_compiler: Any,
        objective: str,
        success_definition: Iterable[str],
        required_capabilities: Iterable[str] = (),
        optional_capabilities: Iterable[str] = (),
    ) -> ExecutionSpecV2:
        if not hasattr(graph_compiler, "compile"):
            raise TypeError("execution_graph_compiler_required")
        legacy = self._interpret_and_route(request)
        plan = graph_compiler.compile(
            legacy,
            objective=objective,
            success_definition=success_definition,
            required_capabilities=required_capabilities,
            optional_capabilities=optional_capabilities,
        )
        if not isinstance(plan, ExecutionPlan):
            raise RuntimeCompilationError("execution_graph_compiler_invalid_plan")
        return self._compile_from_policy(request, legacy=legacy, plan=plan)


def _gate_id(gate: Any) -> str:
    if isinstance(gate, str) and gate.strip():
        return gate.strip()
    value = getattr(gate, "gate_id", None)
    if isinstance(value, str) and value.strip():
        return value.strip()
    raise RuntimeCompilationError("quality_gate_identity_missing")


def reviewer_spec_from_execution(
    spec: ExecutionSpecV2,
    *,
    review_id: str,
    independent_required: bool = False,
    adversarial_checks: Iterable[str] = (),
    regression_targets: Iterable[str] = (),
    evidence_requirements: Iterable[str] = (),
) -> ReviewerSpec:
    if not isinstance(spec, ExecutionSpecV2):
        raise TypeError("execution_spec_v2_required")
    gate_ids = tuple(dict.fromkeys(_gate_id(g) for g in spec.quality_gates))
    artifact_ids = tuple(artifact.artifact_id for artifact in spec.artifacts)

    return ReviewerSpec(
        review_id=review_id,
        target_artifacts=artifact_ids,
        original_objective=spec.objective,
        original_constraints=tuple(spec.constraints),
        critical_assumptions=tuple(spec.assumptions),
        required_gates=gate_ids,
        regression_targets=tuple(regression_targets),
        adversarial_checks=tuple(adversarial_checks),
        evidence_requirements=tuple(evidence_requirements),
        independent_required=independent_required,
    )
