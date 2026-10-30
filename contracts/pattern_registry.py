"""Declarative pattern contracts for the v0.2.10 compiler runtime."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class PatternDefinition:
    pattern_id: str
    name: str
    activation_features: tuple[str, ...] = ()
    blocking_features: tuple[str, ...] = ()
    prerequisites: tuple[str, ...] = ()
    required_capabilities: tuple[str, ...] = ()
    produced_artifacts: tuple[str, ...] = ()
    default_gates: tuple[str, ...] = ()
    failure_routes: tuple[str, ...] = ()
    complexity_cost: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.pattern_id, str) or not self.pattern_id.strip():
            raise ValueError("pattern_id_required")
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("pattern_name_required")
        if (
            not isinstance(self.complexity_cost, int)
            or isinstance(self.complexity_cost, bool)
            or self.complexity_cost < 0
        ):
            raise ValueError("pattern_complexity_cost_invalid")


class PatternRegistry:
    def __init__(self, patterns: Iterable[PatternDefinition] = ()) -> None:
        self._patterns: dict[str, PatternDefinition] = {}
        for pattern in patterns:
            self.register(pattern)

    def register(self, pattern: PatternDefinition) -> None:
        if not isinstance(pattern, PatternDefinition):
            raise TypeError("pattern_definition_invalid")
        if pattern.pattern_id in self._patterns:
            raise ValueError(f"pattern_id_duplicate:{pattern.pattern_id}")
        self._patterns[pattern.pattern_id] = pattern

    def get(self, pattern_id: str) -> PatternDefinition:
        try:
            return self._patterns[pattern_id]
        except KeyError as exc:
            raise KeyError(f"pattern_unknown:{pattern_id}") from exc

    def ids(self) -> tuple[str, ...]:
        return tuple(self._patterns)


def default_pattern_registry() -> PatternRegistry:
    """Return the declarative P01-P08 baseline.

    These definitions describe contracts and default verification obligations.
    They do not replace the recovered v0.2.9 scoring policy in this wave.
    """
    return PatternRegistry(
        (
            PatternDefinition(
                "P01",
                "BUILD",
                activation_features=("actions.CREATE",),
                produced_artifacts=("implementation",),
                default_gates=("REQUIREMENT_GATE",),
                failure_routes=("requirement_failure", "implementation_failure"),
                complexity_cost=2,
            ),
            PatternDefinition(
                "P02",
                "REFACTOR",
                activation_features=(
                    "actions.MODIFY",
                    "preservation.BEHAVIOR",
                ),
                produced_artifacts=("refactored_implementation",),
                default_gates=("REGRESSION_GATE",),
                failure_routes=("regression", "implementation_failure"),
                complexity_cost=2,
            ),
            PatternDefinition(
                "P03",
                "DEBUG",
                activation_features=("actions.DIAGNOSE",),
                produced_artifacts=("root_cause", "fix"),
                default_gates=("REGRESSION_GATE",),
                failure_routes=("implementation_failure", "regression"),
                complexity_cost=2,
            ),
            PatternDefinition(
                "P04",
                "SYSTEM_DESIGN",
                activation_features=(
                    "actions.DESIGN",
                    "architecture.DESIGN_BEFORE_BUILD",
                ),
                produced_artifacts=("architecture_spec",),
                default_gates=("OUTPUT_CONTRACT_GATE",),
                failure_routes=("requirement_failure", "quality_failure"),
                complexity_cost=3,
            ),
            PatternDefinition(
                "P05",
                "OPTIMIZE",
                activation_features=("actions.OPTIMIZE",),
                prerequisites=("measurable_baseline_or_proxy",),
                produced_artifacts=("optimization_result",),
                default_gates=("BASELINE_GATE", "REGRESSION_GATE"),
                failure_routes=("quality_failure", "regression"),
                complexity_cost=2,
            ),
            PatternDefinition(
                "P06",
                "CLEAN_ARCHITECTURE",
                activation_features=("architecture.BOUNDARIES",),
                produced_artifacts=("modularized_implementation",),
                default_gates=("REGRESSION_GATE",),
                failure_routes=("regression", "quality_failure"),
                complexity_cost=3,
            ),
            PatternDefinition(
                "P07",
                "MULTI_AGENT",
                activation_features=(
                    "execution.INDEPENDENT_REVIEW",
                    "execution.PARALLELIZABLE",
                ),
                produced_artifacts=("role_handoffs",),
                default_gates=("INDEPENDENT_REVIEW_GATE",),
                failure_routes=("quality_failure", "integration_failure"),
                complexity_cost=4,
            ),
            PatternDefinition(
                "P08",
                "PRODUCTION_UI",
                activation_features=("ui_requirements.PRODUCTION",),
                produced_artifacts=("production_ui",),
                default_gates=("ACCESSIBILITY_GATE", "RESPONSIVE_GATE"),
                failure_routes=("quality_failure", "requirement_failure"),
                complexity_cost=2,
            ),
        )
    )
