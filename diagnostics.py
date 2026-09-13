def classify_failure(semantics_correct, route_correct, execution_correct, output_valid):
    if not semantics_correct:
        return 'SEMANTIC'
    if not route_correct:
        return 'POLICY'
    if not execution_correct:
        return 'EXECUTION'
    if not output_valid:
        return 'VALIDATION'
    return None
