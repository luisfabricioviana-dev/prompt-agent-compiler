from __future__ import annotations
from typing import Any

OWNER_ORDER = ["provider_boundary","semantic_contract","semantic_interpreter","policy_router","evaluation_fixture"]

REPAIR_GUIDANCE = {
    "provider_boundary": "Repair structured-output parsing, grounding checks, transport, or fail-closed behavior. Do not change routing policy.",
    "semantic_contract": "Repair schema/contract consistency or validator rules. Preserve policy unless a separate policy failure is demonstrated.",
    "semantic_interpreter": "Repair semantic interpretation examples/instructions or model selection. Do not patch policy to compensate for wrong NormalizedTask.",
    "policy_router": "Repair deterministic pattern/gate/complexity rules against correct NormalizedTask. Do not change interpreter prompts to mask policy defects.",
    "evaluation_fixture": "Repair benchmark annotation or fixture only after independent review proves the expected label is wrong.",
}


def plan_repairs(errors: list[dict[str, Any]]) -> dict[str, Any]:
    owners=[]
    for owner in OWNER_ORDER:
        if any(e.get("owner")==owner for e in errors): owners.append(owner)
    if not owners:
        return {"minimum_scope":"none","components_to_change":[],"actions":[],"reverification_scope":"none"}
    minimum=owners[0] if len(owners)==1 else "multi_component"
    actions=[{"component":o,"guidance":REPAIR_GUIDANCE[o]} for o in owners]
    return {
        "minimum_scope": minimum,
        "components_to_change": owners,
        "actions": actions,
        "reverification_scope": "affected_stage_then_end_to_end",
    }
