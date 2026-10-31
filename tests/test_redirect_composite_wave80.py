"""Wave80: composite urllib redirect behavior with synthetic HTTP responses."""
import io
import unittest
from urllib.error import HTTPError, URLError
from urllib.request import Request
from tools.audit_remote_release_archive import SafeArtifactRedirect


class RedirectResponse(io.BytesIO):
    pass


class CompositeRedirectTests(unittest.TestCase):
    def setUp(self):
        self.handler = SafeArtifactRedirect()
        self.opened = []

        def open_stub(request, timeout=0):
            self.opened.append(request)
            return RedirectResponse(b"")
        self.handler.parent = type("Parent", (), {"open": staticmethod(open_stub)})()

    def hop(self, request, url, code=302):
        request.timeout = 10
        fp = RedirectResponse(b"")
        return self.handler.http_error_302(
            request, fp, code, "Found", {"location": url})

    def test_mixed_redirect_statuses_preserve_credential_isolation(self):
        current = Request("https://api.github.com/archive",
                          headers={"Authorization": "Bearer sensitive", "Cookie": "private"})
        for index, code in enumerate((302, 303, 307)):
            self.hop(current, "https://objects.githubusercontent.com/hop" + str(index), code)
            current = self.opened[-1]
            keys = {key.lower() for key in current.headers}
            keys.update(key.lower() for key in current.unredirected_hdrs)
            self.assertFalse(keys & {"authorization", "cookie", "proxy-authorization"})
            self.assertEqual(current.get_method(), "GET")

    def test_fourth_mixed_redirect_fails_closed(self):
        current = Request("https://api.github.com/archive")
        for index, code in enumerate((302, 303, 307)):
            self.hop(current, "https://objects.githubusercontent.com/hop" + str(index), code)
            current = self.opened[-1]
        with self.assertRaises(HTTPError):
            self.hop(current, "https://objects.githubusercontent.com/hop3", 302)

    def test_redirect_chain_protocol_downgrade_blocks(self):
        current = Request("https://api.github.com/archive")
        self.hop(current, "https://objects.githubusercontent.com/first")
        current = self.opened[-1]
        with self.assertRaises(URLError):
            self.hop(current, "http://objects.githubusercontent.com/unsafe")

    def test_redirect_chain_userinfo_blocks(self):
        current = Request("https://api.github.com/archive")
        self.hop(current, "https://objects.githubusercontent.com/first")
        current = self.opened[-1]
        with self.assertRaises(URLError):
            self.hop(current, "https://name:secret@objects.githubusercontent.com/unsafe")


if __name__ == "__main__":
    unittest.main()
