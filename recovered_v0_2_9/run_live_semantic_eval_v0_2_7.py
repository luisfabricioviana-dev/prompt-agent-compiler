from __future__ import annotations
import argparse, json, os
from pathlib import Path

from openai_responses_semantic_provider import OpenAIResponsesSemanticProvider
from evaluate_semantic_provider_v0_2_7 import evaluate_provider

ROOT=Path(__file__).parent


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--model", default=os.getenv("PAC_SEMANTIC_MODEL","gpt-5.6-terra"))
    ap.add_argument("--cases", default=str(ROOT/"semantic_dev_cases_v0_2_7.json"))
    ap.add_argument("--out", default=str(ROOT/"semantic_model_report_v0_2_7.json"))
    args=ap.parse_args()
    provider=OpenAIResponsesSemanticProvider(model=args.model)
    out=evaluate_provider(provider, Path(args.cases))
    Path(args.out).write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({k:v for k,v in out.items() if k != "details"},ensure_ascii=False,indent=2))

if __name__=="__main__": main()
