from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from normalized_task import NormalizedTask
from semantic_contract import SemanticContractError, validate_task
from policy_v0_2_7 import compile_semantic_task
from models import PatternStatus
from semantic_eval_v0_2_7 import evaluate_prediction, aggregate, GROUPS

ROOT = Path(__file__).parent


def _expanded_expected(case: dict[str, Any]) -> dict[str, Any]:
    x = {g: [] for g in GROUPS}
    x["risks"] = {}
    x["unknowns"] = []
    x["contradictions"] = []
    x.update(case.get("expected", {}))
    return x


def _route_eval(case: dict[str, Any], task: NormalizedTask) -> dict[str, Any]:
    spec = compile_semantic_task(task)
    selected = {pid for pid, d in spec.patterns.items() if d.status != PatternStatus.REJECTED}
    route = case.get("route", {})
    required, allowed, forbidden = set(route.get("required", [])), set(route.get("allowed", [])), set(route.get("forbidden", []))
    actual_gates = {g.gate_id for g in spec.quality_gates}
    required_gates = set(route.get("gates", []))
    errors = []
    if required - selected: errors.append("POLICY_PATTERN_ERROR: missing " + str(sorted(required-selected)))
    if forbidden & selected: errors.append("POLICY_PATTERN_ERROR: forbidden " + str(sorted(forbidden&selected)))
    unexpected = selected - required - allowed
    if unexpected: errors.append("POLICY_PATTERN_ERROR: unexpected " + str(sorted(unexpected)))
    if required_gates - actual_gates: errors.append("POLICY_GATE_ERROR: missing " + str(sorted(required_gates-actual_gates)))
    if route.get("complexity") and spec.complexity_level not in set(route["complexity"]):
        errors.append(f"POLICY_COMPLEXITY_ERROR: {spec.complexity_level} not in {route['complexity']}")
    return {"errors": errors, "pass": not errors, "complexity": spec.complexity_level, "selected": sorted(selected), "gates": sorted(actual_gates)}


def evaluate_provider(provider, cases_path: Path | None = None) -> dict[str, Any]:
    cases = json.loads((cases_path or ROOT/"semantic_dev_cases_v0_2_7.json").read_text(encoding="utf-8"))
    semantic_results, details = [], []
    valid_count = route_pass = 0

    for case in cases:
        expected = _expanded_expected(case)
        failure_class = None
        try:
            task = provider.interpret(case["request"])
            validate_task(task)
            valid_count += 1
        except SemanticContractError as exc:
            details.append({"id":case["id"],"failure_class":"CONTRACT_VALIDATION_ERROR","error":str(exc)})
            continue
        except Exception as exc:
            details.append({"id":case["id"],"failure_class":"INTERPRETER_PROVIDER_ERROR","error":str(exc)})
            continue

        predicted = task.to_dict()
        semantic = evaluate_prediction(expected, predicted, case["request"])
        semantic_results.append(semantic)

        false_neg = []
        false_pos = []
        for group in GROUPS:
            e, p = set(expected.get(group, [])), set(predicted.get(group, []))
            false_neg += [f"{group}.{v}" for v in sorted(e-p)]
            false_pos += [f"{group}.{v}" for v in sorted(p-e)]
        if false_neg: failure_class = "INTERPRETER_FALSE_NEGATIVE"
        elif false_pos: failure_class = "INTERPRETER_FALSE_POSITIVE"
        elif semantic["risk"]["critical_recall"] < 1.0 or semantic["risk"]["mae"] > 0:
            failure_class = "INTERPRETER_RISK_ERROR"
        elif semantic["evidence_span_grounding"] < 1.0:
            failure_class = "INTERPRETER_EVIDENCE_ERROR"

        route_result = _route_eval(case, task)
        route_pass += int(route_result["pass"])
        if not failure_class and route_result["errors"]:
            failure_class = route_result["errors"][0].split(":",1)[0]

        details.append({
            "id": case["id"],
            "failure_class": failure_class,
            "false_negatives": false_neg,
            "false_positives": false_pos,
            "semantic": semantic,
            "route": route_result,
        })

    agg = aggregate(semantic_results)
    return {
        "cases": len(cases),
        "contract_valid_rate": valid_count/len(cases) if cases else 1.0,
        "semantic": agg,
        "route_pass_rate": route_pass/len(cases) if cases else 1.0,
        "details": details,
    }


class OracleSemanticProvider:
    """Evaluation harness oracle. Not a production interpreter."""
    def __init__(self, cases):
        self.by_request = {c["request"]: _expanded_expected(c) for c in cases}

    def interpret(self, request: str) -> NormalizedTask:
        d = dict(self.by_request[request])
        d["raw_request"] = request
        evidence = {}
        for group in GROUPS:
            for value in d.get(group, []):
                evidence[f"{group}.{value}"] = {
                    "source": "INFERRED",
                    "confidence": 1.0,
                    "evidence_span": None,
                    "rationale": "oracle benchmark annotation"
                }
        for key, value in d.get("risks", {}).items():
            if int(value) > 0:
                evidence[f"risks.{key}"] = {
                    "source": "INFERRED",
                    "confidence": 1.0,
                    "evidence_span": None,
                    "rationale": "oracle benchmark annotation"
                }
        d["feature_evidence"] = evidence
        # core contract treats zero/absent risks equivalently
        return validate_task(NormalizedTask.from_dict(d))


def main():
    cases = json.loads((ROOT/"semantic_dev_cases_v0_2_7.json").read_text(encoding="utf-8"))
    out = evaluate_provider(OracleSemanticProvider(cases))
    (ROOT/"semantic_oracle_harness_report_v0_2_7.json").write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({k:v for k,v in out.items() if k != "details"}, indent=2, ensure_ascii=False))

if __name__ == "__main__": main()
