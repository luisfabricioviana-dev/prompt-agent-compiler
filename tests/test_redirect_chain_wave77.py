"""Wave77 successive redirect credential isolation and authority restrictions."""
import unittest
from urllib.error import URLError
from urllib.request import Request
from tools.audit_remote_release_archive import SafeArtifactRedirect

class RedirectChainTests(unittest.TestCase):
    def test_two_https_redirects_do_not_restore_credentials(self):
        original = Request("https://api.github.com/artifact",
                           headers={"Authorization":"Bearer SECRET", "Cookie":"sensitive"})
        original.add_unredirected_header("Proxy-Authorization", "Bearer PROXY")
        handler = SafeArtifactRedirect()
        first = handler.redirect_request(original, None, 302, "Found", {},
                                         "https://objects.githubusercontent.com/one")
        second = handler.redirect_request(first, None, 302, "Found", {},
                                          "https://objects.githubusercontent.com/two")
        for request in (first, second):
            fields = {key.lower() for key in request.headers}
            fields.update(key.lower() for key in request.unredirected_hdrs)
            self.assertFalse(fields & {"authorization", "cookie", "proxy-authorization"})
            self.assertEqual(request.get_method(), "GET")

    def test_reject_nonstandard_port(self):
        request = Request("https://api.github.com/artifact")
        with self.assertRaises(URLError):
            SafeArtifactRedirect().redirect_request(
                request, None, 302, "Found", {}, "https://objects.example:444/zip")

    def test_reject_userinfo_in_redirect(self):
        request = Request("https://api.github.com/artifact")
        with self.assertRaises(URLError):
            SafeArtifactRedirect().redirect_request(
                request, None, 302, "Found", {}, "https://alice:secret@objects.example/zip")

    def test_reject_http_in_later_redirect(self):
        handler = SafeArtifactRedirect()
        first = handler.redirect_request(Request("https://api.github.com/artifact"),
                                         None, 302, "Found", {}, "https://objects.example/one")
        with self.assertRaises(URLError):
            handler.redirect_request(first, None, 302, "Found", {}, "http://objects.example/two")

if __name__ == "__main__":
    unittest.main()
