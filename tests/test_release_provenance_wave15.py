"""Wave 15: no release dispatch from mere structural validity or approval."""
import hashlib
import unittest
from contracts.rea_release_node import ReleaseNode, ReleaseAdmission
from contracts.rea_pipeline import PipelineResult
from test_rea_release_node_v0210 import make_spec, pass_review, FakeSignedReleaseRunner

PAYLOAD = b"artifact"
def admission(**overrides):
    values = dict(spec_id="spec-release", artifact_id="artifact-1",
                  artifact_sha256=hashlib.sha256(PAYLOAD).hexdigest(),
                  provenance_reference="trusted:fixture")
    values.update(overrides)
    return ReleaseAdmission(**values)

class ReleaseProvenanceTests(unittest.TestCase):
    def execute(self, *, verifier=None, admission_value=None, approved=True):
        runner = FakeSignedReleaseRunner()
        node = ReleaseNode(signed_release_runner=runner, provenance_verifier=verifier)
        result = node.execute(
            spec=make_spec(), review=pass_review(), artifact_id="artifact-1",
            payload=PAYLOAD, enable_dispatch=True, release_approved=approved,
            admission=admission_value)
        return result, runner

    def test_approval_alone_never_dispatches(self):
        result, runner = self.execute()
        self.assertEqual(result.reason, "release_provenance_admission_required")
        self.assertEqual(runner.calls, [])

    def test_unavailable_verifier_fails_closed(self):
        result, runner = self.execute(admission_value=admission())
        self.assertEqual(result.reason, "release_provenance_verifier_unavailable")
        self.assertEqual(runner.calls, [])

    def test_cross_artifact_or_cross_spec_or_digest_mismatch_fails(self):
        for altered in (dict(spec_id="different"),
                        dict(artifact_id="other"),
                        dict(artifact_sha256="0"*64)):
            with self.subTest(altered=altered):
                result, runner = self.execute(
                    verifier=lambda _: True, admission_value=admission(**altered))
                self.assertEqual(result.reason, "release_provenance_binding_mismatch")
                self.assertEqual(runner.calls, [])

    def test_negative_or_exception_verifier_fails_closed(self):
        for verifier, reason in (
            (lambda _: False, "release_provenance_not_verified"),
            (lambda _: (_ for _ in ()).throw(ValueError("bad")), "release_provenance_verification_failed"),
        ):
            result, runner = self.execute(verifier=verifier, admission_value=admission())
            self.assertEqual(result.reason, reason)
            self.assertEqual(runner.calls, [])

    def test_only_verified_and_approved_proceeds_to_signed_bridge(self):
        result, runner = self.execute(verifier=lambda _: True, admission_value=admission())
        self.assertEqual(result.state, "DRY_RUN")
        self.assertEqual(len(runner.calls), 1)

    def test_dry_run_remains_compatible_without_admission(self):
        runner = FakeSignedReleaseRunner()
        node = ReleaseNode(signed_release_runner=runner)
        result = node.execute(spec=make_spec(), review=pass_review(),
                              artifact_id="artifact-1", payload=PAYLOAD)
        self.assertEqual(result.state, "DRY_RUN")
        self.assertFalse(runner.calls[0][1]["enable_dispatch"])

if __name__ == "__main__":
    unittest.main()
