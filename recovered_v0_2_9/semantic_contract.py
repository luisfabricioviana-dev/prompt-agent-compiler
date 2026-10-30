from __future__ import annotations
from normalized_task import (
    NormalizedTask, ALLOWED_ACTIONS, ALLOWED_PRESERVATION, ALLOWED_PERFORMANCE, ALLOWED_EVIDENCE_POLICY,
    ALLOWED_UI, ALLOWED_ARCHITECTURE, ALLOWED_EXTERNAL_STATE, ALLOWED_EXECUTION, ALLOWED_CAPABILITIES, ALLOWED_RISKS
)


class SemanticContractError(ValueError):
    pass


def _subset(name, values, allowed):
    invalid=set(values)-set(allowed)
    if invalid:
        raise SemanticContractError(f"{name} contains invalid values: {sorted(invalid)}")


def validate_task(t: NormalizedTask) -> NormalizedTask:
    _subset("actions", t.actions, ALLOWED_ACTIONS)
    _subset("preservation", t.preservation, ALLOWED_PRESERVATION)
    _subset("performance_dimensions", t.performance_dimensions, ALLOWED_PERFORMANCE)
    _subset("evidence_policy", t.evidence_policy, ALLOWED_EVIDENCE_POLICY)
    _subset("ui_requirements", t.ui_requirements, ALLOWED_UI)
    _subset("architecture", t.architecture, ALLOWED_ARCHITECTURE)
    _subset("external_state", t.external_state, ALLOWED_EXTERNAL_STATE)
    _subset("execution", t.execution, ALLOWED_EXECUTION)
    _subset("capabilities", t.capabilities, ALLOWED_CAPABILITIES)
    _subset("risks", t.risks, ALLOWED_RISKS)

    for k,v in t.risks.items():
        if not isinstance(v, int) or not 0 <= v <= 4:
            raise SemanticContractError(f"risk {k} must be integer 0..4")

    if "PRODUCTION" in t.ui_requirements and "UI" not in t.ui_requirements:
        raise SemanticContractError("PRODUCTION UI requires UI")
    if ("ACCESSIBILITY" in t.ui_requirements or "RESPONSIVE" in t.ui_requirements) and "UI" not in t.ui_requirements:
        raise SemanticContractError("UI quality requirements require UI")
    if "SUPPLIED_ONLY" in t.evidence_policy and "ANALYZE_EVIDENCE" not in t.actions:
        raise SemanticContractError("SUPPLIED_ONLY requires ANALYZE_EVIDENCE")
    if "TRACEABLE" in t.evidence_policy and not ({"ANALYZE_EVIDENCE","ANALYZE_DATA"} & t.actions):
        raise SemanticContractError("TRACEABLE requires an evidence-bearing analysis action")
    if "OPTIMIZE" in t.actions and not t.performance_dimensions:
        raise SemanticContractError("OPTIMIZE requires at least one performance dimension")
    if "HUMAN_APPROVAL" in t.execution and "HUMAN_APPROVAL" not in t.capabilities:
        raise SemanticContractError("HUMAN_APPROVAL execution requires HUMAN_APPROVAL capability")

    return t
