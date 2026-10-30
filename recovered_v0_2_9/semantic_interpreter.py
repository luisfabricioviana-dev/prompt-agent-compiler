from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Set
import re


def _has(text: str, *phrases: str) -> bool:
    t = text.casefold()
    return any(p.casefold() in t for p in phrases)


def _word(text: str, *words: str) -> bool:
    t = text.casefold()
    return any(re.search(r"(?<!\w)" + re.escape(w.casefold()) + r"(?!\w)", t) for w in words)


@dataclass
class SemanticTaskModel:
    raw_request: str

    create_new: bool = False
    modify_existing: bool = False
    diagnose_failure: bool = False
    review_existing: bool = False
    research: bool = False
    analyze_evidence: bool = False
    analyze_data: bool = False
    design_before_build: bool = False
    architecture_change: bool = False
    improve_quality: bool = False
    improve_performance: bool = False
    performance_assessment_only: bool = False
    performance_dimensions: Set[str] = field(default_factory=set)

    preserve_behavior: bool = False
    evidence_only: bool = False
    traceability_required: bool = False
    current_evidence_required: bool = False

    ui_required: bool = False
    production_ui: bool = False
    accessibility_required: bool = False
    responsive_required: bool = False
    ui_state_description: bool = False

    external_or_persistent_state: bool = False
    operate_external_system: bool = False
    authorization_required: bool = False
    human_approval_required: bool = False
    destructive_action: bool = False
    reversibility_risk: int = 0
    state_domain: str | None = None

    multi_step: bool = False
    large_workload: bool = False
    specialized_roles: bool = False
    independent_review_value: bool = False
    explicit_multi_agent: bool = False
    parallelizable: bool = False
    high_consequence: bool = False
    boundary_problem: bool = False

    ambiguity: int = 0
    contradictions: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    capabilities: List[str] = field(default_factory=list)


def interpret_request(request: str) -> SemanticTaskModel:
    t = request.casefold().strip()
    m = SemanticTaskModel(raw_request=request)

    # --- UI semantic role first, so "erro" in a state list is not treated as DEBUG.
    m.ui_required = _has(t, "dashboard", "formulário", "frontend", "interface", "componente", "botão") or _word(t, "ui")
    m.responsive_required = _has(t, "responsivo", "responsiva", "responsive")
    m.accessibility_required = _has(t, "acessível", "acessibilidade", "navegação por teclado", "aria", "screen reader")
    m.ui_state_description = m.ui_required and _has(t, "estados de", "loading", "empty", "erro", "error")
    m.production_ui = m.ui_required and (
        m.responsive_required or m.accessibility_required or _has(t, "pronto para produção", "produção", "dashboard", "formulário", "estados de")
    )

    # --- Action / lifecycle.
    m.create_new = (_word(t, "crie", "implemente", "construa", "desenvolva", "adicione") or
                    _has(t, "escreva uma função", "escrever uma função", "faça uma função", "criar uma função"))
    m.modify_existing = _has(
        t,
        "melhore", "refatore", "reorganize", "reestruture", "reescreva", "troque toda", "troque a arquitetura",
        "migre", "migração", "atualize", "corrija", "conserte", "reduza o consumo", "reduza a latência",
        "reduza seu tempo", "sem mudar a api", "sem alterar o resultado", "preserve exatamente"
    )
    m.review_existing = _has(t, "revise", "audite", "avalie", "verifique", "faça revisão", "revisão de")
    m.research = _has(t, "pesquise", "opções atuais", "alternativas atuais", "tendência atual", "compare custo")
    m.current_evidence_required = m.research or _has(t, "atuais", "atual para", "tendência atual")

    architecture_mentioned = _has(t, "arquitetura", "arquiteturas")
    architecture_change_action = _has(t, "troque", "reescreva", "reestruture", "migre", "migração", "nova arquitetura")
    m.architecture_change = architecture_mentioned and architecture_change_action
    m.design_before_build = _has(t, "projete", "desenhe a arquitetura", "antes de qualquer implementação", "antes de implement", "projete e implemente") or (
        m.architecture_change and _has(t, "troque toda", "nova arquitetura")
    )
    m.improve_quality = _has(t, "melhore", "mais clara", "reduzir duplicação", "reorganize", "refatore", "reescreva")

    # --- Performance ontology.
    perf_map = {
        "latency": ("latência", "mais rápido", "tempo de execução", "lento", "lenta"),
        "memory": ("memória", "ram"),
        "throughput": ("throughput", "requisições por segundo", "rps"),
        "cost": ("custo", "custos", "créditos", "tokens"),
        "compute": ("cpu", "gpu", "compute"),
        "quality_accuracy": ("acurácia", "accuracy", "qualidade"),
        "general": ("performance", "desempenho"),
    }
    for dim, phrases in perf_map.items():
        if _has(t, *phrases):
            m.performance_dimensions.add(dim)

    explicit_optimize = _has(t, "otimize", "reduza a latência", "reduza o consumo", "reduza seu tempo de execução", "reduza o tempo", "reduza o custo")
    profiling_only = _has(t, "veja se existe algum gargalo", "identifique o gargalo", "meça a baseline", "profile", "perfil") and _has(t, "não faça otimizações ainda", "sem otimizar", "não otimize")
    regression_measurement = _has(t, "meça se", "piorou a performance", "impacto na performance", "regressão de performance")
    m.performance_assessment_only = profiling_only or regression_measurement
    m.improve_performance = explicit_optimize and not profiling_only

    # --- Preserve semantics / regression contract.
    m.preserve_behavior = _has(
        t,
        "sem alterar", "sem mudar", "preserve", "preservando", "não altere",
        "mesmo significado", "significado técnico", "resultado final", "resultado e",
        "api pública", "comportamento observável", "compatibilidade", "sem quebra", "sem piorar"
    )
    if m.preserve_behavior:
        m.constraints.append("preserve_observable_behavior")

    # --- Evidence / documentary semantics.
    docs = _has(t, "documentos", "documentos anexados", "documentos fornecidos", "processo de licenciamento", "processo administrativo", "normas fornecidas")
    evidence_terms = _has(t, "comprovado", "fato documental", "fatos", "interpretação", "pendências", "rastreabilidade", "confronte cada conclusão", "evidências")
    m.analyze_evidence = docs and (_has(t, "analise", "avalie", "reconstrua", "identifique", "confronte") or evidence_terms)
    m.evidence_only = docs and _has(t, "somente", "exclusivamente", "sem usar fontes externas", "não utilize conhecimento externo")
    m.traceability_required = m.analyze_evidence and (
        evidence_terms or m.evidence_only or _has(t, "rastreabilidade", "cada conclusão", "processo administrativo", "processo de licenciamento")
    )
    if m.evidence_only:
        m.constraints.append("external_knowledge_forbidden")

    # --- Structured data / analytical evidence semantics.
    m.analyze_data = _has(t, "analise este csv", "analise o csv", "analise estes dados", "drivers de churn", "recomendação baseada em evidências")

    # --- Failure intent with local semantic role disambiguation.
    failure_phrase = _has(
        t, "não funciona", "falhou", "bug", "deveria", "retornando", "keyerror", "exception",
        "tem alguma coisa errada", "está errada", "está errado", "corrija o bug", "conserte"
    )
    bare_error = _word(t, "erro") and not m.ui_state_description
    m.diagnose_failure = failure_phrase or bare_error

    if m.current_evidence_required:
        m.capabilities.append("web_or_current_evidence_access")

    # --- External / persistent state and capabilities.
    if _has(t, "calendário", "evento existente"):
        m.external_or_persistent_state = True
        m.operate_external_system = True
        m.state_domain = "calendar"
        m.capabilities += ["calendar_read_access", "calendar_write_access"]
    if _has(t, "e-mail", "email", "último e-mail"):
        m.external_or_persistent_state = True
        m.operate_external_system = True
        m.state_domain = "email"
        m.capabilities += ["email_read_access", "email_write_access"]
    if _has(t, "publique", "publicar", "na minha conta", "canal está conectado"):
        m.external_or_persistent_state = True
        m.operate_external_system = True
        m.authorization_required = True
        m.state_domain = "publishing"
        m.capabilities += ["external_write_access", "authorization", "connection_state_access"]
    if _has(t, "arquive a conversa"):
        m.external_or_persistent_state = True
        m.operate_external_system = True
        m.capabilities += ["conversation_state_write_access"]

    # --- Destructive / approval.
    m.destructive_action = _has(t, "exclua todos", "apague todos", "remova todos", "delete todos", "não mantenha backup")
    if m.destructive_action:
        m.external_or_persistent_state = True
        m.operate_external_system = True
        m.authorization_required = True
        m.reversibility_risk = 4
        m.capabilities += ["external_write_access", "authorization"]
    elif m.operate_external_system:
        m.reversibility_risk = 1

    m.human_approval_required = _has(t, "aprovação humana", "só execute depois", "somente após aprovação", "depois de uma aprovação")
    if m.human_approval_required:
        m.authorization_required = True
        m.capabilities.append("human_approval")

    # --- Architecture / clean boundaries.
    m.boundary_problem = _has(t, "acoplamento", "responsabilidades", "persistência", "regras de negócio", "http", "boundaries", "módulos") and m.modify_existing

    # --- Workload / execution shape.
    m.large_workload = bool(re.search(r"\b(?:[12-9]\d\d|\d{4,})\s+páginas\b", t)) or _has(t, "400 páginas", "200 páginas")
    composite_deliverable = (_has(t, "incluindo") and sum(bool(_has(t, x)) for x in ("roteiro", "plano de cenas", "especificações", "narração", "qa")) >= 2)
    m.multi_step = (
        m.design_before_build or m.research or m.analyze_evidence or m.analyze_data or m.external_or_persistent_state or
        m.human_approval_required or m.large_workload or composite_deliverable or
        _has(t, "depois", "e depois", "só então", "antes da aprovação")
    )
    security_context = _has(t, "segurança", "autenticação", "mfa", "sessão", "recuperação de conta")
    m.specialized_roles = (_has(t, "segurança", "jurídic", "técnic", "arquitetura", "performance", "factualidade") and m.multi_step) or (security_context and m.review_existing)
    m.independent_review_value = _has(t, "revisão independente", "sistema crítico", "antes da aprovação", "antes da publicação") or (
        m.analyze_evidence and _has(t, "consequências jurídicas", "jurídicas e técnicas")
    )
    m.explicit_multi_agent = _has(t, "vários agentes", "multiagente", "cinco agentes", "quatro agentes")
    m.parallelizable = m.explicit_multi_agent or _has(t, "quatro arquiteturas independentes", "em paralelo")
    m.high_consequence = (
        _has(t, "sistema crítico", "pagamentos", "produção", "jurídic", "licenciamento", "processo administrativo") or
        security_context or (m.analyze_evidence and _has(t, "normas", "normativo", "cada conclusão")) or m.destructive_action
    )

    # --- Ambiguity.
    if t in {"melhore isso.", "melhore isso", "otimize isso.", "otimize isso", "conserte isso.", "conserte isso"}:
        m.ambiguity = 2

    # --- Contradictions / tensions.
    if m.architecture_change and _has(t, "não altere absolutamente nada"):
        m.contradictions.append("large_internal_change_vs_no_observable_change")

    # Deduplicate capabilities while preserving order.
    seen = set()
    m.capabilities = [x for x in m.capabilities if not (x in seen or seen.add(x))]
    return m
