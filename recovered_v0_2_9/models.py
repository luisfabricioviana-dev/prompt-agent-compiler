
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional


class FeatureSource(str, Enum):
    EXPLICIT = "explicit"
    INFERRED = "inferred"
    UNKNOWN = "unknown"
    CONTRADICTION = "contradiction"


class PatternStatus(str, Enum):
    MANDATORY = "mandatory"
    OPTIONAL = "optional"
    REJECTED = "rejected"


@dataclass
class FeatureValue:
    name: str
    value: Any
    source: FeatureSource
    confidence: float
    evidence_span: Optional[str] = None
    rationale: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["source"] = self.source.value
        return d


@dataclass
class PatternDecision:
    pattern_id: str
    score: float
    status: PatternStatus
    reasons: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pattern_id": self.pattern_id,
            "score": round(self.score, 2),
            "status": self.status.value,
            "reasons": list(self.reasons),
        }


@dataclass
class QualityGate:
    gate_id: str
    category: str
    criterion: str
    blocking: bool = True
    severity: str = "error"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ExecutionSpec:
    raw_request: str
    features: Dict[str, FeatureValue]
    complexity_level: str
    complexity_score: int
    patterns: Dict[str, PatternDecision]
    quality_gates: List[QualityGate]
    constraints: List[str]
    capabilities: List[str]
    contradictions: List[str]
    why_this_route: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "raw_request": self.raw_request,
            "features": {k: v.to_dict() for k, v in self.features.items()},
            "complexity_level": self.complexity_level,
            "complexity_score": self.complexity_score,
            "patterns": {k: v.to_dict() for k, v in self.patterns.items()},
            "quality_gates": [g.to_dict() for g in self.quality_gates],
            "constraints": self.constraints,
            "capabilities": self.capabilities,
            "contradictions": self.contradictions,
            "why_this_route": self.why_this_route,
        }
