"""Wave75: harden GitHub artifact redirect and API inventory handling."""
import unittest
from urllib.error import URLError
from urllib.request import Request
from tools.audit_remote_release_archive import SafeArtifactRedirect, audit_remote_archive


class RedirectHardeningTests(unittest.TestCase):
    def test_https_redirect_never_propagates_bearer(self):
        request = Request("https://api.github.com/repos/a/b/actions/artifacts/1/zip",
                          headers={"Authorization": "Bearer secret", "Cookie": "private"})
        moved = SafeArtifactRedirect().redirect_request(
            request, None, 302, "Found", {},
            "https://objects.githubusercontent.com/archive.zip")
        self.assertIsNotNone(moved)
        self.assertFalse(any(k.lower() in {"authorization", "cookie"} for k in moved.headers))

    def test_http_redirect_is_rejected(self):
        request = Request("https://api.github.com/archive")
        with self.assertRaises(URLError):
            SafeArtifactRedirect().redirect_request(
                request, None, 302, "Found", {}, "http://example.org/archive.zip")

    def test_malformed_commit_is_rejected_before_http(self):
        for sha in ("A" * 40, "a" * 39, "not-a-sha"):
            result = audit_remote_archive(run_id="123", commit_sha=sha, attempt="1", token="t")
            self.assertEqual(result["status"], "BLOCK")

    def test_invalid_attempt_is_rejected_before_http(self):
        result = audit_remote_archive(run_id="123", commit_sha="a" * 40,
                                      attempt="one", token="t")
        self.assertEqual(result["status"], "BLOCK")


if __name__ == "__main__":
    unittest.main()
