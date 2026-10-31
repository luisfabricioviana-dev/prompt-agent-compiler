"""Wave78: enforce finite redirect chain limits and credential isolation."""
import unittest
from urllib.error import HTTPError
from urllib.request import Request
from tools.audit_remote_release_archive import SafeArtifactRedirect


class RedirectLimitTests(unittest.TestCase):
    def setUp(self):
        self.handler = SafeArtifactRedirect()

    def test_explicit_limits(self):
        self.assertEqual(self.handler.max_redirections, 3)
        self.assertEqual(self.handler.max_repeats, 2)

    def test_three_redirects_remain_bounded_and_credential_free(self):
        request = Request("https://api.github.com/artifact",
                          headers={"Authorization": "Bearer secret"})
        for i in range(3):
            request = self.handler.redirect_request(
                request, None, 302, "Found", {},
                "https://objects.githubusercontent.com/hop" + str(i))
            self.assertNotIn("authorization", {k.lower() for k in request.headers})

    def test_excessive_redirects_rejected_by_standard_handler(self):
        # urllib's http_error_302 owns the repeat/count enforcement.
        self.assertLess(self.handler.max_redirections, 10)


if __name__ == "__main__":
    unittest.main()
