"""Executable v0.2.10 specification contracts.

This module adds runtime structure without replacing the recovered v0.2.9
semantic/policy lineage. It is a compatibility layer for the next compiler
runtime and does not activate REA release behavior.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping

from .capability_registry import (
    CapabilityGateState,
    CapabilityRegistry,
    CapabilityResolution,
)


@dataclass(frozen=True)
class ExecutionNode:
    node_id: str
    purpose: str
    role: str
    required_capabilities: tuple[str, ...] = ()
    prerequisites: tuple[str, ...] = ()
    output_artifacts: tuple[str, ...] = ()
    quality_gates: tuple[str, ...] = ()
    on_pass: tuple[str, ...] = ()
    on_fail: tuple[str, ...] = ()
    retry_limit: int = 0

    def __post_init__(self) -> None:
        if not self.node_id:
            raise ValueError("node_id_required")
        if not self.purpose:
            raise ValueError("node_purpose_required")
        if not self.role:
            raise ValueError("node_role_required")
        if self.node_id in self.prerequisites:
            raise ValueError("node_self_dependency")
        if not isinstance(self.retry_limit, int) or isinstance(self.retry_limit, bool):
            raise TypeError("retry_limit_invalid")
        if self.retry_limit < 0:
            raise ValueError("retry_limit_invalid")


@dataclass(frozen=True)
class ArtifactContract:
    artifact_id: str
    artifact_type: str
    producer_node: str
    required_fields: tuple[str, ...] = ()
    validity_conditions: tuple[str, ...] = ()
    downstream_consumers: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.artifact_id:
            raise ValueError("artifact_id_required")
        if not self.artifact_type:
            raise ValueError("artifact_type_required")
        if not self.producer_node:
            raise ValueError("artifact_producer_required")


@dataclass(frozen=True)
class FailureRoute:
    failure_class: str
    source_node: str
    target: str
    repair_scope: str = "local"

    def __post_init__(self) -> None:
        if not self.failure_class:
            raise ValueError("failure_class_required")
        if not self.source_node:
            raise ValueError("failure_source_required")
        if not self.target:
            raise ValueError("failure_target_required")
        if self.repair_scope not in {
            "local",
            "node",
            "downstream_branch",
            "full_pipeline",
        }:
            raise ValueError("repair_scope_invalid")


@dataclass(frozen=True)
class ExecutionSpecV2:
    spec_id: str
    compiler_version: str
    raw_request: str
    objective: str
    success_definition: tuple[str, ...]
    complexity_level: str
    complexity_score: int
    capabilities: CapabilityResolution

    known_context: tuple[str, ...] = ()
    unknowns: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()
    contradictions: tuple[str, ...] = ()
    constraints: tuple[str, ...] = ()
    dependencies: tuple[str, ...] = ()
    roles: tuple[str, ...] = ()

    legacy_patterns: Mapping[str, Any] = field(default_factory=dict)
    execution_nodes: tuple[ExecutionNode, ...] = ()
    artifacts: tuple[ArtifactContract, ...] = ()
    quality_gates: tuple[Any, ...] = ()
    verification_plan: tuple[str, ...] = ()
    failure_routes: tuple[FailureRoute, ...] = ()
    stop_conditions: tuple[str, ...] = ()
    output_contract: Mapping[str, Any] = field(default_factory=dict)
    learning_trace: Mapping[str, Any] = field(default_factory=dict)

    def validation_errors(self) -> tuple[str, ...]:
        errors: list[str] = []
        if not self.spec_id:
            errors.append("spec_id_required")
        if not self.compiler_version:
            errors.append("compiler_version_required")
        if not self.objective:
            errors.append("objective_required")
        if not self.success_definition:
            errors.append("success_definition_required")
        if not self.execution_nodes:
            errors.append("execution_graph_empty")
            return tuple(errors)

        node_ids = [node.node_id for node in self.execution_nodes]
        if len(node_ids) != len(set(node_ids)):
            errors.append("execution_node_id_duplicate")
        node_set = set(node_ids)

        for node in self.execution_nodes:
            for prerequisite in node.prerequisites:
                if prerequisite not in node_set:
                    errors.append(
                        f"missing_prerequisite:{node.node_id}->{prerequisite}"
                    )

        if self._has_cycle():
            errors.append("execution_graph_cycle")

        artifact_ids = [artifact.artifact_id for artifact in self.artifacts]
        if len(artifact_ids) != len(set(artifact_ids)):
            errors.append("artifact_id_duplicate")
        artifact_set = set(artifact_ids)
        for artifact in self.artifacts:
            if artifact.producer_node not in node_set:
                errors.append(
                    f"artifact_producer_missing:{artifact.artifact_id}"
                    f"->{artifact.producer_node}"
                )
            for consumer in artifact.downstream_consumers:
                if consumer not in node_set:
                    errors.append(
                        f"artifact_consumer_missing:{artifact.artifact_id}"
                        f"->{consumer}"
                    )
        for node in self.execution_nodes:
            for artifact_id in node.output_artifacts:
                if artifact_id not in artifact_set:
                    errors.append(
                        f"node_output_contract_missing:{node.node_id}"
                        f"->{artifact_id}"
                    )

        resolved_names = {
            spec.name
            for spec in (*self.capabilities.required, *self.capabilities.optional)
        }
        for node in self.execution_nodes:
            for name in node.required_capabilities:
                if name not in resolved_names:
                    errors.append(
                        f"node_capability_unresolved:{node.node_id}->{name}"
                    )

        for route in self.failure_routes:
            if route.source_node not in node_set:
                errors.append(
                    f"failure_route_source_missing:{route.source_node}"
                )

        return tuple(dict.fromkeys(errors))

    def _has_cycle(self) -> bool:
        nodes = {node.node_id: node for node in self.execution_nodes}
        state: dict[str, int] = {}

        def visit(node_id: str) -> bool:
            mark = state.get(node_id, 0)
            if mark == 1:
                return True
            if mark == 2:
                return False
            state[node_id] = 1
            for prerequisite in nodes[node_id].prerequisites:
                if prerequisite in nodes and visit(prerequisite):
                    return True
            state[node_id] = 2
            return False

        return any(visit(node_id) for node_id in nodes if state.get(node_id, 0) == 0)

    @property
    def readiness(self) -> str:
        if self.validation_errors():
            return "INVALID"
        if self.capabilities.state is CapabilityGateState.BLOCKED:
            return "BLOCKED"
        if self.capabilities.state is CapabilityGateState.UNKNOWN:
            return "UNKNOWN_CAPABILITY"
        if self.capabilities.state is CapabilityGateState.ADAPT_REQUIRED:
            return "ADAPT_REQUIRED"
        return "READY"

    @classmethod
    def from_legacy(
        cls,
        legacy: object,
        *,
        registry: CapabilityRegistry,
        mandatory_capabilities: Iterable[str],
        objective: str,
        success_definition: Iterable[str],
        execution_nodes: Iterable[ExecutionNode],
        artifacts: Iterable[ArtifactContract] = (),
        dependencies: Iterable[str] = (),
        roles: Iterable[str] = (),
        verification_plan: Iterable[str] = (),
        failure_routes: Iterable[FailureRoute] = (),
        stop_conditions: Iterable[str] = (),
        output_contract: Mapping[str, Any] | None = None,
        spec_id: str = "legacy-adapter-v0.2.10",
    ) -> "ExecutionSpecV2":
        legacy_caps = tuple(getattr(legacy, "capabilities", ()) or ())
        mandatory = tuple(mandatory_capabilities)
        optional = tuple(name for name in legacy_caps if name not in set(mandatory))
        resolution = registry.resolve(required=mandatory, optional=optional)

        return cls(
            spec_id=spec_id,
            compiler_version="0.2.10",
            raw_request=getattr(legacy, "raw_request", ""),
            objective=objective,
            success_definition=tuple(success_definition),
            complexity_level=getattr(legacy, "complexity_level", "N0"),
            complexity_score=getattr(legacy, "complexity_score", 0),
            capabilities=resolution,
            contradictions=tuple(getattr(legacy, "contradictions", ()) or ()),
            constraints=tuple(getattr(legacy, "constraints", ()) or ()),
            dependencies=tuple(dependencies),
            roles=tuple(roles),
            legacy_patterns=getattr(legacy, "patterns", {}) or {},
            execution_nodes=tuple(execution_nodes),
            artifacts=tuple(artifacts),
            quality_gates=tuple(getattr(legacy, "quality_gates", ()) or ()),
            verification_plan=tuple(verification_plan),
            failure_routes=tuple(failure_routes),
            stop_conditions=tuple(stop_conditions),
            output_contract=dict(output_contract or {}),
        )
