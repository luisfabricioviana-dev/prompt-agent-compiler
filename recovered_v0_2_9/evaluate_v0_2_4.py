from __future__ import annotations
import json
from pathlib import Path
from policy_router import compile_request
from models import PatternStatus

ROOT = Path(__file__).parent


def eval_cases(cases):
    report=[]
    required_total=required_hit=selected_total=selected_valid=forbidden_selected=gate_total=gate_hit=complexity_hit=0
    for case in cases:
        spec=compile_request(case['input'])
        selected={pid for pid,d in spec.patterns.items() if d.status != PatternStatus.REJECTED}
        required=set(case.get('required',[])); allowed=set(case.get('allowed',[])); forbidden=set(case.get('forbidden',[]))
        valid=required|allowed
        required_total+=len(required); required_hit+=len(required&selected)
        selected_total+=len(selected); selected_valid+=len(selected&valid)
        forbidden_selected+=len(forbidden&selected)
        actual_gates={g.gate_id for g in spec.quality_gates}; expected_gates=set(case.get('gates',[]))
        gate_total+=len(expected_gates); gate_hit+=len(expected_gates&actual_gates)
        c_ok=spec.complexity_level in set(case.get('complexity',[])); complexity_hit+=int(c_ok)
        errors=[]
        if required-selected: errors.append(f"missing required patterns: {sorted(required-selected)}")
        if forbidden&selected: errors.append(f"forbidden patterns selected: {sorted(forbidden&selected)}")
        if expected_gates-actual_gates: errors.append(f"missing gates: {sorted(expected_gates-actual_gates)}")
        if not c_ok: errors.append(f"complexity {spec.complexity_level} not in {case.get('complexity')}")
        unexpected=selected-valid
        if unexpected: errors.append(f"unexpected selected patterns: {sorted(unexpected)}")
        report.append({'id':case['id'],'input':case['input'],'selected':sorted(selected),'gates':sorted(actual_gates),'complexity':spec.complexity_level,'score':spec.complexity_score,'errors':errors,'pass':not errors})
    n=len(cases)
    return {
      'metrics':{
        'routing_precision': round(selected_valid/selected_total,4) if selected_total else 1.0,
        'routing_recall': round(required_hit/required_total,4) if required_total else 1.0,
        'overengineering_rate': round(forbidden_selected/n,4),
        'gate_recall': round(gate_hit/gate_total,4) if gate_total else 1.0,
        'complexity_accuracy': round(complexity_hit/n,4),
        'case_pass_rate': round(sum(x['pass'] for x in report)/n,4),
        'cases': n,
      },
      'cases':report
    }


def main():
    golden=json.loads((ROOT/'benchmark_cases.json').read_text(encoding='utf-8'))
    dev=json.loads((ROOT/'holdout_cases_v0_2_3.json').read_text(encoding='utf-8'))
    # v0.2.3 was retired after one blind evaluation. It is now explicitly development data.
    out={'golden':eval_cases(golden),'retired_holdout_as_development':eval_cases(dev),'combined':eval_cases(golden+dev)}
    (ROOT/'development_report_v0_2_4.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    lines=['# Development Report v0.2.4','', '> Includes the original golden set and the retired v0.2.3 holdout, now used only as development data.','']
    for section in ('golden','retired_holdout_as_development','combined'):
        lines += [f'## {section}', '']
        for k,v in out[section]['metrics'].items(): lines.append(f'- **{k}**: {v}')
        fails=[x for x in out[section]['cases'] if not x['pass']]
        lines.append(f'- **failed_cases**: {len(fails)}')
        lines.append('')
        for x in fails:
            lines.append(f"### {x['id']} — FAIL")
            for e in x['errors']: lines.append(f'- {e}')
            lines.append('')
    (ROOT/'development_report_v0_2_4.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps(out['combined']['metrics'],indent=2))
    fails=[x for x in out['combined']['cases'] if not x['pass']]
    print('failed_cases=',len(fails))
    for x in fails: print(x['id'],'=>','; '.join(x['errors']))

if __name__=='__main__': main()
