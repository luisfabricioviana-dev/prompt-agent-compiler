import unittest

from normalized_task import NormalizedTask, SemanticEvidence
from semantic_contract import validate_task, SemanticContractError
from policy_v0_2_6 import compile_semantic_task
from models import PatternStatus


class NormalizedPolicyTests(unittest.TestCase):
    def task(self, **kwargs):
        base = dict(raw_request="opaque text", actions=set(), preservation=set(), performance_dimensions=set(),
                    evidence_policy=set(), ui_requirements=set(), architecture=set(), external_state=set(),
                    execution=set(), capabilities=set(), risks={}, feature_evidence={})
        base.update(kwargs)
        return NormalizedTask(**base)

    def test_policy_is_independent_of_request_wording(self):
        semantics = dict(actions={"MODIFY"}, preservation={"BEHAVIOR"}, architecture={"CHANGE"},
                         execution={"MULTI_STEP"})
        a = self.task(raw_request="Reescreva tudo.", **semantics)
        b = self.task(raw_request="Mude por dentro sem quebrar por fora.", **semantics)
        sa = compile_semantic_task(a)
        sb = compile_semantic_task(b)
        self.assertEqual(sa.complexity_level, sb.complexity_level)
        self.assertEqual({p:d.status for p,d in sa.patterns.items()}, {p:d.status for p,d in sb.patterns.items()})
        self.assertEqual({g.gate_id for g in sa.quality_gates}, {g.gate_id for g in sb.quality_gates})

    def test_performance_semantics_compile_baseline_and_regression(self):
        t = self.task(actions={"MODIFY","OPTIMIZE"}, preservation={"QUALITY"},
                      performance_dimensions={"THROUGHPUT","QUALITY_ACCURACY"}, execution={"MULTI_STEP"})
        s = compile_semantic_task(t)
        self.assertEqual(s.patterns["P05"].status, PatternStatus.MANDATORY)
        gates = {g.gate_id for g in s.quality_gates}
        self.assertIn("BASELINE_GATE", gates)
        self.assertIn("REGRESSION_GATE", gates)

    def test_evidence_policy_compiles_evidence_and_traceability(self):
        t = self.task(actions={"ANALYZE_EVIDENCE"}, evidence_policy={"SUPPLIED_ONLY","TRACEABLE"},
                      risks={"LEGAL_REGULATORY":3}, execution={"MULTI_STEP"})
        s = compile_semantic_task(t)
        gates = {g.gate_id for g in s.quality_gates}
        self.assertIn("EVIDENCE_GATE", gates)
        self.assertIn("TRACEABILITY_GATE", gates)
        self.assertIn(s.complexity_level, {"N3","N4"})

    def test_destructive_state_compiles_control_gate(self):
        t = self.task(actions={"OPERATE"}, external_state={"DATABASE"}, execution={"STATEFUL"},
                      risks={"REVERSIBILITY":4,"DATA_LOSS":4}, capabilities={"EXTERNAL_WRITE"})
        s = compile_semantic_task(t)
        self.assertIn("DESTRUCTIVE_ACTION_GATE", {g.gate_id for g in s.quality_gates})
        self.assertIn(s.complexity_level, {"N3","N4"})

    def test_ui_error_state_does_not_imply_debug(self):
        t = self.task(actions={"CREATE"}, ui_requirements={"UI","PRODUCTION","ACCESSIBILITY"})
        s = compile_semantic_task(t)
        self.assertEqual(s.patterns["P03"].status, PatternStatus.REJECTED)
        self.assertEqual(s.patterns["P08"].status, PatternStatus.MANDATORY)

    def test_explicit_multiagent_without_value_is_rejected(self):
        t = self.task(actions={"CREATE"}, execution={"EXPLICIT_MULTI_AGENT"})
        s = compile_semantic_task(t)
        self.assertEqual(s.patterns["P07"].status, PatternStatus.REJECTED)

    def test_independent_review_is_separate_from_multiagent_execution(self):
        t = self.task(actions={"REVIEW"}, execution={"INDEPENDENT_REVIEW"}, risks={"SECURITY":3})
        s = compile_semantic_task(t)
        self.assertIn("INDEPENDENT_REVIEW_GATE", {g.gate_id for g in s.quality_gates})
        self.assertIn(s.patterns["P07"].status, {PatternStatus.OPTIONAL, PatternStatus.MANDATORY})


class ContractValidationTests(unittest.TestCase):
    def task(self, **kwargs):
        base = dict(raw_request="x", actions=set(), preservation=set(), performance_dimensions=set(),
                    evidence_policy=set(), ui_requirements=set(), architecture=set(), external_state=set(),
                    execution=set(), capabilities=set(), risks={}, feature_evidence={})
        base.update(kwargs)
        return NormalizedTask(**base)

    def test_production_ui_requires_ui_flag(self):
        t = self.task(ui_requirements={"PRODUCTION"})
        with self.assertRaises(SemanticContractError):
            validate_task(t)

    def test_supplied_only_requires_evidence_analysis(self):
        t = self.task(evidence_policy={"SUPPLIED_ONLY"})
        with self.assertRaises(SemanticContractError):
            validate_task(t)

    def test_optimize_requires_dimension(self):
        t = self.task(actions={"OPTIMIZE"})
        with self.assertRaises(SemanticContractError):
            validate_task(t)

    def test_feature_evidence_has_source_confidence_and_span(self):
        ev = SemanticEvidence(source="EXPLICIT", confidence=0.98, evidence_span="sem alterar o resultado")
        self.assertEqual(ev.source, "EXPLICIT")
        self.assertGreater(ev.confidence, 0.9)
        self.assertTrue(ev.evidence_span)


if __name__ == "__main__":
    unittest.main()

class PolicyComplexityFloorTests(unittest.TestCase):
    def test_production_ui_is_at_least_structured(self):
        t = NormalizedTask(raw_request="x", actions={"CREATE"}, ui_requirements={"UI","PRODUCTION","ACCESSIBILITY","RESPONSIVE"})
        s = compile_semantic_task(t)
        self.assertIn(s.complexity_level, {"N2","N3"})

class PolicyV027RegressionTests(unittest.TestCase):
    def test_optimization_with_preservation_is_at_least_structured(self):
        t = NormalizedTask(
            raw_request="x",
            actions={"OPTIMIZE"},
            preservation={"QUALITY"},
            performance_dimensions={"THROUGHPUT","QUALITY_ACCURACY"},
        )
        s = compile_semantic_task(t)
        self.assertIn(s.complexity_level, {"N2","N3","N4"})

    def test_boundary_refactor_does_not_require_system_design_without_design_action(self):
        t = NormalizedTask(
            raw_request="x",
            actions={"MODIFY"},
            preservation={"BEHAVIOR"},
            architecture={"BOUNDARIES","CHANGE"},
            execution={"MULTI_STEP"},
        )
        s = compile_semantic_task(t)
        self.assertEqual(s.patterns["P06"].status, PatternStatus.MANDATORY)
        self.assertEqual(s.patterns["P04"].status, PatternStatus.REJECTED)
