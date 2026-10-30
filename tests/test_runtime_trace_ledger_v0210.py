import hashlib
import sqlite3
import tempfile
import unittest
from datetime import datetime, timezone

from contracts.artifact_registry import ArtifactRegistry
from contracts.capability_registry import (
    CapabilityRegistry,
    CapabilitySpec,
    CapabilityStatus,
)
from contracts.execution_spec_v2 import (
    ArtifactContract,
    ExecutionNode,
    ExecutionSpecV2,
)
from contracts.runtime_state import NodeState, RuntimeStateMachine
from contracts.runtime_trace_ledger import (
    RuntimeTraceLedgerError,
    SQLiteRuntimeTraceLedger,
    execution_spec_fingerprint,
)


FIXED_TIME = datetime(2026, 10, 30, 17, 10, tzinfo=timezone.utc)


def clock():
    return FIXED_TIME


def make_spec(*, raw_request="execute"):
    resolution = CapabilityRegistry(
        (CapabilitySpec("files.read", CapabilityStatus.AVAILABLE),)
    ).resolve(required=("files.read",))
    return ExecutionSpecV2(
        spec_id="trace-spec",
        compiler_version="0.2.10",
        raw_request=raw_request,
        objective="Build and verify.",
        success_definition=("all nodes pass",),
        complexity_level="N2",
        complexity_score=6,
        capabilities=resolution,
        execution_nodes=(
            ExecutionNode(
                node_id="build",
                purpose="Build artifact",
                role="builder",
                required_capabilities=("files.read",),
                output_artifacts=("artifact-1",),
            ),
            ExecutionNode(
                node_id="verify",
                purpose="Verify",
                role="verifier",
                prerequisites=("build",),
            ),
        ),
        artifacts=(
            ArtifactContract(
                artifact_id="artifact-1",
                artifact_type="BinaryArtifact",
                producer_node="build",
            ),
        ),
    )


class SQLiteRuntimeTraceLedgerTests(unittest.TestCase):
    def test_spec_fingerprint_is_stable_and_content_bound(self):
        a = execution_spec_fingerprint(make_spec())
        b = execution_spec_fingerprint(make_spec())
        c = execution_spec_fingerprint(make_spec(raw_request="different"))

        self.assertEqual(a, b)
        self.assertEqual(len(a), 64)
        self.assertNotEqual(a, c)

    def test_register_run_is_idempotent_but_conflict_fails_closed(self):
        with sqlite3.connect(":memory:") as db:
            ledger = SQLiteRuntimeTraceLedger(db, clock=clock)
            first = ledger.register_run("run-1", make_spec())
            second = ledger.register_run("run-1", make_spec())
            self.assertEqual(first, second)

            with self.assertRaisesRegex(
                RuntimeTraceLedgerError,
                "run_spec_conflict:run-1",
            ):
                ledger.register_run(
                    "run-1",
                    make_spec(raw_request="different"),
                )

    def test_event_chain_detects_tampering(self):
        with sqlite3.connect(":memory:") as db:
            ledger = SQLiteRuntimeTraceLedger(db, clock=clock)
            ledger.register_run("run-1", make_spec())
            ledger.commit_step(
                "run-1",
                events=(
                    {
                        "event_type": "node_started",
                        "node_id": "build",
                        "from_state": "READY",
                        "to_state": "RUNNING",
                    },
                    {
                        "event_type": "node_passed",
                        "node_id": "build",
                        "from_state": "RUNNING",
                        "to_state": "PASS",
                    },
                ),
            )
            self.assertTrue(ledger.verify_chain("run-1"))

            db.execute(
                "UPDATE pac_runtime_events SET event_type='tampered' "
                "WHERE run_id='run-1' AND event_index=2"
            )
            db.commit()
            self.assertFalse(ledger.verify_chain("run-1"))

    def test_artifact_metadata_is_idempotent_and_conflict_bound(self):
        spec = make_spec()
        registry = ArtifactRegistry(spec.artifacts)
        record = registry.register_bytes(
            "artifact-1",
            b"payload",
            producer_node="build",
        )
        with sqlite3.connect(":memory:") as db:
            ledger = SQLiteRuntimeTraceLedger(db, clock=clock)
            ledger.register_run("run-1", spec)
            ledger.commit_step("run-1", artifacts=(record,))
            ledger.commit_step("run-1", artifacts=(record,))
            stored = ledger.artifacts("run-1")
            self.assertEqual(len(stored), 1)
            self.assertEqual(stored[0]["sha256"], record.sha256)

            forged = type(record)(
                artifact_id=record.artifact_id,
                artifact_type=record.artifact_type,
                producer_node=record.producer_node,
                sha256="0" * 64,
                byte_size=record.byte_size,
                state=record.state,
                sequence=record.sequence,
            )
            with self.assertRaisesRegex(
                RuntimeTraceLedgerError,
                "artifact_metadata_conflict:artifact-1",
            ):
                ledger.commit_step("run-1", artifacts=(forged,))

    def test_file_backed_ledger_survives_reopen(self):
        spec = make_spec()
        with tempfile.TemporaryDirectory() as td:
            path = td + "/runtime.db"
            with sqlite3.connect(path) as db:
                ledger = SQLiteRuntimeTraceLedger(db, clock=clock)
                ledger.register_run("run-1", spec)
                ledger.commit_step(
                    "run-1",
                    events=(
                        {"event_type": "runtime_initialized"},
                    ),
                )

            with sqlite3.connect(path) as db:
                reopened = SQLiteRuntimeTraceLedger(db, clock=clock)
                events = reopened.events("run-1")
                self.assertEqual(len(events), 1)
                self.assertEqual(
                    events[0]["event_type"],
                    "runtime_initialized",
                )
                self.assertTrue(reopened.verify_chain("run-1"))

    def test_naive_clock_is_rejected(self):
        with sqlite3.connect(":memory:") as db:
            ledger = SQLiteRuntimeTraceLedger(
                db,
                clock=lambda: datetime(2026, 10, 30, 17, 10),
            )
            ledger.register_run("run-1", make_spec())
            with self.assertRaisesRegex(
                RuntimeTraceLedgerError,
                "trace_clock_timezone_required",
            ):
                ledger.commit_step(
                    "run-1",
                    events=({"event_type": "x"},),
                )


class RuntimeStateTraceIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.spec = make_spec()
        self.ledger = SQLiteRuntimeTraceLedger(self.db, clock=clock)
        self.artifacts = ArtifactRegistry(self.spec.artifacts)
        self.runtime = RuntimeStateMachine(
            self.spec,
            artifact_registry=self.artifacts,
            trace_ledger=self.ledger,
            run_id="run-1",
        )

    def tearDown(self):
        self.db.close()

    def test_runtime_initialization_is_durably_traced(self):
        events = self.ledger.events("run-1")
        self.assertEqual(
            [event["event_type"] for event in events],
            ["runtime_initialized"],
        )
        self.assertTrue(self.ledger.verify_chain("run-1"))

    def test_start_and_complete_commit_trace_artifact_and_ready_transition(self):
        self.runtime.start("build")
        self.runtime.complete(
            "build",
            outputs={"artifact-1": b"payload"},
        )

        events = self.ledger.events("run-1")
        self.assertEqual(
            [event["event_type"] for event in events],
            [
                "runtime_initialized",
                "node_started",
                "artifact_recorded",
                "node_passed",
                "node_ready",
            ],
        )
        self.assertEqual(self.runtime.node_state("verify"), NodeState.READY)
        stored = self.ledger.artifacts("run-1")
        self.assertEqual(stored[0]["artifact_id"], "artifact-1")
        self.assertEqual(
            stored[0]["sha256"],
            hashlib.sha256(b"payload").hexdigest(),
        )
        self.assertTrue(self.ledger.verify_chain("run-1"))

    def test_failure_and_downstream_block_are_committed_together(self):
        self.runtime.start("build")
        self.runtime.fail("build", reason="implementation_failure")

        events = self.ledger.events("run-1")
        self.assertEqual(
            [event["event_type"] for event in events][-2:],
            ["node_failed", "node_blocked"],
        )
        self.assertEqual(self.runtime.node_state("build"), NodeState.FAIL)
        self.assertEqual(self.runtime.node_state("verify"), NodeState.BLOCKED)

    def test_trace_write_failure_prevents_start_transition(self):
        class FailingLedger:
            def register_run(self, run_id, spec):
                return {"run_id": run_id}

            def commit_step(self, *args, **kwargs):
                raise RuntimeTraceLedgerError("trace_write_failed")

        runtime = RuntimeStateMachine(
            self.spec,
            artifact_registry=ArtifactRegistry(self.spec.artifacts),
            trace_ledger=FailingLedger(),
            run_id="run-x",
        )

        with self.assertRaisesRegex(
            RuntimeTraceLedgerError,
            "trace_write_failed",
        ):
            runtime.start("build")
        self.assertEqual(runtime.node_state("build"), NodeState.READY)


if __name__ == "__main__":
    unittest.main()
