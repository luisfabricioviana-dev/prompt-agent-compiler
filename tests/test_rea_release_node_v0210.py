import unittest

from contracts.capability_registry import (
    CapabilityRegistry,
    CapabilitySpec,
    CapabilityStatus,
)
from contracts.execution_spec_v2 import ArtifactContract, ExecutionNode, ExecutionSpecV2
from contracts.rea_release_node import ReleaseNode
from contracts.reviewer_spec import ReviewResult
from contracts.rea_pipeline import PipelineResult


class FakeSignedReleaseRunner:
    def __init__(self, result=None):
        self.calls = []
        self.result = result or PipelineResult(
            "DRY_RUN", "artifact_checked_dispatch_disabled", "abc"
        )

    def __call__(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return self.result


def pass_review():
    return ReviewResult(
        state="PASS",
        failed_gates=(),
        reasons=(),
        required_repairs=(),
        reverification_scope=(),
    )


def make_spec(*, release_status=CapabilityStatus.AVAILABLE, include_release=True):
    specs = [CapabilitySpec("files.read", CapabilityStatus.AVAILABLE)]
    required = ["files.read"]
    if include_release:
        specs.append(CapabilitySpec("rea.release", release_status))
        required.append("rea.release")
    registry = CapabilityRegistry(specs)
    resolution = registry.resolve(required=required)
    return ExecutionSpecV2(
        spec_id="spec-release",
        compiler_version="0.2.10",
        raw_request="release artifact",
        objective="Release an approved artifact.",
        success_definition=("release state recorded",),
        complexity_level="N4",
        complexity_score=15,
        capabilities=resolution,
        execution_nodes=(
            ExecutionNode(
                node_id="build",
                purpose="Build artifact",
                role="builder",
                required_capabilities=("files.read",),
                output_artifacts=("artifact-1",),
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


class ReleaseNodeTests(unittest.TestCase):
    def test_default_release_is_dry_run_delegate(self):
        runner = FakeSignedReleaseRunner()
        node = ReleaseNode(signed_release_runner=runner)

        result = node.execute(
            spec=make_spec(),
            review=pass_review(),
            artifact_id="artifact-1",
            payload=b"artifact",
            rea_kwargs={"destination_id": "repo:example"},
        )

        self.assertEqual(result.state, "DRY_RUN")
        self.assertEqual(len(runner.calls), 1)
        _, kwargs = runner.calls[0]
        self.assertFalse(kwargs["enable_dispatch"])

    def test_non_ready_execution_spec_blocks_before_rea(self):
        runner = FakeSignedReleaseRunner()
        node = ReleaseNode(signed_release_runner=runner)

        result = node.execute(
            spec=make_spec(release_status=CapabilityStatus.UNKNOWN),
            review=pass_review(),
            artifact_id="artifact-1",
            payload=b"artifact",
        )

        self.assertEqual(result.state, "BLOCKED")
        self.assertIn("execution_spec_not_ready:UNKNOWN_CAPABILITY", result.reason)
        self.assertEqual(runner.calls, [])

    def test_failed_review_blocks_before_rea(self):
        runner = FakeSignedReleaseRunner()
        node = ReleaseNode(signed_release_runner=runner)
        review = ReviewResult(
            state="FAIL",
            failed_gates=("REGRESSION_GATE",),
            reasons=("gate_failed:REGRESSION_GATE",),
            required_repairs=("repair_gate:REGRESSION_GATE",),
            reverification_scope=("reverify_gate:REGRESSION_GATE",),
        )

        result = node.execute(
            spec=make_spec(),
            review=review,
            artifact_id="artifact-1",
            payload=b"artifact",
        )

        self.assertEqual(result.state, "BLOCKED")
        self.assertEqual(result.reason, "review_not_passed")
        self.assertEqual(runner.calls, [])

    def test_release_capability_must_be_required(self):
        runner = FakeSignedReleaseRunner()
        node = ReleaseNode(signed_release_runner=runner)

        result = node.execute(
            spec=make_spec(include_release=False),
            review=pass_review(),
            artifact_id="artifact-1",
            payload=b"artifact",
        )

        self.assertEqual(result.state, "BLOCKED")
        self.assertEqual(result.reason, "release_capability_not_required")
        self.assertEqual(runner.calls, [])

    def test_unknown_artifact_blocks_before_rea(self):
        runner = FakeSignedReleaseRunner()
        node = ReleaseNode(signed_release_runner=runner)

        result = node.execute(
            spec=make_spec(),
            review=pass_review(),
            artifact_id="missing",
            payload=b"artifact",
        )

        self.assertEqual(result.state, "BLOCKED")
        self.assertEqual(result.reason, "artifact_not_in_execution_spec")
        self.assertEqual(runner.calls, [])

    def test_empty_payload_blocks_before_rea(self):
        runner = FakeSignedReleaseRunner()
        node = ReleaseNode(signed_release_runner=runner)

        result = node.execute(
            spec=make_spec(),
            review=pass_review(),
            artifact_id="artifact-1",
            payload=b"",
        )

        self.assertEqual(result.state, "BLOCKED")
        self.assertEqual(result.reason, "release_payload_unavailable")
        self.assertEqual(runner.calls, [])

    def test_dispatch_requires_explicit_release_approval(self):
        runner = FakeSignedReleaseRunner()
        node = ReleaseNode(signed_release_runner=runner)

        result = node.execute(
            spec=make_spec(),
            review=pass_review(),
            artifact_id="artifact-1",
            payload=b"artifact",
            enable_dispatch=True,
            release_approved=False,
        )

        self.assertEqual(result.state, "BLOCKED")
        self.assertEqual(result.reason, "explicit_release_approval_required")
        self.assertEqual(runner.calls, [])

    def test_explicit_dispatch_passes_enable_flag_only_after_approval(self):
        runner = FakeSignedReleaseRunner(
            PipelineResult("CONFIRMED_BY_OBSERVER", "DELIVERY_CONFIRMED", "abc")
        )
        node = ReleaseNode(signed_release_runner=runner)

        result = node.execute(
            spec=make_spec(),
            review=pass_review(),
            artifact_id="artifact-1",
            payload=b"artifact",
            enable_dispatch=True,
            release_approved=True,
            provenance_verifier=lambda **kwargs: True,
            rea_kwargs={"destination_id": "repo:example"},
        )

        self.assertEqual(result.state, "CONFIRMED_BY_OBSERVER")
        self.assertEqual(len(runner.calls), 1)
        _, kwargs = runner.calls[0]
        self.assertTrue(kwargs["enable_dispatch"])

    def test_rea_exception_fails_closed(self):
        class FailingRunner:
            def __call__(self, *args, **kwargs):
                raise RuntimeError("downstream")

        node = ReleaseNode(signed_release_runner=FailingRunner())
        result = node.execute(
            spec=make_spec(),
            review=pass_review(),
            artifact_id="artifact-1",
            payload=b"artifact",
        )

        self.assertEqual(result.state, "BLOCKED")
        self.assertEqual(result.reason, "rea_release_runner_failed")


if __name__ == "__main__":
    unittest.main()
