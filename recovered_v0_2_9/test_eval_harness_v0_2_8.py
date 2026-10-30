import json
import copy
import tempfile
import unittest
from pathlib import Path

from normalized_task import NormalizedTask
from semantic_contract import validate_task


class DictProvider:
    def __init__(self, by_request): self.by_request=by_request
    def interpret(self, request):
        d=dict(self.by_request[request]); d["raw_request"]=request
        return validate_task(NormalizedTask.from_dict(d))


class EvalHarnessV028Tests(unittest.TestCase):
    def cases(self):
        return json.loads(Path(__file__).with_name("semantic_dev_cases_v0_2_7.json").read_text(encoding="utf-8"))

    def oracle_map(self, cases):
        groups=["actions","preservation","performance_dimensions","evidence_policy","ui_requirements","architecture","external_state","execution","capabilities"]
        out={}
        for c in cases:
            d={g:[] for g in groups}; d.update({"risks":{},"unknowns":[],"contradictions":[],"feature_evidence":{}}); d.update(copy.deepcopy(c.get("expected",{})))
            ev={}
            for g in groups:
                for v in d.get(g,[]): ev[f"{g}.{v}"]={"source":"INFERRED","confidence":1.0,"evidence_span":None,"rationale":"oracle"}
            for k,v in d.get("risks",{}).items():
                if int(v)>0: ev[f"risks.{k}"]={"source":"INFERRED","confidence":1.0,"evidence_span":None,"rationale":"oracle"}
            d["feature_evidence"]=ev
            out[c["request"]]=d
        return out

    def test_oracle_semantics_has_no_causal_errors(self):
        from model_eval_runner_v0_2_8 import evaluate_model_provider
        cases=self.cases()
        report=evaluate_model_provider(DictProvider(self.oracle_map(cases)), cases)
        self.assertEqual(report["stage_metrics"]["semantic_exact_rate"],1.0)
        self.assertEqual(report["stage_metrics"]["causal_policy_pass_rate"],1.0)
        self.assertEqual(report["stage_metrics"]["end_to_end_pass_rate"],1.0)

    def test_semantic_role_confusion_does_not_count_as_causal_policy_error(self):
        from model_eval_runner_v0_2_8 import evaluate_model_provider
        cases=[self.cases()[0]]
        m=self.oracle_map(cases)
        m[cases[0]["request"]]["actions"].append("DIAGNOSE")
        report=evaluate_model_provider(DictProvider(m),cases)
        self.assertEqual(report["error_counts"].get("INTERPRETER_ROLE_CONFUSION_UI_ERROR_AS_DEBUG"),1)
        self.assertEqual(report["stage_metrics"]["semantic_exact_rate"],0.0)
        self.assertEqual(report["causal_error_counts"].get("POLICY_PATTERN_ERROR",0),0)

    def test_prediction_record_can_be_replayed(self):
        from model_eval_runner_v0_2_8 import evaluate_model_provider
        from recorded_semantic_provider_v0_2_8 import RecordedSemanticProvider
        cases=self.cases()[:2]; provider=DictProvider(self.oracle_map(cases))
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"cache.json"
            report=evaluate_model_provider(provider,cases,record_path=path)
            self.assertTrue(path.exists())
            replay=evaluate_model_provider(RecordedSemanticProvider(path),cases)
            self.assertEqual(report["stage_metrics"],replay["stage_metrics"])

    def test_mutation_suite_classifies_expected_error_families(self):
        from mutation_suite_v0_2_8 import run_mutation_suite
        report=run_mutation_suite()
        self.assertEqual(report["pass_rate"],1.0)
        self.assertGreaterEqual(report["cases"],8)


if __name__ == "__main__": unittest.main()
