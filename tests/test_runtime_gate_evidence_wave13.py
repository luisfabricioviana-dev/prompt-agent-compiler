"""Wave 13: runtime gate evidence required before PASS."""
import unittest

from contracts.capability_registry import CapabilityRegistry
from contracts.execution_spec_v2 import ExecutionNode, ExecutionSpecV2
from contracts.reviewer_spec import ReviewFinding
from contracts.gate_evidence import GateEvidence
from contracts.runtime_state import NodeState, RuntimeStateError, RuntimeStateMachine


def make_runtime():
    spec = ExecutionSpecV2(
        spec_id="gate-runtime",
        compiler_version="0.2.10",
        raw_request="test",
        objective="Verified output",
        success_definition=("all gates passed",),
        complexity_level="N2",
        complexity_score=5,
        capabilities=CapabilityRegistry().resolve(required=()),
        execution_nodes=(
            ExecutionNode("execute", "Execute", "executor"),
            ExecutionNode(
                "verify", "Verify", "verifier",
                prerequisites=("execute",),
                quality_gates=("REGRESSION_GATE", "BASELINE_GATE"),
            ),
            ExecutionNode(
                "independent-review", "Review independently", "independent_reviewer",
                prerequisites=("verify",),
                quality_gates=("INDEPENDENT_REVIEW_GATE",),
            ),
        ),
        quality_gates=("REGRESSION_GATE", "BASELINE_GATE", "INDEPENDENT_REVIEW_GATE"),
    )
    runtime = RuntimeStateMachine(spec)
    runtime.start("execute")
    runtime.complete("execute")
    runtime.start("verify")
    return runtime


def bound(runtime, node, labels):
    rows = tuple(GateEvidence(runtime.run_id, node, name, name.encode())
                 for name in labels)
    findings = tuple(ReviewFinding(row.gate_id, True, (row.digest,)) for row in rows)
    return findings, rows


class GateEvidenceRuntimeTests(unittest.TestCase):
    def test_missing_findings_cannot_complete_verify(self):
        runtime = make_runtime()
        with self.assertRaisesRegex(RuntimeStateError, "runtime_gate_evidence_required"):
            runtime.complete("verify")
        self.assertEqual(runtime.node_state("verify"), NodeState.RUNNING)
        self.assertEqual(runtime.node_state("independent-review"), NodeState.PENDING)

    def test_missing_or_failed_gate_rejects_completion(self):
        for findings in (
            (ReviewFinding("REGRESSION_GATE", True, ("ok",)),),
            (
                ReviewFinding("REGRESSION_GATE", False, ("failure",)),
                ReviewFinding("BASELINE_GATE", True, ("ok",)),
            ),
            (
                ReviewFinding("REGRESSION_GATE", True),
                ReviewFinding("BASELINE_GATE", True, ("ok",)),
            ),
        ):
            with self.subTest(findings=findings):
                runtime = make_runtime()
                with self.assertRaisesRegex(RuntimeStateError, "runtime_gate_binding_required"):
                    runtime.complete("verify", findings=findings)
                self.assertEqual(runtime.node_state("verify"), NodeState.RUNNING)

    def test_evidenced_gates_promote_downstream_review(self):
        runtime = make_runtime()
        findings, evidence = bound(runtime, "verify", ("REGRESSION_GATE", "BASELINE_GATE"))
        runtime.complete("verify", findings=findings, gate_evidence=evidence)
        self.assertEqual(runtime.node_state("verify"), NodeState.PASS)
        self.assertEqual(runtime.node_state("independent-review"), NodeState.READY)

    def test_independent_review_requires_confirmation(self):
        runtime = make_runtime()
        findings, evidence = bound(runtime, "verify", ("REGRESSION_GATE", "BASELINE_GATE"))
        runtime.complete("verify", findings=findings, gate_evidence=evidence)
        runtime.start("independent-review")
        findings, evidence = bound(runtime, "independent-review", ("INDEPENDENT_REVIEW_GATE",))
        with self.assertRaisesRegex(RuntimeStateError, "runtime_gate_review_failed"):
            runtime.complete("independent-review", findings=findings, gate_evidence=evidence)
        runtime.complete("independent-review", findings=findings,
                         independent_reviewer_confirmed=True, gate_evidence=evidence)
        self.assertEqual(runtime.overall_state, "COMPLETE")

    def test_ungated_node_still_completes_without_findings(self):
        spec = ExecutionSpecV2(
            spec_id="ungated", compiler_version="0.2.10",
            raw_request="simple", objective="Do", success_definition=("done",),
            complexity_level="N1", complexity_score=1,
            capabilities=CapabilityRegistry().resolve(required=()),
            execution_nodes=(ExecutionNode("execute", "Execute", "executor"),),
        )
        runtime = RuntimeStateMachine(spec)
        runtime.start("execute")
        runtime.complete("execute")
        self.assertEqual(runtime.overall_state, "COMPLETE")


if __name__ == "__main__":
    unittest.main()
