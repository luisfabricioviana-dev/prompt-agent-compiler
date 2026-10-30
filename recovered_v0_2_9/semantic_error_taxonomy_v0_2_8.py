from __future__ import annotations
from typing import Any

GROUPS = [
    "actions", "preservation", "performance_dimensions", "evidence_policy",
    "ui_requirements", "architecture", "external_state", "execution", "capabilities"
]

GROUP_PREFIX = {
    "actions":"ACTION", "preservation":"PRESERVATION", "performance_dimensions":"PERFORMANCE_DIMENSION",
    "evidence_policy":"EVIDENCE_POLICY", "ui_requirements":"UI_REQUIREMENT", "architecture":"ARCHITECTURE",
    "external_state":"EXTERNAL_STATE", "execution":"EXECUTION", "capabilities":"CAPABILITY"
}


def _err(code: str, owner: str, detail: str, severity: str = "error", **extra) -> dict[str, Any]:
    return {"code":code, "owner":owner, "severity":severity, "detail":detail, **extra}


def _grounding_errors(predicted: dict[str, Any], request: str) -> list[dict[str, Any]]:
    out=[]
    ev = predicted.get("feature_evidence", {}) or {}
    items = ev.items() if isinstance(ev, dict) else [(x.get("feature"), x) for x in ev]
    for feature,item in items:
        if not item or item.get("source") != "EXPLICIT":
            continue
        span=item.get("evidence_span")
        if not span or span not in request:
            out.append(_err(
                "PROVIDER_GROUNDING_ERROR","provider_boundary",
                f"explicit evidence for {feature!r} is not grounded in the request",
                severity="critical", feature=feature, evidence_span=span
            ))
    return out


def decompose_semantic_errors(expected: dict[str, Any], predicted: dict[str, Any], request: str) -> list[dict[str, Any]]:
    """Classify semantic differences by the component that can causally repair them.

    This function compares normalized semantics. It intentionally does not inspect
    routing outcomes; policy failures are classified downstream only when semantics
    are exact enough to make that attribution causal.
    """
    errors: list[dict[str, Any]] = []

    # Boundary integrity outranks semantic scoring.
    errors.extend(_grounding_errors(predicted, request))

    # Specific role confusion before generic false-positive classification.
    e_ui=set(expected.get("ui_requirements", [])); p_actions=set(predicted.get("actions", []))
    if "STATEFUL_UI" in e_ui and "DIAGNOSE" in p_actions and "DIAGNOSE" not in set(expected.get("actions", [])):
        errors.append(_err(
            "INTERPRETER_ROLE_CONFUSION_UI_ERROR_AS_DEBUG","semantic_interpreter",
            "UI error-state semantics were confused with software-failure diagnosis"
        ))

    for group in GROUPS:
        e=set(expected.get(group, [])); p=set(predicted.get(group, []))
        for value in sorted(e-p):
            errors.append(_err(
                f"INTERPRETER_{GROUP_PREFIX[group]}_FALSE_NEGATIVE","semantic_interpreter",
                f"missing normalized feature {group}.{value}", feature=f"{group}.{value}"
            ))
        for value in sorted(p-e):
            # Avoid duplicating the specialized UI role-confusion as a generic action FP.
            if group=="actions" and value=="DIAGNOSE" and "STATEFUL_UI" in e_ui:
                continue
            errors.append(_err(
                f"INTERPRETER_{GROUP_PREFIX[group]}_FALSE_POSITIVE","semantic_interpreter",
                f"unsupported normalized feature {group}.{value}", feature=f"{group}.{value}"
            ))

    er={k:int(v) for k,v in (expected.get("risks",{}) or {}).items()}
    pr={k:int(v) for k,v in (predicted.get("risks",{}) or {}).items()}
    for key in sorted(set(er)|set(pr)):
        ev,pv=er.get(key,0),pr.get(key,0)
        if pv < ev:
            severity="critical" if ev>=3 and pv<3 else "error"
            errors.append(_err(
                "INTERPRETER_RISK_UNDERESTIMATION","semantic_interpreter",
                f"risk {key} expected {ev} but predicted {pv}", severity=severity,
                risk=key, expected=ev, predicted=pv
            ))
        elif pv > ev:
            errors.append(_err(
                "INTERPRETER_RISK_OVERESTIMATION","semantic_interpreter",
                f"risk {key} expected {ev} but predicted {pv}", severity="warning",
                risk=key, expected=ev, predicted=pv
            ))

    ec=bool(expected.get("contradictions")); pc=bool(predicted.get("contradictions"))
    if ec and not pc:
        errors.append(_err("INTERPRETER_CONTRADICTION_MISS","semantic_interpreter","expected contradiction was not detected"))
    elif pc and not ec:
        errors.append(_err("INTERPRETER_CONTRADICTION_HALLUCINATION","semantic_interpreter","contradiction was predicted without benchmark support","warning"))

    # Evidence coverage is a distinct interpreter-output quality issue.
    required=set()
    for group in GROUPS:
        required |= {f"{group}.{v}" for v in expected.get(group, [])}
    required |= {f"risks.{k}" for k,v in er.items() if int(v)>0}
    ev = predicted.get("feature_evidence", {}) or {}
    supplied=set(ev) if isinstance(ev,dict) else {x.get("feature") for x in ev if x.get("feature")}
    for feature in sorted(required-supplied):
        errors.append(_err(
            "INTERPRETER_EVIDENCE_COVERAGE_MISS","semantic_interpreter",
            f"material feature {feature} has no feature_evidence", severity="warning", feature=feature
        ))

    return errors


def semantic_exact(expected: dict[str, Any], predicted: dict[str, Any]) -> bool:
    for group in GROUPS:
        if set(expected.get(group, [])) != set(predicted.get(group, [])):
            return False
    if {k:int(v) for k,v in (expected.get("risks",{}) or {}).items() if int(v)} != {k:int(v) for k,v in (predicted.get("risks",{}) or {}).items() if int(v)}:
        return False
    if bool(expected.get("contradictions")) != bool(predicted.get("contradictions")):
        return False
    return True
