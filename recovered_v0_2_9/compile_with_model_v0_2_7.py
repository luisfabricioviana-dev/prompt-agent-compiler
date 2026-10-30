from __future__ import annotations
import argparse, json, os
from openai_responses_semantic_provider import OpenAIResponsesSemanticProvider
from interpreter_provider import compile_request


def main():
    ap=argparse.ArgumentParser(description="Compile one human request through model semantic interpretation + deterministic policy.")
    ap.add_argument("request")
    ap.add_argument("--model", default=os.getenv("PAC_SEMANTIC_MODEL","gpt-5.6-terra"))
    args=ap.parse_args()
    provider=OpenAIResponsesSemanticProvider(model=args.model)
    spec=compile_request(args.request, provider)
    print(json.dumps(spec.to_dict(), ensure_ascii=False, indent=2))

if __name__=="__main__": main()
