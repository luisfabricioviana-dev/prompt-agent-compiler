"""Wave 16: context-bound HMAC, substitution and replay-boundary tests."""
import unittest
import tempfile
from pathlib import Path
from contracts.durable_replay_ledger import DurableReplayLedger
from contracts.bound_provenance import BoundProvenanceVerifier, sign_fixture
from contracts.rea_release_node import ReleaseNode
from test_rea_release_node_v0210 import FakeSignedReleaseRunner, make_spec, pass_review

KEY=b"k"*32
def fixture(payload=b"artifact"):
    statement=sign_fixture(key=KEY, issuer="fixture-issuer", spec_id="spec-release",
                         artifact_id="artifact-1", run_id="run-1", payload=payload,nonce="n-1")
    verifier=BoundProvenanceVerifier(trusted_issuer="fixture-issuer",verification_key=KEY)
    return statement,verifier

def dispatch(**overrides):
    statement,verifier=fixture()
    args=dict(spec=make_spec(),review=pass_review(),artifact_id="artifact-1",
              payload=b"artifact",enable_dispatch=True,release_approved=True,
              provenance_verifier=lambda **kwargs: True,
              bound_statement=statement,bound_verifier=verifier,run_id="run-1")
    args.update(overrides)
    with tempfile.TemporaryDirectory() as tmp:
        args.setdefault('replay_ledger', DurableReplayLedger(Path(tmp)/'ledger.sqlite'))
        runner=FakeSignedReleaseRunner()
        result=ReleaseNode(signed_release_runner=runner).execute(**args)
    return result,runner

# end dispatch


class SignedContextTests(unittest.TestCase):
    def test_fixture_signature_allows_delegate_only(self):
        result,runner=dispatch()
        self.assertEqual(result.state,"DRY_RUN")
        self.assertEqual(len(runner.calls),1)

    def test_true_callback_without_bound_signature_blocks(self):
        result,runner=dispatch(bound_statement=None)
        self.assertEqual(result.reason,"bound_provenance_required")
        self.assertEqual(runner.calls,[])

    def test_wrong_run_blocks_replay(self):
        result,runner=dispatch(run_id="run-other")
        self.assertEqual(result.reason,"bound_provenance_invalid")
        self.assertFalse(runner.calls)

    def test_wrong_artifact_or_payload_blocks(self):
        for change in (dict(payload=b"tampered"),dict(artifact_id="other")):
            with self.subTest(change=change):
                result,runner=dispatch(**change)
                self.assertEqual(result.state,"BLOCKED")
                self.assertFalse(runner.calls)

    def test_wrong_signing_key_blocks(self):
        statement,_=fixture()
        wrong=BoundProvenanceVerifier(trusted_issuer="fixture-issuer",verification_key=b"z"*32)
        result,runner=dispatch(bound_statement=statement,bound_verifier=wrong)
        self.assertEqual(result.reason,"bound_provenance_invalid")
        self.assertFalse(runner.calls)

    def test_wrong_issuer_blocks(self):
        wrong=BoundProvenanceVerifier(trusted_issuer="other",verification_key=KEY)
        result,runner=dispatch(bound_verifier=wrong)
        self.assertEqual(result.reason,"bound_provenance_invalid")
        self.assertFalse(runner.calls)

if __name__=="__main__":
    unittest.main()
