from __future__ import annotations
from copy import deepcopy
from semantic_error_taxonomy_v0_2_8 import decompose_semantic_errors


def base():
    groups=["actions","preservation","performance_dimensions","evidence_policy","ui_requirements","architecture","external_state","execution","capabilities"]
    d={g:[] for g in groups}; d.update({"risks":{},"unknowns":[],"contradictions":[],"feature_evidence":{}}); return d


def _case(cid,request,expected,predicted,code):
    return {"id":cid,"request":request,"expected":expected,"predicted":predicted,"expected_code":code}


def mutation_cases():
    cases=[]
    e=base(); e["actions"]=["DIAGNOSE"]; p=deepcopy(e); p["actions"]=[]
    cases.append(_case("M01","o serviço falhou",e,p,"INTERPRETER_ACTION_FALSE_NEGATIVE"))

    e=base(); e["actions"]=["CREATE"]; e["ui_requirements"]=["UI","STATEFUL_UI"]; p=deepcopy(e); p["actions"].append("DIAGNOSE")
    cases.append(_case("M02","tela com estado de erro",e,p,"INTERPRETER_ROLE_CONFUSION_UI_ERROR_AS_DEBUG"))

    e=base(); e["performance_dimensions"]=["MEMORY"]; p=deepcopy(e); p["performance_dimensions"]=[]
    cases.append(_case("M03","reduza memória",e,p,"INTERPRETER_PERFORMANCE_DIMENSION_FALSE_NEGATIVE"))

    e=base(); e["evidence_policy"]=["TRACEABLE"]; p=deepcopy(e); p["evidence_policy"]=[]
    cases.append(_case("M04","cite a fonte de cada conclusão",e,p,"INTERPRETER_EVIDENCE_POLICY_FALSE_NEGATIVE"))

    e=base(); e["risks"]={"SECURITY":4}; p=deepcopy(e); p["risks"]={"SECURITY":2}
    cases.append(_case("M05","sistema crítico de segurança",e,p,"INTERPRETER_RISK_UNDERESTIMATION"))

    e=base(); e["contradictions"]=["irreversible vs restore"]; p=deepcopy(e); p["contradictions"]=[]
    cases.append(_case("M06","apague definitivamente mas garanta restauração",e,p,"INTERPRETER_CONTRADICTION_MISS"))

    e=base(); e["actions"]=["CREATE"]; p=deepcopy(e); p["feature_evidence"]={"actions.CREATE":{"source":"EXPLICIT","confidence":0.99,"evidence_span":"trecho inventado","rationale":"x"}}
    cases.append(_case("M07","crie um botão",e,p,"PROVIDER_GROUNDING_ERROR"))

    e=base(); e["external_state"]=["CALENDAR"]; p=deepcopy(e); p["external_state"]=[]
    cases.append(_case("M08","atualize o evento existente",e,p,"INTERPRETER_EXTERNAL_STATE_FALSE_NEGATIVE"))

    e=base(); e["capabilities"]=["HUMAN_APPROVAL"]; p=deepcopy(e); p["capabilities"]=[]
    cases.append(_case("M09","aguarde aprovação humana",e,p,"INTERPRETER_CAPABILITY_FALSE_NEGATIVE"))
    return cases


def run_mutation_suite():
    details=[]; passed=0
    for c in mutation_cases():
        errors=decompose_semantic_errors(c["expected"],c["predicted"],c["request"])
        codes={e["code"] for e in errors}
        ok=c["expected_code"] in codes
        passed += int(ok)
        details.append({"id":c["id"],"expected_code":c["expected_code"],"codes":sorted(codes),"pass":ok})
    return {"cases":len(details),"passed":passed,"pass_rate":passed/len(details) if details else 1.0,"details":details}

if __name__=="__main__":
    import json; print(json.dumps(run_mutation_suite(),indent=2,ensure_ascii=False))
