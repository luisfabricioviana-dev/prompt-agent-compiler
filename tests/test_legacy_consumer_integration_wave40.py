"""Wave 40: end-to-end legacy result quarantine compatibility fixtures.

Never calls a publisher. A positive legacy transport response is not a
governed release audit; an uncertain response never grants a retry.
"""
import unittest
from unittest.mock import Mock, patch

from contracts.rea_pipeline import PipelineResult
from contracts.rea_release_node import ReleaseNode
from contracts.release_audit_service import ReleaseAuditService


class LegacyConsumerIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.runner = Mock(side_effect=AssertionError("release runner invoked"))
        self.node = ReleaseNode(signed_release_runner=self.runner)
        self.audit = ReleaseAuditService()

    def tearDown(self):
        self.runner.assert_not_called()

    def test_pipeline_success_remains_quarantined(self):
        legacy = PipelineResult("CONFIRMED_BY_OBSERVER", "DELIVERY_CONFIRMED", "a"*64)
        result = self.audit.inspect_legacy(legacy)
        self.assertEqual((result.status, result.reason),
                         ("BLOCK", "governed_audit_required"))
        self.assertIs(result.dispatch_authorized, False)

    def test_legacy_dict_and_tuple_confirmations_are_not_governed(self):
        for legacy in (
            {"state": "CONFIRMED"}, {"state": "CONSISTENT"},
            ("DELIVERY_CONFIRMED", "ok"), ("SUCCESS", "ok"),
        ):
            with self.subTest(legacy=legacy):
                self.assertEqual(self.audit.inspect_legacy(legacy).status, "BLOCK")

    def test_uncertain_pipeline_preserves_no_retry(self):
        for legacy in (
            PipelineResult("IN_DOUBT", "timeout", "a"*64),
            {"state": "DISPATCHING"}, ("UNCERTAIN", "ack_lost"),
        ):
            with self.subTest(legacy=legacy):
                decision = self.audit.inspect_legacy(legacy)
                self.assertEqual(decision.status, "IN_DOUBT")
                self.assertFalse(decision.dispatch_authorized)

    def test_quarantine_does_not_upgrade_to_governed_audit(self):
        with patch.object(self.audit, "_audit", side_effect=AssertionError("unexpected governed call")):
            decision = self.audit.inspect_legacy(
                PipelineResult("CONFIRMED_BY_OBSERVER", "ok", "a"*64))
        self.assertEqual(decision.status, "BLOCK")

    def test_explicit_authority_still_forbidden_for_any_legacy_status(self):
        for legacy in (
            {"state": "CONFIRMED"}, {"state": "IN_DOUBT"}, {"state": "DRY_RUN"},
        ):
            with self.subTest(legacy=legacy):
                with self.assertRaises(PermissionError):
                    self.audit.authorize_dispatch(self.audit.inspect_legacy(legacy))


if __name__ == "__main__":
    unittest.main()
