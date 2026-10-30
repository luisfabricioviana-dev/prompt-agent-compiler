from __future__ import annotations
import hashlib, json
from pathlib import Path
ROOT=Path(__file__).parent
MANIFEST=ROOT/'FREEZE_MANIFEST_v0_2_9.json'

def sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()

def create_manifest():
    names=[
        'blind_holdout_v0_2_9.json',
        'semantic_interpreter_prompt_v0_2_7.md',
        'semantic_provider_schema_v0_2_7.json',
        'openai_responses_semantic_provider.py',
        'semantic_contract.py',
        'normalized_task.py',
        'policy_v0_2_7.py',
        'semantic_error_taxonomy_v0_2_8.py',
        'end_to_end_decomposition_v0_2_8.py',
        'model_eval_runner_v0_2_8.py',
        'promotion_gate_v0_2_9.py',
        'holdout_evaluator_v0_2_9.py',
    ]
    files={n:sha256(ROOT/n) for n in names}
    data={'version':'0.2.9','frozen':True,'algorithm':'sha256','files':files}
    MANIFEST.write_text(json.dumps(data,indent=2),encoding='utf-8')
    return data

def verify_freeze():
    data=json.loads(MANIFEST.read_text(encoding='utf-8'))
    drift=[]
    for n,expected in data['files'].items():
        p=ROOT/n
        actual=sha256(p) if p.exists() else None
        if actual!=expected: drift.append({'file':n,'expected':expected,'actual':actual})
    return {'valid':not drift,'drift':drift,'checked':len(data['files'])}

if __name__=='__main__':
    if not MANIFEST.exists(): create_manifest()
    print(json.dumps(verify_freeze(),indent=2))
