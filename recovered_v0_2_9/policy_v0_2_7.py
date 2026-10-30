from __future__ import annotations
from typing import Dict, List

from normalized_task import NormalizedTask
from semantic_contract import validate_task
from models import FeatureSource, FeatureValue, PatternDecision, PatternStatus, QualityGate, ExecutionSpec
from patterns import PATTERNS


def _present(s, item): return item in s


def _feature_values(t: NormalizedTask) -> Dict[str, FeatureValue]:
    groups = {
        "actions": sorted(t.actions),
        "preservation": sorted(t.preservation),
        "performance_dimensions": sorted(t.performance_dimensions),
        "evidence_policy": sorted(t.evidence_policy),
        "ui_requirements": sorted(t.ui_requirements),
        "architecture": sorted(t.architecture),
        "external_state": sorted(t.external_state),
        "execution": sorted(t.execution),
        "capabilities": sorted(t.capabilities),
        "risks": dict(t.risks),
    }
    out={}
    for name,value in groups.items():
        ev=t.feature_evidence.get(name)
        if ev:
            src={"EXPLICIT":FeatureSource.EXPLICIT,"INFERRED":FeatureSource.INFERRED,"UNKNOWN":FeatureSource.UNKNOWN,"CONTRADICTION":FeatureSource.CONTRADICTION}[ev.source]
            out[name]=FeatureValue(name,value,src,ev.confidence,ev.evidence_span,ev.rationale)
        else:
            out[name]=FeatureValue(name,value,FeatureSource.INFERRED,0.8 if value else 0.0,None,"normalized semantic contract")
    return out


def _complexity(t: NormalizedTask):
    workflow = 0
    if "MULTI_STEP" in t.execution: workflow=2
    if "DESIGN_BEFORE_BUILD" in t.architecture and ({"CREATE","MODIFY"}&t.actions): workflow=3
    if "LARGE_WORKLOAD" in t.execution: workflow=max(workflow,2)

    consequence = max(t.risks.get("LEGAL_REGULATORY",0), t.risks.get("SECURITY",0), t.risks.get("FINANCIAL",0), t.risks.get("DATA_LOSS",0))
    consequence = 0 if consequence <=1 else (1 if consequence==2 else (2 if consequence==3 else 3))

    state = 0
    if t.external_state or "STATEFUL" in t.execution: state=2
    if "AUTHORIZATION" in t.capabilities or "HUMAN_APPROVAL" in t.execution: state=3

    uncertainty = 2 if t.unknowns else 0
    if len(t.unknowns)>=3: uncertainty=3

    verification=0
    if {"CREATE","DIAGNOSE","REVIEW"}&t.actions: verification=1
    if t.preservation or "OPTIMIZE" in t.actions or "ACCESSIBILITY" in t.ui_requirements or "RESPONSIVE" in t.ui_requirements: verification=max(verification,2)
    if "TRACEABLE" in t.evidence_policy or "SUPPLIED_ONLY" in t.evidence_policy or "INDEPENDENT_REVIEW" in t.execution or "HUMAN_APPROVAL" in t.execution: verification=3

    reversibility = 0
    rv=t.risks.get("REVERSIBILITY",0)
    if rv>=4: reversibility=3
    elif rv>=2: reversibility=2
    elif rv==1: reversibility=1

    specialization=0
    if "PARALLELIZABLE" in t.execution: specialization=1
    if "INDEPENDENT_REVIEW" in t.execution: specialization=2

    score=sum([workflow,consequence,state,uncertainty,verification,reversibility,specialization])
    if score<=1: level="N0"
    elif score<=4: level="N1"
    elif score<=8: level="N2"
    elif score<=12: level="N3"
    else: level="N4"

    # semantic floors
    if t.actions and level=="N0": level="N1"
    if ("MULTI_STEP" in t.execution or "DESIGN_BEFORE_BUILD" in t.architecture or "ANALYZE_EVIDENCE" in t.actions or
        "ANALYZE_DATA" in t.actions or t.external_state or "LARGE_WORKLOAD" in t.execution or "CURRENT_EXTERNAL" in t.evidence_policy or
        "PRODUCTION" in t.ui_requirements or ("OPTIMIZE" in t.actions and bool(t.preservation))):
        if level in {"N0","N1"}: level="N2"
    if (t.risks.get("LEGAL_REGULATORY",0)>=3 or t.risks.get("SECURITY",0)>=3 or t.risks.get("FINANCIAL",0)>=3) and (
        "INDEPENDENT_REVIEW" in t.execution or "DESIGN" in t.actions or "ANALYZE_EVIDENCE" in t.actions):
        if level in {"N0","N1","N2"}: level="N3"
    if t.risks.get("REVERSIBILITY",0)>=4 and t.risks.get("DATA_LOSS",0)>=3:
        if level in {"N0","N1","N2"}: level="N3"
    return score,level


def _patterns(t: NormalizedTask) -> Dict[str, PatternDecision]:
    raw={p:0.0 for p in PATTERNS}; why={p:[] for p in PATTERNS}
    if "CREATE" in t.actions: raw["P01"]+=90; why["P01"].append("CREATE action")
    if "MODIFY" in t.actions: raw["P02"]+=48; why["P02"].append("MODIFY action")
    if t.preservation: raw["P02"]+=40; why["P02"].append("preservation contract")
    if "DIAGNOSE" in t.actions: raw["P03"]+=95; why["P03"].append("DIAGNOSE action")
    if "DESIGN" in t.actions or "DESIGN_BEFORE_BUILD" in t.architecture: raw["P04"]+=90; why["P04"].append("system design semantics")
    elif "CHANGE" in t.architecture and "BOUNDARIES" not in t.architecture: raw["P04"]+=65; why["P04"].append("material architecture change")
    elif "CHANGE" in t.architecture and "BOUNDARIES" in t.architecture: why["P04"].append("boundary refactor handled by P06 without separate design signal")
    if "OPTIMIZE" in t.actions: raw["P05"]+=92; why["P05"].append("OPTIMIZE action")
    elif t.performance_dimensions and "REVIEW" in t.actions: raw["P05"]+=62; why["P05"].append("performance review/profile")
    if "BOUNDARIES" in t.architecture: raw["P06"]+=90; why["P06"].append("boundary/modularity semantics")
    value_signals=sum(["PARALLELIZABLE" in t.execution,"INDEPENDENT_REVIEW" in t.execution,max(t.risks.values(),default=0)>=3])
    if value_signals>=2: raw["P07"]+=70; why["P07"].append("independent specialization/review value")
    if value_signals>=3: raw["P07"]+=15
    if "EXPLICIT_MULTI_AGENT" in t.execution: raw["P07"]+=10; why["P07"].append("explicit multi-agent request")
    if "EXPLICIT_MULTI_AGENT" in t.execution and value_signals==0:
        raw["P07"]=0; why["P07"].append("anti-overengineering")
    if "PRODUCTION" in t.ui_requirements: raw["P08"]+=95; why["P08"].append("production UI")
    elif "UI" in t.ui_requirements: raw["P08"]+=65; why["P08"].append("UI deliverable")

    out={}
    for pid,score in raw.items():
        score=max(0,min(100,score))
        status=PatternStatus.MANDATORY if score>=80 else (PatternStatus.OPTIONAL if score>=60 else PatternStatus.REJECTED)
        if pid=="P01" and "CREATE" in t.actions: status=PatternStatus.MANDATORY
        if pid=="P02" and "MODIFY" in t.actions and t.preservation: status=PatternStatus.MANDATORY
        if pid=="P03" and "DIAGNOSE" in t.actions: status=PatternStatus.MANDATORY
        if pid=="P04" and ("DESIGN" in t.actions or "DESIGN_BEFORE_BUILD" in t.architecture): status=PatternStatus.MANDATORY
        if pid=="P05" and "OPTIMIZE" in t.actions: status=PatternStatus.MANDATORY
        if pid=="P06" and "BOUNDARIES" in t.architecture: status=PatternStatus.MANDATORY
        if pid=="P08" and "PRODUCTION" in t.ui_requirements: status=PatternStatus.MANDATORY
        if pid=="P07" and "EXPLICIT_MULTI_AGENT" in t.execution and value_signals==0: status=PatternStatus.REJECTED
        out[pid]=PatternDecision(pid,score,status,why[pid] or ["no normalized activation evidence"])
    return out


def _gates(t: NormalizedTask) -> List[QualityGate]:
    gates=[]; seen=set()
    def add(gid,cat,criterion,blocking=True,severity="error"):
        if gid not in seen:
            gates.append(QualityGate(gid,cat,criterion,blocking,severity)); seen.add(gid)
    if t.preservation: add("REGRESSION_GATE","regression","Preservation contract must be verified.")
    if "OPTIMIZE" in t.actions or (t.performance_dimensions and "REVIEW" in t.actions): add("BASELINE_GATE","performance","Baseline/proxy required for performance conclusions.")
    if "ANALYZE_EVIDENCE" in t.actions: add("EVIDENCE_GATE","evidence","Material conclusions require source evidence.")
    if "TRACEABLE" in t.evidence_policy: add("TRACEABILITY_GATE","traceability","Material conclusions must be source traceable.")
    if "ACCESSIBILITY" in t.ui_requirements: add("ACCESSIBILITY_GATE","accessibility","Accessibility must be verified.")
    if "RESPONSIVE" in t.ui_requirements: add("RESPONSIVE_GATE","consistency","Responsive behavior must be verified.")
    if t.risks.get("REVERSIBILITY",0)>=4 or t.risks.get("DATA_LOSS",0)>=4: add("DESTRUCTIVE_ACTION_GATE","requirement","Destructive action requires explicit authorization.",True,"critical")
    if "INDEPENDENT_REVIEW" in t.execution: add("INDEPENDENT_REVIEW_GATE","consistency","Independent review must pass.",True,"critical")
    if "HUMAN_APPROVAL" in t.execution: add("HUMAN_APPROVAL_GATE","requirement","Explicit human approval required before execution.",True,"critical")
    return gates


def compile_semantic_task(t: NormalizedTask) -> ExecutionSpec:
    validate_task(t)
    score,level=_complexity(t)
    patterns=_patterns(t); gates=_gates(t)
    why=["Policy v0.2.6 consumed only NormalizedTask; request wording was not inspected."]
    why += [f"{p} {d.status.value}: {'; '.join(d.reasons[:2])}" for p,d in patterns.items() if d.status != PatternStatus.REJECTED]
    return ExecutionSpec(
        raw_request=t.raw_request,
        features=_feature_values(t),
        complexity_level=level,
        complexity_score=score,
        patterns=patterns,
        quality_gates=gates,
        constraints=sorted(t.preservation | t.evidence_policy),
        capabilities=sorted(t.capabilities),
        contradictions=list(t.contradictions),
        why_this_route=why,
    )
