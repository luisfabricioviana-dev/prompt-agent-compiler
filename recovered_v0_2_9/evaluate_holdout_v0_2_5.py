from __future__ import annotations
import json
from pathlib import Path
from policy_router import compile_request
from models import PatternStatus

ROOT=Path(__file__).parent

def evaluate():
    cases=json.loads((ROOT/'holdout_cases_v0_2_5.json').read_text(encoding='utf-8'))
    report=[]; req_t=req_h=sel_t=sel_v=forbid_h=gate_t=gate_h=c_h=0
    for c in cases:
        spec=compile_request(c['input'])
        selected={p for p,d in spec.patterns.items() if d.status != PatternStatus.REJECTED}
        req=set(c['required']); allow=set(c['allowed']); forbid=set(c['forbidden']); valid=req|allow
        req_t+=len(req); req_h+=len(req&selected); sel_t+=len(selected); sel_v+=len(selected&valid); forbid_h+=len(forbid&selected)
        actual_g={g.gate_id for g in spec.quality_gates}; exp_g=set(c['gates']); gate_t+=len(exp_g); gate_h+=len(exp_g&actual_g)
        cok=spec.complexity_level in set(c['complexity']); c_h+=int(cok)
        errors=[]
        if req-selected: errors.append(f"missing required patterns: {sorted(req-selected)}")
        if forbid&selected: errors.append(f"forbidden patterns selected: {sorted(forbid&selected)}")
        if exp_g-actual_g: errors.append(f"missing gates: {sorted(exp_g-actual_g)}")
        if not cok: errors.append(f"complexity {spec.complexity_level} not in {c['complexity']}")
        unexpected=selected-valid
        if unexpected: errors.append(f"unexpected selected patterns: {sorted(unexpected)}")
        report.append({'id':c['id'],'category':c['category'],'input':c['input'],'selected':sorted(selected),'gates':sorted(actual_g),'complexity':spec.complexity_level,'score':spec.complexity_score,'errors':errors,'pass':not errors})
    n=len(cases)
    metrics={
      'routing_precision':round(sel_v/sel_t,4) if sel_t else 1.0,
      'routing_recall':round(req_h/req_t,4) if req_t else 1.0,
      'overengineering_rate':round(forbid_h/n,4),
      'gate_recall':round(gate_h/gate_t,4) if gate_t else 1.0,
      'complexity_accuracy':round(c_h/n,4),
      'case_pass_rate':round(sum(x['pass'] for x in report)/n,4),
      'cases':n,
    }
    out={'suite':'UNSEEN_HOLDOUT_v0.2.5','router_version':'v0.2.4','frozen_before_evaluation':True,'post_observation_tuning_allowed':False,'metrics':metrics,'cases':report}
    (ROOT/'holdout_report_v0_2_5.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    lines=['# Blind Holdout v0.2.5 — Router v0.2.4','', '> Frozen before the first evaluation. Do not tune Router v0.2.4 against this suite.','', '## Metrics','']
    for k,v in metrics.items(): lines.append(f'- **{k}**: {v}')
    fails=[x for x in report if not x['pass']]
    lines += ['', f'## Failures ({len(fails)})','']
    for x in fails:
        lines.append(f"### {x['id']} — {x['category']}")
        lines.append(f"- Input: {x['input']}")
        lines.append(f"- Selected: {', '.join(x['selected']) or 'none'}")
        lines.append(f"- Complexity: {x['complexity']} ({x['score']})")
        for e in x['errors']: lines.append(f'- Error: {e}')
        lines.append('')
    (ROOT/'holdout_report_v0_2_5.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps(metrics,indent=2))
    print('failed_cases=',len(fails))
    for x in fails: print(x['id'],'=>','; '.join(x['errors']))

if __name__=='__main__': evaluate()
