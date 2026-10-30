from __future__ import annotations
import json
from collections import Counter
from pathlib import Path
from typing import Any

from normalized_task import NormalizedTask
from semantic_contract import SemanticContractError, validate_task
from semantic_eval_v0_2_7 import evaluate_prediction, aggregate, GROUPS
from semantic_error_taxonomy_v0_2_8 import semantic_exact
from end_to_end_decomposition_v0_2_8 import decompose_case


def expanded_expected(case: dict[str, Any]) -> dict[str, Any]:
    x={g:[] for g in GROUPS}
    x.update({"risks":{},"unknowns":[],"contradictions":[],"feature_evidence":{}})
    x.update(case.get("expected",{}))
    return x


def _blocking(errors: list[dict[str,Any]]) -> list[dict[str,Any]]:
    return [e for e in errors if e.get("severity","error") in {"error","critical"} and e.get("causal",True)]


def evaluate_model_provider(provider, cases: list[dict[str,Any]], record_path: str|Path|None=None) -> dict[str,Any]:
    details=[]; semantic_results=[]; recordings={}
    provider_ok=contract_ok=semantic_exact_n=0
    exact_policy_cases=exact_policy_pass=0
    e2e_pass=0
    error_counts=Counter(); owner_counts=Counter(); causal_counts=Counter()

    for case in cases:
        request=case["request"]
        expected=expanded_expected(case)
        try:
            task=provider.interpret(request)
            provider_ok += 1
        except SemanticContractError as exc:
            err={"code":"CONTRACT_VALIDATION_ERROR","owner":"semantic_contract","severity":"critical","detail":str(exc),"causal":True}
            details.append({"id":case["id"],"request":request,"errors":[err],"semantic_exact":False,"route":None})
            error_counts[err["code"]]+=1; owner_counts[err["owner"]]+=1; causal_counts[err["code"]]+=1
            continue
        except Exception as exc:
            err={"code":"INTERPRETER_PROVIDER_ERROR","owner":"provider_boundary","severity":"critical","detail":str(exc),"causal":True}
            details.append({"id":case["id"],"request":request,"errors":[err],"semantic_exact":False,"route":None})
            error_counts[err["code"]]+=1; owner_counts[err["owner"]]+=1; causal_counts[err["code"]]+=1
            continue

        try:
            validate_task(task); contract_ok += 1
        except Exception as exc:
            err={"code":"CONTRACT_VALIDATION_ERROR","owner":"semantic_contract","severity":"critical","detail":str(exc),"causal":True}
            details.append({"id":case["id"],"request":request,"errors":[err],"semantic_exact":False,"route":None})
            error_counts[err["code"]]+=1; owner_counts[err["owner"]]+=1; causal_counts[err["code"]]+=1
            continue

        predicted=task.to_dict()
        recordings[request]=predicted
        semantic_results.append(evaluate_prediction(expected,predicted,request))
        exact=semantic_exact(expected,predicted)
        semantic_exact_n += int(exact)

        decomp=decompose_case(request,expected,predicted,case.get("route",{}))
        if exact:
            exact_policy_cases += 1
            causal_policy=[e for e in decomp["errors"] if e.get("owner")=="policy_router" and e.get("causal",True) and e.get("severity","error") in {"error","critical"}]
            exact_policy_pass += int(not causal_policy)
        blocking=_blocking(decomp["errors"])
        e2e_pass += int(not blocking)

        for e in decomp["errors"]:
            error_counts[e["code"]]+=1; owner_counts[e["owner"]]+=1
            if e.get("causal",True): causal_counts[e["code"]]+=1
        details.append({"id":case["id"],"request":request,**decomp})

    if record_path is not None:
        Path(record_path).write_text(json.dumps(recordings,ensure_ascii=False,indent=2),encoding="utf-8")

    n=len(cases)
    return {
        "cases":n,
        "stage_metrics":{
            "provider_success_rate": provider_ok/n if n else 1.0,
            "contract_valid_rate": contract_ok/n if n else 1.0,
            "semantic_exact_rate": semantic_exact_n/n if n else 1.0,
            "causal_policy_pass_rate": exact_policy_pass/exact_policy_cases if exact_policy_cases else 1.0,
            "end_to_end_pass_rate": e2e_pass/n if n else 1.0,
            "policy_cases_with_exact_semantics": exact_policy_cases,
        },
        "semantic_metrics":aggregate(semantic_results),
        "error_counts":dict(error_counts),
        "owner_counts":dict(owner_counts),
        "causal_error_counts":dict(causal_counts),
        "details":details,
    }
