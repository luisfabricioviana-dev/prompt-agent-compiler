"""Guarded optional REA release node for ExecutionSpecV2.

This adapter connects an approved execution artifact to the existing signed REA
bridge without turning compiler readiness into release authorization.
Dispatch remains disabled by default and requires a separate explicit approval.
"""
from __future__ import annotations

import hashlib
from typing import Any, Callable, Mapping

from .capability_registry import CapabilityStatus
from .execution_spec_v2 import ExecutionSpecV2
from .rea_pipeline import PipelineResult
from .reviewer_spec import ReviewResult
from .bound_provenance import BoundProvenanceStatement, BoundProvenanceVerifier
from .durable_replay_ledger import DurableReplayLedger, ReplayAdmissionError


class ReleaseNode:
    def __init__(self, *, signed_release_runner: Callable[..., PipelineResult] | None = None):
        if signed_release_runner is None:
            from rea_signed_release_bridge import run_signed_optional_release
            signed_release_runner = run_signed_optional_release
        if not callable(signed_release_runner):
            raise TypeError("signed_release_runner_callable_required")
        self.signed_release_runner = signed_release_runner

    def inspect_delivery(self, *, audit_service, **audit_context):
        """Read-only governed inspection. Never invokes the release runner."""
        from .release_audit_service import AuditDecision, ReleaseAuditService
        if not isinstance(audit_service, ReleaseAuditService):
            return AuditDecision("BLOCK", "governed_audit_service_required")
        return audit_service.inspect(**audit_context)

    @staticmethod
    def _digest(payload: bytes) -> str:
        return hashlib.sha256(payload).hexdigest() if isinstance(payload, bytes) else ""

    @staticmethod
    def _blocked(reason: str, payload: bytes = b"") -> PipelineResult:
        return PipelineResult("BLOCKED", reason, ReleaseNode._digest(payload))

    @staticmethod
    def _release_capability_ready(spec: ExecutionSpecV2) -> bool:
        for capability in spec.capabilities.required:
            if capability.name == "rea.release":
                return capability.status is CapabilityStatus.AVAILABLE
        return False

    def execute(
        self,
        *,
        spec: ExecutionSpecV2,
        review: ReviewResult,
        artifact_id: str,
        payload: bytes,
        conn: Any = None,
        statement: Any = None,
        authorization: Any = None,
        enable_dispatch: bool = False,
        release_approved: bool = False,
        provenance_verifier: Callable[..., bool] | None = None,
        provenance_verified: bool = False,
        bound_statement: BoundProvenanceStatement | None = None,
        bound_verifier: BoundProvenanceVerifier | None = None,
        run_id: str | None = None,
        replay_ledger: DurableReplayLedger | None = None,
        rea_kwargs: Mapping[str, Any] | None = None,
    ) -> PipelineResult:
        if not isinstance(spec, ExecutionSpecV2):
            return self._blocked("execution_spec_v2_required", payload)

        readiness = spec.readiness
        if readiness != "READY":
            return self._blocked(f"execution_spec_not_ready:{readiness}", payload)

        if not isinstance(review, ReviewResult) or review.state != "PASS":
            return self._blocked("review_not_passed", payload)

        if not self._release_capability_ready(spec):
            return self._blocked("release_capability_not_required", payload)

        if not isinstance(artifact_id, str) or artifact_id not in {
            artifact.artifact_id for artifact in spec.artifacts
        }:
            return self._blocked("artifact_not_in_execution_spec", payload)

        if not isinstance(payload, bytes) or not payload:
            return self._blocked("release_payload_unavailable")

        if enable_dispatch is not False and enable_dispatch is not True:
            return self._blocked("enable_dispatch_invalid", payload)

        if enable_dispatch and release_approved is not True:
            return self._blocked("explicit_release_approval_required", payload)

        if enable_dispatch:
            if not isinstance(bound_verifier, BoundProvenanceVerifier) or not isinstance(
                bound_statement, BoundProvenanceStatement
            ) or not isinstance(run_id, str) or not run_id.strip():
                return self._blocked("bound_provenance_required", payload)
            if not bound_verifier.verify(
                statement=bound_statement, spec_id=spec.spec_id,
                artifact_id=artifact_id, run_id=run_id, payload=payload,
            ):
                return self._blocked("bound_provenance_invalid", payload)

        # A caller's boolean claim is never provenance evidence. The separately
        # supplied verifier is a trust boundary and must be provisioned by the
        # deployment, not inferred from structural gate evidence.
        if enable_dispatch:
            if provenance_verifier is None or not callable(provenance_verifier):
                return self._blocked("provenance_verifier_required", payload)
            try:
                verified = provenance_verifier(
                    spec_id=spec.spec_id,
                    artifact_id=artifact_id,
                    digest=self._digest(payload),
                    statement=statement,
                    authorization=authorization,
                )
            except Exception:
                return self._blocked("provenance_verification_failed", payload)
            if verified is not True:
                return self._blocked("provenance_not_verified", payload)

        kwargs = dict(rea_kwargs or {})
        if "enable_dispatch" in kwargs:
            return self._blocked("release_dispatch_flag_must_be_explicit", payload)

        # Reserve before any external side effect. A crash after DISPATCHING
        # cannot be automatically retried; a trusted observer must reconcile.
        if enable_dispatch:
            if not isinstance(replay_ledger, DurableReplayLedger):
                return self._blocked("durable_replay_ledger_required", payload)
            try:
                replay_ledger.reserve(bound_statement, payload)
                replay_ledger.transition(
                    bound_statement, payload, expected="RESERVED", target="DISPATCHING"
                )
            except (ReplayAdmissionError, OSError, Exception) as exc:
                return self._blocked("replay_admission_blocked:" + type(exc).__name__, payload)

        # The node never synthesizes credentials, signing material, provenance,
        # destination identity, or authorization. Those remain caller/runtime
        # boundary inputs to the existing fail-closed REA bridge.
        kwargs["enable_dispatch"] = enable_dispatch

        try:
            result = self.signed_release_runner(
                conn,
                payload,
                statement,
                authorization,
                **kwargs,
            )
        except Exception:
            if enable_dispatch:
                try:
                    replay_ledger.transition(bound_statement, payload, expected="DISPATCHING", target="UNCERTAIN")
                except Exception:
                    pass  # Persistent DISPATCHING remains a no-retry barrier.
            return self._blocked("rea_release_runner_failed", payload)

        if enable_dispatch:
            try:
                if not isinstance(result, PipelineResult):
                    replay_ledger.transition(bound_statement, payload, expected="DISPATCHING", target="UNCERTAIN")
                    return self._blocked("rea_release_result_invalid", payload)
                if result.state == "CONFIRMED_BY_OBSERVER":
                    # A bridge's positive status is NOT authenticated durable evidence.
                    # Leave a no-retry barrier until governed offline reconciliation.
                    replay_ledger.transition(
                        bound_statement, payload, expected="DISPATCHING", target="UNCERTAIN"
                    )
                    return self._blocked("authenticated_reconciliation_required", payload)
                else:
                    replay_ledger.transition(bound_statement, payload, expected="DISPATCHING", target="UNCERTAIN")
            except Exception:
                return self._blocked("replay_result_recording_failed", payload)
        if not isinstance(result, PipelineResult):
            return self._blocked("rea_release_result_invalid", payload)
        return result
