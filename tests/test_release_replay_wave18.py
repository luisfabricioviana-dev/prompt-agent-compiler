"""Wave 18: release side-effect admission and replay avoidance."""
import tempfile
import unittest
from pathlib import Path
from contracts.bound_provenance import BoundProvenanceVerifier, sign_fixture
from contracts.durable_replay_ledger import DurableReplayLedger
from contracts.rea_release_node import ReleaseNode
from contracts.rea_pipeline import PipelineResult
from test_rea_release_node_v0210 import make_spec, pass_review, FakeSignedReleaseRunner

class ReleaseReplayTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.ledger=DurableReplayLedger(Path(tmp.name)/"replay.sqlite")
        self.statement=sign_fixture(key=b"k"*32,issuer="fixture",spec_id="spec-release",
                                    artifact_id="artifact-1",run_id="run-18",
                                    payload=b"payload",nonce="unique")
        self.kwargs=dict(spec=make_spec(),review=pass_review(),artifact_id="artifact-1",
                         payload=b"payload",enable_dispatch=True,release_approved=True,
                         provenance_verifier=lambda **k: True,
                         bound_verifier=BoundProvenanceVerifier(
                             trusted_issuer="fixture",verification_key=b"k"*32),
                         bound_statement=self.statement,run_id="run-18",
                         replay_ledger=self.ledger)
    def test_missing_ledger_never_invokes_runner(self):
        runner=FakeSignedReleaseRunner()
        result=ReleaseNode(signed_release_runner=runner).execute(
            **{**self.kwargs,"replay_ledger":None})
        self.assertEqual(result.reason,"durable_replay_ledger_required")
        self.assertFalse(runner.calls)
    def test_same_nonce_cannot_dispatch_twice(self):
        runner=FakeSignedReleaseRunner(PipelineResult("CONFIRMED_BY_OBSERVER","OK","abc"))
        node=ReleaseNode(signed_release_runner=runner)
        first=node.execute(**self.kwargs)
        second=node.execute(**self.kwargs)
        self.assertEqual(first.state,"CONFIRMED_BY_OBSERVER")
        self.assertEqual(second.state,"BLOCKED")
        self.assertEqual(len(runner.calls),1)
        self.assertEqual(self.ledger.state(issuer="fixture",nonce="unique"),"CONFIRMED")
    def test_exception_is_uncertain_and_not_retried(self):
        class CrashRunner:
            def __init__(self): self.calls=0
            def __call__(self,*a,**k):
                self.calls+=1
                raise RuntimeError("response lost after send")
        runner=CrashRunner()
        node=ReleaseNode(signed_release_runner=runner)
        first=node.execute(**self.kwargs)
        second=node.execute(**self.kwargs)
        self.assertEqual(first.state,"BLOCKED")
        self.assertEqual(second.state,"BLOCKED")
        self.assertEqual(runner.calls,1)
        self.assertEqual(self.ledger.state(issuer="fixture",nonce="unique"),"UNCERTAIN")
    def test_dry_run_does_not_reserve_nonce(self):
        runner=FakeSignedReleaseRunner()
        args={**self.kwargs,"enable_dispatch":False}
        result=ReleaseNode(signed_release_runner=runner).execute(**args)
        self.assertEqual(result.state,"DRY_RUN")
        self.assertIsNone(self.ledger.state(issuer="fixture",nonce="unique"))

if __name__=="__main__":
    unittest.main()
