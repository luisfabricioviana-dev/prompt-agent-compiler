"""Executable review contract for v0.2.10."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReviewFinding:
    gate_id: str
    passed: bool
    evidence: tuple[str, ...] = ()
    severity: str = "error"
    detail: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.gate_id, str) or not self.gate_id.strip():
            raise ValueError("review_gate_id_required")
        if not isinstance(self.passed, bool):
            raise TypeError("review_gate_passed_invalid")


@dataclass(frozen=True)
class ReviewResult:
    state: str
    failed_gates: tuple[str, ...]
    reasons: tuple[str, ...]
    required_repairs: tuple[str, ...]
    reverification_scope: tuple[str, ...]


@dataclass(frozen=True)
class ReviewerSpec:
    review_id: str
    target_artifacts: tuple[str, ...]
    original_objective: str
    original_constraints: tuple[str, ...] = ()
    critical_assumptions: tuple[str, ...] = ()
    required_gates: tuple[str, ...] = ()
    regression_targets: tuple[str, ...] = ()
    adversarial_checks: tuple[str, ...] = ()
    evidence_requirements: tuple[str, ...] = ()
    independent_required: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.review_id, str) or not self.review_id.strip():
            raise ValueError("review_id_required")
        if not isinstance(self.original_objective, str) or not self.original_objective.strip():
            raise ValueError("review_objective_required")
        if not isinstance(self.independent_required, bool):
            raise TypeError("independent_required_invalid")
        if len(self.required_gates) != len(set(self.required_gates)):
            raise ValueError("required_gate_duplicate")

    def evaluate(
        self,
        *,
        findings: tuple[ReviewFinding, ...],
        independent_reviewer_confirmed: bool = False,
    ) -> ReviewResult:
        by_gate: dict[str, ReviewFinding] = {}
        reasons: list[str] = []
        failed: list[str] = []

        for finding in findings:
            if not isinstance(finding, ReviewFinding):
                raise TypeError("review_finding_invalid")
            if finding.gate_id in by_gate:
                raise ValueError(f"review_finding_duplicate:{finding.gate_id}")
            by_gate[finding.gate_id] = finding

        for gate_id in self.required_gates:
            finding = by_gate.get(gate_id)
            if finding is None:
                failed.append(gate_id)
                reasons.append(f"missing_required_gate:{gate_id}")
                continue
            if not finding.passed:
                failed.append(gate_id)
                reasons.append(f"gate_failed:{gate_id}")
                continue
            if not finding.evidence:
                failed.append(gate_id)
                reasons.append(f"missing_gate_evidence:{gate_id}")

        if self.independent_required and not independent_reviewer_confirmed:
            failed.append("INDEPENDENT_REVIEW_REQUIRED")
            reasons.append("independent_reviewer_not_confirmed")

        failed_unique = tuple(dict.fromkeys(failed))
        if failed_unique:
            repairable = tuple(
                gate_id
                for gate_id in failed_unique
                if gate_id != "INDEPENDENT_REVIEW_REQUIRED"
            )
            repairs = tuple(f"repair_gate:{gate_id}" for gate_id in repairable)
            reverification = tuple(
                f"reverify_gate:{gate_id}" for gate_id in repairable
            )
            if "INDEPENDENT_REVIEW_REQUIRED" in failed_unique:
                repairs += ("obtain_independent_review",)
                reverification += ("reverify_independent_review",)
            return ReviewResult(
                state="FAIL",
                failed_gates=failed_unique,
                reasons=tuple(reasons),
                required_repairs=repairs,
                reverification_scope=reverification,
            )

        return ReviewResult(
            state="PASS",
            failed_gates=(),
            reasons=(),
            required_repairs=(),
            reverification_scope=(),
        )
