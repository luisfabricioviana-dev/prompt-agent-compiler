from semantic_interpreter import SemanticInterpreter
from v029_runtime import PolicyRouter

class CompilerRuntime:
    def __init__(self, provider):
        self.interpreter = SemanticInterpreter(provider)
        self.router = PolicyRouter()

    def compile(self, request):
        task = self.interpreter.interpret(request)
        return self.router.route(task)
