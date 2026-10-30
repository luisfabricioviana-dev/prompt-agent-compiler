from __future__ import annotations
import argparse, json
from pathlib import Path
from recorded_semantic_provider_v0_2_8 import RecordedSemanticProvider
from model_eval_runner_v0_2_8 import evaluate_model_provider

ROOT=Path(__file__).parent

def main():
    ap=argparse.ArgumentParser(description="Replay a recorded semantic model run without model/API calls.")
    ap.add_argument("--predictions", default=str(ROOT/"semantic_model_predictions_v0_2_8.json"))
    ap.add_argument("--cases", default=str(ROOT/"semantic_dev_cases_v0_2_7.json"))
    ap.add_argument("--out", default=str(ROOT/"semantic_replay_report_v0_2_8.json"))
    args=ap.parse_args()
    cases=json.loads(Path(args.cases).read_text(encoding="utf-8"))
    report=evaluate_model_provider(RecordedSemanticProvider(args.predictions),cases)
    Path(args.out).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"stage_metrics":report["stage_metrics"],"error_counts":report["error_counts"]},ensure_ascii=False,indent=2))

if __name__=="__main__": main()
