from __future__ import annotations
import json
from pathlib import Path
from normalized_task import NormalizedTask
from policy_v0_2_6 import compile_semantic_task
from models import PatternStatus

ROOT=Path(__file__).parent

def task_from_case(case):
    d={
      'raw_request':f"oracle:{case['id']}",
      'actions':set(), 'preservation':set(), 'performance_dimensions':set(), 'evidence_policy':set(),
      'ui_requirements':set(), 'architecture':set(), 'external_state':set(), 'execution':set(),
      'capabilities':set(), 'risks':{}, 'feature_evidence':{}, 'unknowns':[], 'contradictions':[]
    }
    for k,v in case.get('task',{}).items():
        d[k]=set(v) if k in {'actions','preservation','performance_dimensions','evidence_policy','ui_requirements','architecture','external_state','execution','capabilities'} else v
    return NormalizedTask(**d)

def evaluate():
    cases=json.loads((ROOT/'semantic_oracle_cases_v0_2_6.json').read_text())
    rows=[]; rt=rh=st=sv=fh=gt=gh=ch=0
    for c in cases:
        s=compile_semantic_task(task_from_case(c))
        selected={p for p,d in s.patterns.items() if d.status != PatternStatus.REJECTED}
        req=set(c['required']); allow=set(c['allowed']); forbid=set(c['forbidden']); valid=req|allow
        rt+=len(req); rh+=len(req&selected); st+=len(selected); sv+=len(selected&valid); fh+=len(forbid&selected)
        actual={g.gate_id for g in s.quality_gates}; exp=set(c['gates']); gt+=len(exp); gh+=len(exp&actual)
        cok=s.complexity_level in set(c['complexity']); ch+=int(cok)
        errs=[]
        if req-selected: errs.append(f"missing patterns {sorted(req-selected)}")
        if forbid&selected: errs.append(f"forbidden selected {sorted(forbid&selected)}")
        if exp-actual: errs.append(f"missing gates {sorted(exp-actual)}")
        if not cok: errs.append(f"complexity {s.complexity_level} not in {c['complexity']}")
        unexpected=selected-valid
        if unexpected: errs.append(f"unexpected selected {sorted(unexpected)}")
        rows.append({'id':c['id'],'pass':not errs,'errors':errs,'selected':sorted(selected),'gates':sorted(actual),'complexity':s.complexity_level})
    n=len(cases)
    metrics={'routing_precision':round(sv/st,4) if st else 1.0,'routing_recall':round(rh/rt,4) if rt else 1.0,'overengineering_rate':round(fh/n,4),'gate_recall':round(gh/gt,4) if gt else 1.0,'complexity_accuracy':round(ch/n,4),'case_pass_rate':round(sum(r['pass'] for r in rows)/n,4),'cases':n}
    out={'layer':'DETERMINISTIC_POLICY_ONLY','semantic_input':'ORACLE_NORMALIZED_TASK','metrics':metrics,'cases':rows}
    (ROOT/'oracle_policy_report_v0_2_6.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
    lines=['# Oracle Policy Report v0.2.6','', '> This benchmark bypasses natural-language interpretation. It tests only NormalizedTask → ExecutionSpec.','']+[f'- **{k}**: {v}' for k,v in metrics.items()]+['','## Failures','']
    for r in rows:
        if not r['pass']:
            lines.append(f"### {r['id']}")
            for e in r['errors']: lines.append(f'- {e}')
    (ROOT/'oracle_policy_report_v0_2_6.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps(metrics,indent=2))
    for r in rows:
        if not r['pass']: print(r['id'],r['errors'])

if __name__=='__main__': evaluate()
