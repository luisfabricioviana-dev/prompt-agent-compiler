"""Wave 39: legacy compatibility inspection is non-authorizing and fail-closed."""
import unittest
from contracts.release_audit_service import ReleaseAuditService
from contracts.rea_pipeline import PipelineResult


class LegacyAuditFacadeTests(unittest.TestCase):
    def setUp(self):
        self.service = ReleaseAuditService()

    def test_legacy_confirmations_require_governed_audit(self):
        for value in (
            PipelineResult("CONFIRMED_BY_OBSERVER", "confirmed", "a"*64),
            {"state": "CONSISTENT"}, ("CONFIRMED", "confirmed"),
            {"state": True},
        ):
            with self.subTest(value=value):
                result = self.service.inspect_legacy(value)
                self.assertEqual(result.status, "BLOCK")
                self.assertFalse(result.dispatch_authorized)

    def test_in_doubt_remains_no_retry(self):
        result = self.service.inspect_legacy({"state": "IN_DOUBT"})
        self.assertEqual(result.status, "IN_DOUBT")
        self.assertFalse(result.dispatch_authorized)

    def test_malformed_unhashable_states_fail_closed(self):
        for value in ({"state": []}, {"state": {}}, {"state": ["CONFIRMED"]},
                      (["CONSISTENT"], "ok")):
            with self.subTest(value=value):
                self.assertEqual(self.service.inspect_legacy(value).status, "BLOCK")

    def test_legacy_inspection_does_not_authorize_dispatch(self):
        with self.assertRaises(PermissionError):
            self.service.authorize_dispatch(self.service.inspect_legacy(
                {"state": "CONFIRMED_BY_OBSERVER"}))


if __name__ == "__main__":
    unittest.main()
