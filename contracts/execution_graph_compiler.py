"""Automatic generic execution-graph compiler for v0.2.10.

The graph is derived from active PatternRegistry contracts plus the gates that
the deterministic policy actually emitted. It does not invent new routing
rules, domain-specific nodes, or hidden runtime capabilities.
"""
from __future__ import annotations

from typing import Any, Iterable, Mapping

from .execution_spec_v2 import ArtifactContract, ExecutionNode, FailureRoute
from .pattern_registry import PatternRegistry


class ExecutionGraphCompilationError(RuntimeError):
    pass


def _status_value(value: Any) -> str:
    raw = getattr(value, "value", value)
    return str(raw)


def _gate_id(gate: Any) -> str:
    if isinstance(gate, str) and gate.strip():
        return gate.strip()
    value = getattr(gate, "gate_id", None)
    if isinstance(value, str) and value.strip():
        return value.strip()
    raise ExecutionGraphCompilationError("quality_gate_identity_missing")


class ExecutionGraphCompiler:
    def __init__(self, registry: PatternRegistry) -> None:
        if not isinstance(registry, PatternRegistry):
            raise TypeError("pattern_registry_invalid")
        self.registry = registry

    def _active_patterns(self, policy_result: Any) -> tuple[str, ...]:
        patterns = getattr(policy_result, "patterns", None)
        if not isinstance(patterns, Mapping):
            raise ExecutionGraphCompilationError("policy_patterns_invalid")
        active: list[str] = []
        for pattern_id, decision in patterns.items():
            try:
                self.registry.get(pattern_id)
            except KeyError as exc:
                raise ExecutionGraphCompilationError(
                    f"unknown_policy_pattern:{pattern_id}"
                ) from exc
            if _status_value(getattr(decision, "status", "rejected")) != "rejected":
                active.append(pattern_id)
        return tuple(active)

    def compile(
        self,
        policy_result: Any,
        *,
        objective: str,
        success_definition: Iterable[str],
        required_capabilities: Iterable[str] = (),
        optional_capabilities: Iterable[str] = (),
    ):
        from .canonical_runtime import ExecutionPlan

        if not isinstance(objective, str) or not objective.strip():
            raise ExecutionGraphCompilationError("objective_required")
        success = tuple(success_definition)
        if not success:
            raise ExecutionGraphCompilationError("success_definition_required")

        active = self._active_patterns(policy_result)
        required_caps = tuple(dict.fromkeys(required_capabilities))
        optional_caps = tuple(
            cap for cap in dict.fromkeys(optional_capabilities)
            if cap not in set(required_caps)
        )

        prerequisites: list[str] = []
        produced: list[str] = []
        for pattern_id in active:
            pattern = self.registry.get(pattern_id)
            prerequisites.extend(pattern.prerequisites)
            produced.extend(pattern.produced_artifacts)
        prerequisites = list(dict.fromkeys(prerequisites))
        produced = list(dict.fromkeys(produced))

        gates = tuple(
            dict.fromkeys(
                _gate_id(gate)
                for gate in tuple(getattr(policy_result, "quality_gates", ()) or ())
            )
        )
        independent_gate = "INDEPENDENT_REVIEW_GATE"
        verification_gates = tuple(
            gate for gate in gates if gate != independent_gate
        )

        nodes: list[ExecutionNode] = []
        artifacts: list[ArtifactContract] = []
        roles: list[str] = []
        failure_routes: list[FailureRoute] = []

        if prerequisites:
            nodes.append(
                ExecutionNode(
                    node_id="prepare",
                    purpose="Satisfy prerequisites: " + ", ".join(prerequisites),
                    role="planner",
                    output_artifacts=("prerequisites",),
                    on_fail=("repair:prepare",),
                )
            )
            artifacts.append(
                ArtifactContract(
                    artifact_id="prerequisites",
                    artifact_type="PrerequisiteEvidence",
                    producer_node="prepare",
                    required_fields=("evidence",),
                )
            )
            roles.append("planner")
            failure_routes.append(
                FailureRoute(
                    failure_class="requirement_failure",
                    source_node="prepare",
                    target="repair:prepare",
                    repair_scope="local",
                )
            )

        execute_prereqs = ("prepare",) if prerequisites else ()
        nodes.append(
            ExecutionNode(
                node_id="execute",
                purpose=(
                    "Execute active patterns: "
                    + (", ".join(active) if active else "none")
                ),
                role="executor",
                required_capabilities=required_caps,
                prerequisites=execute_prereqs,
                output_artifacts=tuple(produced),
                on_fail=("repair:execute",),
            )
        )
        roles.append("executor")
        failure_routes.append(
            FailureRoute(
                failure_class="implementation_failure",
                source_node="execute",
                target="repair:execute",
                repair_scope="node",
            )
        )

        for artifact_id in produced:
            artifacts.append(
                ArtifactContract(
                    artifact_id=artifact_id,
                    artifact_type="PatternArtifact",
                    producer_node="execute",
                )
            )

        if verification_gates:
            nodes.append(
                ExecutionNode(
                    node_id="verify",
                    purpose="Verify policy-emitted quality gates.",
                    role="verifier",
                    prerequisites=("execute",),
                    quality_gates=verification_gates,
                    on_fail=("repair:verify",),
                )
            )
            roles.append("verifier")
            failure_routes.append(
                FailureRoute(
                    failure_class="quality_failure",
                    source_node="verify",
                    target="repair:verify",
                    repair_scope="local",
                )
            )

        if independent_gate in gates:
            parent = "verify" if verification_gates else "execute"
            nodes.append(
                ExecutionNode(
                    node_id="independent-review",
                    purpose="Perform independent review required by policy.",
                    role="independent_reviewer",
                    prerequisites=(parent,),
                    quality_gates=("INDEPENDENT_REVIEW_GATE",),
                    on_fail=("repair:independent-review",),
                )
            )
            roles.append("independent_reviewer")
            failure_routes.append(
                FailureRoute(
                    failure_class="quality_failure",
                    source_node="independent-review",
                    target="repair:independent-review",
                    repair_scope="local",
                )
            )

        return ExecutionPlan(
            objective=objective.strip(),
            success_definition=success,
            required_capabilities=required_caps,
            optional_capabilities=optional_caps,
            execution_nodes=tuple(nodes),
            artifacts=tuple(artifacts),
            roles=tuple(dict.fromkeys(roles)),
            verification_plan=tuple(f"verify_gate:{gate}" for gate in gates),
            failure_routes=tuple(failure_routes),
            stop_conditions=(
                "blocking_gate_failed",
                "required_capability_not_ready",
            ),
            output_contract={
                "active_patterns": active,
                "artifact_ids": tuple(a.artifact_id for a in artifacts),
            },
            learning_trace={
                "execution_graph_compiler": "v0.2.10",
                "graph_source": "pattern_registry_plus_policy_gates",
            },
        )
