from __future__ import annotations
from typing import Protocol
from normalized_task import NormalizedTask
from semantic_contract import validate_task
from policy_v0_2_7 import compile_semantic_task


class SemanticInterpreterProvider(Protocol):
    def interpret(self, request: str) -> NormalizedTask: ...


def compile_request(request: str, provider: SemanticInterpreterProvider):
    task=provider.interpret(request)
    if task.raw_request != request:
        task.raw_request=request
    validate_task(task)
    return compile_semantic_task(task)
