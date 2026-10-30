import unittest
from unittest.mock import patch
from contracts.release_audit_service import ReleaseAuditService, AuditDecision


class ReleaseAuditServiceTests(unittest.TestCase):
    def test_does_not_allow_runner_override(self):
        with self.assertRaisesRegex(ValueError, "audit_runner_override_forbidden"):
            ReleaseAuditService(audit_runner=lambda: ("CONSISTENT", "fake"))

    def test_consistent_never_authorizes_dispatch(self):
        service = ReleaseAuditService()
        with patch.object(service, "_audit", return_value=("CONSISTENT", "verified")):
            result = service.inspect()
        self.assertEqual(result, AuditDecision("CONSISTENT", "verified", False))

    def test_unavailable_audit_fails_closed(self):
        service = ReleaseAuditService()
        with patch.object(service, "_audit", side_effect=RuntimeError("offline")):
            self.assertEqual(service.inspect(), AuditDecision("BLOCK", "governed_audit_unavailable", False))

    def test_unexpected_verdict_fails_closed(self):
        service = ReleaseAuditService()
        with patch.object(service, "_audit", return_value=("ALLOW", "unsafe")):
            self.assertEqual(service.inspect().status, "BLOCK")

    def test_authorization_forbidden(self):
        with self.assertRaisesRegex(PermissionError, "audit_cannot_authorize_dispatch"):
            ReleaseAuditService().authorize_dispatch()


if __name__ == "__main__":
    unittest.main()
