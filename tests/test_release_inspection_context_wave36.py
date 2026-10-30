"""Wave 36: mandatory identity context for the governed inspection path."""
import unittest
from unittest.mock import Mock, patch
from contracts.rea_release_node import ReleaseNode
from contracts.release_audit_service import ReleaseAuditService


class ContextBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.runner = Mock(side_effect=AssertionError("dispatch forbidden"))
        self.node = ReleaseNode(signed_release_runner=self.runner)
        self.service = ReleaseAuditService()
        self.context = dict(
            ledger=object(), rea_conn=object(), recovery=object(),
            binding_registry=object(), issuer="issuer", nonce="nonce",
            release_id="release", artifact_sha256="a"*64,
            destination_id="destination", observer_id="observer",
            observer_key=b"k"*32, binding=object(), binding_verifier=object(),
        )

    def inspect(self, **updates):
        return self.node.inspect_delivery(audit_service=self.service,
                                          **{**self.context, **updates})

    def test_complete_context_reaches_governed_service(self):
        with patch.object(self.service, "_audit", return_value=("CONSISTENT", "verified")) as audit:
            result = self.inspect()
            self.assertEqual(result.status, "CONSISTENT")
            self.assertFalse(result.dispatch_authorized)
            audit.assert_called_once()

    def test_empty_or_missing_identity_blocks_before_audit(self):
        with patch.object(self.service, "_audit") as audit:
            self.assertEqual(self.inspect(issuer="").reason, "release_inspection_identity_invalid")
            subset = dict(self.context)
            subset.pop("nonce")
            self.assertEqual(self.node.inspect_delivery(
                audit_service=self.service, **subset).reason, "release_inspection_context_invalid")
            audit.assert_not_called()

    def test_dispatch_flags_are_not_audit_arguments(self):
        with patch.object(self.service, "_audit") as audit:
            self.assertEqual(self.inspect(enable_dispatch=True).status, "BLOCK")
            self.assertEqual(self.inspect(release_approved=True).status, "BLOCK")
            audit.assert_not_called()

    def tearDown(self):
        self.runner.assert_not_called()


if __name__ == "__main__":
    unittest.main()
