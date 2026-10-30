from __future__ import annotations
import argparse, importlib.util, json, os, sys
from pathlib import Path

ROOT=Path(__file__).parent


def write_status(status: dict):
    (ROOT/"LIVE_EVAL_STATUS_v0_2_8.json").write_text(json.dumps(status,ensure_ascii=False,indent=2),encoding="utf-8")


def main():
    ap=argparse.ArgumentParser(description="Run model-backed semantic evaluation with causal error decomposition.")
    ap.add_argument("--model", default=os.getenv("PAC_SEMANTIC_MODEL","gpt-5.6-terra"))
    ap.add_argument("--cases", default=str(ROOT/"semantic_dev_cases_v0_2_7.json"))
    ap.add_argument("--report", default=str(ROOT/"semantic_model_report_v0_2_8.json"))
    ap.add_argument("--record", default=str(ROOT/"semantic_model_predictions_v0_2_8.json"))
    args=ap.parse_args()

    if importlib.util.find_spec("openai") is None:
        status={"version":"0.2.8","live_eval_run":False,"status":"BLOCKED","reason":"openai SDK is not installed in this runtime","model":args.model}
        write_status(status); print(json.dumps(status,indent=2)); return 2
    if not os.getenv("OPENAI_API_KEY"):
        status={"version":"0.2.8","live_eval_run":False,"status":"BLOCKED","reason":"OPENAI_API_KEY is not configured in this runtime","model":args.model}
        write_status(status); print(json.dumps(status,indent=2)); return 2

    from openai_responses_semantic_provider import OpenAIResponsesSemanticProvider
    from model_eval_runner_v0_2_8 import evaluate_model_provider

    cases=json.loads(Path(args.cases).read_text(encoding="utf-8"))
    provider=OpenAIResponsesSemanticProvider(model=args.model)
    report=evaluate_model_provider(provider,cases,record_path=Path(args.record))
    Path(args.report).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    status={"version":"0.2.8","live_eval_run":True,"status":"COMPLETED","model":args.model,"cases":len(cases),"stage_metrics":report["stage_metrics"]}
    write_status(status)
    print(json.dumps(status,ensure_ascii=False,indent=2))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
