import unittest
from semantic_eval_v0_2_7 import evaluate_prediction


def base():
    return {
        "actions": [], "preservation": [], "performance_dimensions": [], "evidence_policy": [],
        "ui_requirements": [], "architecture": [], "external_state": [], "execution": [],
        "capabilities": [], "risks": {}, "unknowns": [], "contradictions": []
    }


class SemanticMetricsV027Tests(unittest.TestCase):
    def test_feature_evidence_coverage_counts_material_positive_features(self):
        expected=base(); expected["actions"]=["OPTIMIZE"]; expected["performance_dimensions"]=["MEMORY"]
        predicted=base(); predicted["actions"]=["OPTIMIZE"]; predicted["performance_dimensions"]=["MEMORY"]
        predicted["feature_evidence"]={
            "actions.OPTIMIZE":{"source":"INFERRED","confidence":0.9,"evidence_span":None,"rationale":"x"}
        }
        r=evaluate_prediction(expected,predicted,"x")
        self.assertEqual(r["feature_evidence_coverage"],0.5)

    def test_confidence_calibration_rewards_correct_high_confidence_claim(self):
        expected=base(); expected["actions"]=["CREATE"]
        predicted=base(); predicted["actions"]=["CREATE"]
        predicted["feature_evidence"]={
            "actions.CREATE":{"source":"INFERRED","confidence":1.0,"evidence_span":None,"rationale":"x"}
        }
        r=evaluate_prediction(expected,predicted,"x")
        self.assertEqual(r["confidence_calibration"]["items"],1)
        self.assertEqual(r["confidence_calibration"]["brier"],0.0)

    def test_contradiction_presence_is_scored(self):
        expected=base(); expected["contradictions"]=["conflict"]
        predicted=base(); predicted["contradictions"]=[]
        r=evaluate_prediction(expected,predicted,"x")
        self.assertEqual(r["contradiction"]["correct"],0.0)

if __name__=='__main__': unittest.main()
