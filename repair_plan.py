def repair_scope(failure_class):
    scopes = {
        'SEMANTIC': 'REINTERPRET_REQUEST',
        'POLICY': 'REPAIR_POLICY_ROUTE',
        'EXECUTION': 'REPAIR_EXECUTION_SPEC',
        'VALIDATION': 'REPAIR_OUTPUT',
    }
    return scopes[failure_class]
