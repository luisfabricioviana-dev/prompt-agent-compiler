import json
import unittest
from contracts.rea_github_role_preflight import check_github_actor_repository_role

class Response:
    def __init__(self, data): self.data = json.dumps(data).encode()
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self, limit): return self.data[:limit]

class GitHubRolePreflightTests(unittest.TestCase):
    def test_authenticated_actor_write_role(self):
        urls = []
        def opener(request, timeout):
            urls.append(request.full_url)
            return Response({"login": "test-user"} if request.full_url.endswith("/user")
                            else {"permission": "write"})
        self.assertEqual(check_github_actor_repository_role(
            "owner/repo", token="test-token", opener=opener), "write")
        self.assertEqual(urls, ["https://api.github.com/user",
            "https://api.github.com/repos/owner/repo/collaborators/test-user/permission"])

    def test_read_only_and_unknown_roles_rejected(self):
        for role in ("read", "none", None):
            def opener(request, timeout):
                return Response({"login":"test-user"} if request.full_url.endswith("/user")
                                else {"permission":role})
            with self.assertRaisesRegex(ValueError, "actor_write_role_unverified"):
                check_github_actor_repository_role("owner/repo", token="test-token", opener=opener)

    def test_invalid_actor_and_credentials_rejected(self):
        with self.assertRaisesRegex(ValueError, "github_token_missing"):
            check_github_actor_repository_role("owner/repo", token="")
        with self.assertRaisesRegex(ValueError, "actor_identity_unverified"):
            check_github_actor_repository_role("owner/repo", token="test-token",
                opener=lambda *args, **kwargs: Response({}))
if __name__ == "__main__":
    unittest.main()
