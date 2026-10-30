"""Wave31: schema lifecycle and restart coverage are fail-closed."""
import sqlite3
import tempfile
import unittest
from pathlib import Path
from contracts.durable_replay_ledger import DurableReplayLedger
from contracts.durable_cross_ledger_binding_registry import DurableBindingRegistry
from contracts.monotonic_ledger_audit import (
    install_revision_tracking, revision, verify_revision_lifecycle,
)


class RevisionLifecycleTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        self.ledger = DurableReplayLedger(root / "replay.db")
        self.registry = DurableBindingRegistry(root / "bindings.db")
        self.rea_path = root / "rea.db"
        self.rea = sqlite3.connect(self.rea_path, isolation_level=None)
        self.addCleanup(self.rea.close)
        self.rea.execute("CREATE TABLE rea_release_claims "
                         "(release_id TEXT PRIMARY KEY, artifact_sha256 TEXT NOT NULL)")
        with self.ledger._connection() as db:
            install_revision_tracking(db, role="replay")
        with self.registry._connection() as db:
            install_revision_tracking(db, role="binding")
        install_revision_tracking(self.rea, role="rea")

    def check(self):
        return verify_revision_lifecycle(
            ledger=self.ledger, rea_conn=self.rea, binding_registry=self.registry)

    def test_restart_coverage_verified(self):
        self.assertEqual(self.check(), (True, "REVISION_LIFECYCLE_VERIFIED"))
        with sqlite3.connect(self.rea_path) as reopened:
            self.assertGreaterEqual(revision(reopened, role="rea"), 0)

    def test_lazy_table_without_triggers_blocks(self):
        self.rea.execute("CREATE TABLE rea_release_confirmations "
                         "(release_id TEXT PRIMARY KEY)")
        self.assertEqual(self.check(), (False, "revision_lifecycle_unverified"))

    def test_removed_tracked_table_blocks(self):
        self.rea.execute("DROP TABLE rea_release_claims")
        self.assertEqual(self.check(), (False, "revision_lifecycle_unverified"))

    def test_adding_tracking_after_lazy_table_restores_coverage(self):
        self.rea.execute("CREATE TABLE rea_release_confirmations "
                         "(release_id TEXT PRIMARY KEY)")
        self.assertFalse(self.check()[0])
        install_revision_tracking(self.rea, role="rea")
        self.assertTrue(self.check()[0])

    def test_missing_coverage_table_blocks(self):
        with self.registry._connection() as db:
            db.execute("DROP TABLE audit_revision_coverage")
        self.assertEqual(self.check(), (False, "revision_lifecycle_unverified"))


if __name__ == "__main__":
    unittest.main()
