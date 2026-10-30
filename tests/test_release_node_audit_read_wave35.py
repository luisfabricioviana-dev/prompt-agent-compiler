"""Wave 35: release node audit read path is never a dispatch path."""
import unittest
from unittest.mock import Mock, patch
from contracts.rea_release_node import ReleaseNode
from contracts.release_audit_service import AuditDecision, ReleaseAuditService


def context():
    return dict(ledger=object(), rea_conn=object(), recovery=object(),
                binding_registry=object(), issuer="issuer", nonce="nonce",
                release_id="release", artifact_sha256="a"*64,
                destination_id="destination", observer_id="observer",
                observer_key=b"k"*32, binding=object(),
                binding_verifier=object())


class ReleaseNodeAuditReadTests(unittest.TestCase):
    def test_inspection_does_not_invoke_release_runner(self):
        runner = Mock(side_effect=AssertionError("dispatch must not run"))
        node = ReleaseNode(signed_release_runner=runner)
        service = ReleaseAuditService()
        with patch.object(service, "_audit", return_value=("CONSISTENT", "verified")):
            result = node.inspect_delivery(audit_service=service, **context())
        self.assertEqual(result, AuditDecision("CONSISTENT", "verified", False))
        runner.assert_not_called()

    def test_absent_service_blocks_without_dispatch(self):
        runner = Mock()
        result = ReleaseNode(signed_release_runner=runner).inspect_delivery(audit_service=None)
        self.assertEqual(result, AuditDecision("BLOCK", "governed_audit_service_required", False))
        runner.assert_not_called()

    def test_unavailable_governed_audit_fails_closed(self):
        runner = Mock()
        service = ReleaseAuditService()
        with patch.object(service, "_audit", side_effect=RuntimeError("offline")):
            result = ReleaseNode(signed_release_runner=runner).inspect_delivery(audit_service=service, **context())
        self.assertEqual(result, AuditDecision("BLOCK", "governed_audit_unavailable", False))
        runner.assert_not_called()

    def test_uncertain_audit_never_authorizes_dispatch(self):
        runner = Mock()
        service = ReleaseAuditService()
        with patch.object(service, "_audit", return_value=("IN_DOUBT", "no_retry")):
            result = ReleaseNode(signed_release_runner=runner).inspect_delivery(audit_service=service, **context())
        self.assertFalse(result.dispatch_authorized)
        self.assertEqual(result.status, "IN_DOUBT")
        runner.assert_not_called()


if __name__ == "__main__":
    unittest.main()
