from __future__ import annotations
import argparse, json
from pathlib import Path
from collections import Counter
from repair_router_v0_2_8 import plan_repairs


def build_markdown(report: dict) -> str:
    lines=["# Semantic Model Error Report v0.2.8","","## Stage metrics",""]
    for k,v in report.get("stage_metrics",{}).items(): lines.append(f"- **{k}**: {v}")
    lines += ["","## Errors by class",""]
    counts=report.get("error_counts",{})
    if not counts: lines.append("No classified errors.")
    for k,v in sorted(counts.items(), key=lambda x:(-x[1],x[0])): lines.append(f"- **{k}**: {v}")
    lines += ["","## Errors by owner",""]
    for k,v in sorted(report.get("owner_counts",{}).items(), key=lambda x:(-x[1],x[0])): lines.append(f"- **{k}**: {v}")
    causal=[]
    for d in report.get("details",[]):
        causal.extend([e for e in d.get("errors",[]) if e.get("causal",True) and e.get("severity","error") in {"error","critical"}])
    repair=plan_repairs(causal)
    lines += ["","## Minimum repair plan","",f"- **minimum_scope**: {repair['minimum_scope']}",f"- **components_to_change**: {', '.join(repair['components_to_change']) or 'none'}"]
    for a in repair.get("actions",[]): lines.append(f"- **{a['component']}**: {a['guidance']}")
    lines += ["","## Failing cases",""]
    failed=0
    for d in report.get("details",[]):
        blocking=[e for e in d.get("errors",[]) if e.get("causal",True) and e.get("severity","error") in {"error","critical"}]
        if not blocking: continue
        failed+=1; lines.append(f"### {d['id']}")
        lines.append(f"- Request: {d.get('request','')}")
        for e in blocking: lines.append(f"- `{e['code']}` [{e['owner']}]: {e['detail']}")
        lines.append("")
    if not failed: lines.append("No blocking causal failures.")
    return "\n".join(lines)


def main():
    ap=argparse.ArgumentParser(); ap.add_argument("report"); ap.add_argument("--out",default=None); args=ap.parse_args()
    p=Path(args.report); report=json.loads(p.read_text(encoding="utf-8")); out=Path(args.out) if args.out else p.with_suffix(".md")
    out.write_text(build_markdown(report),encoding="utf-8"); print(out)

if __name__=="__main__": main()
