"""Standalone v0.2.10 normalized-task semantic contract.

This mirrors the recovered v0.2.9 fail-closed contract without importing the
recovered implementation into the installable contracts distribution.
"""
from __future__ import annotations

from typing import Any


ALLOWED_ACTIONS = {
    "CREATE","MODIFY","DIAGNOSE","REVIEW","RESEARCH","ANALYZE_EVIDENCE",
    "ANALYZE_DATA","DESIGN","OPTIMIZE","OPERATE"
}
ALLOWED_PRESERVATION = {
    "BEHAVIOR","API","OUTPUT","MEANING","QUALITY","COMPATIBILITY"
}
ALLOWED_PERFORMANCE = {
    "LATENCY","THROUGHPUT","MEMORY","COMPUTE","FINANCIAL_COST","TOKEN_COST",
    "QUALITY_ACCURACY","RESOURCE_UTILIZATION","GENERAL"
}
ALLOWED_EVIDENCE_POLICY = {
    "OPEN","SUPPLIED_ONLY","CURRENT_EXTERNAL","TRACEABLE"
}
ALLOWED_UI = {
    "UI","PRODUCTION","ACCESSIBILITY","RESPONSIVE","STATEFUL_UI"
}
ALLOWED_ARCHITECTURE = {
    "DESIGN_BEFORE_BUILD","CHANGE","BOUNDARIES","MIGRATION"
}
ALLOWED_EXTERNAL_STATE = {
    "EMAIL","CALENDAR","PUBLISHING","DATABASE","FILES","ACCOUNT","OTHER"
}
ALLOWED_EXECUTION = {
    "MULTI_STEP","LARGE_WORKLOAD","PARALLELIZABLE","INDEPENDENT_REVIEW",
    "EXPLICIT_MULTI_AGENT","HUMAN_APPROVAL","STATEFUL"
}
ALLOWED_CAPABILITIES = {
    "WEB_CURRENT_EVIDENCE","FILE_READ","EMAIL_READ","EMAIL_WRITE",
    "CALENDAR_READ","CALENDAR_WRITE","EXTERNAL_WRITE","AUTHORIZATION",
    "CONNECTION_STATE","HUMAN_APPROVAL","PERSISTENT_STATE_READ",
    "PERSISTENT_STATE_WRITE"
}
ALLOWED_RISKS = {
    "REVERSIBILITY","BLAST_RADIUS","FINANCIAL","LEGAL_REGULATORY","SECURITY",
    "DATA_LOSS","REPUTATIONAL"
}


class SemanticTaskContractError(ValueError):
    pass


def _values(task: Any, name: str):
    if not hasattr(task, name):
        raise SemanticTaskContractError(f"normalized_task_missing_field:{name}")
    return getattr(task, name)


def _subset(name: str, values, allowed: set[str]) -> None:
    try:
        invalid = set(values) - allowed
    except TypeError as exc:
        raise SemanticTaskContractError(
            f"{name} must be an iterable of strings"
        ) from exc
    if invalid:
        raise SemanticTaskContractError(
            f"{name} contains invalid values: {sorted(invalid)}"
        )


def validate_normalized_task(task: Any) -> Any:
    actions = _values(task, "actions")
    preservation = _values(task, "preservation")
    performance = _values(task, "performance_dimensions")
    evidence = _values(task, "evidence_policy")
    ui = _values(task, "ui_requirements")
    architecture = _values(task, "architecture")
    external = _values(task, "external_state")
    execution = _values(task, "execution")
    capabilities = _values(task, "capabilities")
    risks = _values(task, "risks")

    _subset("actions", actions, ALLOWED_ACTIONS)
    _subset("preservation", preservation, ALLOWED_PRESERVATION)
    _subset("performance_dimensions", performance, ALLOWED_PERFORMANCE)
    _subset("evidence_policy", evidence, ALLOWED_EVIDENCE_POLICY)
    _subset("ui_requirements", ui, ALLOWED_UI)
    _subset("architecture", architecture, ALLOWED_ARCHITECTURE)
    _subset("external_state", external, ALLOWED_EXTERNAL_STATE)
    _subset("execution", execution, ALLOWED_EXECUTION)
    _subset("capabilities", capabilities, ALLOWED_CAPABILITIES)
    _subset("risks", risks, ALLOWED_RISKS)

    for key, value in risks.items():
        if (
            not isinstance(value, int)
            or isinstance(value, bool)
            or not 0 <= value <= 4
        ):
            raise SemanticTaskContractError(
                f"risk {key} must be integer 0..4"
            )

    if "PRODUCTION" in ui and "UI" not in ui:
        raise SemanticTaskContractError("PRODUCTION UI requires UI")
    if (
        "ACCESSIBILITY" in ui or "RESPONSIVE" in ui
    ) and "UI" not in ui:
        raise SemanticTaskContractError("UI quality requirements require UI")
    if "SUPPLIED_ONLY" in evidence and "ANALYZE_EVIDENCE" not in actions:
        raise SemanticTaskContractError(
            "SUPPLIED_ONLY requires ANALYZE_EVIDENCE"
        )
    if "TRACEABLE" in evidence and not (
        {"ANALYZE_EVIDENCE", "ANALYZE_DATA"} & set(actions)
    ):
        raise SemanticTaskContractError(
            "TRACEABLE requires an evidence-bearing analysis action"
        )
    if "OPTIMIZE" in actions and not performance:
        raise SemanticTaskContractError(
            "OPTIMIZE requires at least one performance dimension"
        )
    if (
        "HUMAN_APPROVAL" in execution
        and "HUMAN_APPROVAL" not in capabilities
    ):
        raise SemanticTaskContractError(
            "HUMAN_APPROVAL execution requires HUMAN_APPROVAL capability"
        )
    return task
