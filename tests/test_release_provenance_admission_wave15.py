"""Wave 15: no dispatch on structure-only evidence or self-asserted approval."""
import unittest
from contracts.rea_release_node import ReleaseNode
from contracts.rea_pipeline import PipelineResult
from test_rea_release_node_v0210 import FakeSignedReleaseRunner, make_spec, pass_review
from contracts.bound_provenance import BoundProvenanceVerifier, sign_fixture

class AdmissionTests(unittest.TestCase):
    def kwargs(self):
        key = b"k" * 32
        return dict(spec=make_spec(),review=pass_review(),artifact_id="artifact-1",
                    payload=b"artifact",enable_dispatch=True,release_approved=True,
                    bound_verifier=BoundProvenanceVerifier(trusted_issuer="fixture", verification_key=key),
                    bound_statement=sign_fixture(key=key, issuer="fixture", spec_id="spec-release", artifact_id="artifact-1", run_id="run-1", payload=b"artifact", nonce="nonce"),
                    run_id="run-1")
    def test_unverified_provenance_cannot_dispatch(self):
        runner=FakeSignedReleaseRunner()
        result=ReleaseNode(signed_release_runner=runner).execute(**self.kwargs())
        self.assertEqual(result.reason,"provenance_verifier_required")
        self.assertFalse(runner.calls)
    def test_claimed_true_without_verifier_cannot_dispatch(self):
        runner=FakeSignedReleaseRunner()
        result=ReleaseNode(signed_release_runner=runner).execute(
            **self.kwargs(),provenance_verified=True)
        self.assertEqual(result.state,"BLOCKED")
        self.assertFalse(runner.calls)
    def test_verifier_denial_blocks(self):
        runner=FakeSignedReleaseRunner()
        result=ReleaseNode(signed_release_runner=runner).execute(
            **self.kwargs(),provenance_verifier=lambda **k: False)
        self.assertEqual(result.reason,"provenance_not_verified")
        self.assertFalse(runner.calls)
    def test_verifier_failure_blocks(self):
        runner=FakeSignedReleaseRunner()
        def fail(**kwargs): raise RuntimeError("verifier unavailable")
        result=ReleaseNode(signed_release_runner=runner).execute(
            **self.kwargs(),provenance_verifier=fail)
        self.assertEqual(result.reason,"provenance_verification_failed")
        self.assertFalse(runner.calls)
    def test_exact_binding_reaches_verifier(self):
        runner=FakeSignedReleaseRunner()
        observed=[]
        def verify(*, spec_id, artifact_id, digest, statement, authorization):
            observed.append((spec_id,artifact_id,digest,statement,authorization))
            return True
        result=ReleaseNode(signed_release_runner=runner).execute(
            **self.kwargs(),provenance_verifier=verify)
        self.assertEqual(result.state,"DRY_RUN")
        self.assertEqual(observed[0][0:2],("spec-release","artifact-1"))
        self.assertEqual(len(observed[0][2]),64)
        self.assertEqual(len(runner.calls),1)
    def test_dry_run_still_works_without_external_verifier(self):
        runner=FakeSignedReleaseRunner()
        kwargs=self.kwargs()
        kwargs["enable_dispatch"]=False
        result=ReleaseNode(signed_release_runner=runner).execute(**kwargs)
        self.assertEqual(result.state,"DRY_RUN")
