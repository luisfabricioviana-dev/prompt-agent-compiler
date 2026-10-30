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


class ReleaseNode:
    def __init__(self, *, signed_release_runner: Callable[..., PipelineResult] | None = None):
        if signed_release_runner is not None and not callable(signed_release_runner):
            raise TypeError("signed_release_runner_callable_required")
        self.signed_release_runner = signed_release_runner

    def _resolve_runner(self):
        if self.signed_release_runner is not None:
            return self.signed_release_runner
        try:
            from rea_signed_release_bridge import run_signed_optional_release
        except (ImportError, ModuleNotFoundError):
            return None
        return run_signed_optional_release

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

        kwargs = dict(rea_kwargs or {})
        if "enable_dispatch" in kwargs:
            return self._blocked("release_dispatch_flag_must_be_explicit", payload)

        # The node never synthesizes credentials, signing material, provenance,
        # destination identity, or authorization. Those remain caller/runtime
        # boundary inputs to the existing fail-closed REA bridge.
        kwargs["enable_dispatch"] = enable_dispatch

        runner = self._resolve_runner()
        if runner is None:
            return self._blocked("rea_release_runner_unavailable", payload)

        try:
            result = runner(
                conn,
                payload,
                statement,
                authorization,
                **kwargs,
            )
        except Exception:
            return self._blocked("rea_release_runner_failed", payload)

        if not isinstance(result, PipelineResult):
            return self._blocked("rea_release_result_invalid", payload)
        return result
