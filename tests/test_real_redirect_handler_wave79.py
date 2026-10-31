"""Wave79: exercise urllib's actual redirect response handler offline.

Unlike the Wave78 configuration checks, these tests invoke http_error_302
with synthetic HTTP responses and no network access.
"""
import io
import unittest
from urllib.error import HTTPError
from urllib.request import Request
from tools.audit_remote_release_archive import SafeArtifactRedirect


class RedirectResponse(io.BytesIO):
    status = 302
    code = 302
    def info(self):
        return {"Location": self.location}


class RedirectHandlerExerciseTests(unittest.TestCase):
    def setUp(self):
        self.handler = SafeArtifactRedirect()
        self.calls = []

        def fake_open(request, timeout=0):
            self.calls.append(request)
            response = RedirectResponse(b"")
            response.location = "https://objects.githubusercontent.com/next"
            return response

        self.handler.parent = type("Parent", (), {"open": staticmethod(fake_open)})()

    def redirect(self, request, destination):
        response = RedirectResponse(b"")
        response.location = destination
        return self.handler.http_error_302(request, response, 302, "Found",
                                           {"location": destination})

    def test_one_redirect_invokes_handler_and_drops_credentials(self):
        request = Request("https://api.github.com/artifact",
                          headers={"Authorization": "Bearer secret"})
        self.redirect(request, "https://objects.githubusercontent.com/a")
        self.assertEqual(len(self.calls), 1)
        self.assertFalse(any(k.lower() == "authorization" for k in self.calls[0].headers))

    def test_excessive_chain_rejected_by_real_handler(self):
        request = Request("https://api.github.com/start")
        for number in range(3):
            self.redirect(request, "https://objects.githubusercontent.com/hop" + str(number))
            request = self.calls[-1]
        with self.assertRaises(HTTPError):
            self.redirect(request, "https://objects.githubusercontent.com/hop3")

    def test_repeated_target_rejected(self):
        request = Request("https://api.github.com/start")
        target = "https://objects.githubusercontent.com/repeated"
        for _ in range(2):
            self.redirect(request, target)
            request = self.calls[-1]
        with self.assertRaises(HTTPError):
            self.redirect(request, target)


if __name__ == "__main__":
    unittest.main()
