import json, tempfile, unittest
from pathlib import Path

class HoldoutProtocolTests(unittest.TestCase):
    def test_holdout_is_frozen_and_has_at_least_50_cases(self):
        from holdout_protocol_v0_2_9 import load_holdout
        suite = load_holdout()
        self.assertTrue(suite['frozen'])
        self.assertGreaterEqual(len(suite['cases']), 50)

    def test_ids_are_unique(self):
        from holdout_protocol_v0_2_9 import load_holdout
        ids=[c['id'] for c in load_holdout()['cases']]
        self.assertEqual(len(ids), len(set(ids)))

    def test_prediction_exchange_rejects_unknown_case(self):
        from prediction_exchange_v0_2_9 import normalize_predictions, PredictionExchangeError
        with self.assertRaises(PredictionExchangeError):
            normalize_predictions({'NOPE': {'raw_request':'x'}}, {'H001'})

    def test_prediction_exchange_accepts_mapping(self):
        from prediction_exchange_v0_2_9 import normalize_predictions
        out=normalize_predictions({'H001': {'raw_request':'abc'}}, {'H001'})
        self.assertIn('H001',out)

    def test_promotion_rejects_low_semantic_recall(self):
        from promotion_gate_v0_2_9 import decide_promotion
        report={'stage_metrics':{'provider_success_rate':1,'contract_valid_rate':1,'semantic_exact_rate':.4,'end_to_end_pass_rate':.5},
                'semantic_metrics':{'critical_risk_recall':1.0,'evidence_grounding_rate':1.0}}
        d=decide_promotion(report)
        self.assertFalse(d['promote'])

    def test_promotion_requires_zero_critical_grounding_failures(self):
        from promotion_gate_v0_2_9 import decide_promotion
        report={'stage_metrics':{'provider_success_rate':1,'contract_valid_rate':1,'semantic_exact_rate':.95,'end_to_end_pass_rate':.95},
                'semantic_metrics':{'critical_risk_recall':1.0,'evidence_grounding_rate':.99}}
        d=decide_promotion(report)
        self.assertFalse(d['promote'])

    def test_holdout_evaluator_reports_missing_predictions_without_faking_results(self):
        from holdout_evaluator_v0_2_9 import evaluate_prediction_file
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'pred.json'; p.write_text('{}')
            r=evaluate_prediction_file(p)
            self.assertEqual(r['status'],'INCOMPLETE')
            self.assertGreater(r['missing_predictions'],0)

if __name__=='__main__': unittest.main()

class FreezeIntegrityTests(unittest.TestCase):
    def test_freeze_manifest_verifies(self):
        from freeze_integrity_v0_2_9 import verify_freeze
        result=verify_freeze()
        self.assertTrue(result['valid'])
