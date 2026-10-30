
from __future__ import annotations
import json
from pathlib import Path
from router import compile_request
from models import PatternStatus

ROOT = Path(__file__).parent


def evaluate():
    cases = json.loads((ROOT / "benchmark_cases.json").read_text(encoding="utf-8"))
    report = []

    required_total = required_hit = 0
    selected_total = selected_valid = 0
    forbidden_selected = 0
    gate_total = gate_hit = 0
    complexity_hit = 0

    for case in cases:
        spec = compile_request(case["input"])
        selected = {pid for pid, d in spec.patterns.items() if d.status != PatternStatus.REJECTED}
        required = set(case["required"])
        allowed = set(case["allowed"])
        forbidden = set(case["forbidden"])
        expected_valid = required | allowed

        required_total += len(required)
        required_hit += len(required & selected)

        selected_total += len(selected)
        selected_valid += len(selected & expected_valid)
        forbidden_selected += len(forbidden & selected)

        actual_gates = {g.gate_id for g in spec.quality_gates}
        expected_gates = set(case["gates"])
        gate_total += len(expected_gates)
        gate_hit += len(expected_gates & actual_gates)

        c_ok = spec.complexity_level in set(case["complexity"])
        complexity_hit += int(c_ok)

        errors = []
        missing = sorted(required - selected)
        forbidden_hits = sorted(forbidden & selected)
        missing_gates = sorted(expected_gates - actual_gates)
        extra_selected = sorted(selected - expected_valid)
        if missing: errors.append(f"missing required patterns: {missing}")
        if forbidden_hits: errors.append(f"forbidden patterns selected: {forbidden_hits}")
        if missing_gates: errors.append(f"missing gates: {missing_gates}")
        if not c_ok: errors.append(f"complexity {spec.complexity_level} not in {case['complexity']}")
        if extra_selected: errors.append(f"unexpected selected patterns: {extra_selected}")

        report.append({
            "id": case["id"],
            "input": case["input"],
            "selected": sorted(selected),
            "required": sorted(required),
            "allowed": sorted(allowed),
            "forbidden": sorted(forbidden),
            "gates": sorted(actual_gates),
            "complexity": spec.complexity_level,
            "complexity_score": spec.complexity_score,
            "errors": errors,
            "pass": not errors,
        })

    precision = selected_valid / selected_total if selected_total else 1.0
    recall = required_hit / required_total if required_total else 1.0
    over = forbidden_selected / len(cases)
    gate_recall = gate_hit / gate_total if gate_total else 1.0
    c_acc = complexity_hit / len(cases)
    case_pass = sum(r["pass"] for r in report) / len(report)

    metrics = {
        "routing_precision": round(precision, 4),
        "routing_recall": round(recall, 4),
        "overengineering_rate": round(over, 4),
        "gate_recall": round(gate_recall, 4),
        "complexity_accuracy": round(c_acc, 4),
        "case_pass_rate": round(case_pass, 4),
        "cases": len(cases),
    }

    out = {"metrics": metrics, "cases": report}
    (ROOT / "benchmark_report.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    md = [
        "# Router Harness v0.2.2 — Benchmark Report",
        "",
        "## Metrics",
        "",
    ]
    for k, v in metrics.items():
        md.append(f"- **{k}**: {v}")
    md += ["", "## Case results", ""]
    for r in report:
        mark = "PASS" if r["pass"] else "FAIL"
        md.append(f"### {r['id']} — {mark}")
        md.append(f"- Selected: {', '.join(r['selected']) or 'none'}")
        md.append(f"- Complexity: {r['complexity']} ({r['complexity_score']})")
        md.append(f"- Gates: {', '.join(r['gates']) or 'none'}")
        if r["errors"]:
            for e in r["errors"]:
                md.append(f"- Error: {e}")
        md.append("")
    (ROOT / "benchmark_report.md").write_text("\n".join(md), encoding="utf-8")

    return out


if __name__ == "__main__":
    out = evaluate()
    print(json.dumps(out["metrics"], indent=2))
    failed = [c for c in out["cases"] if not c["pass"]]
    print(f"failed_cases={len(failed)}")
    for c in failed:
        print(c["id"], "=>", "; ".join(c["errors"]))
