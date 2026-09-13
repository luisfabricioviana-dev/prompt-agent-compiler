from v029_runtime import NormalizedTask

class SemanticInterpreter:
    def __init__(self, provider):
        self.provider = provider

    def interpret(self, request):
        raw = self.provider.interpret(request)
        return NormalizedTask(
            raw['intent'],
            raw['objective'],
            raw['task_mode'],
            raw.get('evidence_required', False),
            raw.get('material_ambiguity', False),
        )
