"""Wave 33: governed path enforces lifecycle and never invokes dispatch."""
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from contracts.durable_replay_ledger import DurableReplayLedger
from contracts.durable_cross_ledger_binding_registry import DurableBindingRegistry
from contracts.monotonic_ledger_audit import install_revision_tracking
from contracts.governed_audit_entrypoint import governed_release_audit
from contracts.three_ledger_release_audit import ThreeLedgerVerdict


class GovernedAuditEntrypointTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        self.ledger = DurableReplayLedger(root/"replay.db")
        self.registry = DurableBindingRegistry(root/"registry.db")
        self.rea = sqlite3.connect(root/"rea.db", isolation_level=None)
        self.addCleanup(self.rea.close)
        self.rea.execute("CREATE TABLE rea_release_claims "
                         "(release_id TEXT PRIMARY KEY, artifact_sha256 TEXT NOT NULL)")
        with self.ledger._connection() as db:
            install_revision_tracking(db, role="replay")
        with self.registry._connection() as db:
            install_revision_tracking(db, role="binding")
        install_revision_tracking(self.rea, role="rea")

    def check(self):
        return governed_release_audit(
            ledger=self.ledger, rea_conn=self.rea, recovery=None,
            binding_registry=self.registry, issuer="issuer", nonce="nonce",
            release_id="release", artifact_sha256="a"*64, destination_id="dest",
            observer_id="observer", observer_key=b"k"*32,
            binding=None, binding_verifier=None,
        )

    def test_preflight_prevents_callback_on_untracked_table(self):
        self.rea.execute("CREATE TABLE rea_release_confirmations (release_id TEXT PRIMARY KEY)")
        with patch("contracts.governed_audit_entrypoint.audit_stable_three_ledgers") as audit:
            self.assertEqual(self.check(), ("BLOCK", "revision_lifecycle_unverified"))
            audit.assert_not_called()

    def test_valid_coverage_invokes_stable_read_not_dispatch(self):
        with patch("contracts.governed_audit_entrypoint.audit_stable_three_ledgers",
                   return_value=ThreeLedgerVerdict("BLOCK", "binding_required")) as audit:
            self.assertEqual(self.check(), ("BLOCK", "binding_required"))
            audit.assert_called_once()

    def test_incomplete_tracking_blocks_after_restart(self):
        with self.registry._connection() as db:
            db.execute("DROP TABLE audit_revision_coverage")
        with patch("contracts.governed_audit_entrypoint.audit_stable_three_ledgers") as audit:
            self.assertEqual(self.check()[0], "BLOCK")
            audit.assert_not_called()


if __name__ == "__main__":
    unittest.main()
