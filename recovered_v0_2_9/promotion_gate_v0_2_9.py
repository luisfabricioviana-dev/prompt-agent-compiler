from __future__ import annotations
THRESHOLDS={
 "provider_success_rate":1.0,
 "contract_valid_rate":1.0,
 "semantic_exact_rate":0.85,
 "end_to_end_pass_rate":0.90,
 "critical_risk_recall":1.0,
 "evidence_grounding_rate":1.0,
 "min_group_f1":0.90,
 "feature_evidence_coverage":0.90,
 "contradiction_accuracy":0.95,
}
def _semantic(report,key,default=0.0):
    sm=report.get("semantic_metrics",{}) or {}
    if key=="critical_risk_recall": return sm.get("critical_risk_recall",sm.get("risk",{}).get("critical_recall",default))
    if key=="evidence_grounding_rate": return sm.get("evidence_grounding_rate",sm.get("evidence_span_grounding",default))
    return sm.get(key,default)
def decide_promotion(report):
    st=report.get("stage_metrics",{}) or {}; sm=report.get("semantic_metrics",{}) or {}
    checks=[]
    for key in ("provider_success_rate","contract_valid_rate","semantic_exact_rate","end_to_end_pass_rate"):
        value=float(st.get(key,0)); checks.append({"metric":key,"value":value,"threshold":THRESHOLDS[key],"pass":value>=THRESHOLDS[key]})
    for key in ("critical_risk_recall","evidence_grounding_rate"):
        value=float(_semantic(report,key)); checks.append({"metric":key,"value":value,"threshold":THRESHOLDS[key],"pass":value>=THRESHOLDS[key]})
    groups=sm.get("groups",{}) or {}
    min_f1=min((float(v.get("f1",0)) for v in groups.values()),default=1.0)
    checks.append({"metric":"min_group_f1","value":min_f1,"threshold":THRESHOLDS["min_group_f1"],"pass":min_f1>=THRESHOLDS["min_group_f1"]})
    for key in ("feature_evidence_coverage","contradiction_accuracy"):
        value=float(sm.get(key,0)); checks.append({"metric":key,"value":value,"threshold":THRESHOLDS[key],"pass":value>=THRESHOLDS[key]})
    return {"promote":all(x["pass"] for x in checks),"checks":checks,"thresholds":dict(THRESHOLDS)}
