"""Wave 32: lifecycle preflight is required, not optional."""
import sqlite3
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from contracts.durable_replay_ledger import DurableReplayLedger
from contracts.durable_cross_ledger_binding_registry import DurableBindingRegistry
from contracts.monotonic_ledger_audit import install_revision_tracking, versioned_audit

class MandatoryPreflightTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root=Path(tmp.name)
        self.ledger=DurableReplayLedger(root/"replay.db")
        self.registry=DurableBindingRegistry(root/"binding.db")
        self.rea=sqlite3.connect(root/"rea.db",isolation_level=None)
        self.addCleanup(self.rea.close)
        self.rea.execute("CREATE TABLE rea_release_claims (release_id TEXT PRIMARY KEY, artifact_sha256 TEXT NOT NULL)")
        with self.ledger._connection() as db:
            install_revision_tracking(db,role="replay")
        with self.registry._connection() as db:
            install_revision_tracking(db,role="binding")
        install_revision_tracking(self.rea,role="rea")
        self.calls=0

    def audit(self):
        self.calls+=1
        return SimpleNamespace(status="CONSISTENT",reason="read_only")

    def run_audit(self):
        return versioned_audit(ledger=self.ledger,rea_conn=self.rea,
                               binding_registry=self.registry,audit=self.audit)

    def test_valid_preflight_allows_read_only_audit(self):
        self.assertEqual(self.run_audit(),("CONSISTENT","read_only"))
        self.assertEqual(self.calls,1)

    def test_new_uninstrumented_table_blocks_before_callback(self):
        self.rea.execute("CREATE TABLE rea_release_confirmations (release_id TEXT PRIMARY KEY)")
        self.assertEqual(self.run_audit(),("BLOCK","revision_lifecycle_unverified"))
        self.assertEqual(self.calls,0)

    def test_removed_tracked_table_blocks_before_callback(self):
        self.rea.execute("DROP TABLE rea_release_claims")
        self.assertEqual(self.run_audit(),("BLOCK","revision_lifecycle_unverified"))
        self.assertEqual(self.calls,0)

    def test_missing_revision_coverage_blocks_before_callback(self):
        with self.registry._connection() as db:
            db.execute("DROP TABLE audit_revision_coverage")
        self.assertEqual(self.run_audit(),("BLOCK","revision_lifecycle_unverified"))
        self.assertEqual(self.calls,0)

    def test_reinstrumentation_restores_admission(self):
        self.rea.execute("CREATE TABLE rea_release_confirmations (release_id TEXT PRIMARY KEY)")
        self.assertEqual(self.run_audit()[0],"BLOCK")
        install_revision_tracking(self.rea,role="rea")
        self.assertEqual(self.run_audit(),("CONSISTENT","read_only"))
        self.assertEqual(self.calls,1)

if __name__=="__main__":
    unittest.main()
