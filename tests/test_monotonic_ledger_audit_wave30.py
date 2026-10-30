"""Wave 30: committed ABA mutations are visible through monotonic revisions."""
import sqlite3
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from contracts.durable_replay_ledger import DurableReplayLedger
from contracts.durable_cross_ledger_binding_registry import DurableBindingRegistry
from contracts.monotonic_ledger_audit import install_revision_tracking, revision, versioned_audit


class MonotonicRevisionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.ledger = DurableReplayLedger(root / "replay.sqlite")
        self.registry = DurableBindingRegistry(root / "binding.sqlite")
        self.rea = sqlite3.connect(root / "rea.sqlite", isolation_level=None)
        self.addCleanup(self.rea.close)
        self.rea.execute("CREATE TABLE rea_release_claims "
                         "(release_id TEXT PRIMARY KEY, artifact_sha256 TEXT NOT NULL)")
        with self.ledger._connection() as db:
            install_revision_tracking(db, role="replay")
        with self.registry._connection() as db:
            install_revision_tracking(db, role="binding")
        install_revision_tracking(self.rea, role="rea")

    def audit(self, fn=None):
        return versioned_audit(
            ledger=self.ledger, rea_conn=self.rea,
            binding_registry=self.registry,
            audit=fn or (lambda: SimpleNamespace(status="CONSISTENT",reason="ok")))

    def test_no_change_retains_audit_verdict(self):
        self.assertEqual(self.audit(), ("CONSISTENT", "ok"))

    def test_committed_aba_during_audit_is_blocked(self):
        self.rea.execute("INSERT INTO rea_release_claims VALUES ('r','a')")
        def aba():
            self.rea.execute("UPDATE rea_release_claims SET artifact_sha256='b' WHERE release_id='r'")
            self.rea.execute("UPDATE rea_release_claims SET artifact_sha256='a' WHERE release_id='r'")
            return SimpleNamespace(status="CONSISTENT",reason="ok")
        self.assertEqual(self.audit(aba), ("BLOCK", "monotonic_revision_changed"))
        self.assertEqual(self.rea.execute(
            "SELECT artifact_sha256 FROM rea_release_claims WHERE release_id='r'").fetchone(), ("a",))

    def test_missing_tracking_fails_closed(self):
        self.rea.execute("DROP TRIGGER audit_rev_rea_release_claims_update")
        self.assertEqual(self.audit(), ("BLOCK", "revision_tracking_unavailable"))

    def test_rolled_back_change_does_not_increment(self):
        before = revision(self.rea, role="rea")
        self.rea.execute("BEGIN")
        self.rea.execute("INSERT INTO rea_release_claims VALUES ('temporary','digest')")
        self.rea.rollback()
        self.assertEqual(revision(self.rea, role="rea"), before)

    def test_binding_mutation_changes_version(self):
        with self.registry._connection() as db:
            before = revision(db, role="binding")
            db.execute("INSERT INTO cross_ledger_bindings VALUES (?,?,?,?,?,?)",
                       ("issuer","nonce","release","digest","destination","signature"))
            after = revision(db, role="binding")
        self.assertGreater(after, before)


if __name__ == "__main__":
    unittest.main()
