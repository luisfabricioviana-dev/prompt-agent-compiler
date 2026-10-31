"""Wave85 strict Content-Length contract tests."""
import unittest
from email.message import Message
from tools.audit_remote_release_archive import parse_archive_content_length


class ContentLengthParserTests(unittest.TestCase):
    def test_missing_content_length_is_allowed_for_digest_verification(self):
        self.assertIsNone(parse_archive_content_length({}))

    def test_single_decimal_length_is_parsed(self):
        self.assertEqual(parse_archive_content_length({"Content-Length": "123"}), 123)
        self.assertEqual(parse_archive_content_length({"Content-Length": "0"}), 0)

    def test_duplicate_headers_are_rejected(self):
        headers = Message()
        headers.add_header("Content-Length", "3")
        headers.add_header("Content-Length", "3")
        with self.assertRaises(ValueError):
            parse_archive_content_length(headers)

    def test_malformed_and_ambiguous_lengths_rejected(self):
        for bad in ("3, 3", " 3", "+3", "-1", "1.0", "abc", "10000001"):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    parse_archive_content_length({"Content-Length": bad})

if __name__ == "__main__":
    unittest.main()
