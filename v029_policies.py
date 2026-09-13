def detect_constraint_conflict(constraints):
    normalized = [c.strip().lower() for c in constraints or []]
    exhaustive = any('exhaustive' in c or 'complete' in c for c in normalized)
    ultra_short = any('30 words' in c or '50 words' in c for c in normalized)
    return exhaustive and ultra_short


def demonstration_policy(examples):
    examples = list(examples or [])
    return {'count': len(examples), 'use': 'MINIMUM_REPRESENTATIVE_SET'}


def role_capability_check(role, claimed_capability):
    return {'role': role, 'capability_verified': bool(claimed_capability), 'role_is_not_authority': True}


def rationale_mode(checkable_steps=False, evidence=False):
    if evidence:
        return 'EVIDENCE_BOUND_RATIONALE'
    if checkable_steps:
        return 'CHECKABLE_STEPS'
    return 'CONCISE_RATIONALE'


def ideation_pipeline(candidates):
    unique = []
    seen = set()
    for candidate in candidates or []:
        key = candidate.strip().lower()
        if key and key not in seen:
            seen.add(key)
            unique.append(candidate)
    return unique


def production_prompt_ready(eval_defined, fixtures_defined, versioned):
    return bool(eval_defined and fixtures_defined and versioned)


def duplicate_evidence(content_id, seen_content_ids):
    return content_id in set(seen_content_ids or [])


class ModelEvalRunner:
    def run(self, value, checks):
        results = tuple(bool(check(value)) for check in checks)
        return {'passed': all(results), 'results': results}
