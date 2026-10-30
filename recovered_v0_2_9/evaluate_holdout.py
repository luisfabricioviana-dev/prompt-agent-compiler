
from __future__ import annotations
import json
from pathlib import Path
from router import compile_request
from models import PatternStatus

ROOT = Path(__file__).parent

def evaluate():
    cases = json.loads((ROOT / "holdout_cases_v0_2_3.json").read_text(encoding="utf-8"))
    report = []

    required_total = required_hit = 0
    selected_total = selected_valid = 0
    forbidden_selected = 0
    gate_total = gate_hit = 0
    complexity_hit = 0

    by_category = {}

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
        unexpected = sorted(selected - expected_valid)

        if missing: errors.append(f"missing required patterns: {missing}")
        if forbidden_hits: errors.append(f"forbidden patterns selected: {forbidden_hits}")
        if missing_gates: errors.append(f"missing gates: {missing_gates}")
        if not c_ok: errors.append(f"complexity {spec.complexity_level} not in {case['complexity']}")
        if unexpected: errors.append(f"unexpected selected patterns: {unexpected}")

        passed = not errors
        report.append({
            "id": case["id"],
            "category": case["category"],
            "input": case["input"],
            "selected": sorted(selected),
            "required": sorted(required),
            "allowed": sorted(allowed),
            "forbidden": sorted(forbidden),
            "gates": sorted(actual_gates),
            "expected_gates": sorted(expected_gates),
            "complexity": spec.complexity_level,
            "complexity_score": spec.complexity_score,
            "errors": errors,
            "pass": passed,
        })
        by_category.setdefault(case["category"], {"total":0,"pass":0})
        by_category[case["category"]]["total"] += 1
        by_category[case["category"]]["pass"] += int(passed)

    metrics = {
        "routing_precision": round(selected_valid / selected_total, 4) if selected_total else 1.0,
        "routing_recall": round(required_hit / required_total, 4) if required_total else 1.0,
        "overengineering_rate": round(forbidden_selected / len(cases), 4),
        "gate_recall": round(gate_hit / gate_total, 4) if gate_total else 1.0,
        "complexity_accuracy": round(complexity_hit / len(cases), 4),
        "case_pass_rate": round(sum(r["pass"] for r in report) / len(report), 4),
        "cases": len(cases),
    }

    for k,v in by_category.items():
        v["pass_rate"] = round(v["pass"]/v["total"],4)

    out = {
        "suite":"BLIND_HOLDOUT_v0.2.3",
        "frozen": True,
        "rule_change_after_observation": False,
        "metrics": metrics,
        "by_category": by_category,
        "cases": report,
    }
    (ROOT / "holdout_report_v0_2_3.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    md = [
        "# PROMPT & AGENT COMPILER — Blind Holdout Report v0.2.3",
        "",
        "> Frozen holdout. This suite was evaluated against the v0.2.2 Router without post-observation rule changes.",
        "",
        "## Metrics",
        "",
    ]
    for k,v in metrics.items():
        md.append(f"- **{k}**: {v}")
    md += ["", "## Failures", ""]
    failures = [r for r in report if not r["pass"]]
    if not failures:
        md.append("No failures.")
    for r in failures:
        md.append(f"### {r['id']} — {r['category']}")
        md.append(f"- Input: {r['input']}")
        md.append(f"- Selected: {', '.join(r['selected']) or 'none'}")
        md.append(f"- Complexity: {r['complexity']} ({r['complexity_score']})")
        for e in r["errors"]:
            md.append(f"- Error: {e}")
        md.append("")
    md += ["", "## Passed cases", ""]
    for r in report:
        if r["pass"]:
            md.append(f"- {r['id']} — {r['category']}")
    (ROOT / "holdout_report_v0_2_3.md").write_text("\n".join(md), encoding="utf-8")
    return out

if __name__ == "__main__":
    out = evaluate()
    print(json.dumps(out["metrics"], indent=2))
    failures = [c for c in out["cases"] if not c["pass"]]
    print(f"failed_cases={len(failures)}")
    for c in failures:
        print(c["id"], "=>", "; ".join(c["errors"]))
