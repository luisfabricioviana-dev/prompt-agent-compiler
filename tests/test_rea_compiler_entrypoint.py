import sqlite3
import unittest
from compiler import run_optional_rea_release
from contracts.rea_pipeline import PipelineResult

class EntryPointTests(unittest.TestCase):
    def test_default_entrypoint_cannot_dispatch(self):
        calls=[]
        with sqlite3.connect(":memory:") as db:
            result=run_optional_rea_release(
                db,b"candidate",None,None,issuer="nobody",issuer_key=b"",
                destination_id="none",observer_id="none",observer_key=b"",
                dispatch=lambda *_: calls.append(True),
                observe=lambda *_: calls.append("observed"))
        self.assertIsInstance(result,PipelineResult)
        self.assertEqual(result.state,"BLOCKED")
        self.assertEqual(result.reason,"artifact_evidence_missing")
        self.assertEqual(calls,[])

    def test_github_wrapper_preserves_default_no_dispatch(self):
        from compiler import run_optional_rea_github_release
        calls = []
        with sqlite3.connect(":memory:") as db:
            result = run_optional_rea_github_release(
                db, b"candidate", None, None, issuer="nobody", issuer_key=b"",
                destination_id="owner/repo", github_token="",
                observer_id="observer", observer_key=b"",
                dispatch=lambda *_: calls.append("dispatch"),
                observe=lambda *_: calls.append("observe"),
                github_opener=lambda *_ , **__: calls.append("network"))
        self.assertEqual(result.state, "BLOCKED")
        self.assertEqual(result.reason, "artifact_evidence_missing")
        self.assertEqual(calls, [])

    def test_enabled_github_release_requires_pinned_repository_id(self):
        from compiler import run_optional_rea_github_release
        calls = []
        with sqlite3.connect(":memory:") as db:
            result = run_optional_rea_github_release(
                db, b"candidate", None, None, issuer="owner", issuer_key=b"",
                destination_id="owner/repo", github_token="fixture",
                observer_id="observer", observer_key=b"",
                dispatch=lambda *_: calls.append("dispatch"),
                observe=lambda *_: calls.append("observe"),
                github_opener=lambda *_args, **_kwargs: calls.append("network"),
                enable_dispatch=True)
        self.assertEqual(result.state, "BLOCKED")
        self.assertEqual(result.reason, "trusted_repository_id_required")
        self.assertEqual(calls, [])

    def test_role_preflight_denies_read_only_before_claim_or_dispatch(self):
        import hashlib
        import hmac
        import json
        from compiler import run_optional_rea_github_release
        from contracts.rea_release_authority import ReleaseAuthorization
        from contracts.rea_security_gate import ArtifactEvidence

        payload = b"safe fixture"
        sha = hashlib.sha256(payload).hexdigest()
        destination = "owner/destination"
        release = "release-unique-101"
        key = b"issuer-key-for-test-only-1234567890"
        message = f"REA-RELEASE-DEST-v2\\nissuer\\n{release}\\n{sha}\\n{destination}".replace("\\n", "\n").encode()
        auth = ReleaseAuthorization(sha, release, "issuer",
            hmac.new(key, message, hashlib.sha256).hexdigest())
        evidence = ArtifactEvidence(True, False, False, True, sha)
        calls = []
        class Response:
            def __init__(self, data): self.data = json.dumps(data).encode()
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self, limit): return self.data[:limit]
        def opener(request, timeout):
            calls.append(request.full_url)
            url = request.full_url
            if url.endswith("/user"): return Response({"login": "tester"})
            if "/collaborators/" in url: return Response({"permission": "read"})
            return Response({"full_name": destination, "id": 42})
        with sqlite3.connect(":memory:") as db:
            outcome = run_optional_rea_github_release(
                db, payload, evidence, auth, issuer="issuer", issuer_key=key,
                destination_id=destination, github_token="fixture-token",
                observer_id="observer-01", observer_key=b"observer-test-key-12345678901234567890",
                dispatch=lambda *_: calls.append("DISPATCH"),
                observe=lambda *_: calls.append("OBSERVE"),
                enable_dispatch=True, github_opener=opener, expected_repository_id=42)
            self.assertEqual(outcome.state, "BLOCKED")
            self.assertEqual(outcome.reason, "trusted_destination_resolution_failed")
            self.assertNotIn("DISPATCH", calls)
            self.assertIsNone(db.execute(
                "SELECT name FROM sqlite_master WHERE name='rea_release_claims'").fetchone())

if __name__ == "__main__":
    unittest.main()
