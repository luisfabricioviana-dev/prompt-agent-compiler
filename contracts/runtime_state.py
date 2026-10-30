"""Deterministic in-process execution state machine for ExecutionSpecV2."""
from __future__ import annotations

from enum import Enum
from typing import Any, Mapping

from .artifact_registry import ArtifactRegistry
from .execution_spec_v2 import ExecutionSpecV2


class RuntimeStateError(RuntimeError):
    pass


class NodeState(str, Enum):
    PENDING = "PENDING"
    READY = "READY"
    RUNNING = "RUNNING"
    PASS = "PASS"
    FAIL = "FAIL"
    BLOCKED = "BLOCKED"


class RuntimeStateMachine:
    def __init__(
        self,
        spec: ExecutionSpecV2,
        *,
        artifact_registry: ArtifactRegistry | None = None,
        trace_ledger: Any | None = None,
        run_id: str | None = None,
    ) -> None:
        if not isinstance(spec, ExecutionSpecV2):
            raise TypeError("execution_spec_v2_required")
        if spec.readiness != "READY":
            raise RuntimeStateError(
                f"execution_spec_not_ready:{spec.readiness}"
            )
        self.spec = spec
        self.artifact_registry = (
            artifact_registry
            if artifact_registry is not None
            else ArtifactRegistry(spec.artifacts)
        )
        if not isinstance(self.artifact_registry, ArtifactRegistry):
            raise TypeError("artifact_registry_invalid")
        if (trace_ledger is None) != (run_id is None):
            raise RuntimeStateError("trace_ledger_and_run_id_required_together")
        self.trace_ledger = trace_ledger
        self.run_id = run_id

        self._nodes = {node.node_id: node for node in spec.execution_nodes}
        self._states: dict[str, NodeState] = {}
        self._failure_reasons: dict[str, str] = {}
        self._dependents: dict[str, set[str]] = {
            node_id: set() for node_id in self._nodes
        }
        for node in spec.execution_nodes:
            for prerequisite in node.prerequisites:
                self._dependents[prerequisite].add(node.node_id)

        for node in spec.execution_nodes:
            self._states[node.node_id] = (
                NodeState.READY
                if not node.prerequisites
                else NodeState.PENDING
            )

        if self.trace_ledger is not None:
            self.trace_ledger.register_run(self.run_id, self.spec)
            self.trace_ledger.commit_step(
                self.run_id,
                events=(
                    {
                        "event_type": "runtime_initialized",
                        "from_state": None,
                        "to_state": self.overall_state,
                    },
                ),
            )

    def _trace_step(self, *, events=(), artifacts=()) -> None:
        if self.trace_ledger is not None:
            self.trace_ledger.commit_step(
                self.run_id,
                events=tuple(events),
                artifacts=tuple(artifacts),
            )

    def _node(self, node_id: str):
        try:
            return self._nodes[node_id]
        except KeyError as exc:
            raise RuntimeStateError(f"node_unknown:{node_id}") from exc

    def node_state(self, node_id: str) -> NodeState:
        self._node(node_id)
        return self._states[node_id]

    def failure_reason(self, node_id: str) -> str | None:
        self._node(node_id)
        return self._failure_reasons.get(node_id)

    @property
    def overall_state(self) -> str:
        states = tuple(self._states.values())
        if any(state is NodeState.FAIL for state in states):
            return "FAILED"
        if states and all(state is NodeState.PASS for state in states):
            return "COMPLETE"
        if any(state is NodeState.RUNNING for state in states):
            return "RUNNING"
        if any(state is NodeState.READY for state in states):
            return "READY"
        if any(state is NodeState.BLOCKED for state in states):
            return "BLOCKED"
        return "PENDING"

    def start(self, node_id: str) -> None:
        self._node(node_id)
        if self._states[node_id] is not NodeState.READY:
            raise RuntimeStateError(f"node_not_ready:{node_id}")
        self._trace_step(
            events=(
                {
                    "event_type": "node_started",
                    "node_id": node_id,
                    "from_state": NodeState.READY.value,
                    "to_state": NodeState.RUNNING.value,
                },
            ),
        )
        self._states[node_id] = NodeState.RUNNING

    def _promotable_dependents(self, node_id: str) -> tuple[str, ...]:
        promoted = []
        for dependent_id in sorted(self._dependents[node_id]):
            if self._states[dependent_id] is not NodeState.PENDING:
                continue
            dependent = self._nodes[dependent_id]
            if all(
                pre == node_id or self._states[pre] is NodeState.PASS
                for pre in dependent.prerequisites
            ):
                promoted.append(dependent_id)
        return tuple(promoted)

    def _promote_dependents(self, node_id: str) -> None:
        for dependent_id in sorted(self._dependents[node_id]):
            if self._states[dependent_id] is not NodeState.PENDING:
                continue
            dependent = self._nodes[dependent_id]
            if all(
                self._states[pre] is NodeState.PASS
                for pre in dependent.prerequisites
            ):
                self._states[dependent_id] = NodeState.READY

    def complete(
        self,
        node_id: str,
        *,
        outputs: Mapping[str, bytes] | None = None,
    ) -> None:
        node = self._node(node_id)
        if self._states[node_id] is not NodeState.RUNNING:
            raise RuntimeStateError(f"node_not_running:{node_id}")

        supplied = {} if outputs is None else outputs
        # Artifact validation/recording happens before the state transition.
        # Any registry failure leaves the node RUNNING and dependents unchanged.
        records = self.artifact_registry.record_node_outputs(node, supplied)
        promoted = self._promotable_dependents(node_id)
        events = [
            {
                "event_type": "artifact_recorded",
                "node_id": node_id,
                "artifact_id": record.artifact_id,
                "details": {
                    "sha256": record.sha256,
                    "byte_size": record.byte_size,
                },
            }
            for record in records
        ]
        events.append(
            {
                "event_type": "node_passed",
                "node_id": node_id,
                "from_state": NodeState.RUNNING.value,
                "to_state": NodeState.PASS.value,
            }
        )
        events.extend(
            {
                "event_type": "node_ready",
                "node_id": dependent_id,
                "from_state": NodeState.PENDING.value,
                "to_state": NodeState.READY.value,
            }
            for dependent_id in promoted
        )
        self._trace_step(events=events, artifacts=records)

        self._states[node_id] = NodeState.PASS
        self._promote_dependents(node_id)

    def _blockable_descendants(self, node_id: str) -> tuple[str, ...]:
        ordered = []
        seen = set()

        def visit(source_id: str) -> None:
            for dependent_id in sorted(self._dependents[source_id]):
                if dependent_id in seen:
                    continue
                seen.add(dependent_id)
                if self._states[dependent_id] in {
                    NodeState.PENDING,
                    NodeState.READY,
                }:
                    ordered.append(dependent_id)
                visit(dependent_id)

        visit(node_id)
        return tuple(ordered)

    def _block_descendants(self, node_id: str) -> None:
        for dependent_id in sorted(self._dependents[node_id]):
            state = self._states[dependent_id]
            if state in {NodeState.PENDING, NodeState.READY}:
                self._states[dependent_id] = NodeState.BLOCKED
            self._block_descendants(dependent_id)

    def fail(self, node_id: str, *, reason: str) -> None:
        self._node(node_id)
        if self._states[node_id] is not NodeState.RUNNING:
            raise RuntimeStateError(f"node_not_running:{node_id}")
        if not isinstance(reason, str) or not reason.strip():
            raise RuntimeStateError("failure_reason_required")
        reason = reason.strip()
        blocked = self._blockable_descendants(node_id)
        events = [
            {
                "event_type": "node_failed",
                "node_id": node_id,
                "from_state": NodeState.RUNNING.value,
                "to_state": NodeState.FAIL.value,
                "reason": reason,
            }
        ]
        events.extend(
            {
                "event_type": "node_blocked",
                "node_id": dependent_id,
                "from_state": self._states[dependent_id].value,
                "to_state": NodeState.BLOCKED.value,
                "reason": f"upstream_failure:{node_id}",
            }
            for dependent_id in blocked
        )
        self._trace_step(events=events)
        self._states[node_id] = NodeState.FAIL
        self._failure_reasons[node_id] = reason
        self._block_descendants(node_id)
