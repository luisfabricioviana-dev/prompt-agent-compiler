def repair_scope(failure_class):
    scopes = {
        'SEMANTIC': 'REINTERPRET_REQUEST',
        'POLICY': 'REPAIR_POLICY_ROUTE',
        'EXECUTION': 'REPAIR_EXECUTION_SPEC',
        'VALIDATION': 'REPAIR_OUTPUT',
        'TOOL': 'REPAIR_TOOL_STEP',
        'PROVIDER': 'REPAIR_PROVIDER_STEP',
        'DATA': 'REPAIR_DATA_INPUT',
        'RENDER': 'REPAIR_RENDER_ONLY',
    }
    return scopes[failure_class]
