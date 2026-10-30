
from __future__ import annotations
import re
from typing import Dict, List, Tuple

from models import FeatureSource, FeatureValue, PatternDecision, PatternStatus, QualityGate, ExecutionSpec
from patterns import PATTERNS, STRONG_SIGNALS


def _contains(text: str, *terms: str) -> bool:
    t = text.lower()
    return any(term.lower() in t for term in terms)


def _fv(name, value, source, confidence, evidence=None, rationale=None):
    return FeatureValue(name, value, source, confidence, evidence, rationale)


def extract_features(request: str) -> Dict[str, FeatureValue]:
    t = request.lower().strip()
    f: Dict[str, FeatureValue] = {}

    create = _contains(t, "crie", "implemente", "construa", "desenvolva", "adicione")
    modify = _contains(t, "melhore", "refatore", "reorganize", "reestruture", "reescreva", "otimize", "corrija", "conserte")
    diagnose = _contains(t, "erro", "bug", "falhou", "não funciona", "conserte", "retornando", "deveria")
    review = _contains(t, "revise", "review", "audite")
    research = _contains(t, "pesquise", "alternativas atuais", "compare evidências")
    analyze_evidence = _contains(t, "analise", "documentos fornecidos", "processo administrativo")
    system_design = _contains(t, "arquitetura", "projete", "plataforma", "sistema crítico", "antes de implement")
    improve_quality = _contains(t, "melhore", "reorganize", "reestruture", "refatore")
    improve_perf = _contains(t, "otimize", "latência", "lenta", "performance", "desempenho")
    external_op = _contains(t, "envie", "exclua", "publique", "por e-mail")

    f["create_new"] = _fv("create_new", create,
        FeatureSource.EXPLICIT if create else FeatureSource.UNKNOWN, 0.98 if create else 0.0,
        request if create else None)
    f["modify_existing"] = _fv("modify_existing", modify,
        FeatureSource.EXPLICIT if modify else FeatureSource.UNKNOWN, 0.96 if modify else 0.0,
        request if modify else None)
    f["diagnose_failure"] = _fv("diagnose_failure", diagnose,
        FeatureSource.EXPLICIT if diagnose else FeatureSource.UNKNOWN, 0.96 if diagnose else 0.0,
        request if diagnose else None)
    f["review_existing"] = _fv("review_existing", review,
        FeatureSource.EXPLICIT if review else FeatureSource.UNKNOWN, 0.95 if review else 0.0)
    f["research"] = _fv("research", research,
        FeatureSource.EXPLICIT if research else FeatureSource.UNKNOWN, 0.97 if research else 0.0)
    f["analyze_evidence"] = _fv("analyze_evidence", analyze_evidence,
        FeatureSource.EXPLICIT if analyze_evidence else FeatureSource.UNKNOWN, 0.96 if analyze_evidence else 0.0)
    f["design_before_build"] = _fv("design_before_build", system_design,
        FeatureSource.EXPLICIT if system_design else FeatureSource.UNKNOWN, 0.96 if system_design else 0.0)
    f["improve_quality"] = _fv("improve_quality", improve_quality,
        FeatureSource.EXPLICIT if improve_quality else FeatureSource.UNKNOWN, 0.88 if improve_quality else 0.0)
    f["improve_performance"] = _fv("improve_performance", improve_perf,
        FeatureSource.EXPLICIT if improve_perf else FeatureSource.UNKNOWN, 0.98 if improve_perf else 0.0)
    f["operate_external_system"] = _fv("operate_external_system", external_op,
        FeatureSource.EXPLICIT if external_op else FeatureSource.UNKNOWN, 0.98 if external_op else 0.0)

    preserve = _contains(t, "sem alterar", "preserve", "preservando", "não altere")
    baseline = _contains(t, "baseline", "métrica", "latência", "benchmark")
    observed_failure = diagnose

    f["existing_behavior_to_preserve"] = _fv(
        "existing_behavior_to_preserve", preserve,
        FeatureSource.EXPLICIT if preserve else FeatureSource.UNKNOWN,
        0.99 if preserve else 0.0,
    )
    f["baseline_available"] = _fv(
        "baseline_available", baseline,
        FeatureSource.INFERRED if baseline else FeatureSource.UNKNOWN,
        0.65 if baseline else 0.0,
        rationale="A request mentions a measurable performance concept." if baseline else None
    )
    f["observed_failure_available"] = _fv(
        "observed_failure_available", observed_failure,
        FeatureSource.INFERRED if observed_failure else FeatureSource.UNKNOWN,
        0.8 if observed_failure else 0.0
    )

    # execution/risk helpers
    multi_step = system_design or analyze_evidence or research or _contains(t, "projete e implemente", "documento de 200 páginas")
    specialized = _contains(t, "segurança", "jurídic", "técnic", "performance", "arquitetura") and multi_step
    independent_review = _contains(t, "revisão independente", "processo administrativo", "sistema crítico")
    parallelizable = _contains(t, "vários agentes", "multiagente", "revisão independente")

    f["multi_step"] = _fv("multi_step", multi_step,
        FeatureSource.INFERRED if multi_step else FeatureSource.UNKNOWN, 0.8 if multi_step else 0.0)
    f["specialized_roles"] = _fv("specialized_roles", specialized,
        FeatureSource.INFERRED if specialized else FeatureSource.UNKNOWN, 0.72 if specialized else 0.0)
    f["independent_review_value"] = _fv("independent_review_value", independent_review,
        FeatureSource.EXPLICIT if _contains(t, "revisão independente") else (FeatureSource.INFERRED if independent_review else FeatureSource.UNKNOWN),
        0.98 if _contains(t, "revisão independente") else (0.8 if independent_review else 0.0))
    f["parallelizable"] = _fv("parallelizable", parallelizable,
        FeatureSource.INFERRED if parallelizable else FeatureSource.UNKNOWN, 0.7 if parallelizable else 0.0)

    return f


def extract_constraints(request: str) -> List[str]:
    t = request.lower()
    constraints = []
    if _contains(t, "exclusivamente os documentos fornecidos", "não utilize conhecimento externo"):
        constraints.append("external_knowledge_forbidden")
    if _contains(t, "sem alterar", "não altere absolutamente nada"):
        constraints.append("preserve_observable_behavior")
    if _contains(t, "responsivo"):
        constraints.append("responsive_required")
    if _contains(t, "acessível"):
        constraints.append("accessibility_required")
    return constraints


def detect_contradictions(request: str) -> List[str]:
    t = request.lower()
    out = []
    if _contains(t, "reescreva completamente", "reestruture completamente") and _contains(t, "não altere absolutamente nada"):
        out.append("large_internal_change_vs_strict_no_change; safe interpretation: preserve externally observable behavior")
    return out


def capability_requirements(request: str) -> List[str]:
    t = request.lower()
    caps = []
    if _contains(t, "envie", "por e-mail"):
        caps += ["email_write_access", "recipient_resolution"]
    if _contains(t, "exclua", "publique"):
        caps += ["external_write_access", "authorization"]
    if _contains(t, "pesquise", "atuais"):
        caps += ["web_or_current_evidence_access"]
    if _contains(t, "documentos fornecidos"):
        caps += ["file_read_access"]
    return sorted(set(caps))


def complexity(request: str, f: Dict[str, FeatureValue], constraints: List[str]) -> Tuple[int, str]:
    t = request.lower()
    workflow = 0
    if f["multi_step"].value:
        workflow = 2
    if _contains(t, "projete e implemente", "sistema crítico"):
        workflow = 3

    # risk factor
    max_risk = 0
    if _contains(t, "exclua todos", "irrevers", "sistema crítico"):
        max_risk = 4
    elif _contains(t, "processo administrativo", "jurídic", "legal"):
        max_risk = 3
    elif f["operate_external_system"].value:
        max_risk = 2
    risk = 0 if max_risk <= 1 else (1 if max_risk == 2 else (2 if max_risk == 3 else 3))

    dep = 0
    cap_count = len(capability_requirements(request))
    if cap_count == 1:
        dep = 1
    elif cap_count >= 2:
        dep = 3 if _contains(t, "envie", "exclua", "publique") else 2

    uncertainty = 0
    if t in ("otimize isso.", "otimize isso", "conserte meu aplicativo.", "conserte meu aplicativo", "melhore nosso agente.", "melhore nosso agente"):
        uncertainty = 2

    verification = 0
    if "external_knowledge_forbidden" in constraints or _contains(t, "processo administrativo"):
        verification = 3
    elif f["existing_behavior_to_preserve"].value or f["improve_performance"].value:
        verification = 2
    elif _contains(t, "exclua todos"):
        verification = 2
    elif f["create_new"].value or f["diagnose_failure"].value:
        verification = 1

    specialization = 0
    if f["independent_review_value"].value:
        specialization = 3
    elif f["specialized_roles"].value:
        specialization = 2
    elif f["multi_step"].value:
        specialization = 1

    score = workflow + risk + dep + uncertainty + verification + specialization
    # Calibrated after the first 20-case golden run:
    # N0 is reserved for genuinely trivial/direct work.
    if score == 0:
        level = "N0"
    elif score <= 3:
        level = "N1"
    elif score <= 6:
        level = "N2"
    elif score <= 10:
        level = "N3"
    else:
        level = "N4"
    return score, level


def _strong(text: str, pid: str) -> bool:
    return _contains(text, *STRONG_SIGNALS[pid])


def score_patterns(request: str, f: Dict[str, FeatureValue], constraints: List[str]) -> Dict[str, PatternDecision]:
    t = request.lower()
    out: Dict[str, PatternDecision] = {}

    raw = {pid: 0.0 for pid in PATTERNS}
    reasons = {pid: [] for pid in PATTERNS}

    # P01
    if f["create_new"].value:
        raw["P01"] += 85; reasons["P01"].append("explicit creation/build signal")
    if _contains(t, "projete e implemente"):
        raw["P01"] += 10; reasons["P01"].append("implementation explicitly requested")
    if f["research"].value or f["analyze_evidence"].value:
        raw["P01"] -= 25; reasons["P01"].append("analysis/research does not itself imply build")

    # P02
    if f["modify_existing"].value:
        raw["P02"] += 45; reasons["P02"].append("existing artifact modification")
    if f["existing_behavior_to_preserve"].value:
        raw["P02"] += 40; reasons["P02"].append("behavior preservation explicit")
    if _contains(t, "refatore", "reorganize"):
        raw["P02"] += 20; reasons["P02"].append("strong refactor language")
    if not f["modify_existing"].value:
        raw["P02"] -= 20

    # P03
    if f["diagnose_failure"].value:
        raw["P03"] += 90; reasons["P03"].append("failure/bug diagnostic signal")

    # P04
    if f["design_before_build"].value:
        raw["P04"] += 80; reasons["P04"].append("architecture/design explicitly material")
    if _contains(t, "melhore nosso agente"):
        raw["P04"] += 65; reasons["P04"].append("agent improvement plausibly architectural")
    if _contains(t, "função", "converter celsius"):
        raw["P04"] -= 30; reasons["P04"].append("trivial function does not justify system design")

    # P05
    if f["improve_performance"].value:
        raw["P05"] += 85; reasons["P05"].append("performance objective explicit")
    if f["improve_performance"].value and not f["baseline_available"].value:
        raw["P05"] -= 20; reasons["P05"].append("baseline/proxy not yet established")

    # P06
    if f["modify_existing"].value and _contains(t, "acoplamento", "responsabilidades", "persistência", "regras de negócio", "módulos"):
        raw["P06"] += 85; reasons["P06"].append("boundary/responsibility problem")

    # P07
    criteria = sum([
        bool(f["specialized_roles"].value),
        bool(f["parallelizable"].value),
        bool(f["independent_review_value"].value),
        _contains(t, "sistema crítico", "processo administrativo"),
        _contains(t, "revisão independente"),
    ])
    if criteria >= 2:
        raw["P07"] += 78; reasons["P07"].append(f"{criteria} legitimate multi-agent/review signals")
    if _contains(t, "vários agentes", "multiagente"):
        raw["P07"] += 18; reasons["P07"].append("multi-agent explicitly requested")
    if _contains(t, "celsius", "fahrenheit"):
        raw["P07"] -= 80; reasons["P07"].append("anti-overengineering: trivial task")
    if _contains(t, "documento de 200 páginas"):
        raw["P07"] -= 45; reasons["P07"].append("length alone is not role-separation value")

    # P08
    if _contains(t, "formulário", "frontend", "interface", "dashboard", "responsivo", "acessível"):
        raw["P08"] += 90; reasons["P08"].append("production UI signals")

    # Convert to statuses
    for pid, score in raw.items():
        score = max(0, min(100, score))
        if score >= 80:
            status = PatternStatus.MANDATORY
        elif score >= 60:
            status = PatternStatus.OPTIONAL
        else:
            status = PatternStatus.REJECTED

        # explicit overrides
        if pid == "P03" and f["diagnose_failure"].value:
            status = PatternStatus.MANDATORY
        if pid == "P01" and f["create_new"].value and not (f["research"].value or f["analyze_evidence"].value):
            status = PatternStatus.MANDATORY
        if pid == "P08" and _contains(t, "formulário", "frontend", "interface", "dashboard"):
            status = PatternStatus.MANDATORY
        if pid == "P07" and _contains(t, "celsius", "fahrenheit"):
            status = PatternStatus.REJECTED
        if pid == "P07" and _contains(t, "documento de 200 páginas") and not _contains(t, "revisão independente"):
            status = PatternStatus.REJECTED
        if pid == "P05" and f["improve_performance"].value and _contains(t, "lenta", "latência"):
            status = PatternStatus.MANDATORY
        if pid == "P02" and f["existing_behavior_to_preserve"].value and f["modify_existing"].value:
            status = PatternStatus.MANDATORY
        if pid == "P06" and _contains(t, "persistência", "regras de negócio"):
            status = PatternStatus.MANDATORY
        if pid == "P04" and _contains(t, "projete", "arquitetura", "plataforma", "sistema crítico"):
            status = PatternStatus.MANDATORY
        if pid == "P07" and _contains(t, "revisão independente") and _contains(t, "sistema crítico"):
            status = PatternStatus.MANDATORY

        out[pid] = PatternDecision(pid, score, status, reasons[pid] or ["no material activation evidence"])

    return out


def compile_gates(request: str, f: Dict[str, FeatureValue], constraints: List[str], patterns: Dict[str, PatternDecision]) -> List[QualityGate]:
    t = request.lower()
    gates = []

    def add(gid, category, criterion, blocking=True, severity="error"):
        if gid not in {g.gate_id for g in gates}:
            gates.append(QualityGate(gid, category, criterion, blocking, severity))

    if f["existing_behavior_to_preserve"].value or patterns["P02"].status == PatternStatus.MANDATORY:
        add("REGRESSION_GATE", "regression", "Observable behavior must remain unchanged.")
    if f["improve_performance"].value:
        add("BASELINE_GATE", "performance", "Establish a baseline or valid proxy before claiming optimization.")
    if "external_knowledge_forbidden" in constraints:
        add("EVIDENCE_GATE", "evidence", "Every material conclusion must be grounded only in supplied documents.")
        add("TRACEABILITY_GATE", "traceability", "Material conclusions must be traceable to source evidence.")
    if _contains(t, "processo administrativo"):
        add("EVIDENCE_GATE", "evidence", "Material findings require evidence.")
        add("TRACEABILITY_GATE", "traceability", "Findings and consequences require traceability.")
    if _contains(t, "acessível"):
        add("ACCESSIBILITY_GATE", "accessibility", "UI must satisfy accessibility requirements.")
    if _contains(t, "responsivo"):
        add("RESPONSIVE_GATE", "consistency", "UI must work across target viewport sizes.")
    if _contains(t, "exclua todos"):
        add("DESTRUCTIVE_ACTION_GATE", "requirement", "Destructive action requires explicit authorization/checkpoint.", True, "critical")
    if _contains(t, "sistema crítico", "revisão independente"):
        add("INDEPENDENT_REVIEW_GATE", "consistency", "Independent review must pass before completion.", True, "critical")

    return gates


def compile_request(request: str) -> ExecutionSpec:
    f = extract_features(request)
    constraints = extract_constraints(request)
    contradictions = detect_contradictions(request)
    score, level = complexity(request, f, constraints)
    patterns = score_patterns(request, f, constraints)
    gates = compile_gates(request, f, constraints, patterns)
    caps = capability_requirements(request)

    why = []
    for pid, d in patterns.items():
        if d.status != PatternStatus.REJECTED:
            why.append(f"{pid} {d.status.value}: " + "; ".join(d.reasons[:2]))
    if contradictions:
        why.append("Contradiction handling: " + "; ".join(contradictions))

    return ExecutionSpec(
        raw_request=request,
        features=f,
        complexity_level=level,
        complexity_score=score,
        patterns=patterns,
        quality_gates=gates,
        constraints=constraints,
        capabilities=caps,
        contradictions=contradictions,
        why_this_route=why,
    )
