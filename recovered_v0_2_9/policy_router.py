from __future__ import annotations
from typing import Dict, List, Tuple

from models import FeatureSource, FeatureValue, PatternDecision, PatternStatus, QualityGate, ExecutionSpec
from patterns import PATTERNS
from semantic_interpreter import SemanticTaskModel, interpret_request


def _fv(name: str, value, explicit: bool = False, confidence: float = 0.9, rationale: str | None = None) -> FeatureValue:
    if value is None or value is False or value == set() or value == []:
        source = FeatureSource.UNKNOWN
        conf = 0.0
    else:
        source = FeatureSource.EXPLICIT if explicit else FeatureSource.INFERRED
        conf = confidence
    return FeatureValue(name=name, value=value, source=source, confidence=conf, rationale=rationale)


def feature_values(m: SemanticTaskModel) -> Dict[str, FeatureValue]:
    names = [
        "create_new", "modify_existing", "diagnose_failure", "review_existing", "research", "analyze_evidence", "analyze_data",
        "design_before_build", "architecture_change", "improve_quality", "improve_performance", "performance_assessment_only",
        "preserve_behavior", "evidence_only", "traceability_required", "current_evidence_required", "ui_required",
        "production_ui", "accessibility_required", "responsive_required", "external_or_persistent_state", "operate_external_system",
        "authorization_required", "human_approval_required", "destructive_action", "multi_step", "large_workload", "specialized_roles",
        "independent_review_value", "explicit_multi_agent", "parallelizable", "high_consequence", "boundary_problem"
    ]
    out = {n: _fv(n, getattr(m, n), confidence=0.88) for n in names}
    out["performance_dimensions"] = _fv("performance_dimensions", sorted(m.performance_dimensions), confidence=0.9)
    out["reversibility_risk"] = _fv("reversibility_risk", m.reversibility_risk, confidence=0.95 if m.reversibility_risk else 0.0)
    out["ambiguity"] = _fv("ambiguity", m.ambiguity, confidence=0.9 if m.ambiguity else 0.0)
    return out


def complexity_from_semantics(m: SemanticTaskModel) -> Tuple[int, str, Dict[str, int]]:
    # Factorized dimensions. These are policy decisions over normalized semantics, not request text.
    workflow = 0
    if m.multi_step:
        workflow = 2
    if m.design_before_build and (m.create_new or m.modify_existing or m.architecture_change):
        workflow = 3
    if m.large_workload and workflow < 2:
        workflow = 2

    consequence = 0
    if m.high_consequence:
        consequence = 2
    if m.destructive_action:
        consequence = 3

    external_state = 0
    if m.external_or_persistent_state:
        external_state = 2
    if m.authorization_required:
        external_state = 3

    uncertainty = min(2, m.ambiguity)

    verification = 0
    if m.create_new or m.diagnose_failure or m.review_existing:
        verification = 1
    if m.preserve_behavior or m.improve_performance or m.performance_assessment_only or m.accessibility_required or m.responsive_required:
        verification = max(verification, 2)
    if m.evidence_only or m.traceability_required or m.independent_review_value or m.human_approval_required or m.destructive_action:
        verification = 3

    reversibility = 0
    if m.reversibility_risk >= 4:
        reversibility = 3
    elif m.reversibility_risk >= 2:
        reversibility = 2
    elif m.reversibility_risk == 1:
        reversibility = 1

    specialization = 0
    if m.specialized_roles:
        specialization = 1
    if m.independent_review_value:
        specialization = 2

    factors = {
        "workflow": workflow,
        "consequence": consequence,
        "external_state": external_state,
        "uncertainty": uncertainty,
        "verification": verification,
        "reversibility": reversibility,
        "specialization": specialization,
    }
    score = sum(factors.values())

    # N0 is genuinely trivial. External state, high consequence, evidence-only and large workload impose floors.
    if score <= 1:
        level = "N0"
    elif score <= 4:
        level = "N1"
    elif score <= 8:
        level = "N2"
    elif score <= 12:
        level = "N3"
    else:
        level = "N4"

    # Semantic complexity floors by task class. These avoid threshold collapse for
    # classes whose minimum process is known independent of raw score magnitude.
    if (m.create_new or m.diagnose_failure or m.review_existing or m.improve_quality or
            m.improve_performance or m.performance_assessment_only or m.modify_existing):
        if level == "N0":
            level = "N1"

    if (m.multi_step or m.design_before_build or m.architecture_change or m.analyze_evidence or m.analyze_data or
            m.external_or_persistent_state or m.large_workload or m.current_evidence_required or
            (m.improve_performance and m.preserve_behavior)):
        if level in {"N0", "N1"}:
            level = "N2"

    if m.destructive_action:
        level = "N4" if score >= 11 else "N3"

    if m.high_consequence and (m.independent_review_value or m.analyze_evidence or m.design_before_build or m.specialized_roles):
        if level in {"N0", "N1", "N2"}:
            level = "N3"

    return score, level, factors


def score_patterns_from_semantics(m: SemanticTaskModel) -> Dict[str, PatternDecision]:
    raw = {pid: 0.0 for pid in PATTERNS}
    reasons = {pid: [] for pid in PATTERNS}

    # P01 BUILD
    if m.create_new:
        raw["P01"] += 85; reasons["P01"].append("normalized create_new=true")
    if m.research and not m.create_new:
        raw["P01"] -= 30; reasons["P01"].append("research-only does not imply build")
    if m.analyze_evidence and not m.create_new:
        raw["P01"] -= 30; reasons["P01"].append("evidence analysis does not imply build")

    # P02 REFACTOR / behavior-preserving modification
    if m.modify_existing:
        raw["P02"] += 48; reasons["P02"].append("normalized modify_existing=true")
    if m.preserve_behavior:
        raw["P02"] += 38; reasons["P02"].append("preservation contract present")
    if m.boundary_problem:
        raw["P02"] += 12; reasons["P02"].append("structural/boundary improvement")

    # P03 DEBUG
    if m.diagnose_failure:
        raw["P03"] += 92; reasons["P03"].append("failure intent after semantic-role disambiguation")

    # P04 SYSTEM DESIGN
    if m.design_before_build:
        raw["P04"] += 85; reasons["P04"].append("design_before_build=true")
    elif m.architecture_change:
        raw["P04"] += 72; reasons["P04"].append("material architecture change")
    if m.ui_required and not m.design_before_build:
        raw["P04"] -= 15; reasons["P04"].append("UI work alone is not system design")

    # P05 OPTIMIZE
    if m.improve_performance:
        raw["P05"] += 90; reasons["P05"].append("explicit performance improvement objective")
    elif m.performance_assessment_only:
        raw["P05"] += 65; reasons["P05"].append("profiling/bottleneck assessment only")

    # P06 CLEAN ARCHITECTURE
    if m.boundary_problem:
        raw["P06"] += 88; reasons["P06"].append("normalized boundary/responsibility problem")
    elif m.architecture_change and m.modify_existing:
        raw["P06"] += 58; reasons["P06"].append("architecture migration may benefit from modularization")

    # P07 MULTI-AGENT -- explicit request is insufficient without task value.
    legitimate = sum([
        bool(m.specialized_roles), bool(m.parallelizable), bool(m.independent_review_value), bool(m.high_consequence)
    ])
    if legitimate >= 3:
        raw["P07"] += 82; reasons["P07"].append(f"{legitimate} independent role/value signals")
    elif legitimate >= 2:
        raw["P07"] += 62; reasons["P07"].append(f"{legitimate} role/value signals")
    if m.explicit_multi_agent:
        raw["P07"] += 10; reasons["P07"].append("multi-agent explicitly requested")
    if m.explicit_multi_agent and not (m.specialized_roles or m.parallelizable or m.independent_review_value or m.high_consequence):
        raw["P07"] = 0; reasons["P07"].append("anti-overengineering: no real role separation/value")

    # P08 PRODUCTION UI
    if m.production_ui:
        raw["P08"] += 92; reasons["P08"].append("production UI requirements")
    elif m.ui_required:
        raw["P08"] += 62; reasons["P08"].append("UI deliverable without production-hardening requirements")

    out: Dict[str, PatternDecision] = {}
    for pid, score in raw.items():
        score = max(0.0, min(100.0, score))
        if score >= 80:
            status = PatternStatus.MANDATORY
        elif score >= 60:
            status = PatternStatus.OPTIONAL
        else:
            status = PatternStatus.REJECTED

        # Policy overrides based only on normalized semantics.
        if pid == "P01" and m.create_new and not (m.research and not m.create_new):
            status = PatternStatus.MANDATORY
        if pid == "P02" and m.modify_existing and m.preserve_behavior:
            status = PatternStatus.MANDATORY
        if pid == "P03" and m.diagnose_failure:
            status = PatternStatus.MANDATORY
        if pid == "P04" and m.design_before_build:
            status = PatternStatus.MANDATORY
        if pid == "P05" and m.improve_performance:
            status = PatternStatus.MANDATORY
        if pid == "P06" and m.boundary_problem:
            status = PatternStatus.MANDATORY
        if pid == "P08" and m.production_ui:
            status = PatternStatus.MANDATORY
        if pid == "P07" and m.explicit_multi_agent and not (m.specialized_roles or m.parallelizable or m.independent_review_value or m.high_consequence):
            status = PatternStatus.REJECTED

        out[pid] = PatternDecision(pid, score, status, reasons[pid] or ["no normalized activation evidence"])
    return out


def compile_gates_from_semantics(m: SemanticTaskModel) -> List[QualityGate]:
    gates: List[QualityGate] = []
    seen = set()

    def add(gid: str, category: str, criterion: str, blocking: bool = True, severity: str = "error"):
        if gid not in seen:
            gates.append(QualityGate(gid, category, criterion, blocking, severity))
            seen.add(gid)

    if m.preserve_behavior:
        add("REGRESSION_GATE", "regression", "Preserved observable behavior/meaning must remain equivalent.")
    if m.improve_performance or m.performance_assessment_only:
        add("BASELINE_GATE", "performance", "Measure a baseline or valid proxy before optimization/performance conclusions.")
    if m.evidence_only or m.analyze_evidence:
        add("EVIDENCE_GATE", "evidence", "Material findings require source-grounded evidence.")
    if m.evidence_only or m.traceability_required:
        add("TRACEABILITY_GATE", "traceability", "Material conclusions must be traceable to source evidence.")
    if m.accessibility_required:
        add("ACCESSIBILITY_GATE", "accessibility", "Accessibility requirements must be verified.")
    if m.responsive_required:
        add("RESPONSIVE_GATE", "consistency", "Responsive behavior must be verified across target viewports.")
    if m.destructive_action:
        add("DESTRUCTIVE_ACTION_GATE", "requirement", "Destructive state change requires explicit authorization and consequence check.", True, "critical")
    if m.independent_review_value:
        add("INDEPENDENT_REVIEW_GATE", "consistency", "Independent review must pass before release/approval.", True, "critical")
    if m.human_approval_required:
        add("HUMAN_APPROVAL_GATE", "requirement", "Execution must not proceed before explicit human approval.", True, "critical")
    return gates


def compile_request(request: str) -> ExecutionSpec:
    m = interpret_request(request)
    score, level, factors = complexity_from_semantics(m)
    patterns = score_patterns_from_semantics(m)
    gates = compile_gates_from_semantics(m)

    why = [f"semantic factors: {factors}"]
    for pid, d in patterns.items():
        if d.status != PatternStatus.REJECTED:
            why.append(f"{pid} {d.status.value}: " + "; ".join(d.reasons[:2]))
    if m.contradictions:
        why.append("contradictions: " + "; ".join(m.contradictions))

    return ExecutionSpec(
        raw_request=request,
        features=feature_values(m),
        complexity_level=level,
        complexity_score=score,
        patterns=patterns,
        quality_gates=gates,
        constraints=list(m.constraints),
        capabilities=list(m.capabilities),
        contradictions=list(m.contradictions),
        why_this_route=why,
    )
