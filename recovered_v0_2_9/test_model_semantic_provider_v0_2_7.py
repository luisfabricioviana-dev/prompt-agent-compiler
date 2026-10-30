import json
import unittest

from normalized_task import NormalizedTask


class FakeResponse:
    def __init__(self, payload):
        self.output_text = json.dumps(payload, ensure_ascii=False)


class FakeResponses:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return FakeResponse(self.payload)


class FakeClient:
    def __init__(self, payload):
        self.responses = FakeResponses(payload)


class ModelSemanticProviderTests(unittest.TestCase):
    def payload(self):
        return {
            "actions": ["MODIFY", "OPTIMIZE"],
            "preservation": ["QUALITY"],
            "performance_dimensions": ["MEMORY", "QUALITY_ACCURACY"],
            "evidence_policy": [],
            "ui_requirements": [],
            "architecture": [],
            "external_state": [],
            "execution": ["MULTI_STEP"],
            "capabilities": [],
            "risks": {
                "REVERSIBILITY": 0,
                "BLAST_RADIUS": 0,
                "FINANCIAL": 0,
                "LEGAL_REGULATORY": 0,
                "SECURITY": 0,
                "DATA_LOSS": 0,
                "REPUTATIONAL": 0
            },
            "feature_evidence": [
                {
                    "feature": "actions.OPTIMIZE",
                    "source": "EXPLICIT",
                    "confidence": 0.99,
                    "evidence_span": "reduza o uso de memória",
                    "rationale": "performance objective"
                }
            ],
            "unknowns": [],
            "contradictions": []
        }

    def test_provider_calls_responses_api_with_strict_json_schema(self):
        from openai_responses_semantic_provider import OpenAIResponsesSemanticProvider
        client = FakeClient(self.payload())
        provider = OpenAIResponsesSemanticProvider(client=client, model="test-model")
        provider.interpret("reduza o uso de memória sem piorar a qualidade")
        call = client.responses.calls[0]
        self.assertEqual(call["model"], "test-model")
        fmt = call["text"]["format"]
        self.assertEqual(fmt["type"], "json_schema")
        self.assertTrue(fmt["strict"])
        self.assertEqual(fmt["name"], "normalized_task_v0_2_7")
        self.assertFalse(fmt["schema"]["additionalProperties"])

    def test_provider_maps_evidence_list_to_core_contract(self):
        from openai_responses_semantic_provider import OpenAIResponsesSemanticProvider
        provider = OpenAIResponsesSemanticProvider(client=FakeClient(self.payload()), model="test-model")
        task = provider.interpret("reduza o uso de memória sem piorar a qualidade")
        self.assertIsInstance(task, NormalizedTask)
        self.assertIn("OPTIMIZE", task.actions)
        self.assertIn("MEMORY", task.performance_dimensions)
        self.assertIn("actions.OPTIMIZE", task.feature_evidence)
        self.assertEqual(task.feature_evidence["actions.OPTIMIZE"].source, "EXPLICIT")

    def test_provider_rejects_non_grounded_explicit_evidence_span(self):
        from openai_responses_semantic_provider import OpenAIResponsesSemanticProvider, SemanticGroundingError
        payload = self.payload()
        payload["feature_evidence"][0]["evidence_span"] = "texto que não está no pedido"
        provider = OpenAIResponsesSemanticProvider(client=FakeClient(payload), model="test-model")
        with self.assertRaises(SemanticGroundingError):
            provider.interpret("reduza o uso de memória sem piorar a qualidade")

    def test_provider_does_not_require_openai_package_when_client_is_injected(self):
        from openai_responses_semantic_provider import OpenAIResponsesSemanticProvider
        provider = OpenAIResponsesSemanticProvider(client=FakeClient(self.payload()), model="test-model")
        task = provider.interpret("reduza o uso de memória sem piorar a qualidade")
        self.assertIn("QUALITY", task.preservation)


class SemanticEvaluatorTests(unittest.TestCase):
    def test_multilabel_metrics_and_risk_metrics(self):
        from semantic_eval_v0_2_7 import evaluate_prediction
        expected = {
            "actions": ["MODIFY", "OPTIMIZE"],
            "preservation": ["QUALITY"],
            "performance_dimensions": ["MEMORY"],
            "evidence_policy": [],
            "ui_requirements": [],
            "architecture": [],
            "external_state": [],
            "execution": ["MULTI_STEP"],
            "capabilities": [],
            "risks": {"SECURITY": 3}
        }
        predicted = {
            **expected,
            "actions": ["OPTIMIZE"],
            "risks": {"SECURITY": 2},
            "feature_evidence": {},
            "unknowns": [],
            "contradictions": []
        }
        result = evaluate_prediction(expected, predicted, request="x")
        self.assertLess(result["groups"]["actions"]["recall"], 1.0)
        self.assertEqual(result["risk"]["mae"], 1.0)
        self.assertEqual(result["risk"]["critical_recall"], 0.0)

    def test_evidence_span_grounding_metric(self):
        from semantic_eval_v0_2_7 import evaluate_prediction
        expected = {k: [] for k in ["actions","preservation","performance_dimensions","evidence_policy","ui_requirements","architecture","external_state","execution","capabilities"]}
        expected["risks"] = {}
        predicted = dict(expected)
        predicted["feature_evidence"] = {
            "actions.CREATE": {
                "source": "EXPLICIT",
                "confidence": 0.9,
                "evidence_span": "não existe",
                "rationale": "x"
            }
        }
        result = evaluate_prediction(expected, predicted, request="crie um botão")
        self.assertEqual(result["evidence_span_grounding"], 0.0)


if __name__ == "__main__":
    unittest.main()
