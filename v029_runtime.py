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


class NormalizedTask:
    def __init__(self, intent, objective, task_mode, evidence_required=False, material_ambiguity=False):
        if task_mode not in TASK_MODES:
            raise ValueError('invalid task_mode')
        if not intent.strip() or not objective.strip():
            raise ValueError('intent and objective are required')
        self.intent = intent.strip()
        self.objective = objective.strip()
        self.task_mode = task_mode
        self.evidence_required = bool(evidence_required)
        self.material_ambiguity = bool(material_ambiguity)


class ExecutionSpec:
    def __init__(self, route, task, require_eval=True, require_grounding=False):
        self.route = route
        self.task = task
        self.require_eval = require_eval
        self.require_grounding = require_grounding


class PolicyRouter:
    def route(self, task):
        if task.material_ambiguity:
            return ExecutionSpec('CLARIFY', task, require_eval=False)
        if task.evidence_required:
            return ExecutionSpec('GROUNDED_EXECUTION', task, require_grounding=True)
        routes = {
            'EXPLORE': 'DIVERGENT_PLANNER',
            'SELECT': 'DECISION_ROUTER',
            'PLAN': 'PLANNER',
            'EXECUTE': 'EXECUTOR',
            'VALIDATE': 'VALIDATOR',
            'REPAIR': 'REPAIR_ROUTER',
        }
        return ExecutionSpec(routes.get(task.task_mode, 'DIRECT_EXECUTION'), task)
