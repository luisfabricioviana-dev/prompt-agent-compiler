import io
import json
import unittest
from contracts.rea_github_destination import resolve_github_destination

class Response:
    def __init__(self, data): self.data = data
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self, limit): return self.data[:limit]

class GithubDestinationTests(unittest.TestCase):
    def test_matching_authenticated_repository_metadata(self):
        observed = []
        def opener(req, timeout):
            observed.append((req.full_url, req.get_header("Authorization"), timeout))
            return Response(json.dumps({"full_name": "owner/destination"}).encode())
        actual = resolve_github_destination("owner/destination", token="fixture-key", opener=opener)
        self.assertEqual(actual, "owner/destination")
        self.assertEqual(observed, [("https://api.github.com/repos/owner/destination", "Bearer fixture-key", 10)])

    def test_mismatched_repository_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "github_identity_mismatch"):
            resolve_github_destination("owner/destination", token="fixture-key",
                opener=lambda *_ , **__: Response(b'{"full_name":"other/destination"}'))

    def test_immutable_repository_id_pin(self):
        def response(repository_id):
            return lambda *_args, **_kwargs: Response(
                json.dumps({"full_name": "owner/destination", "id": repository_id}).encode())
        actual = resolve_github_destination(
            "owner/destination", token="fixture-key", opener=response(42),
            expected_repository_id=42)
        self.assertEqual(actual, "owner/destination")
        with self.assertRaisesRegex(ValueError, "github_repository_id_mismatch"):
            resolve_github_destination(
                "owner/destination", token="fixture-key", opener=response(43),
                expected_repository_id=42)
        with self.assertRaisesRegex(ValueError, "expected_repository_id_invalid"):
            resolve_github_destination(
                "owner/destination", token="fixture-key", expected_repository_id=True)

    def test_missing_credentials_invalid_path_and_bad_metadata(self):
        with self.assertRaisesRegex(ValueError, "github_token_missing"):
            resolve_github_destination("owner/destination", token="")
        with self.assertRaisesRegex(ValueError, "invalid_repository"):
            resolve_github_destination("https://other.example", token="fixture-key")
        with self.assertRaisesRegex(ValueError, "metadata_invalid"):
            resolve_github_destination("owner/destination", token="fixture-key",
                opener=lambda *_ , **__: Response(b"not-json"))
        with self.assertRaisesRegex(ValueError, "github_identity_unverified"):
            resolve_github_destination("owner/destination", token="fixture-key",
                opener=lambda *_ , **__: Response(b'{}'))

if __name__ == "__main__":
    unittest.main()
