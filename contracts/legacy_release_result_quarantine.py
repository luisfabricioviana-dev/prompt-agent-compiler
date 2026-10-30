"""Quarantine legacy release outputs at an audit boundary.

Legacy PipelineResult, mapping, and tuple statuses are NOT authenticated,
durable three-ledger evidence. No conversion may grant dispatch authority.
Use ReleaseAuditService with full governed context for actual inspections.
"""
from __future__ import annotations
from .release_audit_service import AuditDecision


def classify_legacy_release_result(value) -> AuditDecision:
    """Compatibility parser that never upgrades a legacy success to CONSISTENT."""
    from .rea_pipeline import PipelineResult

    state = None
    if isinstance(value, PipelineResult):
        state = value.state
    elif isinstance(value, dict):
        state = value.get("state")
    elif isinstance(value, tuple) and len(value) == 2:
        state = value[0]

    if state in ("IN_DOUBT", "UNCERTAIN", "DISPATCHING", "DISPATCHED"):
        return AuditDecision("IN_DOUBT", "legacy_unreconciled_no_retry")
    if state in ("CONFIRMED_BY_OBSERVER", "DELIVERY_CONFIRMED", "CONFIRMED",
                 "CONSISTENT", "SUCCESS", "PASS", True):
        return AuditDecision("BLOCK", "governed_audit_required")
    return AuditDecision("BLOCK", "legacy_release_result_untrusted")
