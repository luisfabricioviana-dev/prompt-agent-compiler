from __future__ import annotations
import json
from pathlib import Path
from holdout_protocol_v0_2_9 import load_holdout
from prediction_exchange_v0_2_9 import load_predictions
from model_eval_runner_v0_2_8 import evaluate_model_provider
from normalized_task import NormalizedTask
from semantic_contract import validate_task
from promotion_gate_v0_2_9 import decide_promotion

class _Provider:
    def __init__(self, by_request): self.by_request=by_request
    def interpret(self, request):
        payload=dict(self.by_request[request]); payload["raw_request"]=request
        return validate_task(NormalizedTask.from_dict(payload))

def evaluate_prediction_file(path):
    suite=load_holdout(); cases=suite["cases"]; ids={c["id"] for c in cases}
    predictions=load_predictions(path,ids)
    missing=sorted(ids-set(predictions))
    if missing:
        return {"status":"INCOMPLETE","suite":suite["suite_id"],"cases":len(cases),"received_predictions":len(predictions),"missing_predictions":len(missing),"missing_ids":missing,"promotion":None}
    by_request={c["request"]:predictions[c["id"]] for c in cases}
    report=evaluate_model_provider(_Provider(by_request),cases)
    promotion=decide_promotion(report)
    return {"status":"COMPLETE","suite":suite["suite_id"],"frozen":True,"report":report,"promotion":promotion}

def main(argv=None):
    import argparse
    ap=argparse.ArgumentParser(); ap.add_argument("predictions"); ap.add_argument("--out",default="holdout_eval_result_v0_2_9.json")
    ns=ap.parse_args(argv); result=evaluate_prediction_file(ns.predictions); Path(ns.out).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8"); print(json.dumps({"status":result["status"],"promotion":result.get("promotion")},indent=2))
if __name__=="__main__": main()
