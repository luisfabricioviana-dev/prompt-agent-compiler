"""Wave 12: externally injected artifact registries must match the execution spec."""
from dataclasses import replace
import unittest

from contracts.artifact_registry import ArtifactRegistry
from contracts.capability_registry import CapabilityRegistry
from contracts.execution_spec_v2 import ArtifactContract, ExecutionNode, ExecutionSpecV2
from contracts.runtime_state import RuntimeStateError, RuntimeStateMachine


def spec_with_artifact():
    return ExecutionSpecV2(
        spec_id="binding-test",
        compiler_version="0.2.10",
        raw_request="test",
        objective="Prove artifact-contract binding.",
        success_definition=("result verified",),
        complexity_level="N1",
        complexity_score=1,
        capabilities=CapabilityRegistry().resolve(required=()),
        execution_nodes=(
            ExecutionNode(node_id="build", purpose="Build", role="executor",
                          output_artifacts=("result",)),
        ),
        artifacts=(
            ArtifactContract("result", "ExpectedType", "build",
                             required_fields=("verified",)),
        ),
    )


class ArtifactContractBindingTests(unittest.TestCase):
    def test_default_registry_accepts_matching_contract(self):
        spec = spec_with_artifact()
        runtime = RuntimeStateMachine(spec)
        runtime.start("build")
        runtime.complete("build", outputs={"result": b"content"})
        self.assertEqual(runtime.overall_state, "COMPLETE")

    def test_explicit_matching_registry_is_accepted(self):
        spec = spec_with_artifact()
        runtime = RuntimeStateMachine(spec, artifact_registry=ArtifactRegistry(spec.artifacts))
        self.assertEqual(runtime.overall_state, "READY")

    def test_different_artifact_type_is_rejected_before_execution(self):
        spec = spec_with_artifact()
        incompatible = replace(spec.artifacts[0], artifact_type="WrongType")
        with self.assertRaisesRegex(RuntimeStateError, "artifact_registry_contract_mismatch"):
            RuntimeStateMachine(spec, artifact_registry=ArtifactRegistry((incompatible,)))

    def test_different_required_fields_are_rejected(self):
        spec = spec_with_artifact()
        incompatible = replace(spec.artifacts[0], required_fields=())
        with self.assertRaisesRegex(RuntimeStateError, "artifact_registry_contract_mismatch"):
            RuntimeStateMachine(spec, artifact_registry=ArtifactRegistry((incompatible,)))

    def test_missing_or_extra_contract_is_rejected(self):
        spec = spec_with_artifact()
        extra = ArtifactContract("extra", "ExtraType", "build")
        for contracts in ((), (*spec.artifacts, extra)):
            with self.subTest(contracts=contracts):
                with self.assertRaisesRegex(RuntimeStateError, "artifact_registry_contract_mismatch"):
                    RuntimeStateMachine(spec, artifact_registry=ArtifactRegistry(contracts))


if __name__ == "__main__":
    unittest.main()
