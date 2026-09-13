FAILURE_CLASSES = ('SEMANTIC','POLICY','EXECUTION','VALIDATION','TOOL','PROVIDER','DATA','RENDER')

def classify_failure(semantics_correct, route_correct, execution_correct, output_valid, stage_failure=None):
    if not semantics_correct:
        return 'SEMANTIC'
    if not route_correct:
        return 'POLICY'
    if stage_failure in ('TOOL','PROVIDER','DATA','RENDER'):
        return stage_failure
    if not execution_correct:
        return 'EXECUTION'
    if not output_valid:
        return 'VALIDATION'
    return None
