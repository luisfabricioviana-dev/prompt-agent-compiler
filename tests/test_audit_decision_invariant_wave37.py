"""Wave 37: an audit result can never be a dispatch capability."""
import unittest
from dataclasses import replace
from contracts.release_audit_service import AuditDecision, ReleaseAuditService


class AuditDecisionInvariantTests(unittest.TestCase):
    def test_true_dispatch_authorization_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "audit_decision_cannot_authorize_dispatch"):
            AuditDecision("CONSISTENT", "verified", True)

    def test_truthy_nonboolean_authorization_is_rejected(self):
        with self.assertRaises(ValueError):
            AuditDecision("CONSISTENT", "verified", 1)

    def test_mutating_frozen_decision_cannot_authorize(self):
        result = AuditDecision("CONSISTENT", "verified")
        with self.assertRaises(ValueError):
            replace(result, dispatch_authorized=True)
        self.assertFalse(result.dispatch_authorized)

    def test_all_audit_states_are_non_authorizing(self):
        for state in ("CONSISTENT", "IN_DOUBT", "BLOCK"):
            with self.subTest(state=state):
                self.assertIs(AuditDecision(state, "reason").dispatch_authorized, False)

    def test_service_still_refuses_dispatch_authority(self):
        with self.assertRaises(PermissionError):
            ReleaseAuditService().authorize_dispatch()


if __name__ == "__main__":
    unittest.main()
