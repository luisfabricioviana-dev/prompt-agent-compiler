from __future__ import annotations

from typing import Any, Iterable

GROUPS = [
    "actions", "preservation", "performance_dimensions", "evidence_policy",
    "ui_requirements", "architecture", "external_state", "execution", "capabilities"
]
RISK_KEYS = [
    "REVERSIBILITY", "BLAST_RADIUS", "FINANCIAL", "LEGAL_REGULATORY",
    "SECURITY", "DATA_LOSS", "REPUTATIONAL"
]


def _prf(expected: Iterable[str], predicted: Iterable[str]) -> dict[str, float]:
    e, p = set(expected), set(predicted)
    tp = len(e & p)
    precision = tp / len(p) if p else (1.0 if not e else 0.0)
    recall = tp / len(e) if e else (1.0 if not p else 0.0)
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"precision": precision, "recall": recall, "f1": f1, "tp": tp, "expected": len(e), "predicted": len(p)}


def _risk_metrics(expected: dict[str, int], predicted: dict[str, int]) -> dict[str, float]:
    keys = set(expected) | set(predicted)
    if not keys:
        return {"exact_accuracy": 1.0, "mae": 0.0, "critical_recall": 1.0}
    diffs = [abs(int(expected.get(k, 0)) - int(predicted.get(k, 0))) for k in keys]
    exact = sum(int(expected.get(k, 0)) == int(predicted.get(k, 0)) for k in keys) / len(keys)
    critical = {k for k, v in expected.items() if int(v) >= 3}
    critical_hit = {k for k in critical if int(predicted.get(k, 0)) >= 3}
    critical_recall = len(critical_hit) / len(critical) if critical else 1.0
    return {"exact_accuracy": exact, "mae": sum(diffs)/len(diffs), "critical_recall": critical_recall}


def _evidence_items(feature_evidence: Any) -> list[dict[str, Any]]:
    if not feature_evidence:
        return []
    if isinstance(feature_evidence, list):
        return [dict(x) for x in feature_evidence]
    return [dict(v, feature=k) for k, v in feature_evidence.items()]


def _grounding_score(feature_evidence: Any, request: str) -> float:
    explicit = [i for i in _evidence_items(feature_evidence) if i.get("source") == "EXPLICIT"]
    if not explicit:
        return 1.0
    grounded = sum(bool(i.get("evidence_span")) and i.get("evidence_span") in request for i in explicit)
    return grounded / len(explicit)


def _positive_feature_paths(expected: dict[str, Any]) -> set[str]:
    paths = set()
    for group in GROUPS:
        for value in expected.get(group, []):
            paths.add(f"{group}.{value}")
    for key, value in expected.get("risks", {}).items():
        if int(value) > 0:
            paths.add(f"risks.{key}")
    return paths


def _evidence_coverage(expected: dict[str, Any], feature_evidence: Any) -> float:
    required = _positive_feature_paths(expected)
    if not required:
        return 1.0
    supplied = {i.get("feature") for i in _evidence_items(feature_evidence) if i.get("feature")}
    return len(required & supplied) / len(required)


def _claim_correct(feature: str, expected: dict[str, Any], predicted: dict[str, Any]) -> bool:
    if "." not in feature:
        return False
    group, value = feature.split(".", 1)
    if group in GROUPS:
        return value in set(expected.get(group, [])) and value in set(predicted.get(group, []))
    if group == "risks":
        return int(predicted.get("risks", {}).get(value, 0)) == int(expected.get("risks", {}).get(value, 0))
    return False


def _calibration(expected: dict[str, Any], predicted: dict[str, Any]) -> dict[str, float]:
    samples=[]
    for item in _evidence_items(predicted.get("feature_evidence", {})):
        if item.get("source") not in {"EXPLICIT","INFERRED"}:
            continue
        feature=item.get("feature")
        conf=float(item.get("confidence",0.0))
        samples.append((max(0.0,min(1.0,conf)), 1.0 if _claim_correct(feature,expected,predicted) else 0.0))
    if not samples:
        return {"items":0,"brier":0.0,"ece":0.0}
    brier=sum((c-y)**2 for c,y in samples)/len(samples)
    bins=[(0.0,0.5),(0.5,0.7),(0.7,0.8),(0.8,0.9),(0.9,1.0000001)]
    ece=0.0
    for lo,hi in bins:
        bucket=[(c,y) for c,y in samples if lo <= c < hi]
        if not bucket: continue
        avg_c=sum(c for c,_ in bucket)/len(bucket)
        avg_y=sum(y for _,y in bucket)/len(bucket)
        ece += (len(bucket)/len(samples))*abs(avg_c-avg_y)
    return {"items":len(samples),"brier":brier,"ece":ece}


def _contradiction_metric(expected: dict[str, Any], predicted: dict[str, Any]) -> dict[str, float]:
    e=bool(expected.get("contradictions"))
    p=bool(predicted.get("contradictions"))
    return {"expected":float(e),"predicted":float(p),"correct":float(e==p)}


def evaluate_prediction(expected: dict[str, Any], predicted: dict[str, Any], request: str) -> dict[str, Any]:
    groups = {g: _prf(expected.get(g, []), predicted.get(g, [])) for g in GROUPS}
    return {
        "groups": groups,
        "risk": _risk_metrics(expected.get("risks", {}), predicted.get("risks", {})),
        "evidence_span_grounding": _grounding_score(predicted.get("feature_evidence", {}), request),
        "feature_evidence_coverage": _evidence_coverage(expected, predicted.get("feature_evidence", {})),
        "confidence_calibration": _calibration(expected, predicted),
        "contradiction": _contradiction_metric(expected, predicted),
    }


def aggregate(results: list[dict[str, Any]]) -> dict[str, Any]:
    if not results:
        return {}
    out = {"groups": {}}
    for group in GROUPS:
        expected_n = sum(r["groups"][group]["expected"] for r in results)
        predicted_n = sum(r["groups"][group]["predicted"] for r in results)
        tp = sum(r["groups"][group]["tp"] for r in results)
        precision = tp / predicted_n if predicted_n else (1.0 if expected_n == 0 else 0.0)
        recall = tp / expected_n if expected_n else (1.0 if predicted_n == 0 else 0.0)
        f1 = 2*precision*recall/(precision+recall) if precision+recall else 0.0
        out["groups"][group] = {"precision": precision, "recall": recall, "f1": f1}
    out["risk"] = {
        "exact_accuracy": sum(r["risk"]["exact_accuracy"] for r in results)/len(results),
        "mae": sum(r["risk"]["mae"] for r in results)/len(results),
        "critical_recall": sum(r["risk"]["critical_recall"] for r in results)/len(results),
    }
    out["evidence_span_grounding"] = sum(r["evidence_span_grounding"] for r in results)/len(results)
    out["feature_evidence_coverage"] = sum(r["feature_evidence_coverage"] for r in results)/len(results)
    total_items=sum(r["confidence_calibration"]["items"] for r in results)
    if total_items:
        out["confidence_calibration"]={
            "items": total_items,
            "brier": sum(r["confidence_calibration"]["brier"]*r["confidence_calibration"]["items"] for r in results)/total_items,
            "ece": sum(r["confidence_calibration"]["ece"]*r["confidence_calibration"]["items"] for r in results)/total_items,
        }
    else:
        out["confidence_calibration"]={"items":0,"brier":0.0,"ece":0.0}
    out["contradiction_accuracy"] = sum(r["contradiction"]["correct"] for r in results)/len(results)
    return out
