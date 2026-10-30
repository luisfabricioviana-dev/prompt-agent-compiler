"""Durable SQLite runtime trace/provenance ledger for v0.2.10.

The ledger stores spec identity, hash-chained runtime events, and artifact
metadata. It does not store artifact bytes and does not implement runtime
resume/replay.
"""
from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
import sqlite3
from typing import Any, Callable, Iterable, Mapping

from .artifact_registry import ArtifactRecord
from .execution_spec_v2 import ExecutionSpecV2


class RuntimeTraceLedgerError(RuntimeError):
    pass


def _stable(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return _stable(asdict(value))
    if isinstance(value, Mapping):
        return {
            str(key): _stable(value[key])
            for key in sorted(value, key=lambda item: str(item))
        }
    if isinstance(value, (tuple, list)):
        return [_stable(item) for item in value]
    if isinstance(value, set):
        return sorted((_stable(item) for item in value), key=repr)
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return {
        "type": f"{type(value).__module__}.{type(value).__qualname__}",
        "repr": repr(value),
    }


def _gate_identity(gate: Any) -> str:
    if isinstance(gate, str):
        return gate
    value = getattr(gate, "gate_id", None)
    if isinstance(value, str):
        return value
    return f"{type(gate).__module__}.{type(gate).__qualname__}"


def execution_spec_fingerprint(spec: ExecutionSpecV2) -> str:
    if not isinstance(spec, ExecutionSpecV2):
        raise TypeError("execution_spec_v2_required")
    pattern_signature = {}
    for pattern_id, decision in sorted(spec.legacy_patterns.items()):
        pattern_signature[str(pattern_id)] = {
            "status": _stable(getattr(decision, "status", decision)),
            "score": _stable(getattr(decision, "score", None)),
        }
    payload = {
        "spec_id": spec.spec_id,
        "compiler_version": spec.compiler_version,
        "raw_request": spec.raw_request,
        "objective": spec.objective,
        "success_definition": _stable(spec.success_definition),
        "complexity_level": spec.complexity_level,
        "complexity_score": spec.complexity_score,
        "capabilities": _stable(spec.capabilities),
        "known_context": _stable(spec.known_context),
        "unknowns": _stable(spec.unknowns),
        "assumptions": _stable(spec.assumptions),
        "contradictions": _stable(spec.contradictions),
        "constraints": _stable(spec.constraints),
        "dependencies": _stable(spec.dependencies),
        "roles": _stable(spec.roles),
        "patterns": pattern_signature,
        "execution_nodes": _stable(spec.execution_nodes),
        "artifacts": _stable(spec.artifacts),
        "quality_gates": [_gate_identity(g) for g in spec.quality_gates],
        "verification_plan": _stable(spec.verification_plan),
        "failure_routes": _stable(spec.failure_routes),
        "stop_conditions": _stable(spec.stop_conditions),
        "output_contract": _stable(spec.output_contract),
    }
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class SQLiteRuntimeTraceLedger:
    def __init__(
        self,
        conn: sqlite3.Connection,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if not isinstance(conn, sqlite3.Connection):
            raise TypeError("sqlite_connection_required")
        self.conn = conn
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS pac_runtime_runs (
                run_id TEXT PRIMARY KEY,
                spec_id TEXT NOT NULL,
                spec_sha256 TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS pac_runtime_events (
                seq INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                event_index INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                node_id TEXT,
                artifact_id TEXT,
                from_state TEXT,
                to_state TEXT,
                reason TEXT,
                details_json TEXT NOT NULL,
                occurred_at TEXT NOT NULL,
                prev_hash TEXT NOT NULL,
                event_hash TEXT NOT NULL,
                UNIQUE(run_id, event_index)
            );
            CREATE INDEX IF NOT EXISTS idx_pac_runtime_events_run
                ON pac_runtime_events(run_id, event_index);
            CREATE TABLE IF NOT EXISTS pac_runtime_artifacts (
                run_id TEXT NOT NULL,
                artifact_id TEXT NOT NULL,
                artifact_type TEXT NOT NULL,
                producer_node TEXT NOT NULL,
                sha256 TEXT NOT NULL,
                byte_size INTEGER NOT NULL,
                state TEXT NOT NULL,
                artifact_sequence INTEGER NOT NULL,
                PRIMARY KEY(run_id, artifact_id)
            );
            """
        )
        self.conn.commit()

    @staticmethod
    def _run_id(run_id: str) -> str:
        if not isinstance(run_id, str) or not run_id.strip():
            raise RuntimeTraceLedgerError("run_id_required")
        return run_id.strip()

    def register_run(
        self,
        run_id: str,
        spec: ExecutionSpecV2,
    ) -> dict[str, str]:
        run_id = self._run_id(run_id)
        fingerprint = execution_spec_fingerprint(spec)
        existing = self.conn.execute(
            "SELECT spec_id, spec_sha256 FROM pac_runtime_runs WHERE run_id=?",
            (run_id,),
        ).fetchone()
        record = {
            "run_id": run_id,
            "spec_id": spec.spec_id,
            "spec_sha256": fingerprint,
        }
        if existing is not None:
            if existing != (spec.spec_id, fingerprint):
                raise RuntimeTraceLedgerError(
                    f"run_spec_conflict:{run_id}"
                )
            return record
        with self.conn:
            self.conn.execute(
                "INSERT INTO pac_runtime_runs(run_id,spec_id,spec_sha256) "
                "VALUES (?,?,?)",
                (run_id, spec.spec_id, fingerprint),
            )
        return record

    def _now(self) -> str:
        value = self.clock()
        if (
            not isinstance(value, datetime)
            or value.tzinfo is None
            or value.utcoffset() is None
        ):
            raise RuntimeTraceLedgerError("trace_clock_timezone_required")
        return value.isoformat()

    def _require_run(self, run_id: str) -> None:
        row = self.conn.execute(
            "SELECT 1 FROM pac_runtime_runs WHERE run_id=?",
            (run_id,),
        ).fetchone()
        if row is None:
            raise RuntimeTraceLedgerError(f"run_not_registered:{run_id}")

    @staticmethod
    def _event_payload(
        *,
        run_id: str,
        event_index: int,
        event: Mapping[str, Any],
        occurred_at: str,
        prev_hash: str,
    ) -> dict[str, Any]:
        event_type = event.get("event_type")
        if not isinstance(event_type, str) or not event_type.strip():
            raise RuntimeTraceLedgerError("event_type_required")
        details = event.get("details", {})
        if not isinstance(details, Mapping):
            raise RuntimeTraceLedgerError("event_details_mapping_required")
        return {
            "run_id": run_id,
            "event_index": event_index,
            "event_type": event_type.strip(),
            "node_id": event.get("node_id"),
            "artifact_id": event.get("artifact_id"),
            "from_state": event.get("from_state"),
            "to_state": event.get("to_state"),
            "reason": event.get("reason"),
            "details": _stable(dict(details)),
            "occurred_at": occurred_at,
            "prev_hash": prev_hash,
        }

    @staticmethod
    def _hash_event(payload: Mapping[str, Any]) -> str:
        raw = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    @staticmethod
    def _artifact_values(record: ArtifactRecord) -> tuple[Any, ...]:
        if not isinstance(record, ArtifactRecord):
            raise TypeError("artifact_record_required")
        return (
            record.artifact_id,
            record.artifact_type,
            record.producer_node,
            record.sha256,
            record.byte_size,
            record.state,
            record.sequence,
        )

    def commit_step(
        self,
        run_id: str,
        *,
        events: Iterable[Mapping[str, Any]] = (),
        artifacts: Iterable[ArtifactRecord] = (),
    ) -> None:
        run_id = self._run_id(run_id)
        self._require_run(run_id)
        event_list = tuple(events)
        artifact_list = tuple(artifacts)

        last = self.conn.execute(
            "SELECT event_index,event_hash FROM pac_runtime_events "
            "WHERE run_id=? ORDER BY event_index DESC LIMIT 1",
            (run_id,),
        ).fetchone()
        event_index = int(last[0]) if last else 0
        prev_hash = str(last[1]) if last else "0" * 64

        prepared_events = []
        for event in event_list:
            event_index += 1
            occurred_at = self._now()
            payload = self._event_payload(
                run_id=run_id,
                event_index=event_index,
                event=event,
                occurred_at=occurred_at,
                prev_hash=prev_hash,
            )
            event_hash = self._hash_event(payload)
            prepared_events.append((payload, event_hash))
            prev_hash = event_hash

        prepared_artifacts = []
        for record in artifact_list:
            values = self._artifact_values(record)
            existing = self.conn.execute(
                "SELECT artifact_type,producer_node,sha256,byte_size,state,"
                "artifact_sequence FROM pac_runtime_artifacts "
                "WHERE run_id=? AND artifact_id=?",
                (run_id, record.artifact_id),
            ).fetchone()
            expected = values[1:]
            if existing is not None:
                if tuple(existing) != expected:
                    raise RuntimeTraceLedgerError(
                        f"artifact_metadata_conflict:{record.artifact_id}"
                    )
                continue
            prepared_artifacts.append(values)

        with self.conn:
            for values in prepared_artifacts:
                self.conn.execute(
                    "INSERT INTO pac_runtime_artifacts("
                    "run_id,artifact_id,artifact_type,producer_node,sha256,"
                    "byte_size,state,artifact_sequence) VALUES (?,?,?,?,?,?,?,?)",
                    (run_id, *values),
                )
            for payload, event_hash in prepared_events:
                self.conn.execute(
                    "INSERT INTO pac_runtime_events("
                    "run_id,event_index,event_type,node_id,artifact_id,"
                    "from_state,to_state,reason,details_json,occurred_at,"
                    "prev_hash,event_hash) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        run_id,
                        payload["event_index"],
                        payload["event_type"],
                        payload["node_id"],
                        payload["artifact_id"],
                        payload["from_state"],
                        payload["to_state"],
                        payload["reason"],
                        json.dumps(
                            payload["details"],
                            sort_keys=True,
                            separators=(",", ":"),
                            ensure_ascii=False,
                        ),
                        payload["occurred_at"],
                        payload["prev_hash"],
                        event_hash,
                    ),
                )

    def events(self, run_id: str) -> list[dict[str, Any]]:
        run_id = self._run_id(run_id)
        rows = self.conn.execute(
            "SELECT event_index,event_type,node_id,artifact_id,from_state,"
            "to_state,reason,details_json,occurred_at,prev_hash,event_hash "
            "FROM pac_runtime_events WHERE run_id=? ORDER BY event_index",
            (run_id,),
        ).fetchall()
        return [
            {
                "event_index": row[0],
                "event_type": row[1],
                "node_id": row[2],
                "artifact_id": row[3],
                "from_state": row[4],
                "to_state": row[5],
                "reason": row[6],
                "details": json.loads(row[7]),
                "occurred_at": row[8],
                "prev_hash": row[9],
                "event_hash": row[10],
            }
            for row in rows
        ]

    def artifacts(self, run_id: str) -> list[dict[str, Any]]:
        run_id = self._run_id(run_id)
        rows = self.conn.execute(
            "SELECT artifact_id,artifact_type,producer_node,sha256,byte_size,"
            "state,artifact_sequence FROM pac_runtime_artifacts "
            "WHERE run_id=? ORDER BY artifact_sequence,artifact_id",
            (run_id,),
        ).fetchall()
        return [
            {
                "artifact_id": row[0],
                "artifact_type": row[1],
                "producer_node": row[2],
                "sha256": row[3],
                "byte_size": row[4],
                "state": row[5],
                "sequence": row[6],
            }
            for row in rows
        ]

    def verify_chain(self, run_id: str) -> bool:
        run_id = self._run_id(run_id)
        events = self.events(run_id)
        prev_hash = "0" * 64
        expected_index = 1
        for event in events:
            if event["event_index"] != expected_index:
                return False
            if event["prev_hash"] != prev_hash:
                return False
            payload = {
                "run_id": run_id,
                "event_index": event["event_index"],
                "event_type": event["event_type"],
                "node_id": event["node_id"],
                "artifact_id": event["artifact_id"],
                "from_state": event["from_state"],
                "to_state": event["to_state"],
                "reason": event["reason"],
                "details": event["details"],
                "occurred_at": event["occurred_at"],
                "prev_hash": event["prev_hash"],
            }
            calculated = self._hash_event(payload)
            if calculated != event["event_hash"]:
                return False
            prev_hash = event["event_hash"]
            expected_index += 1
        return True
