import hashlib
import unittest

from contracts.artifact_registry import (
    ArtifactRegistry,
    ArtifactRegistryError,
)
from contracts.capability_registry import (
    CapabilityRegistry,
    CapabilitySpec,
    CapabilityStatus,
)
from contracts.execution_spec_v2 import (
    ArtifactContract,
    ExecutionNode,
    ExecutionSpecV2,
)
from contracts.runtime_state import (
    NodeState,
    RuntimeStateError,
    RuntimeStateMachine,
)


def make_spec(*, capability_status=CapabilityStatus.AVAILABLE):
    registry = CapabilityRegistry(
        (CapabilitySpec("files.read", capability_status),)
    )
    resolution = registry.resolve(required=("files.read",))
    return ExecutionSpecV2(
        spec_id="runtime-state-spec",
        compiler_version="0.2.10",
        raw_request="execute",
        objective="Execute and verify.",
        success_definition=("all nodes pass",),
        complexity_level="N2",
        complexity_score=6,
        capabilities=resolution,
        execution_nodes=(
            ExecutionNode(
                node_id="build",
                purpose="Build artifact",
                role="builder",
                required_capabilities=("files.read",),
                output_artifacts=("artifact-1",),
            ),
            ExecutionNode(
                node_id="verify",
                purpose="Verify artifact",
                role="verifier",
                prerequisites=("build",),
            ),
        ),
        artifacts=(
            ArtifactContract(
                artifact_id="artifact-1",
                artifact_type="BinaryArtifact",
                producer_node="build",
            ),
        ),
    )


class ArtifactRegistryTests(unittest.TestCase):
    def setUp(self):
        self.spec = make_spec()
        self.registry = ArtifactRegistry(self.spec.artifacts)

    def test_register_bytes_records_digest_size_and_producer(self):
        record = self.registry.register_bytes(
            "artifact-1",
            b"payload",
            producer_node="build",
        )

        self.assertEqual(
            record.sha256,
            hashlib.sha256(b"payload").hexdigest(),
        )
        self.assertEqual(record.byte_size, 7)
        self.assertEqual(record.producer_node, "build")
        self.assertEqual(record.state, "VALID")

    def test_same_bytes_are_idempotent(self):
        first = self.registry.register_bytes(
            "artifact-1",
            b"payload",
            producer_node="build",
        )
        second = self.registry.register_bytes(
            "artifact-1",
            b"payload",
            producer_node="build",
        )

        self.assertEqual(first, second)
        self.assertEqual(self.registry.sequence, 1)

    def test_conflicting_rewrite_fails_closed(self):
        self.registry.register_bytes(
            "artifact-1",
            b"payload-a",
            producer_node="build",
        )

        with self.assertRaisesRegex(
            ArtifactRegistryError,
            "artifact_digest_conflict:artifact-1",
        ):
            self.registry.register_bytes(
                "artifact-1",
                b"payload-b",
                producer_node="build",
            )

    def test_undeclared_artifact_is_rejected(self):
        with self.assertRaisesRegex(
            ArtifactRegistryError,
            "artifact_contract_missing:unknown",
        ):
            self.registry.register_bytes(
                "unknown",
                b"x",
                producer_node="build",
            )

    def test_wrong_producer_is_rejected(self):
        with self.assertRaisesRegex(
            ArtifactRegistryError,
            "artifact_producer_mismatch:artifact-1",
        ):
            self.registry.register_bytes(
                "artifact-1",
                b"x",
                producer_node="verify",
            )

    def test_record_node_outputs_requires_every_declared_output(self):
        node = self.spec.execution_nodes[0]
        with self.assertRaisesRegex(
            ArtifactRegistryError,
            "artifact_output_missing:artifact-1",
        ):
            self.registry.record_node_outputs(node, {})


class RuntimeStateMachineTests(unittest.TestCase):
    def setUp(self):
        self.spec = make_spec()
        self.artifacts = ArtifactRegistry(self.spec.artifacts)
        self.runtime = RuntimeStateMachine(
            self.spec,
            artifact_registry=self.artifacts,
        )

    def test_initial_state_marks_only_roots_ready(self):
        self.assertEqual(self.runtime.node_state("build"), NodeState.READY)
        self.assertEqual(self.runtime.node_state("verify"), NodeState.PENDING)
        self.assertEqual(self.runtime.overall_state, "READY")

    def test_dependency_cannot_start_early(self):
        with self.assertRaisesRegex(
            RuntimeStateError,
            "node_not_ready:verify",
        ):
            self.runtime.start("verify")

    def test_complete_node_records_outputs_then_promotes_dependents(self):
        self.runtime.start("build")
        self.runtime.complete(
            "build",
            outputs={"artifact-1": b"payload"},
        )

        self.assertEqual(self.runtime.node_state("build"), NodeState.PASS)
        self.assertEqual(self.runtime.node_state("verify"), NodeState.READY)
        self.assertEqual(
            self.artifacts.get("artifact-1").state,
            "VALID",
        )

    def test_complete_node_with_missing_required_output_is_rejected(self):
        self.runtime.start("build")

        with self.assertRaisesRegex(
            ArtifactRegistryError,
            "artifact_output_missing:artifact-1",
        ):
            self.runtime.complete("build", outputs={})

        self.assertEqual(self.runtime.node_state("build"), NodeState.RUNNING)

    def test_failure_blocks_all_downstream_nodes(self):
        self.runtime.start("build")
        self.runtime.fail("build", reason="implementation_failure")

        self.assertEqual(self.runtime.node_state("build"), NodeState.FAIL)
        self.assertEqual(self.runtime.node_state("verify"), NodeState.BLOCKED)
        self.assertEqual(self.runtime.overall_state, "FAILED")
        self.assertEqual(
            self.runtime.failure_reason("build"),
            "implementation_failure",
        )

    def test_all_nodes_pass_produces_complete_state(self):
        self.runtime.start("build")
        self.runtime.complete(
            "build",
            outputs={"artifact-1": b"payload"},
        )
        self.runtime.start("verify")
        self.runtime.complete("verify")

        self.assertEqual(self.runtime.overall_state, "COMPLETE")

    def test_non_ready_execution_spec_cannot_enter_runtime(self):
        spec = make_spec(capability_status=CapabilityStatus.UNKNOWN)

        with self.assertRaisesRegex(
            RuntimeStateError,
            "execution_spec_not_ready:UNKNOWN_CAPABILITY",
        ):
            RuntimeStateMachine(
                spec,
                artifact_registry=ArtifactRegistry(spec.artifacts),
            )


if __name__ == "__main__":
    unittest.main()
