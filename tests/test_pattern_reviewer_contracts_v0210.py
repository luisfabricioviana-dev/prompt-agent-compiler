import unittest

from contracts.pattern_registry import (
    PatternDefinition,
    PatternRegistry,
    default_pattern_registry,
)
from contracts.reviewer_spec import (
    ReviewFinding,
    ReviewerSpec,
)


class PatternRegistryTests(unittest.TestCase):
    def test_default_registry_contains_exactly_p01_to_p08(self):
        registry = default_pattern_registry()
        self.assertEqual(
            set(registry.ids()),
            {f"P0{i}" for i in range(1, 9)},
        )

    def test_optimize_pattern_declares_baseline_and_regression_gates(self):
        pattern = default_pattern_registry().get("P05")
        self.assertIn("BASELINE_GATE", pattern.default_gates)
        self.assertIn("REGRESSION_GATE", pattern.default_gates)
        self.assertGreaterEqual(pattern.complexity_cost, 1)

    def test_multi_agent_pattern_declares_independent_review_gate(self):
        pattern = default_pattern_registry().get("P07")
        self.assertIn("INDEPENDENT_REVIEW_GATE", pattern.default_gates)
        self.assertIn("execution.INDEPENDENT_REVIEW", pattern.activation_features)

    def test_production_ui_pattern_declares_accessibility_and_responsive_gates(self):
        pattern = default_pattern_registry().get("P08")
        self.assertIn("ACCESSIBILITY_GATE", pattern.default_gates)
        self.assertIn("RESPONSIVE_GATE", pattern.default_gates)

    def test_registry_rejects_duplicate_pattern_ids(self):
        pattern = PatternDefinition(
            pattern_id="P01",
            name="BUILD",
            activation_features=("actions.CREATE",),
            complexity_cost=1,
        )
        with self.assertRaisesRegex(ValueError, "pattern_id_duplicate"):
            PatternRegistry([pattern, pattern])


class ReviewerSpecTests(unittest.TestCase):
    def spec(self, *, independent_required=False):
        return ReviewerSpec(
            review_id="review-1",
            target_artifacts=("artifact-1",),
            original_objective="Produce a verified result.",
            original_constraints=("preserve_behavior",),
            critical_assumptions=("source_is_complete",),
            required_gates=("EVIDENCE_GATE", "REGRESSION_GATE"),
            regression_targets=("behavior",),
            adversarial_checks=("unsupported_assumptions",),
            evidence_requirements=("source_trace",),
            independent_required=independent_required,
        )

    def test_missing_required_gate_is_fail(self):
        result = self.spec().evaluate(
            findings=(
                ReviewFinding(
                    gate_id="EVIDENCE_GATE",
                    passed=True,
                    evidence=("source:1",),
                ),
            )
        )
        self.assertEqual(result.state, "FAIL")
        self.assertIn("REGRESSION_GATE", result.failed_gates)

    def test_passed_gate_without_evidence_is_fail(self):
        findings = (
            ReviewFinding("EVIDENCE_GATE", True, ()),
            ReviewFinding("REGRESSION_GATE", True, ("test:regression",)),
        )
        result = self.spec().evaluate(findings=findings)
        self.assertEqual(result.state, "FAIL")
        self.assertIn("EVIDENCE_GATE", result.failed_gates)
        self.assertIn("missing_gate_evidence:EVIDENCE_GATE", result.reasons)

    def test_all_required_gates_with_evidence_can_pass(self):
        findings = (
            ReviewFinding("EVIDENCE_GATE", True, ("source:1",)),
            ReviewFinding("REGRESSION_GATE", True, ("test:regression",)),
        )
        result = self.spec().evaluate(findings=findings)
        self.assertEqual(result.state, "PASS")
        self.assertEqual(result.failed_gates, ())

    def test_independent_review_requirement_blocks_self_approval(self):
        findings = (
            ReviewFinding("EVIDENCE_GATE", True, ("source:1",)),
            ReviewFinding("REGRESSION_GATE", True, ("test:regression",)),
        )
        result = self.spec(independent_required=True).evaluate(
            findings=findings,
            independent_reviewer_confirmed=False,
        )
        self.assertEqual(result.state, "FAIL")
        self.assertIn("INDEPENDENT_REVIEW_REQUIRED", result.failed_gates)

    def test_failed_gate_returns_targeted_repair_and_reverification(self):
        findings = (
            ReviewFinding("EVIDENCE_GATE", False, ("source:conflict",)),
            ReviewFinding("REGRESSION_GATE", True, ("test:regression",)),
        )
        result = self.spec().evaluate(findings=findings)
        self.assertEqual(result.state, "FAIL")
        self.assertEqual(
            result.required_repairs,
            ("repair_gate:EVIDENCE_GATE",),
        )
        self.assertEqual(
            result.reverification_scope,
            ("reverify_gate:EVIDENCE_GATE",),
        )


if __name__ == "__main__":
    unittest.main()
