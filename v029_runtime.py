TASK_MODES = ('GENERATE','EXPLORE','EXPLAIN','TRANSFORM','SUMMARIZE','CLASSIFY','EXTRACT','COMPARE','SELECT','PLAN','ASSESS','EXECUTE','VALIDATE','REPAIR')


def merge_task_state(current, delta):
    merged = dict(current or {})
    for key, value in (delta or {}).items():
        if value is None:
            merged.pop(key, None)
        else:
            merged[key] = value
    return merged


def classify_ambiguity(material, resolvable_by_tool=False, safe_default=False):
    if not material:
        return 'SAFE_INFER'
    if resolvable_by_tool:
        return 'RESOLVE_WITH_TOOL'
    if safe_default:
        return 'ASSUME_AND_DISCLOSE'
    return 'CLARIFY'


def classify_solvability(requires_context=False, requires_evidence=False, requires_tool=False, unsafe=False):
    if unsafe:
        return 'UNSAFE_TO_PERSONALIZE'
    if requires_tool:
        return 'REQUIRES_TOOL'
    if requires_evidence:
        return 'REQUIRES_EVIDENCE'
    if requires_context:
        return 'REQUIRES_CONTEXT'
    return 'SOLVABLE_NOW'
