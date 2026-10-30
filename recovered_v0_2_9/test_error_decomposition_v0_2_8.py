import json
import tempfile
import unittest
from pathlib import Path


BASE_GROUPS = [
    "actions", "preservation", "performance_dimensions", "evidence_policy",
    "ui_requirements", "architecture", "external_state", "execution", "capabilities"
]


def base():
    d = {g: [] for g in BASE_GROUPS}
    d.update({"risks": {}, "unknowns": [], "contradictions": [], "feature_evidence": {}})
    return d


class ErrorTaxonomyV028Tests(unittest.TestCase):
    def test_action_false_negative_is_interpreter_owned(self):
        from semantic_error_taxonomy_v0_2_8 import decompose_semantic_errors
        e = base(); e["actions"] = ["DIAGNOSE"]
        p = base()
        errors = decompose_semantic_errors(e, p, request="algo falhou")
        self.assertEqual(errors[0]["code"], "INTERPRETER_ACTION_FALSE_NEGATIVE")
        self.assertEqual(errors[0]["owner"], "semantic_interpreter")

    def test_ui_error_state_confused_with_debug_is_role_confusion(self):
        from semantic_error_taxonomy_v0_2_8 import decompose_semantic_errors
        e = base(); e["actions"]=["CREATE"]; e["ui_requirements"]=["UI","STATEFUL_UI"]
        p = base(); p["actions"]=["CREATE","DIAGNOSE"]; p["ui_requirements"]=["UI","STATEFUL_UI"]
        errors = decompose_semantic_errors(e, p, request="tela com estado de erro")
        codes = {x["code"] for x in errors}
        self.assertIn("INTERPRETER_ROLE_CONFUSION_UI_ERROR_AS_DEBUG", codes)

    def test_critical_risk_underestimation_has_specific_class(self):
        from semantic_error_taxonomy_v0_2_8 import decompose_semantic_errors
        e = base(); e["risks"]={"SECURITY":4}
        p = base(); p["risks"]={"SECURITY":2}
        errors = decompose_semantic_errors(e, p, request="revise segurança")
        self.assertIn("INTERPRETER_RISK_UNDERESTIMATION", {x["code"] for x in errors})

    def test_missing_contradiction_has_specific_class(self):
        from semantic_error_taxonomy_v0_2_8 import decompose_semantic_errors
        e = base(); e["contradictions"]=["change vs preserve"]
        p = base()
        errors = decompose_semantic_errors(e, p, request="mude tudo sem mudar comportamento")
        self.assertIn("INTERPRETER_CONTRADICTION_MISS", {x["code"] for x in errors})

    def test_non_grounded_explicit_evidence_is_provider_boundary_error(self):
        from semantic_error_taxonomy_v0_2_8 import decompose_semantic_errors
        e = base(); e["actions"]=["CREATE"]
        p = base(); p["actions"]=["CREATE"]
        p["feature_evidence"]={
            "actions.CREATE": {"source":"EXPLICIT","confidence":0.99,"evidence_span":"não existe","rationale":"x"}
        }
        errors = decompose_semantic_errors(e,p,request="crie um botão")
        hit = [x for x in errors if x["code"] == "PROVIDER_GROUNDING_ERROR"]
        self.assertTrue(hit)
        self.assertEqual(hit[0]["owner"], "provider_boundary")


class RepairRouterV028Tests(unittest.TestCase):
    def test_interpreter_failure_does_not_recommend_policy_change(self):
        from repair_router_v0_2_8 import plan_repairs
        errors=[{"code":"INTERPRETER_ACTION_FALSE_NEGATIVE","owner":"semantic_interpreter","severity":"error","detail":"missing DIAGNOSE"}]
        plan=plan_repairs(errors)
        self.assertEqual(plan["minimum_scope"], "semantic_interpreter")
        self.assertNotIn("policy_router", plan["components_to_change"])

    def test_policy_failure_is_local_to_policy(self):
        from repair_router_v0_2_8 import plan_repairs
        errors=[{"code":"POLICY_GATE_ERROR","owner":"policy_router","severity":"error","detail":"missing gate"}]
        plan=plan_repairs(errors)
        self.assertEqual(plan["minimum_scope"], "policy_router")
        self.assertEqual(plan["components_to_change"], ["policy_router"])


class RecordedProviderV028Tests(unittest.TestCase):
    def test_recorded_provider_replays_normalized_task_without_model_call(self):
        from recorded_semantic_provider_v0_2_8 import RecordedSemanticProvider
        payload=base(); payload["actions"]=["CREATE"]
        payload["raw_request"]="crie algo"
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"predictions.json"
            path.write_text(json.dumps({"crie algo": payload}),encoding="utf-8")
            provider=RecordedSemanticProvider(path)
            task=provider.interpret("crie algo")
            self.assertIn("CREATE", task.actions)

    def test_recorded_provider_fails_closed_for_unknown_request(self):
        from recorded_semantic_provider_v0_2_8 import RecordedSemanticProvider, RecordedPredictionMissing
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"predictions.json"
            path.write_text("{}",encoding="utf-8")
            provider=RecordedSemanticProvider(path)
            with self.assertRaises(RecordedPredictionMissing):
                provider.interpret("não gravado")


class EndToEndDecompositionTests(unittest.TestCase):
    def test_semantic_error_takes_precedence_over_downstream_route_error(self):
        from end_to_end_decomposition_v0_2_8 import decompose_case
        expected=base(); expected["actions"]=["DIAGNOSE"]
        predicted=base(); predicted["actions"]=[]
        result=decompose_case(
            request="o serviço falhou",
            expected=expected,
            predicted=predicted,
            expected_route={"required":["P03"],"allowed":[],"forbidden":[],"gates":[],"complexity":["N1","N2"]}
        )
        self.assertFalse(result["semantic_exact"])
        self.assertTrue(any(e["owner"]=="semantic_interpreter" for e in result["errors"]))
        self.assertFalse(any(e["owner"]=="policy_router" and e.get("causal") for e in result["errors"]))


if __name__ == "__main__":
    unittest.main()
