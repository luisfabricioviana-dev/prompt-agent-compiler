"""Optional monotonic mutation counters for the three SQLite audit stores.

Migration must run before relying on this instrumentation. Counters are
transactional, detect committed ABA changes during a read, and are NOT a
distributed atomic snapshot, external write log, or dispatch authorization.
"""
from __future__ import annotations
import sqlite3

TABLES = {
    "replay": ("release_attempts", "release_observer_evidence"),
    "rea": ("rea_release_claims", "rea_release_outcomes",
            "rea_release_confirmations", "rea_release_observer_evidence"),
    "binding": ("cross_ledger_bindings",),
}


def install_revision_tracking(conn: sqlite3.Connection, *, role: str) -> None:
    if role not in TABLES:
        raise ValueError("revision_role_invalid")
    # Install before handling traffic and under an exclusive write transaction.
    conn.execute("BEGIN IMMEDIATE")
    try:
        conn.execute("CREATE TABLE IF NOT EXISTS audit_revision ("
                     "id INTEGER PRIMARY KEY CHECK(id=1), revision INTEGER NOT NULL)")
        conn.execute("INSERT OR IGNORE INTO audit_revision VALUES (1,0)")
        conn.execute("CREATE TABLE IF NOT EXISTS audit_revision_coverage ("
                     "role TEXT NOT NULL, table_name TEXT NOT NULL, "
                     "PRIMARY KEY(role,table_name))")
        for table in TABLES[role]:
            present = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
            ).fetchone()
            if not present:
                continue
            conn.execute("INSERT OR IGNORE INTO audit_revision_coverage VALUES (?,?)",
                         (role, table))
            for event in ("INSERT", "UPDATE", "DELETE"):
                name = f"audit_rev_{table}_{event.lower()}"
                conn.execute(
                    f'CREATE TRIGGER IF NOT EXISTS "{name}" AFTER {event} ON "{table}" '
                    'BEGIN UPDATE audit_revision SET revision=revision+1 WHERE id=1; END'
                )
        conn.commit()
    except BaseException:
        conn.rollback()
        raise


def revision(conn: sqlite3.Connection, *, role: str) -> int:
    if role not in TABLES:
        raise ValueError("revision_role_invalid")
    # A missing historical table is as dangerous as a new untracked table.
    coverage = {x[0] for x in conn.execute(
        "SELECT table_name FROM audit_revision_coverage WHERE role=?", (role,))}
    if not coverage:
        raise ValueError("revision_coverage_missing")
    for table in coverage:
        if not conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                            (table,)).fetchone():
            raise ValueError("revision_tracked_table_missing")
    # New tables must have all triggers before audit admission.
    for table in TABLES[role]:
        if conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                        (table,)).fetchone():
            for event in ("insert", "update", "delete"):
                trigger = f"audit_rev_{table}_{event}"
                if not conn.execute("SELECT 1 FROM sqlite_master WHERE type='trigger' AND name=?",
                                    (trigger,)).fetchone():
                    raise ValueError("revision_tracking_incomplete")
    row = conn.execute("SELECT revision FROM audit_revision WHERE id=1").fetchone()
    if row is None or not isinstance(row[0], int) or row[0] < 0:
        raise ValueError("revision_counter_invalid")
    return row[0]


def versioned_audit(*, ledger, rea_conn, binding_registry, audit, **kwargs):
    """Read revisions around a caller-supplied read-only audit function."""
    def read_versions():
        with ledger._connection() as replay, binding_registry._connection() as bindings:
            return (revision(replay, role="replay"),
                    revision(rea_conn, role="rea"),
                    revision(bindings, role="binding"))
    valid, reason = verify_revision_lifecycle(
        ledger=ledger, rea_conn=rea_conn, binding_registry=binding_registry)
    if not valid:
        return ("BLOCK", reason)
    try:
        before = read_versions()
        result = audit(**kwargs)
        after = read_versions()
    except (sqlite3.Error, ValueError, TypeError, AttributeError):
        return ("BLOCK", "revision_tracking_unavailable")
    if before != after:
        return ("BLOCK", "monotonic_revision_changed")
    return (result.status, result.reason)


def verify_revision_lifecycle(*, ledger, rea_conn, binding_registry) -> tuple[bool, str]:
    """Check all three instrumented stores after restart, without mutation."""
    try:
        with ledger._connection() as replay, binding_registry._connection() as bindings:
            revision(replay, role="replay")
            revision(rea_conn, role="rea")
            revision(bindings, role="binding")
    except (sqlite3.Error, ValueError, AttributeError, TypeError):
        return False, "revision_lifecycle_unverified"
    return True, "REVISION_LIFECYCLE_VERIFIED"
