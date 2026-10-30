"""Deployment-facing read-only audit façade.

No audit verdict is a release authorization. Runtime integration requires
explicit adoption; this module does not monkeypatch legacy imports.
"""
from __future__ import annotations
from dataclasses import dataclass
from .governed_audit_entrypoint import governed_release_audit


@dataclass(frozen=True)
class AuditDecision:
    status: str
    reason: str
    dispatch_authorized: bool = False


class ReleaseAuditService:
    def __init__(self, *, audit_runner=None):
        if audit_runner is not None:
            raise ValueError("audit_runner_override_forbidden")
        self._audit = governed_release_audit

    def inspect(self, **kwargs) -> AuditDecision:
        try:
            status, reason = self._audit(**kwargs)
        except Exception:
            return AuditDecision("BLOCK", "governed_audit_unavailable")
        if status not in {"CONSISTENT", "IN_DOUBT", "BLOCK"}:
            return AuditDecision("BLOCK", "audit_verdict_invalid")
        if not isinstance(reason, str) or not reason:
            return AuditDecision("BLOCK", "audit_reason_invalid")
        return AuditDecision(status, reason)

    def authorize_dispatch(self, *args, **kwargs):
        raise PermissionError("audit_cannot_authorize_dispatch")
