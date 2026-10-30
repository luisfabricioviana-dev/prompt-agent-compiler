"""Adversarial scope, digest, and artifact binding regression for Wave 14."""
import hashlib
import unittest
from contracts.capability_registry import CapabilityRegistry
from contracts.execution_spec_v2 import ArtifactContract, ExecutionNode, ExecutionSpecV2
from contracts.gate_evidence import GateEvidence
from contracts.reviewer_spec import ReviewFinding
from contracts.runtime_state import RuntimeStateMachine, RuntimeStateError

def runtime():
    spec = ExecutionSpecV2(
        spec_id="gate-fixture", compiler_version="0.2.10",
        raw_request="test", objective="test", success_definition=("ok",),
        complexity_level="N1", complexity_score=1,
        capabilities=CapabilityRegistry().resolve(required=()),
        execution_nodes=(
            ExecutionNode("build", "build", "executor", output_artifacts=("a",)),
            ExecutionNode("verify", "verify", "verifier",
                          prerequisites=("build",), quality_gates=("G",)),
        ),
        artifacts=(ArtifactContract("a", "Binary", "build"),),
    )
    machine = RuntimeStateMachine(spec, run_id="run-1")
    machine.start("build")
    machine.complete("build", outputs={"a": b"good"})
    machine.start("verify")
    return machine

def proof(*, run="run-1", node="verify", gate="G", payload=b"evidence",
          artifact="a", digest=None):
    if digest is None:
        digest = hashlib.sha256(b"good").hexdigest()
    return GateEvidence(run, node, gate, payload, artifact, digest)

def complete(machine, row, *, finding_digest=None):
    digest = row.digest if finding_digest is None else finding_digest
    machine.complete("verify", findings=(ReviewFinding("G", True, (digest,)),),
                     gate_evidence=(row,))

class Wave14EvidenceTests(unittest.TestCase):
    def test_matching_bound_evidence_passes(self):
        machine = runtime()
        complete(machine, proof())
        self.assertEqual(machine.overall_state, "COMPLETE")

    def test_no_bound_evidence_fails_closed(self):
        machine = runtime()
        with self.assertRaisesRegex(RuntimeStateError, "runtime_gate_binding_required"):
            machine.complete("verify", findings=(ReviewFinding("G", True, ("text",)),))

    def test_cross_run_cross_node_cross_gate_rejected(self):
        for row in (proof(run="run-2"), proof(node="build"), proof(gate="H")):
            with self.subTest(row=row):
                with self.assertRaisesRegex(RuntimeStateError, "runtime_gate_binding_scope_mismatch"):
                    complete(runtime(), row)

    def test_wrong_artifact_digest_rejected(self):
        with self.assertRaisesRegex(RuntimeStateError, "runtime_gate_binding_artifact_mismatch"):
            complete(runtime(), proof(digest="0" * 64))

    def test_wrong_evidence_payload_digest_rejected(self):
        with self.assertRaisesRegex(RuntimeStateError, "runtime_gate_binding_digest_mismatch"):
            complete(runtime(), proof(), finding_digest="0" * 64)

    def test_unknown_artifact_rejected(self):
        with self.assertRaisesRegex(RuntimeStateError, "runtime_gate_binding_artifact_missing"):
            complete(runtime(), proof(artifact="unknown"))

if __name__ == "__main__":
    unittest.main()
