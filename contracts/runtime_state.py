"""Deterministic in-process execution state machine for ExecutionSpecV2."""
from __future__ import annotations

from enum import Enum
from typing import Mapping, Iterable

from .artifact_registry import ArtifactRegistry
from .execution_spec_v2 import ExecutionSpecV2
from .reviewer_spec import ReviewerSpec, ReviewFinding
from .gate_evidence import GateEvidence


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
        run_id: str | None = None,
    ) -> None:
        if not isinstance(spec, ExecutionSpecV2):
            raise TypeError("execution_spec_v2_required")
        if spec.readiness != "READY":
            raise RuntimeStateError(
                f"execution_spec_not_ready:{spec.readiness}"
            )
        self.spec = spec
        self.run_id = run_id if run_id is not None else spec.spec_id
        if not isinstance(self.run_id, str) or not self.run_id.strip():
            raise RuntimeStateError("runtime_run_id_required")
        self.artifact_registry = (
            artifact_registry
            if artifact_registry is not None
            else ArtifactRegistry(spec.artifacts)
        )
        if not isinstance(self.artifact_registry, ArtifactRegistry):
            raise TypeError("artifact_registry_invalid")
        if not self.artifact_registry.matches_contracts(spec.artifacts):
            raise RuntimeStateError("artifact_registry_contract_mismatch")

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
        self._states[node_id] = NodeState.RUNNING

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
        findings: Iterable[ReviewFinding] | None = None,
        independent_reviewer_confirmed: bool = False,
        gate_evidence: Iterable[GateEvidence] | None = None,
    ) -> None:
        node = self._node(node_id)
        if self._states[node_id] is not NodeState.RUNNING:
            raise RuntimeStateError(f"node_not_running:{node_id}")

        if node.quality_gates:
            if findings is None:
                raise RuntimeStateError(f"runtime_gate_evidence_required:{node_id}")
            findings = tuple(findings)
            self._validate_gate_bindings(node_id, tuple(node.quality_gates), findings, gate_evidence)
            reviewer = ReviewerSpec(
                review_id=f"runtime:{node_id}",
                target_artifacts=tuple(node.output_artifacts),
                original_objective=self.spec.objective,
                required_gates=tuple(node.quality_gates),
                independent_required=(node.role == "independent_reviewer"),
            )
            result = reviewer.evaluate(
                findings=tuple(findings),
                independent_reviewer_confirmed=independent_reviewer_confirmed,
            )
            if result.state != "PASS":
                raise RuntimeStateError(
                    f"runtime_gate_review_failed:{node_id}:"
                    + ",".join(result.reasons)
                )

        supplied = {} if outputs is None else outputs
        # Artifact validation/recording happens before the state transition.
        # Any registry failure leaves the node RUNNING and dependents unchanged.
        self.artifact_registry.record_node_outputs(node, supplied)

        self._states[node_id] = NodeState.PASS
        self._promote_dependents(node_id)

    def _validate_gate_bindings(
        self,
        node_id: str,
        gates: tuple[str, ...],
        findings: Iterable[ReviewFinding],
        evidence: Iterable[GateEvidence] | None,
    ) -> None:
        if evidence is None:
            raise RuntimeStateError("runtime_gate_binding_required")
        rows = tuple(evidence)
        by_gate = {}
        for row in rows:
            if not isinstance(row, GateEvidence):
                raise RuntimeStateError("runtime_gate_binding_invalid")
            if (row.run_id != self.run_id or row.node_id != node_id
                    or row.gate_id not in gates):
                raise RuntimeStateError("runtime_gate_binding_scope_mismatch")
            if row.gate_id in by_gate:
                raise RuntimeStateError("runtime_gate_binding_duplicate")
            if not isinstance(row.payload, bytes) or not row.payload:
                raise RuntimeStateError("runtime_gate_binding_payload_invalid")
            if row.artifact_id is not None:
                if not isinstance(row.artifact_sha256, str):
                    raise RuntimeStateError("runtime_gate_binding_artifact_digest_required")
                try:
                    record = self.artifact_registry.get(row.artifact_id)
                except Exception as exc:
                    raise RuntimeStateError("runtime_gate_binding_artifact_missing") from exc
                if record.sha256 != row.artifact_sha256:
                    raise RuntimeStateError("runtime_gate_binding_artifact_mismatch")
            elif row.artifact_sha256 is not None:
                raise RuntimeStateError("runtime_gate_binding_artifact_id_required")
            by_gate[row.gate_id] = row
        for gate in gates:
            row = by_gate.get(gate)
            if row is None:
                raise RuntimeStateError(f"runtime_gate_binding_missing:{gate}")
        for finding in findings:
            row = by_gate.get(finding.gate_id)
            if row is None or row.digest not in finding.evidence:
                raise RuntimeStateError(f"runtime_gate_binding_digest_mismatch:{finding.gate_id}")

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
        self._states[node_id] = NodeState.FAIL
        self._failure_reasons[node_id] = reason.strip()
        self._block_descendants(node_id)
