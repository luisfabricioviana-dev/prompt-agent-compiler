from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Dict, Set, Any

ALLOWED_ACTIONS = {
    "CREATE","MODIFY","DIAGNOSE","REVIEW","RESEARCH","ANALYZE_EVIDENCE","ANALYZE_DATA","DESIGN","OPTIMIZE","OPERATE"
}
ALLOWED_PRESERVATION = {"BEHAVIOR","API","OUTPUT","MEANING","QUALITY","COMPATIBILITY"}
ALLOWED_PERFORMANCE = {"LATENCY","THROUGHPUT","MEMORY","COMPUTE","FINANCIAL_COST","TOKEN_COST","QUALITY_ACCURACY","RESOURCE_UTILIZATION","GENERAL"}
ALLOWED_EVIDENCE_POLICY = {"OPEN","SUPPLIED_ONLY","CURRENT_EXTERNAL","TRACEABLE"}
ALLOWED_UI = {"UI","PRODUCTION","ACCESSIBILITY","RESPONSIVE","STATEFUL_UI"}
ALLOWED_ARCHITECTURE = {"DESIGN_BEFORE_BUILD","CHANGE","BOUNDARIES","MIGRATION"}
ALLOWED_EXTERNAL_STATE = {"EMAIL","CALENDAR","PUBLISHING","DATABASE","FILES","ACCOUNT","OTHER"}
ALLOWED_EXECUTION = {"MULTI_STEP","LARGE_WORKLOAD","PARALLELIZABLE","INDEPENDENT_REVIEW","EXPLICIT_MULTI_AGENT","HUMAN_APPROVAL","STATEFUL"}
ALLOWED_CAPABILITIES = {
    "WEB_CURRENT_EVIDENCE","FILE_READ","EMAIL_READ","EMAIL_WRITE","CALENDAR_READ","CALENDAR_WRITE",
    "EXTERNAL_WRITE","AUTHORIZATION","CONNECTION_STATE","HUMAN_APPROVAL","PERSISTENT_STATE_READ","PERSISTENT_STATE_WRITE"
}
ALLOWED_RISKS = {"REVERSIBILITY","BLAST_RADIUS","FINANCIAL","LEGAL_REGULATORY","SECURITY","DATA_LOSS","REPUTATIONAL"}


@dataclass(frozen=True)
class SemanticEvidence:
    source: str
    confidence: float
    evidence_span: str | None = None
    rationale: str | None = None

    def __post_init__(self):
        if self.source not in {"EXPLICIT","INFERRED","UNKNOWN","CONTRADICTION"}:
            raise ValueError(f"invalid source: {self.source}")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be in [0,1]")


@dataclass
class NormalizedTask:
    raw_request: str
    actions: Set[str] = field(default_factory=set)
    preservation: Set[str] = field(default_factory=set)
    performance_dimensions: Set[str] = field(default_factory=set)
    evidence_policy: Set[str] = field(default_factory=set)
    ui_requirements: Set[str] = field(default_factory=set)
    architecture: Set[str] = field(default_factory=set)
    external_state: Set[str] = field(default_factory=set)
    execution: Set[str] = field(default_factory=set)
    capabilities: Set[str] = field(default_factory=set)
    risks: Dict[str, int] = field(default_factory=dict)
    feature_evidence: Dict[str, SemanticEvidence] = field(default_factory=dict)
    unknowns: list[str] = field(default_factory=list)
    contradictions: list[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "raw_request": self.raw_request,
            "actions": sorted(self.actions),
            "preservation": sorted(self.preservation),
            "performance_dimensions": sorted(self.performance_dimensions),
            "evidence_policy": sorted(self.evidence_policy),
            "ui_requirements": sorted(self.ui_requirements),
            "architecture": sorted(self.architecture),
            "external_state": sorted(self.external_state),
            "execution": sorted(self.execution),
            "capabilities": sorted(self.capabilities),
            "risks": dict(self.risks),
            "feature_evidence": {k: asdict(v) for k,v in self.feature_evidence.items()},
            "unknowns": list(self.unknowns),
            "contradictions": list(self.contradictions),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "NormalizedTask":
        ev = {k: SemanticEvidence(**v) for k,v in d.get("feature_evidence",{}).items()}
        return cls(
            raw_request=d.get("raw_request", ""),
            actions=set(d.get("actions", [])),
            preservation=set(d.get("preservation", [])),
            performance_dimensions=set(d.get("performance_dimensions", [])),
            evidence_policy=set(d.get("evidence_policy", [])),
            ui_requirements=set(d.get("ui_requirements", [])),
            architecture=set(d.get("architecture", [])),
            external_state=set(d.get("external_state", [])),
            execution=set(d.get("execution", [])),
            capabilities=set(d.get("capabilities", [])),
            risks=dict(d.get("risks", {})),
            feature_evidence=ev,
            unknowns=list(d.get("unknowns", [])),
            contradictions=list(d.get("contradictions", [])),
        )
