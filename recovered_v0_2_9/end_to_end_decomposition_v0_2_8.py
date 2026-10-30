from __future__ import annotations
from typing import Any
from normalized_task import NormalizedTask
from semantic_contract import validate_task, SemanticContractError
from policy_v0_2_7 import compile_semantic_task
from models import PatternStatus
from semantic_error_taxonomy_v0_2_8 import decompose_semantic_errors, semantic_exact
from repair_router_v0_2_8 import plan_repairs


def _route_errors(expected_route: dict[str,Any], task: NormalizedTask, causal: bool) -> tuple[list[dict[str,Any]],dict[str,Any]]:
    spec=compile_semantic_task(task)
    selected={pid for pid,d in spec.patterns.items() if d.status != PatternStatus.REJECTED}
    required=set(expected_route.get("required",[])); allowed=set(expected_route.get("allowed",[])); forbidden=set(expected_route.get("forbidden",[]))
    gates={g.gate_id for g in spec.quality_gates}; req_gates=set(expected_route.get("gates",[]))
    errs=[]
    if required-selected:
        errs.append({"code":"POLICY_PATTERN_ERROR","owner":"policy_router","severity":"error","detail":f"missing {sorted(required-selected)}","causal":causal})
    if forbidden&selected:
        errs.append({"code":"POLICY_PATTERN_ERROR","owner":"policy_router","severity":"error","detail":f"forbidden {sorted(forbidden&selected)}","causal":causal})
    unexpected=selected-required-allowed
    if unexpected:
        errs.append({"code":"POLICY_PATTERN_ERROR","owner":"policy_router","severity":"error","detail":f"unexpected {sorted(unexpected)}","causal":causal})
    if req_gates-gates:
        errs.append({"code":"POLICY_GATE_ERROR","owner":"policy_router","severity":"error","detail":f"missing {sorted(req_gates-gates)}","causal":causal})
    if expected_route.get("complexity") and spec.complexity_level not in set(expected_route["complexity"]):
        errs.append({"code":"POLICY_COMPLEXITY_ERROR","owner":"policy_router","severity":"error","detail":f"{spec.complexity_level} not in {expected_route['complexity']}","causal":causal})
    return errs,{"selected":sorted(selected),"gates":sorted(gates),"complexity":spec.complexity_level}


def decompose_case(request: str, expected: dict[str,Any], predicted: dict[str,Any], expected_route: dict[str,Any]) -> dict[str,Any]:
    semantic_errors=decompose_semantic_errors(expected,predicted,request)
    exact=semantic_exact(expected,predicted)
    try:
        task=validate_task(NormalizedTask.from_dict({**predicted,"raw_request":request}))
    except Exception as exc:
        contract={"code":"CONTRACT_VALIDATION_ERROR","owner":"semantic_contract","severity":"critical","detail":str(exc),"causal":True}
        errors=[contract]+semantic_errors
        return {"semantic_exact":False,"errors":errors,"route":None,"repair_plan":plan_repairs(errors)}
    policy_errors,route=_route_errors(expected_route,task,causal=exact)
    # When semantics are wrong, downstream route differences are observational, not causal policy defects.
    if not exact:
        for e in policy_errors:
            e["causal"]=False
    errors=semantic_errors+policy_errors
    return {"semantic_exact":exact,"errors":errors,"route":route,"repair_plan":plan_repairs([e for e in errors if e.get("causal",True)])}
