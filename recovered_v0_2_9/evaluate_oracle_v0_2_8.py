from __future__ import annotations
import json
from pathlib import Path
from evaluate_semantic_provider_v0_2_7 import OracleSemanticProvider
from model_eval_runner_v0_2_8 import evaluate_model_provider
from build_error_report_v0_2_8 import build_markdown

ROOT=Path(__file__).parent

def main():
    cases=json.loads((ROOT/"semantic_dev_cases_v0_2_7.json").read_text(encoding="utf-8"))
    report=evaluate_model_provider(OracleSemanticProvider(cases),cases,record_path=ROOT/"semantic_oracle_predictions_v0_2_8.json")
    (ROOT/"semantic_oracle_report_v0_2_8.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    (ROOT/"semantic_oracle_report_v0_2_8.md").write_text(build_markdown(report),encoding="utf-8")
    print(json.dumps({"stage_metrics":report["stage_metrics"],"error_counts":report["error_counts"]},ensure_ascii=False,indent=2))

if __name__=="__main__": main()
