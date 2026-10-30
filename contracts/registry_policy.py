"""Registry-aware deterministic policy for v0.2.10.

The routing behavior intentionally mirrors recovered v0.2.9. PatternRegistry
becomes the authoritative identity/metadata contract, but this wave does not
retune scores, thresholds, gates, complexity, or anti-overengineering rules.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .pattern_registry import PatternRegistry
from .semantic_task_contract import validate_normalized_task


REGISTRY_CONTRACT = "P01-P08-v0.2.10"
_EXPECTED_PATTERN_METADATA = {
    "P01": ("BUILD", 2),
    "P02": ("REFACTOR", 2),
    "P03": ("DEBUG", 2),
    "P04": ("SYSTEM_DESIGN", 3),
    "P05": ("OPTIMIZE", 2),
    "P06": ("CLEAN_ARCHITECTURE", 3),
    "P07": ("MULTI_AGENT", 4),
    "P08": ("PRODUCTION_UI", 2),
}


class RegistryPolicyContractError(RuntimeError):
    pass


@dataclass(frozen=True)
class RegistryPatternDecision:
    pattern_id: str
    pattern_name: str
    score: float
    status: str
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class RegistryQualityGate:
    gate_id: str
    category: str
    criterion: str
    blocking: bool = True
    severity: str = "error"


@dataclass(frozen=True)
class RegistryPolicyResult:
    raw_request: str
    complexity_level: str
    complexity_score: int
    patterns: Mapping[str, RegistryPatternDecision]
    quality_gates: tuple[RegistryQualityGate, ...]
    constraints: tuple[str, ...]
    capabilities: tuple[str, ...]
    contradictions: tuple[str, ...]
    why_this_route: tuple[str, ...]
    registry_contract: str = REGISTRY_CONTRACT


def _status_value(value: Any) -> str:
    raw = getattr(value, "value", value)
    return str(raw)


def route_signature(result: Any) -> dict[str, Any]:
    """Normalize legacy and v0.2.10 route outputs for equivalence checks."""
    patterns = {}
    for pid, decision in dict(getattr(result, "patterns", {}) or {}).items():
        patterns[pid] = {
            "score": float(getattr(decision, "score")),
            "status": _status_value(getattr(decision, "status")),
            "reasons": list(getattr(decision, "reasons", ()) or ()),
        }

    gates = []
    for gate in tuple(getattr(result, "quality_gates", ()) or ()):
        gates.append(
            {
                "gate_id": getattr(gate, "gate_id"),
                "category": getattr(gate, "category"),
                "criterion": getattr(gate, "criterion"),
                "blocking": bool(getattr(gate, "blocking")),
                "severity": getattr(gate, "severity"),
            }
        )

    return {
        "raw_request": getattr(result, "raw_request"),
        "complexity_level": getattr(result, "complexity_level"),
        "complexity_score": int(getattr(result, "complexity_score")),
        "patterns": patterns,
        "quality_gates": gates,
        "constraints": list(getattr(result, "constraints", ()) or ()),
        "capabilities": list(getattr(result, "capabilities", ()) or ()),
        "contradictions": list(getattr(result, "contradictions", ()) or ()),
    }


class RegistryAwarePolicyCompiler:
    def __init__(self, registry: PatternRegistry) -> None:
        if not isinstance(registry, PatternRegistry):
            raise TypeError("pattern_registry_invalid")
        self.registry = registry

    def _validate_registry_contract(self) -> None:
        ids = tuple(self.registry.ids())
        expected_ids = tuple(_EXPECTED_PATTERN_METADATA)
        if set(ids) != set(expected_ids) or len(ids) != len(expected_ids):
            raise RegistryPolicyContractError("registry_pattern_set_mismatch")
        for pid, (expected_name, expected_cost) in _EXPECTED_PATTERN_METADATA.items():
            pattern = self.registry.get(pid)
            if (
                pattern.name != expected_name
                or pattern.complexity_cost != expected_cost
            ):
                raise RegistryPolicyContractError(
                    f"registry_pattern_metadata_mismatch:{pid}"
                )

    @staticmethod
    def _complexity(t: Any) -> tuple[int, str]:
        workflow = 0
        if "MULTI_STEP" in t.execution:
            workflow = 2
        if "DESIGN_BEFORE_BUILD" in t.architecture and (
            {"CREATE", "MODIFY"} & t.actions
        ):
            workflow = 3
        if "LARGE_WORKLOAD" in t.execution:
            workflow = max(workflow, 2)

        consequence = max(
            t.risks.get("LEGAL_REGULATORY", 0),
            t.risks.get("SECURITY", 0),
            t.risks.get("FINANCIAL", 0),
            t.risks.get("DATA_LOSS", 0),
        )
        consequence = (
            0
            if consequence <= 1
            else (1 if consequence == 2 else (2 if consequence == 3 else 3))
        )

        state = 0
        if t.external_state or "STATEFUL" in t.execution:
            state = 2
        if (
            "AUTHORIZATION" in t.capabilities
            or "HUMAN_APPROVAL" in t.execution
        ):
            state = 3

        uncertainty = 2 if t.unknowns else 0
        if len(t.unknowns) >= 3:
            uncertainty = 3

        verification = 0
        if {"CREATE", "DIAGNOSE", "REVIEW"} & t.actions:
            verification = 1
        if (
            t.preservation
            or "OPTIMIZE" in t.actions
            or "ACCESSIBILITY" in t.ui_requirements
            or "RESPONSIVE" in t.ui_requirements
        ):
            verification = max(verification, 2)
        if (
            "TRACEABLE" in t.evidence_policy
            or "SUPPLIED_ONLY" in t.evidence_policy
            or "INDEPENDENT_REVIEW" in t.execution
            or "HUMAN_APPROVAL" in t.execution
        ):
            verification = 3

        reversibility = 0
        rv = t.risks.get("REVERSIBILITY", 0)
        if rv >= 4:
            reversibility = 3
        elif rv >= 2:
            reversibility = 2
        elif rv == 1:
            reversibility = 1

        specialization = 0
        if "PARALLELIZABLE" in t.execution:
            specialization = 1
        if "INDEPENDENT_REVIEW" in t.execution:
            specialization = 2

        score = sum(
            [
                workflow,
                consequence,
                state,
                uncertainty,
                verification,
                reversibility,
                specialization,
            ]
        )
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

        if t.actions and level == "N0":
            level = "N1"
        if (
            "MULTI_STEP" in t.execution
            or "DESIGN_BEFORE_BUILD" in t.architecture
            or "ANALYZE_EVIDENCE" in t.actions
            or "ANALYZE_DATA" in t.actions
            or t.external_state
            or "LARGE_WORKLOAD" in t.execution
            or "CURRENT_EXTERNAL" in t.evidence_policy
            or "PRODUCTION" in t.ui_requirements
            or ("OPTIMIZE" in t.actions and bool(t.preservation))
        ):
            if level in {"N0", "N1"}:
                level = "N2"
        if (
            (
                t.risks.get("LEGAL_REGULATORY", 0) >= 3
                or t.risks.get("SECURITY", 0) >= 3
                or t.risks.get("FINANCIAL", 0) >= 3
            )
            and (
                "INDEPENDENT_REVIEW" in t.execution
                or "DESIGN" in t.actions
                or "ANALYZE_EVIDENCE" in t.actions
            )
        ):
            if level in {"N0", "N1", "N2"}:
                level = "N3"
        if (
            t.risks.get("REVERSIBILITY", 0) >= 4
            and t.risks.get("DATA_LOSS", 0) >= 3
        ):
            if level in {"N0", "N1", "N2"}:
                level = "N3"
        return score, level

    def _patterns(self, t: Any) -> dict[str, RegistryPatternDecision]:
        raw = {pid: 0.0 for pid in self.registry.ids()}
        why = {pid: [] for pid in self.registry.ids()}

        if "CREATE" in t.actions:
            raw["P01"] += 90
            why["P01"].append("CREATE action")
        if "MODIFY" in t.actions:
            raw["P02"] += 48
            why["P02"].append("MODIFY action")
        if t.preservation:
            raw["P02"] += 40
            why["P02"].append("preservation contract")
        if "DIAGNOSE" in t.actions:
            raw["P03"] += 95
            why["P03"].append("DIAGNOSE action")
        if (
            "DESIGN" in t.actions
            or "DESIGN_BEFORE_BUILD" in t.architecture
        ):
            raw["P04"] += 90
            why["P04"].append("system design semantics")
        elif "CHANGE" in t.architecture and "BOUNDARIES" not in t.architecture:
            raw["P04"] += 65
            why["P04"].append("material architecture change")
        elif "CHANGE" in t.architecture and "BOUNDARIES" in t.architecture:
            why["P04"].append(
                "boundary refactor handled by P06 without separate design signal"
            )
        if "OPTIMIZE" in t.actions:
            raw["P05"] += 92
            why["P05"].append("OPTIMIZE action")
        elif t.performance_dimensions and "REVIEW" in t.actions:
            raw["P05"] += 62
            why["P05"].append("performance review/profile")
        if "BOUNDARIES" in t.architecture:
            raw["P06"] += 90
            why["P06"].append("boundary/modularity semantics")

        value_signals = sum(
            [
                "PARALLELIZABLE" in t.execution,
                "INDEPENDENT_REVIEW" in t.execution,
                max(t.risks.values(), default=0) >= 3,
            ]
        )
        if value_signals >= 2:
            raw["P07"] += 70
            why["P07"].append("independent specialization/review value")
        if value_signals >= 3:
            raw["P07"] += 15
        if "EXPLICIT_MULTI_AGENT" in t.execution:
            raw["P07"] += 10
            why["P07"].append("explicit multi-agent request")
        if "EXPLICIT_MULTI_AGENT" in t.execution and value_signals == 0:
            raw["P07"] = 0
            why["P07"].append("anti-overengineering")

        if "PRODUCTION" in t.ui_requirements:
            raw["P08"] += 95
            why["P08"].append("production UI")
        elif "UI" in t.ui_requirements:
            raw["P08"] += 65
            why["P08"].append("UI deliverable")

        out: dict[str, RegistryPatternDecision] = {}
        for pid, score in raw.items():
            score = max(0, min(100, score))
            status = (
                "mandatory"
                if score >= 80
                else ("optional" if score >= 60 else "rejected")
            )
            if pid == "P01" and "CREATE" in t.actions:
                status = "mandatory"
            if (
                pid == "P02"
                and "MODIFY" in t.actions
                and t.preservation
            ):
                status = "mandatory"
            if pid == "P03" and "DIAGNOSE" in t.actions:
                status = "mandatory"
            if pid == "P04" and (
                "DESIGN" in t.actions
                or "DESIGN_BEFORE_BUILD" in t.architecture
            ):
                status = "mandatory"
            if pid == "P05" and "OPTIMIZE" in t.actions:
                status = "mandatory"
            if pid == "P06" and "BOUNDARIES" in t.architecture:
                status = "mandatory"
            if pid == "P08" and "PRODUCTION" in t.ui_requirements:
                status = "mandatory"
            if (
                pid == "P07"
                and "EXPLICIT_MULTI_AGENT" in t.execution
                and value_signals == 0
            ):
                status = "rejected"

            pattern = self.registry.get(pid)
            out[pid] = RegistryPatternDecision(
                pattern_id=pid,
                pattern_name=pattern.name,
                score=score,
                status=status,
                reasons=tuple(
                    why[pid] or ["no normalized activation evidence"]
                ),
            )
        return out

    @staticmethod
    def _gates(t: Any) -> tuple[RegistryQualityGate, ...]:
        gates: list[RegistryQualityGate] = []
        seen: set[str] = set()

        def add(
            gid: str,
            category: str,
            criterion: str,
            blocking: bool = True,
            severity: str = "error",
        ) -> None:
            if gid not in seen:
                gates.append(
                    RegistryQualityGate(
                        gid, category, criterion, blocking, severity
                    )
                )
                seen.add(gid)

        if t.preservation:
            add(
                "REGRESSION_GATE",
                "regression",
                "Preservation contract must be verified.",
            )
        if (
            "OPTIMIZE" in t.actions
            or (t.performance_dimensions and "REVIEW" in t.actions)
        ):
            add(
                "BASELINE_GATE",
                "performance",
                "Baseline/proxy required for performance conclusions.",
            )
        if "ANALYZE_EVIDENCE" in t.actions:
            add(
                "EVIDENCE_GATE",
                "evidence",
                "Material conclusions require source evidence.",
            )
        if "TRACEABLE" in t.evidence_policy:
            add(
                "TRACEABILITY_GATE",
                "traceability",
                "Material conclusions must be source traceable.",
            )
        if "ACCESSIBILITY" in t.ui_requirements:
            add(
                "ACCESSIBILITY_GATE",
                "accessibility",
                "Accessibility must be verified.",
            )
        if "RESPONSIVE" in t.ui_requirements:
            add(
                "RESPONSIVE_GATE",
                "consistency",
                "Responsive behavior must be verified.",
            )
        if (
            t.risks.get("REVERSIBILITY", 0) >= 4
            or t.risks.get("DATA_LOSS", 0) >= 4
        ):
            add(
                "DESTRUCTIVE_ACTION_GATE",
                "requirement",
                "Destructive action requires explicit authorization.",
                True,
                "critical",
            )
        if "INDEPENDENT_REVIEW" in t.execution:
            add(
                "INDEPENDENT_REVIEW_GATE",
                "consistency",
                "Independent review must pass.",
                True,
                "critical",
            )
        if "HUMAN_APPROVAL" in t.execution:
            add(
                "HUMAN_APPROVAL_GATE",
                "requirement",
                "Explicit human approval required before execution.",
                True,
                "critical",
            )
        return tuple(gates)

    def __call__(self, t: Any) -> RegistryPolicyResult:
        self._validate_registry_contract()
        validate_normalized_task(t)
        score, level = self._complexity(t)
        patterns = self._patterns(t)
        gates = self._gates(t)
        why = [
            "Policy v0.2.10 consumed only normalized semantics; request wording was not inspected."
        ]
        why.extend(
            f"{pid} {decision.status}: {'; '.join(decision.reasons[:2])}"
            for pid, decision in patterns.items()
            if decision.status != "rejected"
        )
        return RegistryPolicyResult(
            raw_request=t.raw_request,
            complexity_level=level,
            complexity_score=score,
            patterns=patterns,
            quality_gates=gates,
            constraints=tuple(sorted(t.preservation | t.evidence_policy)),
            capabilities=tuple(sorted(t.capabilities)),
            contradictions=tuple(t.contradictions),
            why_this_route=tuple(why),
        )
